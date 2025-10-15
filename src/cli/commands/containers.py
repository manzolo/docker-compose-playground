"""
Container management commands
Single container operations: start, stop, restart, logs, exec
"""

import typer
import subprocess
import json as json_lib
from typing import Optional
from rich.console import Console

from ..core.config import load_config, get_image_config
from ..core.docker_ops import (
    start_container, stop_container, restart_container,
    get_container_logs, get_running_containers_dict, get_container
)
from ..utils.display import (
    console, create_containers_table, format_container_status,
    show_port_mappings, show_info_table
)
from ..utils.scripts import execute_script

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
            "ports": data.get("ports", [])
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
            if len(desc) > 50:
                desc = desc[:50] + "..."
            
            table.add_row(
                img["name"],
                img["category"],
                status_str,
                img["image"],
                desc
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
    
    success, container_name = start_container(image, img_data, force)
    
    if not success:
        raise typer.Exit(1)
    
    console.print(f"[green]✓ Container started successfully: {container_name}[/green]")
    
    # Execute post-start script
    scripts = img_data.get('scripts', {})
    if 'post_start' in scripts:
        console.print("[cyan]Running post-start script...[/cyan]")
        execute_script(scripts['post_start'], container_name, image)
    
    # Show connection info
    ports = {}
    for p in img_data.get("ports", []):
        host_port, container_port = p.split(":")
        ports[container_port] = host_port
    
    show_port_mappings(ports)


@app.command()
def stop(
    container: str = typer.Argument(..., help="Container name"),
    remove: bool = typer.Option(True, "--remove/--no-remove", help="Remove container after stopping")
):
    """⏹ Stop a container"""
    container_name = container if container.startswith("playground-") else f"playground-{container}"
    image_name = container_name.replace("playground-", "")
    
    # Execute pre-stop script
    config = load_config()
    if image_name in config:
        scripts = config[image_name].get('scripts', {})
        if 'pre_stop' in scripts:
            console.print("[cyan]Running pre-stop script...[/cyan]")
            execute_script(scripts['pre_stop'], container_name, image_name)
    
    success = stop_container(container_name, remove)
    
    if success:
        console.print(f"[green]✓ Container stopped: {container_name}[/green]")
    else:
        raise typer.Exit(1)


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
    shell = config.get(image_name, {}).get("shell", "/bin/bash")
    
    if command:
        # Execute command
        result = cont.exec_run(command, tty=True)
        console.print(result.output.decode('utf-8', errors='replace'))
    else:
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
    
    show_info_table(info_data, f"Container: {container_name}")