from __future__ import annotations
from pathlib import Path
import typer

from .scan import scan_repo
from .render import render_ui
from .stats import show_stats
from .doctor import doctor as run_doctor
from .util import resolve_out_dir

app = typer.Typer(no_args_is_help=True)

@app.command()
def scan(
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo/workspace"),
    out: Path | None = typer.Option(None, help="Output folder (default: <repo>/.cognibot)"),
):
    out_dir = scan_repo(repo, out)
    typer.echo(f"[cognibot] wrote snapshot under: {out_dir}")

@app.command()
def render(
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo/workspace"),
    out: Path | None = typer.Option(None, help="Output folder (default: <repo>/.cognibot)"),
):
    out_dir = resolve_out_dir(repo.resolve(), out)
    html = render_ui(out_dir)
    typer.echo(f"[cognibot] wrote UI: {html}")

@app.command()
def stats(
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo/workspace"),
    out: Path | None = typer.Option(None, help="Output folder (default: <repo>/.cognibot)"),
):
    out_dir = resolve_out_dir(repo.resolve(), out)
    s = show_stats(out_dir)
    for k, v in s.items():
        typer.echo(f"{k}: {v}")

@app.command()
def doctor(
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo/workspace"),
    out: Path | None = typer.Option(None, help="Output folder (default: <repo>/.cognibot)"),
):
    notes = run_doctor(repo, out)
    for n in notes:
        typer.echo(n)

if __name__ == "__main__":
    app()
