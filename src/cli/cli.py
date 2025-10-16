#!/usr/bin/env python3
"""
Docker Playground CLI - Main Entry Point
Modular version with clean command structure and volume support
"""

import typer
from pathlib import Path
import sys

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.cli.utils.display import show_banner, show_quick_help, console
from src.cli.commands import containers, groups, system, debug

# Main app
app = typer.Typer(
    name="playground",
    help="🐳 Docker Playground CLI - Manage containerized development environments",
    add_completion=True,
    no_args_is_help=False
)

# Register command groups
app.add_typer(groups.app, name="group", help="🚀 Manage container groups")

# Register individual commands from containers module
app.command(name="list")(containers.list)
app.command(name="start")(containers.start)
app.command(name="stop")(containers.stop)
app.command(name="restart")(containers.restart)
app.command(name="logs")(containers.logs)
app.command(name="exec")(containers.exec)
app.command(name="info")(containers.info)
app.command(name="volumes")(containers.volumes)

# Register system commands
app.command(name="ps")(system.ps)
app.command(name="volumes-list")(system.volumes)
app.command(name="stop-all")(system.stop_all)
app.command(name="fix-conflicts")(system.fix_conflicts)
app.command(name="cleanup")(system.cleanup)
app.command(name="clean-images")(system.clean_images)
app.command(name="categories")(system.categories)
app.command(name="version")(system.version)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Docker Playground CLI
    
    Manage containerized development environments with ease.
    """
    if ctx.invoked_subcommand is None:
        # No command specified, show help
        show_banner()
        show_quick_help()


if __name__ == "__main__":
    app()