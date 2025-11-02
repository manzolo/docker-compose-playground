"""
Container management commands
Single container operations: start, stop, restart, logs, exec, info
Updated with volume support
"""

import typer
import subprocess
import json as json_lib
from typing import Optional
from rich.console import Console

from ..core.config import load_config, get_image_config
from ..core.docker_ops import (
    start_container, stop_container, restart_container,
    get_container_logs, get_running_containers_dict, get_container,
    get_container_volumes
)
from ..utils.display import (
    console, create_containers_table, format_container_status,
    show_port_mappings, show_info_table, create_progress_context
)
from ..core.scripts import execute_script

app = typer.Typer()


@app.command()
def list(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (running/stopped)"),
    json: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """📋 List available containers"""
    config = load_config()
    running_containers = get_running_containers_dict()
    
    # Filter images
    images_list = []
    for name, data in config.items():
        if category and data.get("category") != category:
            continue
        
        is_running = name in running_containers
        container_status = "running" if is_running else "stopped"
        
        if status and container_status != status:
            continue
        
        images_list.append({
            "name": name,
            "image": data.get("image"),
            "category": data.get("category"),
            "description": data.get("description"),
            "status": container_status,
            "ports": data.get("ports", []),
            "volumes": len(data.get("volumes", []))
        })
    
    if json:
        console.print(json_lib.dumps(images_list, indent=2))
    else:
        if not images_list:
            console.print("[yellow]No containers found matching criteria[/yellow]")
            return
        
        table = create_containers_table()
        
        for img in images_list:
            is_running = img["status"] == "running"
            status_str = format_container_status(img["status"], is_running)
            desc = img["description"]
            if len(desc) > 40:
                desc = desc[:40] + "..."
            
            vol_info = ""
            if img["volumes"] > 0:
                vol_info = f" [dim]({img['volumes']} volumes)[/dim]"
            
            table.add_row(
                img["name"],
                img["category"],
                status_str,
                img["image"],
                desc + vol_info
            )
        
        console.print(table)
        console.print(f"\n[cyan]Total: {len(images_list)} containers[/cyan]")


@app.command()
def start(
    image: str = typer.Argument(..., help="Container name from config"),
    force: bool = typer.Option(False, "--force", "-f", help="Force restart if already running")
):
    """▶ Start a container"""
    img_data = get_image_config(image)

    # Use spinner for better UX
    with create_progress_context() as progress:
        task = progress.add_task(f"Starting {image}...", total=None)

        success, container_name = start_container(image, img_data, force, progress=progress, task_id=task)

        if not success:
            raise typer.Exit(1)

        full_container_name = f"playground-{image}" if not image.startswith("playground-") else image

        # Execute post-start script - SEMPRE, anche se non configurato
        scripts = img_data.get('scripts', {})
        post_start_script = scripts.get('post_start') if scripts else None

        try:
            progress.update(task, description=f"📜 Running post-start script for {image}...")
            execute_script(post_start_script, full_container_name, image, script_type="init")
        except Exception as e:
            pass  # Script execution handles its own logging

        progress.update(task, description=f"[green]✅ Container {container_name} started successfully[/green]")

    console.print(f"[green]✓ Container started successfully: {container_name}[/green]")

    # Show connection info
    ports = {}
    for p in img_data.get("ports", []):
        if ':' in p:
            host_port, container_port = p.split(":")
            ports[container_port] = host_port

    show_port_mappings(ports)


@app.command()
def stop(
    container: str = typer.Argument(..., help="Container name"),
    remove: bool = typer.Option(True, "--remove/--no-remove", help="Remove container after stopping")
):
    """⏹ Stop a container"""
    # Extract base name and build full name
    if container.startswith("playground-"):
        base_container_name = container.replace("playground-", "")
        full_container_name = container
    else:
        base_container_name = container
        full_container_name = f"playground-{container}"

    # Use spinner for better UX
    with create_progress_context() as progress:
        task = progress.add_task(f"Stopping {base_container_name}...", total=None)

        # Execute pre-stop script - SEMPRE, anche se non configurato
        config = load_config()
        if base_container_name in config:
            img_data = config[base_container_name]
            scripts = img_data.get('scripts', {})
            pre_stop_script = scripts.get('pre_stop') if scripts else None

            try:
                progress.update(task, description=f"📜 Running pre-stop script for {base_container_name}...")
                execute_script(pre_stop_script, full_container_name, base_container_name, script_type="halt")
            except Exception as e:
                pass  # Script execution handles its own logging

        success = stop_container(full_container_name, remove, progress=progress, task_id=task)

        if success:
            progress.update(task, description=f"[green]✅ Container {full_container_name} stopped[/green]")
        else:
            raise typer.Exit(1)

    console.print(f"[green]✓ Container stopped: {full_container_name}[/green]")


@app.command()
def restart(
    container: str = typer.Argument(..., help="Container name")
):
    """🔄 Restart a container"""
    success = restart_container(container)
    
    if success:
        container_name = container if container.startswith("playground-") else f"playground-{container}"
        console.print(f"[green]✓ Container restarted: {container_name}[/green]")
    else:
        raise typer.Exit(1)


@app.command()
def logs(
    container: str = typer.Argument(..., help="Container name"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    tail: int = typer.Option(100, "--tail", "-n", help="Number of lines to show")
):
    """📋 Show container logs"""
    try:
        get_container_logs(container, tail, follow)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped following logs[/yellow]")


@app.command()
def exec(
    container: str = typer.Argument(..., help="Container name"),
    command: str = typer.Argument(None, help="Command to execute (default: shell)")
):
    """💻 Execute command in container"""
    container_name = container if container.startswith("playground-") else f"playground-{container}"
    
    cont = get_container(container_name)
    
    if cont.status != "running":
        console.print(f"[red]❌ Container is not running: {container_name}[/red]")
        raise typer.Exit(1)
    
    # Get shell from config
    image_name = container_name.replace("playground-", "")
    config = load_config()
    img_data = config.get(image_name, {})
    shell = img_data.get("shell", "/bin/bash")
    
    if command:
        # Execute command
        result = cont.exec_run(command, tty=True)
        console.print(result.output.decode('utf-8', errors='replace'))
    else:
        # Show MOTD before opening interactive shell
        motd = img_data.get("motd", "")
        if motd:
            console.print("\n[cyan]" + "="*60 + "[/cyan]")
            console.print(motd)
            console.print("[cyan]" + "="*60 + "[/cyan]\n")
        
        # Interactive shell
        console.print(f"[cyan]Opening shell in {container_name}...[/cyan]")
        console.print(f"[yellow]Using shell: {shell}[/yellow]\n")
        subprocess.run(["docker", "exec", "-it", container_name, shell])


@app.command()
def info(
    container: str = typer.Argument(..., help="Container name")
):
    """ℹ️ Show detailed container information"""
    container_name = container if container.startswith("playground-") else f"playground-{container}"
    
    cont = get_container(container_name)
    config = load_config()
    image_name = container_name.replace("playground-", "")
    
    info_data = {
        "Status": f"[{'green' if cont.status == 'running' else 'red'}]{cont.status}[/]",
        "Image": cont.image.tags[0] if cont.image.tags else cont.image.short_id,
        "Created": cont.attrs['Created'][:19]
    }
    
    if image_name in config:
        img_data = config[image_name]
        info_data["Category"] = img_data.get("category", "N/A")
        info_data["Description"] = img_data.get("description", "N/A")
    
    # Network info
    networks = cont.attrs.get('NetworkSettings', {}).get('Networks', {})
    if networks and isinstance(networks, dict):
        network_names = [str(k) for k in networks.keys()]
        info_data["Networks"] = ", ".join(network_names)
    else:
        info_data["Networks"] = "None"
    
    # Ports
    ports = cont.attrs.get('NetworkSettings', {}).get('Ports')
    if ports and isinstance(ports, dict):
        port_mappings = []
        for container_port, bindings in ports.items():
            if bindings and isinstance(bindings, list):
                for binding in bindings:
                    if isinstance(binding, dict) and 'HostPort' in binding:
                        port_mappings.append(f"{binding['HostPort']}→{container_port}")
        if port_mappings:
            info_data["Ports"] = ", ".join(port_mappings)
        else:
            info_data["Ports"] = "None (exposed but not mapped)"
    else:
        info_data["Ports"] = "None"
    
    # Volumes
    volumes_info = get_container_volumes(container_name)
    if volumes_info:
        info_data["Volumes"] = str(len(volumes_info))
    
    show_info_table(info_data, f"Container: {container_name}")
    
    # Show volumes in detail if any
    if volumes_info:
        console.print("[cyan bold]Volume Mounts:[/cyan bold]")
        for path, info in volumes_info.items():
            console.print(f"  {path}: {info}")
        console.print()


@app.command()
def volumes(
    container: str = typer.Argument(..., help="Container name")
):
    """📦 Show container volumes and mounts"""
    container_name = container if container.startswith("playground-") else f"playground-{container}"
    
    cont = get_container(container_name)
    volumes_info = get_container_volumes(container_name)
    
    console.print(f"\n[cyan bold]Volumes for: {container_name}[/cyan bold]\n")
    
    if not volumes_info:
        console.print("[yellow]No volumes mounted[/yellow]")
        return
    
    for path, info in volumes_info.items():
        console.print(f"  [cyan]{path}[/cyan]")
        console.print(f"    {info}\n")