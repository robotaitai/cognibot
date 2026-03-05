from __future__ import annotations

from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET

from .models import Snapshot, PackageInfo, TopicInfo, ServiceInfo
from .knowledge import ensure_knowledge, knowledge_path
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

            rel_path = str(pkg_xml.parent.relative_to(repo))
            is_vendor = _is_vendor_package(rel_path)

            topics, services = [], []
            if not is_vendor:
                topics, services = _extract_ros_apis(pkg_xml.parent, repo)

            pkgs.append(
                PackageInfo(
                    name=name,
                    path=rel_path,
                    build_type=build_type,
                    depends=sorted(set(depends)),
                    is_vendor=is_vendor,
                    topics=topics,
                    services=services,
                )
            )
        except Exception:
            continue

    pkgs.sort(key=lambda p: (p.is_vendor, p.name.lower()))
    return pkgs


def _is_vendor_package(pkg_path: str) -> bool:
    """A package at src/<name> is user code; src/<vendor>/<name>/... is vendor."""
    parts = Path(pkg_path).parts
    if len(parts) >= 1 and parts[0] == "src":
        return len(parts) > 2
    return False


def _belongs_to_user_package(file_path: str, user_pkg_paths: list[str]) -> bool:
    """Check if a file path is under any user (non-vendor) package directory."""
    return any(file_path.startswith(pkg_path + "/") or file_path == pkg_path for pkg_path in user_pkg_paths)


