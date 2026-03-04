from __future__ import annotations

from pathlib import Path
import typer
import click

from .scan import scan_repo
from .render import render_ui
from .stats import show_stats
from .doctor import doctor as run_doctor
from .util import resolve_out_dir, detect_repo_root
from .serve import serve_dir

app = typer.Typer(no_args_is_help=True)


def _resolve_repo(repo: Path) -> Path:
    return detect_repo_root(repo)


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
    typer.echo(f"[cognibot] wrote snapshot under: {out_dir}")


@app.command()
def render(
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo/workspace"),
    out: Path | None = typer.Option(None, help="Output folder (default: <repo>/.cognibot)"),
):
    repo = _resolve_repo(repo)
    out_dir = resolve_out_dir(repo, out)
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
    out_dir = resolve_out_dir(repo, out)
    serve_dir(out_dir, host=host, port=port, open_browser=(not no_open))


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
    render_ui(out_dir)
    serve_dir(out_dir, host=host, port=port, open_browser=(not no_open))


@app.command()
def stats(
    repo: Path = typer.Option(Path("."), help="Path to ROS2 repo/workspace"),
    out: Path | None = typer.Option(None, help="Output folder (default: <repo>/.cognibot)"),
):
    repo = _resolve_repo(repo)
    out_dir = resolve_out_dir(repo, out)
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


if __name__ == "__main__":
    app()