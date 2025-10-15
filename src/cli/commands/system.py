"""
System management commands
System-wide operations: ps, cleanup, categories, version
"""

import typer
from typing import Optional
from rich.console import Console

from ..core.config import load_config
from ..core.docker_ops import (
    get_playground_containers, docker_client, remove_all_containers
)
from ..utils.display import (
    console, create_ps_table, create_categories_table,
    format_container_status, format_ports, create_progress_context
)

app = typer.Typer()


@app.command()
def ps(
    all: bool = typer.Option(False, "--all", "-a", help="Show all containers (including stopped)")
):
    """📊 List running playground containers"""
    containers = get_playground_containers(all_containers=all)
    
    if not containers:
        console.print("[yellow]No playground containers found[/yellow]")
        return
    
    table = create_ps_table()
    
    for c in containers:
        is_running = c.status == "running"
        
        # Get ports
        ports = []
        port_data = c.attrs.get('NetworkSettings', {}).get('Ports')
        if port_data and isinstance(port_data, dict):
            for container_port, bindings in port_data.items():
                if bindings and isinstance(bindings, list):
                    for binding in bindings:
                        if isinstance(binding, dict) and 'HostPort' in binding:
                            ports.append(f"{binding['HostPort']}→{binding.get('PrivatePort', container_port)}")
        
        table.add_row(
            c.name,
            format_container_status(c.status, is_running),
            c.image.tags[0] if c.image.tags else c.image.short_id,
            format_ports(ports)
        )
    
    console.print(table)


