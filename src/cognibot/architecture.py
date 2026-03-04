import shutil
import json
import datetime
from pathlib import Path

class ArchitectureManager:
    def __init__(self, out_dir: Path):
        self.out_dir = out_dir
        self.arch_dir = out_dir / "architecture"
        self.history_dir = self.arch_dir / "history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.history_index = self.arch_dir / "history.json"

    def snapshot(self) -> Path | None:
        # Files to snapshot
        files = ["architecture.mmd", "architecture.json", "architecture.md"]
        
        # Check if they exist
        if not (self.arch_dir / "architecture.json").exists():
            return None

        # Get latest snapshot ID to correlate
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

        # Update history index
        self._update_index(folder_name, timestamp)
        return dest_dir

    def _update_index(self, snapshot_id, timestamp):
        history = []
        if self.history_index.exists():
            try:
                history = json.loads(self.history_index.read_text())
            except:
                pass
        
        entry = {"id": snapshot_id, "timestamp": timestamp}
        history.insert(0, entry)
        # Keep last 50
        history = history[:50]
        self.history_index.write_text(json.dumps(history, indent=2))