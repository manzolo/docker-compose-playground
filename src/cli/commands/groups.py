"""
Group management commands
Operations on multiple containers: start-group, stop-group, status
"""

import typer
import docker
import time
import json as json_lib
from typing import Optional
from rich.console import Console

from ..core.config import load_config, load_groups
from ..core.docker_ops import (
    start_container, stop_container, get_container,
    docker_client, ensure_network, SHARED_DIR, NETWORK_NAME
)
from ..utils.display import (
    console, create_groups_table, create_status_table,
    format_container_status, show_operation_summary, create_progress_context
)
from ..utils.scripts import execute_script

app = typer.Typer()


@app.command("list")
def list_groups(
    json: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """📚 List available container groups"""
    groups = load_groups()
    
    if not groups:
        console.print("[yellow]No groups found[/yellow]")
        return
    
    if json:
        console.print(json_lib.dumps(groups, indent=2))
    else:
        table = create_groups_table()
        
        for name, group in groups.items():
            containers_count = len(group.get("containers", []))
            containers_list = ", ".join(group.get("containers", []))
            if len(containers_list) > 50:
                containers_list = containers_list[:50] + "..."
            
            table.add_row(
                name,
                group.get("description", "No description"),
                f"{containers_count} containers\n[dim]{containers_list}[/dim]",
                group.get("category", "default"),
                group.get("source", "config.yml")
            )
        
        console.print(table)


@app.command("start")
def start_group(
    group_name: str = typer.Argument(..., help="Group name"),
    force: bool = typer.Option(False, "--force", "-f", help="Force restart running containers")
):
    """🚀 Start all containers in a group"""
    groups = load_groups()
    config = load_config()
    
    if group_name not in groups:
        console.print(f"[red]❌ Group '{group_name}' not found[/red]")
        console.print(f"[yellow]Available groups: {', '.join(groups.keys())}[/yellow]")
        raise typer.Exit(1)
    
    group = groups[group_name]
    containers = group.get("containers", [])
    
    if not containers:
        console.print(f"[yellow]Group '{group_name}' has no containers[/yellow]")
        return
    
    # Validate all containers exist in config
    missing_containers = [c for c in containers if c not in config]
    if missing_containers:
        console.print(f"[red]❌ Containers not found in config: {', '.join(missing_containers)}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[cyan]Starting group '{group_name}': {len(containers)} containers[/cyan]")
    console.print(f"[dim]Description: {group.get('description', 'No description')}[/dim]")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    with create_progress_context() as progress:
        for container_name in containers:
            task = progress.add_task(f"Starting {container_name}...", total=None)
            
            try:
                # Check if container is already running
                full_container_name = f"playground-{container_name}"
                try:
                    existing = docker_client.containers.get(full_container_name)
                    if existing.status == "running" and not force:
                        progress.update(task, description=f"[yellow]Skipping {container_name} (already running)[/yellow]")
                        skipped_count += 1
                        continue
                    elif existing.status == "running" and force:
                        existing.stop(timeout=10)
                        existing.remove()
                except:
                    pass
                
                # Start container
                img_data = config[container_name]
                ensure_network()
                
                # Parse ports
                ports = {}
                for p in img_data.get("ports", []):
                    host_port, container_port = p.split(":")
                    ports[container_port] = host_port
                
                # Start container
                container = docker_client.containers.run(
                    img_data["image"],
                    detach=True,
                    name=full_container_name,
                    hostname=container_name,
                    environment=img_data.get("environment", {}),
                    ports=ports,
                    volumes=[f"{SHARED_DIR}:/shared"],
                    command=img_data["keep_alive_cmd"],
                    network=NETWORK_NAME,
                    stdin_open=True,
                    tty=True,
                    labels={"playground.managed": "true"}
                )
                
                # Wait for container to be running
                max_wait = 30
                elapsed = 0
                started = False
                
                while elapsed < max_wait:
                    container.reload()
                    if container.status == "running":
                        started = True
                        break
                    elif container.status in ["exited", "dead"]:
                        break
                    time.sleep(0.5)
                    elapsed += 0.5
                
                if started:
                    progress.update(task, description=f"[green]Started {container_name}[/green]")
                    success_count += 1
                    
                    # Execute post-start script
                    scripts = img_data.get('scripts', {})
                    if 'post_start' in scripts:
                        execute_script(scripts['post_start'], full_container_name, container_name)
                else:
                    progress.update(task, description=f"[red]Failed to start {container_name}[/red]")
                    failed_count += 1
                    
            except Exception as e:
                import traceback
                error_details = str(e)
                if "port is already allocated" in error_details.lower():
                    error_msg = f"Port conflict: {error_details.split('port')[1] if 'port' in error_details else error_details}"
                else:
                    error_msg = error_details
                progress.update(task, description=f"[red]Error: {container_name} - {error_msg[:50]}[/red]")
                failed_count += 1
                console.print(f"[red]Full error for {container_name}:[/red] {error_details}")
    
    show_operation_summary(success_count, failed_count, skipped_count)


@app.command("stop")
def stop_group(
    group_name: str = typer.Argument(..., help="Group name"),
    remove: bool = typer.Option(True, "--remove/--no-remove", help="Remove containers after stopping")
):
    """⏹ Stop all containers in a group"""
    groups = load_groups()
    config = load_config()
    
    if group_name not in groups:
        console.print(f"[red]❌ Group '{group_name}' not found[/red]")
        console.print(f"[yellow]Available groups: {', '.join(groups.keys())}[/yellow]")
        raise typer.Exit(1)
    
    group = groups[group_name]
    containers = group.get("containers", [])
    
    if not containers:
        console.print(f"[yellow]Group '{group_name}' has no containers[/yellow]")
        return
    
    console.print(f"[cyan]Stopping group '{group_name}': {len(containers)} containers[/cyan]")
    
    success_count = 0
    failed_count = 0
    not_running_count = 0
    
    with create_progress_context() as progress:
        for container_name in containers:
            task = progress.add_task(f"Stopping {container_name}...", total=None)
            
            try:
                full_container_name = f"playground-{container_name}"
                cont = docker_client.containers.get(full_container_name)
                
                if cont.status != "running":
                    progress.update(task, description=f"[yellow]Skipping {container_name} (not running)[/yellow]")
                    not_running_count += 1
                    continue
                
                # Execute pre-stop script
                if container_name in config:
                    scripts = config[container_name].get('scripts', {})
                    if 'pre_stop' in scripts:
                        execute_script(scripts['pre_stop'], full_container_name, container_name)
                
                # Stop container
                cont.stop(timeout=90)
                
                if remove:
                    cont.remove()
                
                progress.update(task, description=f"[green]Stopped {container_name}[/green]")
                success_count += 1
                
            except docker.errors.NotFound:
                progress.update(task, description=f"[yellow]Skipping {container_name} (not found)[/yellow]")
                not_running_count += 1
            except Exception as e:
                progress.update(task, description=f"[red]Error stopping {container_name}: {e}[/red]")
                failed_count += 1
    
    show_operation_summary(success_count, failed_count, not_running=not_running_count)


@app.command("status")
def group_status(
    group_name: str = typer.Argument(..., help="Group name"),
    json: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """📊 Show status of all containers in a group"""
    groups = load_groups()
    
    if group_name not in groups:
        console.print(f"[red]❌ Group '{group_name}' not found[/red]")
        console.print(f"[yellow]Available groups: {', '.join(groups.keys())}[/yellow]")
        raise typer.Exit(1)
    
    group = groups[group_name]
    containers = group.get("containers", [])
    
    if not containers:
        console.print(f"[yellow]Group '{group_name}' has no containers[/yellow]")
        return
    
    console.print(f"[cyan]Group: {group_name}[/cyan]")
    console.print(f"[dim]Description: {group.get('description', 'No description')}[/dim]")
    console.print(f"[dim]Containers: {len(containers)}[/dim]\n")
    
    status_data = {
        "group": group_name,
        "description": group.get("description", ""),
        "total": len(containers),
        "running": 0,
        "containers": []
    }
    
    table = create_status_table()
    
    for container_name in containers:
        full_name = f"playground-{container_name}"
        
        try:
            cont = docker_client.containers.get(full_name)
            status = cont.status
            is_running = status == "running"
            
            if is_running:
                status_data["running"] += 1
            
            container_info = {
                "name": container_name,
                "status": status,
                "running": is_running,
                "image": cont.image.tags[0] if cont.image.tags else cont.image.short_id
            }
            status_data["containers"].append(container_info)
            
            table.add_row(
                container_name,
                format_container_status(status, is_running),
                container_info["image"]
            )
            
        except:
            container_info = {
                "name": container_name,
                "status": "not_found",
                "running": False,
                "image": "N/A"
            }
            status_data["containers"].append(container_info)
            
            table.add_row(
                container_name,
                "[red]⏹ not found[/red]",
                "N/A"
            )
    
    if json:
        console.print(json_lib.dumps(status_data, indent=2))
    else:
        console.print(table)
        
        # Summary
        running = status_data["running"]
        total = status_data["total"]
        console.print(f"\n[cyan]Summary: {running}/{total} running[/cyan]")
        
        if running == total:
            console.print("[green]✓ All containers are running[/green]")
        elif running == 0:
            console.print("[yellow]⚠ No containers are running[/yellow]")
        else:
            console.print(f"[yellow]⚠ {total - running} containers not running[/yellow]")


@app.command("restart")
def restart_group(
    group_name: str = typer.Argument(..., help="Group name")
):
    """🔄 Restart all containers in a group"""
    # First stop the group
    console.print("[cyan]Stopping group...[/cyan]")
    stop_group(group_name, remove=True)
    
    # Then start the group
    console.print("\n[cyan]Starting group...[/cyan]")
    start_group(group_name, force=False)