"""
Docker operations for CLI
Handles all Docker API interactions
"""

import docker
import time
import typer
from pathlib import Path
from typing import List, Dict, Any, Tuple
from rich.console import Console

console = Console()

# Paths
BASE_PATH = Path(__file__).parent.parent.parent.parent
SHARED_DIR = BASE_PATH / "shared-volumes"
NETWORK_NAME = "playground-network"

# Initialize Docker client
try:
    docker_client = docker.from_env()
except docker.errors.DockerException:
    console.print("[red]❌ Could not connect to Docker. Is Docker running?[/red]")
    raise typer.Exit(1)


def ensure_network():
    """Ensure playground network exists"""
    try:
        docker_client.networks.get(NETWORK_NAME)
    except docker.errors.NotFound:
        docker_client.networks.create(NETWORK_NAME, driver="bridge")
        console.print(f"[green]✓ Created network: {NETWORK_NAME}[/green]")


def get_playground_containers(all_containers: bool = True) -> List:
    """Get all playground containers"""
    return docker_client.containers.list(
        all=all_containers,
        filters={"label": "playground.managed=true"}
    )


def get_container(container_name: str):
    """Get container by name, with proper name formatting"""
    if not container_name.startswith("playground-"):
        container_name = f"playground-{container_name}"
    
    try:
        return docker_client.containers.get(container_name)
    except docker.errors.NotFound:
        console.print(f"[red]❌ Container not found: {container_name}[/red]")
        raise typer.Exit(1)


def start_container(
    image_name: str,
    img_data: Dict[str, Any],
    force: bool = False
) -> Tuple[bool, str]:
    """
    Start a container
    Returns: (success: bool, container_name: str)
    """
    container_name = f"playground-{image_name}"
    
    ensure_network()
    
    try:
        # Check if already exists
        try:
            existing = docker_client.containers.get(container_name)
            if existing.status == "running" and not force:
                console.print(f"[yellow]⚠ Container already running: {container_name}[/yellow]")
                return False, container_name
            
            console.print("[yellow]Removing existing container...[/yellow]")
            existing.stop(timeout=10)
            existing.remove()
        except docker.errors.NotFound:
            pass
        
        # Parse ports
        ports = {}
        for p in img_data.get("ports", []):
            host_port, container_port = p.split(":")
            ports[container_port] = host_port
        
        console.print(f"[cyan]Starting container: {container_name}...[/cyan]")
        
        # Start container
        container = docker_client.containers.run(
            img_data["image"],
            detach=True,
            name=container_name,
            hostname=image_name,
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
        
        while elapsed < max_wait:
            container.reload()
            if container.status == "running":
                return True, container_name
            elif container.status in ["exited", "dead"]:
                console.print(f"[red]❌ Container failed to start: {container.status}[/red]")
                return False, container_name
            
            time.sleep(0.5)
            elapsed += 0.5
        
        console.print("[red]❌ Container did not start in time[/red]")
        return False, container_name
        
    except docker.errors.ImageNotFound:
        console.print(f"[red]❌ Docker image not found: {img_data['image']}[/red]")
        console.print(f"[yellow]Try pulling it first: docker pull {img_data['image']}[/yellow]")
        return False, container_name
    except docker.errors.APIError as e:
        console.print(f"[red]❌ Docker error: {e}[/red]")
        return False, container_name


def stop_container(container_name: str, remove: bool = True) -> bool:
    """
    Stop a container
    Returns: success: bool
    """
    if not container_name.startswith("playground-"):
        container_name = f"playground-{container_name}"
    
    try:
        cont = docker_client.containers.get(container_name)
        
        console.print(f"[yellow]Stopping container: {container_name}...[/yellow]")
        cont.stop(timeout=90)
        
        if remove:
            console.print("[yellow]Removing container...[/yellow]")
            cont.remove()
        
        return True
        
    except docker.errors.NotFound:
        console.print(f"[red]❌ Container not found: {container_name}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        return False


def restart_container(container_name: str) -> bool:
    """Restart a container"""
    if not container_name.startswith("playground-"):
        container_name = f"playground-{container_name}"
    
    try:
        cont = docker_client.containers.get(container_name)
        console.print(f"[yellow]Restarting container: {container_name}...[/yellow]")
        cont.restart(timeout=30)
        return True
    except docker.errors.NotFound:
        console.print(f"[red]❌ Container not found: {container_name}[/red]")
        return False


def get_container_logs(container_name: str, tail: int = 100, follow: bool = False):
    """Get container logs"""
    if not container_name.startswith("playground-"):
        container_name = f"playground-{container_name}"
    
    try:
        cont = docker_client.containers.get(container_name)
        
        if follow:
            console.print(f"[cyan]Following logs for {container_name} (Ctrl+C to stop)...[/cyan]\n")
            for line in cont.logs(stream=True, follow=True, tail=tail):
                console.print(line.decode('utf-8', errors='replace'), end='')
        else:
            logs = cont.logs(tail=tail).decode('utf-8', errors='replace')
            console.print(logs)
            
    except docker.errors.NotFound:
        console.print(f"[red]❌ Container not found: {container_name}[/red]")
        raise typer.Exit(1)


def get_running_containers_dict() -> Dict[str, Dict[str, Any]]:
    """Get dictionary of running containers"""
    running = get_playground_containers(all_containers=True)
    return {
        c.name.replace("playground-", ""): {
            "name": c.name,
            "status": c.status
        }
        for c in running
        if c.name.startswith("playground-")
    }


def remove_all_containers(containers: List, show_progress: bool = True) -> int:
    """Remove all specified containers"""
    removed = 0
    
    for c in containers:
        try:
            if c.status == "running":
                c.stop(timeout=30)
            c.remove()
            removed += 1
        except Exception as e:
            console.print(f"[red]Failed to remove {c.name}: {e}[/red]")
    
    return removed