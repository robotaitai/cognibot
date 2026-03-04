import json
import uuid
import datetime
from pathlib import Path
from typing import Optional

class RunLedger:
    def __init__(self, out_dir: Path):
        self.runs_dir = out_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.runs_dir / "index.json"

    def _update_index(self, run_summary):
        runs = []
        if self.index_file.exists():
            try:
                runs = json.loads(self.index_file.read_text())
            except:
                pass
        
        # Update or append
        existing = next((r for r in runs if r["id"] == run_summary["id"]), None)
        if existing:
            existing.update(run_summary)
        else:
            runs.insert(0, run_summary)
        
        self.index_file.write_text(json.dumps(runs, indent=2))

    def start_run(self, title: str) -> str:
        run_id = str(uuid.uuid4())[:8]
        now = datetime.datetime.now().isoformat()
        
        data = {
            "id": run_id,
            "title": title,
            "status": "running",
            "start_time": now,
            "end_time": None,
            "logs": []
        }
        
        (self.runs_dir / f"{run_id}.json").write_text(json.dumps(data, indent=2))
        self._update_index({k: v for k, v in data.items() if k != "logs"})
        return run_id

    def log_entry(self, run_id: str, note: str, file_read=None, file_write=None, cmd=None, exit_code=None, artifact=None):
        run_file = self.runs_dir / f"{run_id}.json"
        if not run_file.exists():
            print(f"Run {run_id} not found.")
            return

        data = json.loads(run_file.read_text())
        entry = {
            "ts": datetime.datetime.now().isoformat(),
            "note": note,
            "file_read": file_read,
            "file_write": file_write,
            "cmd": cmd,
            "exit_code": exit_code,
            "artifact": artifact
        }
        # Filter None
        entry = {k: v for k, v in entry.items() if v is not None}
        
        data["logs"].append(entry)
        run_file.write_text(json.dumps(data, indent=2))
        self._update_index({k: v for k, v in data.items() if k != "logs"})

    def end_run(self, run_id: str, status: str):
        run_file = self.runs_dir / f"{run_id}.json"
        if not run_file.exists():
            return

        data = json.loads(run_file.read_text())
        data["status"] = status
        data["end_time"] = datetime.datetime.now().isoformat()
        run_file.write_text(json.dumps(data, indent=2))
        self._update_index({k: v for k, v in data.items() if k != "logs"})