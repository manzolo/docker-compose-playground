"""
Docker operations for CLI
Handles all Docker API interactions with volume support
"""

import docker
import time
import typer
from pathlib import Path
from typing import List, Dict, Any, Tuple
from rich.console import Console

from .volumes import VolumeManager, validate_and_prepare_volumes
from .docker_compose_params import extract_docker_params

# Import logger utilities
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.cli.utils.logger import log_exception, debug_print

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


def prepare_volumes(volumes_config: List[Dict]) -> Tuple[bool, VolumeManager, List[str]]:
    """
    Prepare volumes for container
    Returns: (success: bool, volume_manager: VolumeManager, errors: List[str])
    """
    if not volumes_config:
        return True, VolumeManager(), []
    
    success, manager, errors = validate_and_prepare_volumes(volumes_config)
    
    if errors:
        for error in errors:
            console.print(f"[yellow]⚠ Volume warning: {error}[/yellow]")
    
    return success, manager, errors


def ensure_named_volumes(volumes: VolumeManager):
    """Create named volumes if they don't exist"""
    for vol in volumes.volumes:
        if vol.volume_type == 'named':
            try:
                docker_client.volumes.get(vol.name)
            except docker.errors.NotFound:
                console.print(f"[cyan]Creating named volume: {vol.name}[/cyan]")
                docker_client.volumes.create(name=vol.name, driver="local")


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
    force: bool = False,
    progress=None,
    task_id=None
) -> Tuple[bool, str]:
    """
    Start a container with volume support
    Returns: (success: bool, container_name: str)

    Args:
        image_name: Name of the container
        img_data: Container configuration
        force: Force restart if already running
        progress: Optional Rich Progress object for spinner
        task_id: Optional task ID for updating spinner
    """
    container_name = f"playground-{image_name}"

    def update_spinner(message: str):
        """Update spinner message if available"""
        if progress and task_id is not None:
            progress.update(task_id, description=message)
        else:
            console.print(f"[cyan]{message}[/cyan]")

    ensure_network()

    try:
        # Check if already exists
        try:
            existing = docker_client.containers.get(container_name)
            if existing.status == "running" and not force:
                console.print(f"[yellow]⚠ Container already running: {container_name}[/yellow]")
                return False, container_name

            update_spinner(f"🗑️  Removing existing container...")
            existing.stop(timeout=10)
            existing.remove()
        except docker.errors.NotFound:
            pass
        
        # Parse ports
        debug_print(f"Parsing ports for {image_name}...")
        ports = {}
        for i, p in enumerate(img_data.get("ports", [])):
            debug_print(f"  Port {i}: {repr(p)} (type: {type(p).__name__})")
            if not isinstance(p, str):
                error_msg = f"Port mapping must be a string, got {type(p).__name__}: {repr(p)}"
                console.print(f"[red]❌ Invalid port configuration:[/red]")
                console.print(f"[red]   {error_msg}[/red]")
                console.print(f"[yellow]💡 Tip: Quote port mappings in YAML (e.g., \"3000:3000\")[/yellow]")
                return False, container_name
            if ':' in p:
                host_port, container_port = p.split(":")
                ports[container_port] = host_port
        
        # Prepare volumes
        update_spinner("📦 Preparing volumes...")
        volumes_config = img_data.get("volumes", [])
        success, volume_manager, errors = prepare_volumes(volumes_config)

        if not success and errors:
            console.print(f"[red]❌ Failed to prepare volumes:[/red]")
            for error in errors:
                console.print(f"   {error}")
            return False, container_name

        # Ensure named volumes exist
        if volume_manager.volumes:
            update_spinner("🔧 Creating named volumes...")
            ensure_named_volumes(volume_manager)

        # Build volumes list
        volumes = [f"{SHARED_DIR}:/shared"]
        volumes.extend(volume_manager.get_compose_volumes())

        update_spinner(f"🐳 Starting container {container_name}...")

        if volume_manager.volumes and not (progress and task_id is not None):
            console.print("[cyan]Volumes:[/cyan]")
            for vol_str in volume_manager.list_volumes():
                console.print(f"  • {vol_str}")

        # Extract Docker Compose parameters
        docker_params = extract_docker_params(img_data)

        # Show additional Docker parameters if any (only if not using spinner)
        if docker_params and not (progress and task_id is not None):
            console.print("[cyan]Additional Docker parameters:[/cyan]")
            for key, value in docker_params.items():
                console.print(f"  • {key}: {value}")

        # Prepare base parameters
        base_params = {
            "detach": True,
            "name": container_name,
            "environment": img_data.get("environment", {}),
            "ports": ports if ports else None,
            "volumes": volumes,
            "command": img_data.get("keep_alive_cmd", "sleep infinity"),
            "network": NETWORK_NAME,
            "stdin_open": True,
            "tty": True,
            "labels": {"playground.managed": "true"}
        }

        # Only set hostname if not already in docker_params
        if "hostname" not in docker_params:
            base_params["hostname"] = image_name

        # Start container with base parameters + Docker Compose parameters
        update_spinner(f"🚀 Launching container...")
        try:
            container = docker_client.containers.run(
                img_data["image"],
                **base_params,
                **docker_params  # Pass through Docker Compose parameters
            )
        except docker.errors.ImageNotFound:
            # Try to pull the image
            update_spinner(f"📥 Pulling image {img_data['image']}...")
            try:
                docker_client.images.pull(img_data['image'])
                update_spinner(f"🚀 Launching container...")
                container = docker_client.containers.run(
                    img_data["image"],
                    **base_params,
                    **docker_params
                )
            except Exception as pull_error:
                console.print(f"[red]❌ Failed to pull image: {pull_error}[/red]")
                return False, container_name

        # Wait for container to be running
        update_spinner(f"⏳ Waiting for container to be ready...")
        max_wait = 30
        elapsed = 0

        while elapsed < max_wait:
            container.reload()
            if container.status == "running":
                update_spinner(f"✅ Container {container_name} is running")
                return True, container_name
            elif container.status in ["exited", "dead"]:
                # Get logs for debugging
                logs = container.logs().decode('utf-8', errors='replace')
                console.print(f"[red]❌ Container failed to start[/red]")
                if logs:
                    console.print("[dim]Container logs:[/dim]")
                    console.print(logs[:500])
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
        log_exception(e, f"Docker API error while starting {container_name}")
        if "port is already allocated" in str(e).lower():
            console.print("[yellow]💡 Tip: The port is already in use by another container[/yellow]")
        return False, container_name
    except Exception as e:
        log_exception(e, f"Unexpected error while starting {container_name}")
        return False, container_name


