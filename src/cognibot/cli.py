from __future__ import annotations

from pathlib import Path
import typer
import click
import os
import subprocess
import json
import datetime

from .scan import scan_repo
from .render import render_ui
from .stats import show_stats
from .doctor import doctor as run_doctor
from .serve import serve_brain
from .run_ledger import RunLedger
from .architecture import ArchitectureManager

app = typer.Typer(no_args_is_help=True)
run_app = typer.Typer(no_args_is_help=True, help="Manage run ledger (progress tracking).")
arch_app = typer.Typer(no_args_is_help=True, help="Manage architecture artifacts.")

app.add_typer(run_app, name="run")
app.add_typer(arch_app, name="arch")


def _resolve_repo(repo: Path) -> Path:
    # 1. Env var
    if os.environ.get("CURSOR_PROJECT_DIR"):
        return Path(os.environ["CURSOR_PROJECT_DIR"])
    
    # 2. Git root
    try:
        root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL).decode().strip()
        return Path(root)
    except Exception:
        pass

    # 3. Current dir (or passed arg if not ".")
    if str(repo) == ".":
        return Path.cwd()
    return repo


def _update_history(out_dir: Path):
    """
    Updates index.json with a history entry of the latest snapshot.
    """
    index_path = out_dir / "index.json"
    if not index_path.exists():
        return

    try:
        data = json.loads(index_path.read_text())
        # Basic snapshot metadata
        snapshot = {
            "id": data.get("snapshot_id"),
            "timestamp": datetime.datetime.now().isoformat(),
            "commit": data.get("commit", "unknown"),
            "dirty": data.get("dirty", False),
            "stats": data.get("stats", {})
        }
        
        history_file = out_dir / "history.json"
        history = []
        if history_file.exists():
            history = json.loads(history_file.read_text())
        
        # Prepend and keep last 200
        history.insert(0, snapshot)
        history = history[:200]
        
        history_file.write_text(json.dumps(history, indent=2))
    except Exception as e:
        print(f"[warn] failed to update history: {e}")


@app.command()
def help(command: str | None = typer.Argument(None, help="Optional subcommand name")):
    """
    Intuitive help: `cognibot help` or `cognibot help scan`
    """
    cmd = typer.main.get_command(app)
    ctx = click.Context(cmd)

    if not command:
        typer.echo(cmd.get_help(ctx))
        return

    sub = cmd.get_command(ctx, command)
    if sub is None:
        typer.echo(f"unknown command: {command}\n")
        typer.echo(cmd.get_help(ctx))
        raise typer.Exit(code=2)

    typer.echo(sub.get_help(click.Context(sub)))


@app.command()
def scan(
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo/workspace"),
    out: Path | None = typer.Option(None, help="Output folder (default: <repo>/.cognibot)"),
):
    repo = _resolve_repo(repo)
    out_dir = scan_repo(repo, out)
    _update_history(out_dir)
    typer.echo(f"[cognibot] wrote snapshot under: {out_dir}")


@app.command()
def render(
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo/workspace"),
    out: Path | None = typer.Option(None, help="Output folder (default: <repo>/.cognibot)"),
):
    repo = _resolve_repo(repo)
    out_dir = _resolve_out_dir(repo, out)
    html = render_ui(out_dir)
    typer.echo(f"[cognibot] wrote UI: {html}")


@app.command()
def serve(
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo/workspace"),
    out: Path | None = typer.Option(None, help="Output folder (default: <repo>/.cognibot)"),
    host: str = typer.Option("127.0.0.1", help="Bind host (use 0.0.0.0 for LAN access)"),
    port: int = typer.Option(8765, help="HTTP port"),
    no_open: bool = typer.Option(False, help="Do not auto-open browser"),
):
    repo = _resolve_repo(repo)
    out_dir = _resolve_out_dir(repo, out)
    serve_brain(out_dir, host=host, port=port, open_browser=(not no_open))


@app.command()
def ui(
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo/workspace"),
    out: Path | None = typer.Option(None, help="Output folder (default: <repo>/.cognibot)"),
    host: str = typer.Option("127.0.0.1", help="Bind host (use 0.0.0.0 for LAN access)"),
    port: int = typer.Option(8765, help="HTTP port"),
    no_open: bool = typer.Option(False, help="Do not auto-open browser"),
):
    """
    One command to get value:
      scan + render + serve
    """
    repo = _resolve_repo(repo)
    out_dir = scan_repo(repo, out)
    _update_history(out_dir)
    render_ui(out_dir)
    serve_brain(out_dir, host=host, port=port, open_browser=(not no_open))


@app.command()
def stats(
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo/workspace"),
    out: Path | None = typer.Option(None, help="Output folder (default: <repo>/.cognibot)"),
):
    repo = _resolve_repo(repo)
    out_dir = _resolve_out_dir(repo, out)
    s = show_stats(out_dir)
    for k, v in s.items():
        typer.echo(f"{k}: {v}")


@app.command()
def doctor(
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo/workspace"),
    out: Path | None = typer.Option(None, help="Output folder (default: <repo>/.cognibot)"),
):
    repo = _resolve_repo(repo)
    notes = run_doctor(repo, out)
    for n in notes:
        typer.echo(n)


# --- Run Ledger Commands ---

@run_app.command("start")
def run_start(
    title: str,
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo"),
):
    repo = _resolve_repo(repo)
    out_dir = _resolve_out_dir(repo, None)
    ledger = RunLedger(out_dir)
    run_id = ledger.start_run(title)
    typer.echo(run_id)


@run_app.command("log")
def run_log(
    run_id: str = typer.Option(..., "--run", help="Run ID"),
    note: str = typer.Option(..., help="Log entry text"),
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo"),
    file_read: str = typer.Option(None, help="File read"),
    file_write: str = typer.Option(None, help="File written"),
    cmd: str = typer.Option(None, help="Command executed"),
    exit_code: int = typer.Option(None, "--exit", help="Exit code of command"),
    artifact: str = typer.Option(None, help="Path to artifact produced"),
):
    repo = _resolve_repo(repo)
    out_dir = _resolve_out_dir(repo, None)
    ledger = RunLedger(out_dir)
    ledger.log_entry(run_id, note, file_read, file_write, cmd, exit_code, artifact)
    typer.echo(f"logged to {run_id}")


@run_app.command("end")
def run_end(
    run_id: str = typer.Option(..., "--run", help="Run ID"),
    status: str = typer.Option("success", help="success | fail"),
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo"),
):
    repo = _resolve_repo(repo)
    out_dir = _resolve_out_dir(repo, None)
    ledger = RunLedger(out_dir)
    ledger.end_run(run_id, status)
    typer.echo(f"ended run {run_id} as {status}")


# --- Architecture Commands ---

@arch_app.command("snapshot")
def arch_snapshot(
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo"),
):
    """
    Snapshot current architecture artifacts (.cognibot/architecture/*) into history.
    """
    repo = _resolve_repo(repo)
    out_dir = _resolve_out_dir(repo, None)
    arch = ArchitectureManager(out_dir)
    path = arch.snapshot()
    if path:
        typer.echo(f"Architecture snapshot saved to: {path}")
    else:
        typer.echo("No architecture artifacts found to snapshot.")


if __name__ == "__main__":
    app()