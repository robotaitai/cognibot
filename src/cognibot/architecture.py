from __future__ import annotations

import shutil
import json
import datetime
from pathlib import Path

from .models import Snapshot


class ArchitectureManager:
    def __init__(self, out_dir: Path):
        self.out_dir = out_dir
        self.arch_dir = out_dir / "architecture"
        self.history_dir = self.arch_dir / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.history_index = self.arch_dir / "history.json"

    def generate(self) -> Path:
        """Auto-generate architecture.mmd from the latest snapshot's wiring data."""
        snap = self._load_latest_snapshot()
        if snap is None:
            raise RuntimeError("No snapshot found. Run `cognibot scan` first.")

        mmd = self._build_mermaid(snap)
        mmd_path = self.arch_dir / "architecture.mmd"
        mmd_path.write_text(mmd, encoding="utf-8")
        return mmd_path

    def _load_latest_snapshot(self) -> Snapshot | None:
        idx_path = self.out_dir / "index.json"
        if not idx_path.exists():
            return None
        try:
            idx = json.loads(idx_path.read_text(encoding="utf-8"))
            sid = idx.get("latest_snapshot_id")
            if not sid:
                return None
            snap_file = self.out_dir / "snapshots" / sid / "snapshot.json"
            if not snap_file.exists():
                return None
            return Snapshot.model_validate_json(snap_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _build_mermaid(self, snap: Snapshot) -> str:
        user_pkgs = [p for p in snap.packages if not p.is_vendor]

        # Collect all topic edges between different packages
        topic_edges: list[tuple[str, str, str, str]] = []   # (from, to, topic, msg_type)
        service_edges: list[tuple[str, str, str, str]] = []  # (client, server, srv, srv_type)

        # Build topic map: topic -> {pubs: [pkg], subs: [pkg]}
        topic_map: dict[str, dict] = {}
        for p in user_pkgs:
            for t in p.topics:
                if t.topic not in topic_map:
                    topic_map[t.topic] = {"msg_type": t.msg_type, "pubs": set(), "subs": set()}
                if t.direction == "pub":
                    topic_map[t.topic]["pubs"].add(p.name)
                else:
                    topic_map[t.topic]["subs"].add(p.name)

        for topic, info in topic_map.items():
            for pub in info["pubs"]:
                for sub in info["subs"]:
                    if pub != sub:
                        topic_edges.append((pub, sub, topic, info["msg_type"]))

        # Build service edges
        srv_map: dict[str, dict] = {}
        for p in user_pkgs:
            for s in p.services:
                if s.service not in srv_map:
                    srv_map[s.service] = {"srv_type": s.srv_type, "servers": set(), "clients": set()}
                if s.role == "server":
                    srv_map[s.service]["servers"].add(p.name)
                else:
                    srv_map[s.service]["clients"].add(p.name)

        for srv, info in srv_map.items():
            for client in info["clients"]:
                for server in info["servers"]:
                    if client != server:
                        service_edges.append((client, server, srv, info["srv_type"]))

        # Classify packages into layers
        layers = self._classify_layers(user_pkgs)

        lines = ["graph TB"]

        # Style definitions
        lines.append("")
        lines.append("    %% styles")
        lines.append("    classDef perception fill:#1a3a4a,stroke:#5ce0d6,color:#e0f0f0")
        lines.append("    classDef navigation fill:#1a2a4a,stroke:#7ba4f7,color:#d0e0ff")
        lines.append("    classDef hardware fill:#2a1a3a,stroke:#c084fc,color:#e0d0f0")
        lines.append("    classDef manipulation fill:#3a2a1a,stroke:#f7a55b,color:#f0e0d0")
        lines.append("    classDef infra fill:#1a1a2a,stroke:#6b7f94,color:#a0b0c0")
        lines.append("")

        # Subgraphs per layer
        for layer_name, pkg_names in layers.items():
            if not pkg_names:
                continue
            display_name = layer_name.upper()
            lines.append(f"    subgraph {layer_name}[{display_name}]")
            for pname in sorted(pkg_names):
                pkg = next((p for p in user_pkgs if p.name == pname), None)
                if not pkg:
                    continue
                node_id = pname.replace("-", "_")
                # Build label with API summary
                pubs = [t for t in pkg.topics if t.direction == "pub"]
                subs = [t for t in pkg.topics if t.direction == "sub"]
                srvs = pkg.services

                label_parts = [pname]
                if pubs:
                    label_parts.append(f"pub: {len(pubs)} topics")
                if subs:
                    label_parts.append(f"sub: {len(subs)} topics")
                if srvs:
                    label_parts.append(f"srv: {len(srvs)}")

                label = "<br/>".join(label_parts)
                lines.append(f'        {node_id}["{label}"]')
            lines.append("    end")
            lines.append("")

        # Topic edges
        if topic_edges:
            lines.append("    %% topic connections")
            seen = set()
            for frm, to, topic, msg_type in sorted(topic_edges):
                key = (frm, to, topic)
                if key in seen:
                    continue
                seen.add(key)
                fid = frm.replace("-", "_")
                tid = to.replace("-", "_")
                short_topic = topic.split("/")[-1] if "/" in topic else topic
                lines.append(f'    {fid} -->|"{short_topic}<br/>[{msg_type}]"| {tid}')

        # Service edges
        if service_edges:
            lines.append("")
            lines.append("    %% service connections")
            seen = set()
            for client, server, srv, srv_type in sorted(service_edges):
                key = (client, server, srv)
                if key in seen:
                    continue
                seen.add(key)
                cid = client.replace("-", "_")
                sid = server.replace("-", "_")
                short_srv = srv.split("/")[-1] if "/" in srv else srv
                lines.append(f'    {cid} -.->|"{short_srv}<br/>[{srv_type}]"| {sid}')

        # Apply styles
        lines.append("")
        style_map = {
            "perception": "perception",
            "navigation": "navigation",
            "hardware": "hardware",
            "manipulation": "manipulation",
            "infrastructure": "infra",
        }
        for layer_name, pkg_names in layers.items():
            cls = style_map.get(layer_name, "infra")
            for pname in pkg_names:
                nid = pname.replace("-", "_")
                lines.append(f"    class {nid} {cls}")

        return "\n".join(lines) + "\n"

    def _classify_layers(self, user_pkgs) -> dict[str, list[str]]:
        """Heuristic layer classification based on package names and dependencies."""
        layers: dict[str, list[str]] = {
            "perception": [],
            "navigation": [],
            "hardware": [],
            "manipulation": [],
            "infrastructure": [],
        }

        for p in user_pkgs:
            name = p.name.lower()
            deps_str = " ".join(p.depends).lower()
            topics_str = " ".join(t.topic for t in p.topics).lower()

            if any(k in name for k in ["oak", "camera", "vision", "slam", "vslam", "perception", "depth", "lidar"]):
                layers["perception"].append(p.name)
            elif any(k in name for k in ["nav", "planner", "control", "path"]):
                layers["navigation"].append(p.name)
            elif any(k in name for k in ["hw", "serial", "motor", "driver", "base"]):
                layers["hardware"].append(p.name)
            elif any(k in name for k in ["arm", "gripper", "manipul", "so101", "so100"]):
                layers["manipulation"].append(p.name)
            elif any(k in topics_str for k in ["/arm/", "gripper", "joint_states"]):
                layers["manipulation"].append(p.name)
            elif any(k in topics_str for k in ["odom", "cmd_vel"]):
                layers["hardware"].append(p.name)
            elif any(k in deps_str for k in ["sensor_msgs", "cv_bridge", "image_transport"]):
                layers["perception"].append(p.name)
            else:
                layers["infrastructure"].append(p.name)

        return layers

    def snapshot(self) -> Path | None:
        files = ["architecture.mmd", "architecture.json", "architecture.md"]

        if not any((self.arch_dir / f).exists() for f in files):
            return None

        sid = "unknown"
        try:
            idx = json.loads((self.out_dir / "index.json").read_text())
            sid = idx.get("latest_snapshot_id", "unknown")
        except Exception:
            pass

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"{timestamp}__{sid}"

        dest_dir = self.history_dir / folder_name
        dest_dir.mkdir(parents=True, exist_ok=True)

        for f in files:
            src = self.arch_dir / f
            if src.exists():
                shutil.copy2(src, dest_dir / f)

        self._update_index(folder_name, timestamp)
        return dest_dir

    def _update_index(self, snapshot_id, timestamp):
        history = []
        if self.history_index.exists():
            try:
                history = json.loads(self.history_index.read_text())
            except Exception:
                pass

        entry = {"id": snapshot_id, "timestamp": timestamp}
        history.insert(0, entry)
        history = history[:50]
        self.history_index.write_text(json.dumps(history, indent=2))