def stop_container(container_name: str, remove: bool = True, progress=None, task_id=None) -> bool:
    """
    Stop a container
    Returns: success: bool

    Args:
        container_name: Name of the container to stop
        remove: Whether to remove the container after stopping
        progress: Optional Rich Progress object for spinner
        task_id: Optional task ID for updating spinner
    """
    if not container_name.startswith("playground-"):
        container_name = f"playground-{container_name}"

    def update_spinner(message: str):
        """Update spinner message if available"""
        if progress and task_id is not None:
            progress.update(task_id, description=message)
        else:
            console.print(f"[yellow]{message}[/yellow]")

    try:
        cont = docker_client.containers.get(container_name)

        update_spinner(f"🛑 Stopping container {container_name}...")
        cont.stop(timeout=10)  # 10 seconds is reasonable for dev environments

        if remove:
            update_spinner(f"🗑️  Removing container {container_name}...")
            cont.remove()
            update_spinner(f"✅ Container {container_name} stopped and removed")
        else:
            update_spinner(f"✅ Container {container_name} stopped")

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


def get_container_volumes(container_name: str) -> Dict[str, str]:
    """Get volumes mounted in a container"""
    if not container_name.startswith("playground-"):
        container_name = f"playground-{container_name}"
    
    try:
        cont = docker_client.containers.get(container_name)
        mounts = cont.attrs.get('Mounts', [])
        
        volumes_info = {}
        for mount in mounts:
            container_path = mount.get('Destination', '')
            mount_type = mount.get('Type', '')
            
            if mount_type == 'volume':
                volume_name = mount.get('Name', '')
                volumes_info[container_path] = f"[volume] {volume_name}"
            elif mount_type == 'bind':
                source = mount.get('Source', '')
                volumes_info[container_path] = f"[bind] {source}"
        
        return volumes_info
    except:
        return {}