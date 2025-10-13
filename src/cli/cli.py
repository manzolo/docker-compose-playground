#!/usr/bin/env python3
"""
Docker Playground CLI - Enhanced Version
Complete command-line interface for Docker Playground management
"""

import typer
import docker
from typing import Optional, List
import yaml
from pathlib import Path
import json as json_lib
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint
import glob
import subprocess
import time

app = typer.Typer(
    name="playground",
    help="🐳 Docker Playground CLI - Manage containerized development environments",
    add_completion=True
)

console = Console()

# Paths
BASE_PATH = Path(__file__).parent.parent.parent
CONFIG_FILE = BASE_PATH / "config.yml"
CONFIG_DIR = BASE_PATH / "config.d"
CUSTOM_CONFIG_DIR = BASE_PATH / "custom.d"
SHARED_DIR = BASE_PATH / "shared-volumes"
SCRIPTS_DIR = BASE_PATH / "scripts"
NETWORK_NAME = "playground-network"

# Initialize Docker client
try:
    docker_client = docker.from_env()
except docker.errors.DockerException:
    console.print("[red]❌ Could not connect to Docker. Is Docker running?[/red]")
    raise typer.Exit(1)


def load_config() -> dict:
    """Load configuration from all sources (config.yml, config.d, custom.d)"""
    images = {}
    
    # Load from config.yml
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r") as f:
                config = yaml.safe_load(f)
                if config and isinstance(config, dict) and "images" in config:
                    images.update(config["images"])
        except yaml.YAMLError as e:
            console.print(f"[red]❌ Failed to parse config.yml: {e}[/red]")
            raise typer.Exit(1)
    
    # Load from config.d
    if CONFIG_DIR.exists():
        for config_file in CONFIG_DIR.glob("*.yml"):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    if config and isinstance(config, dict) and "images" in config:
                        images.update(config["images"])
            except yaml.YAMLError as e:
                console.print(f"[yellow]⚠ Failed to parse {config_file}: {e}[/yellow]")
    
    # Load from custom.d
    if CUSTOM_CONFIG_DIR.exists():
        for config_file in CUSTOM_CONFIG_DIR.glob("*.yml"):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    if config and isinstance(config, dict) and "images" in config:
                        images.update(config["images"])
            except yaml.YAMLError as e:
                console.print(f"[yellow]⚠ Failed to parse {config_file}: {e}[/yellow]")
    
    if not images:
        console.print("[red]❌ No valid configurations found[/red]")
        raise typer.Exit(1)
    
    return dict(sorted(images.items(), key=lambda x: x[0].lower()))


def ensure_network():
    """Ensure playground network exists"""
    try:
        docker_client.networks.get(NETWORK_NAME)
    except docker.errors.NotFound:
        docker_client.networks.create(NETWORK_NAME, driver="bridge")
        console.print(f"[green]✓ Created network: {NETWORK_NAME}[/green]")


def get_playground_containers() -> List:
    """Get all playground containers"""
    return docker_client.containers.list(
        all=True,
        filters={"label": "playground.managed=true"}
    )


