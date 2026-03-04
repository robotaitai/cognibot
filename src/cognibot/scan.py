from __future__ import annotations
from pathlib import Path
import json
import xml.etree.ElementTree as ET

from .models import Snapshot, PackageInfo
from .util import utc_now, get_git_info, make_snapshot_id, is_ignored_path, resolve_out_dir

def _find_packages(repo: Path) -> list[PackageInfo]:
    pkgs: list[PackageInfo] = []
    for pkg_xml in repo.rglob("package.xml"):
        if is_ignored_path(pkg_xml):
            continue
        try:
            tree = ET.parse(pkg_xml)
            root = tree.getroot()
            name = (root.findtext("name") or pkg_xml.parent.name).strip()

            depends: list[str] = []
            for tag in ["depend", "build_depend", "exec_depend", "buildtool_depend", "test_depend"]:
                for d in root.findall(tag):
                    if d.text and d.text.strip():
                        depends.append(d.text.strip())

            build_type = None
            export = root.find("export")
            if export is not None:
                bt = export.find("build_type")
                if bt is not None and bt.text and bt.text.strip():
                    build_type = bt.text.strip()

            pkgs.append(
                PackageInfo(
                    name=name,
                    path=str(pkg_xml.parent.relative_to(repo)),
                    build_type=build_type,
                    depends=sorted(set(depends)),
                )
            )
        except Exception:
            continue

    pkgs.sort(key=lambda p: p.name.lower())
    return pkgs

def _find_launch_and_params(repo: Path) -> tuple[list[str], list[str]]:
    launch: set[str] = set()
    params: set[str] = set()

    for p in repo.rglob("*"):
        if is_ignored_path(p):
            continue
        if not p.is_file():
            continue

        if p.name.endswith((".launch.py", ".launch.xml")):
            launch.add(str(p.relative_to(repo)))
        else:
            if "launch" in p.parts and p.suffix in [".py", ".xml"]:
                launch.add(str(p.relative_to(repo)))

        if p.suffix in [".yaml", ".yml"] and any(x in p.parts for x in ["config", "params", "launch"]):
            params.add(str(p.relative_to(repo)))

    return sorted(launch), sorted(params)

def _find_interfaces(repo: Path) -> dict[str, list[str]]:
    out: dict[str, set[str]] = {"msg": set(), "srv": set(), "action": set()}
    for kind in out.keys():
        for f in repo.rglob(f"{kind}/*"):
            if is_ignored_path(f) or not f.is_file():
                continue
            out[kind].add(str(f.relative_to(repo)))

    return {k: sorted(v) for k, v in out.items()}

def _write_brain_md(snapshot: Snapshot, dest: Path) -> None:
    lines: list[str] = []
    lines.append("# cognibot brain")
    lines.append("")
    lines.append("## provenance")
    lines.append(f"- snapshot_id: `{snapshot.snapshot_id}`")
    lines.append(f"- created_at: `{snapshot.created_at.isoformat()}`")
    lines.append(f"- commit: `{snapshot.git_commit or 'unknown'}`")
    lines.append(f"- dirty: `{snapshot.git_dirty}`")
    lines.append(f"- repo_root: `{snapshot.repo_root}`")
    lines.append("")
    lines.append("## packages")
    if not snapshot.packages:
        lines.append("- (none found)")
    for p in snapshot.packages:
        bt = f" ({p.build_type})" if p.build_type else ""
        lines.append(f"- `{p.name}`{bt} — `{p.path}`")
        if p.depends:
            deps = ", ".join(p.depends[:25])
            suffix = " …" if len(p.depends) > 25 else ""
            lines.append(f"  - deps: {deps}{suffix}")
    lines.append("")
    lines.append("## launch entry points")
    if not snapshot.launch_files:
        lines.append("- (none found)")
    for lf in snapshot.launch_files[:250]:
        lines.append(f"- `{lf}`")
    if len(snapshot.launch_files) > 250:
        lines.append(f"- … ({len(snapshot.launch_files) - 250} more)")
    lines.append("")
    lines.append("## params and config")
    if not snapshot.param_files:
        lines.append("- (none found)")
    for pf in snapshot.param_files[:250]:
        lines.append(f"- `{pf}`")
    if len(snapshot.param_files) > 250:
        lines.append(f"- … ({len(snapshot.param_files) - 250} more)")
    lines.append("")
    lines.append("## interfaces")
    for k in ["msg", "srv", "action"]:
        lines.append(f"### {k}")
        vals = snapshot.interfaces.get(k, [])
        if not vals:
            lines.append("- (none found)")
        for v in vals[:250]:
            lines.append(f"- `{v}`")
        if len(vals) > 250:
            lines.append(f"- … ({len(vals) - 250} more)")
        lines.append("")
    dest.write_text("\n".join(lines), encoding="utf-8")

def scan_repo(repo: Path, out: Path | None = None) -> Path:
    repo = repo.resolve()
    out_dir = resolve_out_dir(repo, out).resolve()

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "snapshots").mkdir(exist_ok=True)
    (out_dir / "ui").mkdir(exist_ok=True)

    git = get_git_info(repo)
    snapshot_id = make_snapshot_id(git)
    snap_dir = out_dir / "snapshots" / snapshot_id
    snap_dir.mkdir(parents=True, exist_ok=True)

    packages = _find_packages(repo)
    launch_files, param_files = _find_launch_and_params(repo)
    interfaces = _find_interfaces(repo)

    snapshot = Snapshot(
        snapshot_id=snapshot_id,
        created_at=utc_now(),
        repo_root=str(repo),
        git_commit=git.commit,
        git_dirty=git.dirty,
        packages=packages,
        launch_files=launch_files,
        param_files=param_files,
        interfaces=interfaces,
    )

    (snap_dir / "snapshot.json").write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    _write_brain_md(snapshot, snap_dir / "brain.md")

    (out_dir / "index.json").write_text(json.dumps({"latest_snapshot_id": snapshot_id}, indent=2), encoding="utf-8")
    return out_dir
