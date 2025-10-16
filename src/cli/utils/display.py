"""
Display utilities for CLI
Handles tables, progress bars, and formatted output
"""

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import List, Dict, Any

console = Console()


def show_banner():
    """Show CLI banner"""
    console.print("""
╔══════════════════════════════════════════╗
║   🐳  Docker Playground CLI              ║
║   Manage containerized environments      ║
╚══════════════════════════════════════════╝
""")


def show_quick_help():
    """Show quick command reference"""
    console.print("""
[cyan]Quick Commands:[/cyan]
  playground list              List all containers
  playground ps                Show running containers
  playground start <name>      Start a container
  playground stop <name>       Stop a container
  playground logs <name>       Show container logs
  playground exec <name>       Open shell in container
  playground info <name>       Show container info
  playground volumes <name>    Show container volumes
  playground --help            Full help
""")


def create_containers_table(title: str = "🐳 Docker Playground Containers") -> Table:
    """Create a table for container listing"""
    table = Table(title=title)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Category", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Image", style="blue")
    table.add_column("Description", style="white")
    return table


def create_groups_table(title: str = "🚀 Docker Playground Groups") -> Table:
    """Create a table for groups listing"""
    table = Table(title=title)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")
    table.add_column("Containers", style="magenta")
    table.add_column("Category", style="blue")
    table.add_column("Source", style="dim")
    return table


def create_status_table() -> Table:
    """Create a table for container status"""
    table = Table()
    table.add_column("Container", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Image", style="blue")
    return table


def create_ps_table(title: str = "🐳 Playground Containers") -> Table:
    """Create a table for ps command"""
    table = Table(title=title)
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Image", style="blue")
    table.add_column("Ports", style="magenta")
    return table


def create_categories_table(title: str = "📚 Categories") -> Table:
    """Create a table for categories"""
    table = Table(title=title)
    table.add_column("Category", style="cyan")
    table.add_column("Containers", style="green", justify="right")
    return table


def format_container_status(status: str, is_running: bool) -> str:
    """Format container status with emoji and color"""
    status_emoji = "▶" if is_running else "⏹"
    status_color = "green" if is_running else "red"
    return f"[{status_color}]{status_emoji} {status}[/{status_color}]"


def format_ports(ports: List[str]) -> str:
    """Format port mappings for display"""
    if not ports:
        return "none"
    return ", ".join(ports)


def show_operation_summary(success: int, failed: int, skipped: int = 0, not_running: int = 0):
    """Show operation summary"""
    console.print()
    if success > 0:
        console.print(f"[green]✓ Successfully completed: {success}[/green]")
    if skipped > 0:
        console.print(f"[yellow]⚠ Skipped: {skipped}[/yellow]")
    if not_running > 0:
        console.print(f"[yellow]⚠ Not running: {not_running}[/yellow]")
    if failed > 0:
        console.print(f"[red]❌ Failed: {failed}[/red]")


def create_progress_context(description: str = "Processing..."):
    """Create a progress context manager"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    )


def show_port_mappings(ports: Dict[str, str]):
    """Show port mappings"""
    if ports:
        console.print("\n[cyan]Port mappings:[/cyan]")
        for container_port, host_port in ports.items():
            console.print(f"  • localhost:{host_port} → {container_port}")


def show_info_table(data: Dict[str, str], title: str = "Information"):
    """Show information in a table format"""
    table = Table(show_header=False, box=None)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    
    for key, value in data.items():
        table.add_row(key, value)
    
    console.print(f"\n[cyan bold]{title}[/cyan bold]\n")
    console.print(table)
    console.print()