# Regex patterns for ROS2 Python pub/sub/service extraction
_PY_PUB_RE = re.compile(
    r"""(?:self\.\w+\s*=\s*)?self\.create_publisher\(\s*(\w+)\s*,\s*['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_PY_SUB_RE = re.compile(
    r"""self\.create_subscription\(\s*(\w+)\s*,\s*['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_PY_SRV_RE = re.compile(
    r"""self\.create_service\(\s*(\w+)\s*,\s*['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_PY_CLI_RE = re.compile(
    r"""self\.create_client\(\s*(\w+)\s*,\s*['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_PY_CLASS_RE = re.compile(r"class\s+(\w+)\s*\(.*Node.*\)")

# Regex for C++ pub/sub/service
_CPP_PUB_RE = re.compile(
    r"""create_publisher<(\w+(?:::\w+)*)>\(\s*"([^"]+)"\s*""",
    re.MULTILINE,
)
_CPP_SUB_RE = re.compile(
    r"""create_subscription<(\w+(?:::\w+)*)>\(\s*"([^"]+)"\s*""",
    re.MULTILINE,
)
_CPP_SRV_RE = re.compile(
    r"""create_service<(\w+(?:::\w+)*)>\(\s*"([^"]+)"\s*""",
    re.MULTILINE,
)
_CPP_CLI_RE = re.compile(
    r"""create_client<(\w+(?:::\w+)*)>\(\s*"([^"]+)"\s*""",
    re.MULTILINE,
)


def _extract_ros_apis(pkg_dir: Path, repo: Path) -> tuple[list[TopicInfo], list[ServiceInfo]]:
    """Extract publisher/subscriber/service declarations from Python and C++ source."""
    topics: list[TopicInfo] = []
    services: list[ServiceInfo] = []

    for src_file in pkg_dir.rglob("*"):
        if not src_file.is_file() or is_ignored_path(src_file):
            continue

        rel_path = str(src_file.relative_to(repo))

        if src_file.suffix == ".py":
            try:
                text = src_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            cls_match = _PY_CLASS_RE.search(text)
            node_class = cls_match.group(1) if cls_match else None

            for msg_type, topic in _PY_PUB_RE.findall(text):
                topics.append(TopicInfo(topic=topic, msg_type=msg_type, direction="pub", source_file=rel_path, node_class=node_class))
            for msg_type, topic in _PY_SUB_RE.findall(text):
                topics.append(TopicInfo(topic=topic, msg_type=msg_type, direction="sub", source_file=rel_path, node_class=node_class))
            for srv_type, srv in _PY_SRV_RE.findall(text):
                services.append(ServiceInfo(service=srv, srv_type=srv_type, role="server", source_file=rel_path, node_class=node_class))
            for srv_type, srv in _PY_CLI_RE.findall(text):
                services.append(ServiceInfo(service=srv, srv_type=srv_type, role="client", source_file=rel_path, node_class=node_class))

        elif src_file.suffix in (".cpp", ".hpp", ".cc", ".h"):
            try:
                text = src_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for msg_type, topic in _CPP_PUB_RE.findall(text):
                topics.append(TopicInfo(topic=topic, msg_type=msg_type, direction="pub", source_file=rel_path))
            for msg_type, topic in _CPP_SUB_RE.findall(text):
                topics.append(TopicInfo(topic=topic, msg_type=msg_type, direction="sub", source_file=rel_path))
            for srv_type, srv in _CPP_SRV_RE.findall(text):
                services.append(ServiceInfo(service=srv, srv_type=srv_type, role="server", source_file=rel_path))
            for srv_type, srv in _CPP_CLI_RE.findall(text):
                services.append(ServiceInfo(service=srv, srv_type=srv_type, role="client", source_file=rel_path))

    # Deduplicate by (topic/service, direction/role) — same topic from multiple source files is one entry
    seen_topics: set[tuple[str, str, str]] = set()
    deduped_topics: list[TopicInfo] = []
    for t in topics:
        key = (t.topic, t.msg_type, t.direction)
        if key not in seen_topics:
            seen_topics.add(key)
            deduped_topics.append(t)

    seen_srvs: set[tuple[str, str, str]] = set()
    deduped_srvs: list[ServiceInfo] = []
    for s in services:
        key = (s.service, s.srv_type, s.role)
        if key not in seen_srvs:
            seen_srvs.add(key)
            deduped_srvs.append(s)

    return deduped_topics, deduped_srvs


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


def _write_brain_md(snapshot: Snapshot, dest: Path, prev_snapshot: Snapshot | None = None) -> None:
    user_pkgs = [p for p in snapshot.packages if not p.is_vendor]
    vendor_pkgs = [p for p in snapshot.packages if p.is_vendor]
    user_pkg_paths = [p.path for p in user_pkgs]
    user_launch = [lf for lf in snapshot.launch_files if _belongs_to_user_package(lf, user_pkg_paths)]
    user_params = [pf for pf in snapshot.param_files if _belongs_to_user_package(pf, user_pkg_paths)]

    lines: list[str] = []
    lines.append("# cognibot brain")
    lines.append("")

    # Provenance (compact)
    lines.append(f"> snapshot `{snapshot.snapshot_id}` | {snapshot.created_at.strftime('%Y-%m-%d %H:%M')} UTC")
    lines.append(f"> commit `{(snapshot.git_commit or 'unknown')[:12]}` {'(dirty)' if snapshot.git_dirty else ''}")
    lines.append("")

    # ── DIFF (what changed since last scan) ──
    if prev_snapshot:
        diff_lines = _compute_diff(prev_snapshot, snapshot)
        if diff_lines:
            lines.append("## what changed (since last scan)")
            lines.extend(diff_lines)
            lines.append("")

    # ── YOUR PACKAGES (the valuable stuff) ──
    lines.append(f"## your packages ({len(user_pkgs)})")
    if not user_pkgs:
        lines.append("- (none found)")
    for p in user_pkgs:
        bt = f" ({p.build_type})" if p.build_type else ""
        lines.append(f"### `{p.name}`{bt} — `{p.path}`")

        if p.topics:
            pubs = [t for t in p.topics if t.direction == "pub"]
            subs = [t for t in p.topics if t.direction == "sub"]
            if pubs:
                lines.append("  **publishes:**")
                for t in pubs:
                    cls = f" ({t.node_class})" if t.node_class else ""
                    lines.append(f"  - `{t.topic}` [{t.msg_type}]{cls}")
            if subs:
                lines.append("  **subscribes:**")
                for t in subs:
                    cls = f" ({t.node_class})" if t.node_class else ""
                    lines.append(f"  - `{t.topic}` [{t.msg_type}]{cls}")
        if p.services:
            servers = [s for s in p.services if s.role == "server"]
            clients = [s for s in p.services if s.role == "client"]
            if servers:
                lines.append("  **services:**")
                for s in servers:
                    lines.append(f"  - `{s.service}` [{s.srv_type}]")
            if clients:
                lines.append("  **service clients:**")
                for s in clients:
                    lines.append(f"  - `{s.service}` [{s.srv_type}]")

        if p.depends:
            user_deps = [d for d in p.depends if any(up.name == d for up in user_pkgs)]
            ros_deps = [d for d in p.depends if d not in user_deps and d not in ("ament_cmake", "ament_lint_auto", "ament_lint_common", "ament_copyright", "ament_flake8", "ament_pep257", "ament_cmake_pytest", "pytest")]
            if user_deps:
                lines.append(f"  internal deps: {', '.join(user_deps)}")
            if ros_deps:
                deps_str = ", ".join(ros_deps[:15])
                suffix = " ..." if len(ros_deps) > 15 else ""
                lines.append(f"  ros deps: {deps_str}{suffix}")
        lines.append("")

    # ── TOPIC WIRING MAP ──
    all_topics: dict[str, dict] = {}
    for p in user_pkgs:
        for t in p.topics:
            key = t.topic
            if key not in all_topics:
                all_topics[key] = {"msg_type": t.msg_type, "pubs": [], "subs": []}
            if t.direction == "pub":
                all_topics[key]["pubs"].append(p.name)
            else:
                all_topics[key]["subs"].append(p.name)
    for p in user_pkgs:
        for s in p.services:
            pass  # services handled separately

    if all_topics:
        lines.append("## topic wiring (your nodes)")
        lines.append("| topic | type | publishers | subscribers |")
        lines.append("|-------|------|-----------|-------------|")
        for topic_name in sorted(all_topics):
            info = all_topics[topic_name]
            pubs = ", ".join(sorted(set(info["pubs"]))) or "—"
            subs = ", ".join(sorted(set(info["subs"]))) or "—"
            lines.append(f"| `{topic_name}` | {info['msg_type']} | {pubs} | {subs} |")
        lines.append("")

    all_srvs: dict[str, dict] = {}
    for p in user_pkgs:
        for s in p.services:
            key = s.service
            if key not in all_srvs:
                all_srvs[key] = {"srv_type": s.srv_type, "servers": [], "clients": []}
            if s.role == "server":
                all_srvs[key]["servers"].append(p.name)
            else:
                all_srvs[key]["clients"].append(p.name)

    if all_srvs:
        lines.append("## service wiring (your nodes)")
        lines.append("| service | type | server | clients |")
        lines.append("|---------|------|--------|---------|")
        for srv_name in sorted(all_srvs):
            info = all_srvs[srv_name]
            servers = ", ".join(sorted(set(info["servers"]))) or "—"
            clients = ", ".join(sorted(set(info["clients"]))) or "—"
            lines.append(f"| `{srv_name}` | {info['srv_type']} | {servers} | {clients} |")
        lines.append("")

    # ── YOUR LAUNCH + PARAMS ──
    lines.append(f"## your launch files ({len(user_launch)})")
    for lf in user_launch:
        lines.append(f"- `{lf}`")
    lines.append("")

    lines.append(f"## your config/params ({len(user_params)})")
    for pf in user_params:
        lines.append(f"- `{pf}`")
    lines.append("")

    # ── CUSTOM INTERFACES ──
    lines.append("## interfaces")
    for k in ["msg", "srv", "action"]:
        vals = snapshot.interfaces.get(k, [])
        if vals:
            lines.append(f"### {k}")
            for v in vals[:100]:
                lines.append(f"- `{v}`")
    lines.append("")

    # ── VENDOR PACKAGES (collapsed reference) ──
    lines.append(f"## vendor packages ({len(vendor_pkgs)} — reference only)")
    vendor_groups: dict[str, list[str]] = {}
    for p in vendor_pkgs:
        parts = Path(p.path).parts
        group = parts[1] if len(parts) > 2 else parts[0]
        vendor_groups.setdefault(group, []).append(p.name)
    for group in sorted(vendor_groups):
        names = ", ".join(sorted(vendor_groups[group]))
        lines.append(f"- **{group}**: {names}")
    lines.append("")

    dest.write_text("\n".join(lines), encoding="utf-8")


def _compute_diff(prev: Snapshot, curr: Snapshot) -> list[str]:
    """Compare two snapshots and return human-readable diff lines."""
    lines: list[str] = []

    prev_pkg_names = {p.name for p in prev.packages}
    curr_pkg_names = {p.name for p in curr.packages}
    added_pkgs = curr_pkg_names - prev_pkg_names
    removed_pkgs = prev_pkg_names - curr_pkg_names
    if added_pkgs:
        lines.append(f"- **added packages**: {', '.join(sorted(added_pkgs))}")
    if removed_pkgs:
        lines.append(f"- **removed packages**: {', '.join(sorted(removed_pkgs))}")

    prev_launch = set(prev.launch_files)
    curr_launch = set(curr.launch_files)
    added_launch = curr_launch - prev_launch
    removed_launch = prev_launch - curr_launch
    if added_launch:
        for lf in sorted(added_launch):
            lines.append(f"- **new launch**: `{lf}`")
    if removed_launch:
        for lf in sorted(removed_launch):
            lines.append(f"- **removed launch**: `{lf}`")

    prev_params = set(prev.param_files)
    curr_params = set(curr.param_files)
    added_params = curr_params - prev_params
    removed_params = prev_params - curr_params
    if added_params:
        for pf in sorted(added_params):
            lines.append(f"- **new config**: `{pf}`")
    if removed_params:
        for pf in sorted(removed_params):
            lines.append(f"- **removed config**: `{pf}`")

    # Topic wiring changes (user packages only)
    prev_topics = {(t.topic, t.direction, p.name) for p in prev.packages if not p.is_vendor for t in p.topics}
    curr_topics = {(t.topic, t.direction, p.name) for p in curr.packages if not p.is_vendor for t in p.topics}
    for topic, direction, pkg in sorted(curr_topics - prev_topics):
        verb = "publishes" if direction == "pub" else "subscribes to"
        lines.append(f"- **new wiring**: `{pkg}` now {verb} `{topic}`")
    for topic, direction, pkg in sorted(prev_topics - curr_topics):
        verb = "published" if direction == "pub" else "subscribed to"
        lines.append(f"- **removed wiring**: `{pkg}` no longer {verb} `{topic}`")

    if not lines:
        lines.append("- no changes detected")
    return lines


def _load_prev_snapshot(out_dir: Path, current_id: str) -> Snapshot | None:
    """Load the most recent snapshot that isn't the current one, for diffing."""
    try:
        idx = _load_index(out_dir)
        for entry in reversed(idx.get("history", [])):
            sid = entry.get("snapshot_id", "")
            if sid and sid != current_id:
                snap_file = out_dir / "snapshots" / sid / "snapshot.json"
                if snap_file.exists():
                    return Snapshot.model_validate_json(snap_file.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def _load_index(out_dir: Path) -> dict:
    idx_path = out_dir / "index.json"
    if not idx_path.exists():
        return {"latest_snapshot_id": None, "history": []}
    try:
        return json.loads(idx_path.read_text(encoding="utf-8"))
    except Exception:
        return {"latest_snapshot_id": None, "history": []}


def _save_index(out_dir: Path, index: dict) -> None:
    (out_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")


def scan_repo(repo: Path, out: Path | None = None) -> Path:
    repo = repo.resolve()
    out_dir = resolve_out_dir(repo, out).resolve()

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "snapshots").mkdir(exist_ok=True)
    (out_dir / "ui").mkdir(exist_ok=True)
    ensure_knowledge(out_dir)

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

    # Load previous snapshot for diffing
    prev_snapshot = _load_prev_snapshot(out_dir, snapshot_id)

    (snap_dir / "snapshot.json").write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    _write_brain_md(snapshot, snap_dir / "brain.md", prev_snapshot)

    # Auto-generate architecture mermaid
    try:
        from .architecture import ArchitectureManager
        arch = ArchitectureManager(out_dir)
        arch.generate()
    except Exception:
        pass

    # Update index.json with history + value metrics
    brain_text = (snap_dir / "brain.md").read_text(encoding="utf-8")
    brain_bytes = len(brain_text.encode("utf-8"))
    brain_words = len(brain_text.split())
    brain_tokens_proxy = int(brain_words * 1.3)

    # Value metrics
    user_pkgs = [p for p in packages if not p.is_vendor]
    total_topics = sum(len(p.topics) for p in user_pkgs)
    total_services = sum(len(p.services) for p in user_pkgs)
    knowledge_entries = _count_knowledge_entries(out_dir)

    # Estimate repo size in tokens (rough: count all source lines in user pkgs)
    repo_source_lines = _count_source_lines(repo, [p.path for p in user_pkgs])
    repo_tokens_est = int(repo_source_lines * 1.3)

    index = _load_index(out_dir)
    index["latest_snapshot_id"] = snapshot_id
    history = index.get("history", [])
    entry = {
        "snapshot_id": snapshot_id,
        "created_at": snapshot.created_at.isoformat(),
        "git_commit": snapshot.git_commit,
        "git_dirty": snapshot.git_dirty,
        "packages": len(packages),
        "user_packages": len(user_pkgs),
        "vendor_packages": len(packages) - len(user_pkgs),
        "launch_files": len(launch_files),
        "param_files": len(param_files),
        "msg": len(interfaces.get("msg", [])),
        "srv": len(interfaces.get("srv", [])),
        "action": len(interfaces.get("action", [])),
        "topics_discovered": total_topics,
        "services_discovered": total_services,
        "brain_bytes": brain_bytes,
        "brain_words": brain_words,
        "brain_tokens_proxy": brain_tokens_proxy,
        "repo_source_lines": repo_source_lines,
        "repo_tokens_est": repo_tokens_est,
        "knowledge_entries": knowledge_entries,
        "compression_ratio": round(repo_tokens_est / max(brain_tokens_proxy, 1), 1),
    }

    if not history or history[-1].get("snapshot_id") != snapshot_id:
        history.append(entry)

    index["history"] = history[-100:]
    _save_index(out_dir, index)

    return out_dir


def _count_knowledge_entries(out_dir: Path) -> int:
    kp = knowledge_path(out_dir)
    if not kp.exists():
        return 0
    text = kp.read_text(encoding="utf-8")
    return sum(1 for line in text.splitlines() if line.strip().startswith("- ["))


def _count_source_lines(repo: Path, user_pkg_paths: list[str]) -> int:
    total = 0
    for pkg_path in user_pkg_paths:
        pkg_dir = repo / pkg_path
        if not pkg_dir.exists():
            continue
        for f in pkg_dir.rglob("*"):
            if not f.is_file() or is_ignored_path(f):
                continue
            if f.suffix in (".py", ".cpp", ".hpp", ".cc", ".h", ".xml", ".yaml", ".yml"):
                try:
                    total += len(f.read_text(encoding="utf-8", errors="ignore").splitlines())
                except Exception:
                    pass
    return total