def execute_script(script_config, container_name: str, image_name: str):
    """Execute post-start or pre-stop script"""
    if not script_config:
        return
    
    try:
        if isinstance(script_config, dict) and 'inline' in script_config:
            # Inline script
            script_content = script_config['inline']
            temp_script = f"/tmp/playground-script-{container_name}.sh"
            
            with open(temp_script, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write(f'CONTAINER_NAME="{container_name}"\n')
                f.write(f'SHARED_DIR="{SHARED_DIR}"\n')
                f.write(script_content)
            
            Path(temp_script).chmod(0o755)
            
            result = subprocess.run(
                ['bash', temp_script, container_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                console.print(f"[green]✓ Script executed successfully[/green]")
            else:
                console.print(f"[yellow]⚠ Script exited with code {result.returncode}[/yellow]")
            
            Path(temp_script).unlink()
            
        elif isinstance(script_config, str):
            # File-based script
            script_path = SCRIPTS_DIR / script_config
            if script_path.exists():
                result = subprocess.run(
                    ['bash', str(script_path), container_name],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env={'SHARED_DIR': str(SHARED_DIR)}
                )
                
                if result.returncode == 0:
                    console.print(f"[green]✓ Script {script_config} executed[/green]")
                else:
                    console.print(f"[yellow]⚠ Script exited with code {result.returncode}[/yellow]")
            else:
                console.print(f"[yellow]⚠ Script file not found: {script_path}[/yellow]")
    
    except subprocess.TimeoutExpired:
        console.print(f"[red]❌ Script timeout for {container_name}[/red]")
    except Exception as e:
        console.print(f"[red]❌ Script execution failed: {e}[/red]")


# ========================================
# COMMANDS
# ========================================

@app.command()
def list(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (running/stopped)"),
    json: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """📋 List available containers"""
    config = load_config()
    
    # Get running containers
    running_containers = {
        c.name.replace("playground-", ""): c.status 
        for c in get_playground_containers()
    }
    
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
        
        table = Table(title="🐳 Docker Playground Containers")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Category", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Image", style="blue")
        table.add_column("Description", style="white")
        
        for img in images_list:
            status_emoji = "▶" if img["status"] == "running" else "⏹"
            status_color = "green" if img["status"] == "running" else "red"
            
            table.add_row(
                img["name"],
                img["category"],
                f"[{status_color}]{status_emoji} {img['status']}[/{status_color}]",
                img["image"],
                img["description"][:50] + "..." if len(img["description"]) > 50 else img["description"]
            )
        
        console.print(table)
        console.print(f"\n[cyan]Total: {len(images_list)} containers[/cyan]")


@app.command()
def start(
    image: str = typer.Argument(..., help="Container name from config"),
    force: bool = typer.Option(False, "--force", "-f", help="Force restart if already running")
):
    """▶ Start a container"""
    config = load_config()
    
    if image not in config:
        console.print(f"[red]❌ Container '{image}' not found in config[/red]")
        raise typer.Exit(1)
    
    img_data = config[image]
    container_name = f"playground-{image}"
    
    ensure_network()
    
    try:
        # Check if already exists
        try:
            existing = docker_client.containers.get(container_name)
            if existing.status == "running" and not force:
                console.print(f"[yellow]⚠ Container already running: {container_name}[/yellow]")
                return
            
            console.print(f"[yellow]Removing existing container...[/yellow]")
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
            hostname=image,
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
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Waiting for container to start...", total=None)
            
            while elapsed < max_wait:
                container.reload()
                if container.status == "running":
                    break
                elif container.status in ["exited", "dead"]:
                    console.print(f"[red]❌ Container failed to start: {container.status}[/red]")
                    raise typer.Exit(1)
                
                time.sleep(0.5)
                elapsed += 0.5
        
        if container.status != "running":
            console.print(f"[red]❌ Container did not start in time[/red]")
            raise typer.Exit(1)
        
        console.print(f"[green]✓ Container started successfully: {container_name}[/green]")
        
        # Execute post-start script
        scripts = img_data.get('scripts', {})
        if 'post_start' in scripts:
            console.print("[cyan]Running post-start script...[/cyan]")
            execute_script(scripts['post_start'], container_name, image)
        
        # Show connection info
        if ports:
            console.print("\n[cyan]Port mappings:[/cyan]")
            for container_port, host_port in ports.items():
                console.print(f"  • localhost:{host_port} → {container_port}")
        
    except docker.errors.ImageNotFound:
        console.print(f"[red]❌ Docker image not found: {img_data['image']}[/red]")
        console.print(f"[yellow]Try pulling it first: docker pull {img_data['image']}[/yellow]")
        raise typer.Exit(1)
    except docker.errors.APIError as e:
        console.print(f"[red]❌ Docker error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def stop(
    container: str = typer.Argument(..., help="Container name"),
    remove: bool = typer.Option(True, "--remove/--no-remove", help="Remove container after stopping")
):
    """⏹ Stop a container"""
    container_name = container if container.startswith("playground-") else f"playground-{container}"
    
    try:
        cont = docker_client.containers.get(container_name)
        
        # Get image name for pre-stop script
        image_name = container_name.replace("playground-", "")
        config = load_config()
        
        # Execute pre-stop script
        if image_name in config:
            scripts = config[image_name].get('scripts', {})
            if 'pre_stop' in scripts:
                console.print("[cyan]Running pre-stop script...[/cyan]")
                execute_script(scripts['pre_stop'], container_name, image_name)
        
        console.print(f"[yellow]Stopping container: {container_name}...[/yellow]")
        cont.stop(timeout=90)
        
        if remove:
            console.print(f"[yellow]Removing container...[/yellow]")
            cont.remove()
        
        console.print(f"[green]✓ Container stopped: {container_name}[/green]")
        
    except docker.errors.NotFound:
        console.print(f"[red]❌ Container not found: {container_name}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def restart(
    container: str = typer.Argument(..., help="Container name")
):
    """🔄 Restart a container"""
    container_name = container if container.startswith("playground-") else f"playground-{container}"
    
    try:
        cont = docker_client.containers.get(container_name)
        console.print(f"[yellow]Restarting container: {container_name}...[/yellow]")
        cont.restart(timeout=30)
        console.print(f"[green]✓ Container restarted: {container_name}[/green]")
    except docker.errors.NotFound:
        console.print(f"[red]❌ Container not found: {container_name}[/red]")
        raise typer.Exit(1)


@app.command()
def logs(
    container: str = typer.Argument(..., help="Container name"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    tail: int = typer.Option(100, "--tail", "-n", help="Number of lines to show")
):
    """📋 Show container logs"""
    container_name = container if container.startswith("playground-") else f"playground-{container}"
    
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
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped following logs[/yellow]")


@app.command()
def exec(
    container: str = typer.Argument(..., help="Container name"),
    command: str = typer.Argument(None, help="Command to execute (default: shell)")
):
    """💻 Execute command in container"""
    container_name = container if container.startswith("playground-") else f"playground-{container}"
    
    try:
        cont = docker_client.containers.get(container_name)
        
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
    
    except docker.errors.NotFound:
        console.print(f"[red]❌ Container not found: {container_name}[/red]")
        raise typer.Exit(1)


@app.command()
def ps(
    all: bool = typer.Option(False, "--all", "-a", help="Show all containers (including stopped)")
):
    """📊 List running playground containers"""
    containers = docker_client.containers.list(
        all=all,
        filters={"label": "playground.managed=true"}
    )
    
    if not containers:
        console.print("[yellow]No playground containers found[/yellow]")
        return
    
    table = Table(title="🐳 Playground Containers")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Image", style="blue")
    table.add_column("Ports", style="magenta")
    
    for c in containers:
        status_color = "green" if c.status == "running" else "red"
        ports = ", ".join([f"{p['HostPort']}→{p['PrivatePort']}" for p in c.attrs['NetworkSettings']['Ports'].values() if p] if c.attrs['NetworkSettings']['Ports'] else [])
        
        table.add_row(
            c.name,
            f"[{status_color}]{c.status}[/{status_color}]",
            c.image.tags[0] if c.image.tags else c.image.short_id,
            ports or "none"
        )
    
    console.print(table)


@app.command()
def stop_all(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation")
):
    """⏹ Stop all running containers"""
    containers = docker_client.containers.list(filters={"label": "playground.managed=true"})
    
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
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task(f"Stopping {len(containers)} containers...", total=len(containers))
        
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
    containers = docker_client.containers.list(
        all=True,
        filters={"label": "playground.managed=true"}
    )
    
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
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task(f"Removing {len(containers)} containers...", total=len(containers))
        
        for c in containers:
            try:
                if c.status == "running":
                    c.stop(timeout=30)
                c.remove()
                progress.advance(task)
            except Exception as e:
                console.print(f"[red]Failed to remove {c.name}: {e}[/red]")
    
    console.print(f"[green]✓ Removed {len(containers)} containers[/green]")
    
    # Remove images if requested
    if remove_images and image_names:
        console.print(f"\n[yellow]Removing {len(image_names)} images...[/yellow]")
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
            task = progress.add_task("Removing images...", total=len(image_names))
            
            for img_name in image_names:
                try:
                    docker_client.images.remove(img_name, force=True)
                    console.print(f"[green]✓ Removed image: {img_name}[/green]")
                    progress.advance(task)
                except Exception as e:
                    console.print(f"[yellow]⚠ Could not remove {img_name}: {e}[/yellow]")
        
        console.print(f"[green]✓ Image cleanup complete[/green]")


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
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        task = progress.add_task(f"Removing {len(images_to_remove)} images...", total=len(images_to_remove))
        
        removed = 0
        for tag, img in images_to_remove:
            try:
                docker_client.images.remove(tag, force=True)
                removed += 1
                progress.advance(task)
            except docker.errors.APIError as e:
                console.print(f"[red]Failed to remove {tag}: {e}[/red]")
    
    console.print(f"[green]✓ Removed {removed}/{len(images_to_remove)} images ({total_size_mb:.2f} MB freed)[/green]")


@app.command()
def categories():
    """📚 List all categories"""
    config = load_config()
    
    # Count containers per category
    categories_count = {}
    for img_data in config.values():
        cat = img_data.get("category", "other")
        categories_count[cat] = categories_count.get(cat, 0) + 1
    
    table = Table(title="📚 Categories")
    table.add_column("Category", style="cyan")
    table.add_column("Containers", style="green", justify="right")
    
    for cat in sorted(categories_count.keys()):
        table.add_row(cat, str(categories_count[cat]))
    
    console.print(table)
    console.print(f"\n[cyan]Total: {len(categories_count)} categories[/cyan]")


@app.command()
def info(
    container: str = typer.Argument(..., help="Container name")
):
    """ℹ️ Show detailed container information"""
    container_name = container if container.startswith("playground-") else f"playground-{container}"
    
    try:
        cont = docker_client.containers.get(container_name)
        config = load_config()
        image_name = container_name.replace("playground-", "")
        
        console.print(f"\n[cyan bold]Container: {container_name}[/cyan bold]\n")
        
        table = Table(show_header=False, box=None)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Status", f"[{'green' if cont.status == 'running' else 'red'}]{cont.status}[/]")
        table.add_row("Image", cont.image.tags[0] if cont.image.tags else cont.image.short_id)
        table.add_row("Created", cont.attrs['Created'][:19])
        
        if image_name in config:
            img_data = config[image_name]
            table.add_row("Category", img_data.get("category", "N/A"))
            table.add_row("Description", img_data.get("description", "N/A"))
        
        # Network info
        networks = cont.attrs.get('NetworkSettings', {}).get('Networks', {})
        if networks and isinstance(networks, dict):
            network_names = [str(k) for k in networks.keys()]
            table.add_row("Networks", ", ".join(network_names))
        else:
            table.add_row("Networks", "None")
        
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
                table.add_row("Ports", ", ".join(port_mappings))
            else:
                table.add_row("Ports", "None (exposed but not mapped)")
        else:
            table.add_row("Ports", "None")
        
        console.print(table)
        console.print()
        
    except docker.errors.NotFound:
        console.print(f"[red]❌ Container not found: {container_name}[/red]")
        raise typer.Exit(1)


@app.command()
def version():
    """🔖 Show version information"""
    console.print("[cyan bold]Docker Playground CLI[/cyan bold]")
    console.print("Version: 2.0.0")
    console.print(f"Docker API: {docker_client.version()['Version']}")
    console.print(f"Config path: {CONFIG_FILE}")


if __name__ == "__main__":
    app()