@app.command()
def stop_all(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation")
):
    """⏹ Stop all running containers"""
    containers = get_playground_containers(all_containers=False)
    
    if not containers:
        console.print("[yellow]No running containers found[/yellow]")
        return
    
    if not confirm:
        console.print(f"[yellow]About to stop {len(containers)} containers:[/yellow]")
        for c in containers:
            console.print(f"  • {c.name}")
        
        if not typer.confirm("\nAre you sure?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    with create_progress_context(f"Stopping {len(containers)} containers...") as progress:
        task = progress.add_task("Stopping...", total=len(containers))
        
        for c in containers:
            try:
                c.stop(timeout=60)
                c.remove()
                progress.advance(task)
            except Exception as e:
                console.print(f"[red]Failed to stop {c.name}: {e}[/red]")
    
    console.print(f"[green]✓ Stopped {len(containers)} containers[/green]")


@app.command()
def cleanup(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    remove_images: bool = typer.Option(False, "--images", help="Also remove Docker images")
):
    """🧹 Remove all playground containers"""
    containers = get_playground_containers(all_containers=True)
    
    if not containers:
        console.print("[yellow]No containers to cleanup[/yellow]")
        return
    
    if not confirm:
        console.print(f"[red]⚠ About to remove {len(containers)} containers:[/red]")
        for c in containers:
            console.print(f"  • {c.name} ({c.status})")
        
        if not typer.confirm("\nThis will permanently delete these containers. Continue?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    # Collect image names before removal
    image_names = set()
    if remove_images:
        for c in containers:
            if c.image.tags:
                image_names.add(c.image.tags[0])
    
    with create_progress_context(f"Removing {len(containers)} containers...") as progress:
        task = progress.add_task("Removing...", total=len(containers))
        
        removed = remove_all_containers(containers, show_progress=False)
        progress.update(task, completed=len(containers))
    
    console.print(f"[green]✓ Removed {removed} containers[/green]")
    
    # Remove images if requested
    if remove_images and image_names:
        console.print(f"\n[yellow]Removing {len(image_names)} images...[/yellow]")
        
        with create_progress_context("Removing images...") as progress:
            task = progress.add_task("Removing...", total=len(image_names))
            
            for img_name in image_names:
                try:
                    docker_client.images.remove(img_name, force=True)
                    console.print(f"[green]✓ Removed image: {img_name}[/green]")
                    progress.advance(task)
                except Exception as e:
                    console.print(f"[yellow]⚠ Could not remove {img_name}: {e}[/yellow]")
        
        console.print("[green]✓ Image cleanup complete[/green]")


@app.command()
def clean_images(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    unused_only: bool = typer.Option(False, "--unused", "-u", help="Only remove unused images")
):
    """🗑️ Remove Docker images from config"""
    config = load_config()
    
    # Get all images from config
    config_images = set(data.get("image") for data in config.values())
    
    # Get Docker images
    docker_images = docker_client.images.list()
    
    # Find matching images
    images_to_remove = []
    for img in docker_images:
        if img.tags:
            for tag in img.tags:
                if tag in config_images:
                    if unused_only:
                        # Check if image is used by any container
                        containers = docker_client.containers.list(all=True, filters={"ancestor": tag})
                        if not containers:
                            images_to_remove.append((tag, img))
                    else:
                        images_to_remove.append((tag, img))
    
    if not images_to_remove:
        console.print("[yellow]No images to remove[/yellow]")
        return
    
    # Calculate total size
    total_size = sum(img.attrs.get('Size', 0) for _, img in images_to_remove)
    total_size_mb = total_size / (1024 * 1024)
    
    if not confirm:
        console.print(f"[yellow]About to remove {len(images_to_remove)} images ({total_size_mb:.2f} MB):[/yellow]")
        for tag, img in images_to_remove:
            size_mb = img.attrs.get('Size', 0) / (1024 * 1024)
            console.print(f"  • {tag} ({size_mb:.2f} MB)")
        
        if not typer.confirm("\nContinue?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    with create_progress_context(f"Removing {len(images_to_remove)} images...") as progress:
        task = progress.add_task("Removing...", total=len(images_to_remove))
        
        removed = 0
        for tag, img in images_to_remove:
            try:
                docker_client.images.remove(tag, force=True)
                removed += 1
                progress.advance(task)
            except Exception as e:
                console.print(f"[red]Failed to remove {tag}: {e}[/red]")
    
    console.print(f"[green]✓ Removed {removed}/{len(images_to_remove)} images ({total_size_mb:.2f} MB freed)[/green]")

@app.command()
def fix_conflicts(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation")
):
    """🔧 Remove stopped containers that cause conflicts"""
    # Get stopped playground containers
    stopped = docker_client.containers.list(
        all=True,
        filters={
            "label": "playground.managed=true",
            "status": "exited"
        }
    )
    
    if not stopped:
        console.print("[green]✓ No stopped containers found - all clean![/green]")
        return
    
    console.print(f"[yellow]Found {len(stopped)} stopped container(s):[/yellow]")
    for c in stopped:
        console.print(f"  • {c.name}")
    console.print()
    
    if not confirm:
        if not typer.confirm("Remove these containers?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    with create_progress_context(f"Removing {len(stopped)} containers...") as progress:
        task = progress.add_task("Removing...", total=len(stopped))
        
        removed = 0
        for c in stopped:
            try:
                c.remove()
                removed += 1
                progress.advance(task)
            except Exception as e:
                console.print(f"[red]Failed to remove {c.name}: {e}[/red]")
    
    console.print(f"\n[green]✓ Removed {removed}/{len(stopped)} containers[/green]")
    console.print("[cyan]You can now start your containers without conflicts[/cyan]")

@app.command()
def categories():
    """📚 List all categories"""
    config = load_config()
    
    # Count containers per category
    categories_count = {}
    for img_data in config.values():
        cat = img_data.get("category", "other")
        categories_count[cat] = categories_count.get(cat, 0) + 1
    
    table = create_categories_table()
    
    for cat in sorted(categories_count.keys()):
        table.add_row(cat, str(categories_count[cat]))
    
    console.print(table)
    console.print(f"\n[cyan]Total: {len(categories_count)} categories[/cyan]")


@app.command()
def version():
    """🔖 Show version information"""
    from pathlib import Path
    
    BASE_PATH = Path(__file__).parent.parent.parent.parent
    CONFIG_FILE = BASE_PATH / "config.yml"
    
    console.print("[cyan bold]Docker Playground CLI[/cyan bold]")
    console.print("Version: 2.0.0")
    console.print(f"Docker API: {docker_client.version()['Version']}")
    console.print(f"Config path: {CONFIG_FILE}")