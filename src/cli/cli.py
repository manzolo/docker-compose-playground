import typer
import docker
from typing import Optional
import yaml
from pathlib import Path
import json

app = typer.Typer(name="playground-cli", help="Independent Docker Playground CLI")

# Path alla config (relativo alla root del progetto)
CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yml"

# Carica config.yml
def load_config():
    if not CONFIG_PATH.exists():
        raise typer.BadParameter("Config file not found at config.yml")
    with CONFIG_PATH.open("r") as f:
        config = yaml.safe_load(f)
    return config.get("images", {})

# Inizializza Docker client
docker_client = docker.from_env()

@app.command()
def list(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    json: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """List available images."""
    config = load_config()
    images = [
        {"name": name, **data}
        for name, data in config.items()
        if not category or data.get("category") == category
    ]
    
    if json:
        typer.echo(json.dumps(images, indent=2))
    else:
        for img in images:
            typer.echo(f"- {img['name']}: {img.get('description', 'No description')}")

@app.command()
def start(
    image: str = typer.Argument(..., help="Image name from config"),
    detach: bool = typer.Option(True, "--detach/-i", help="Run in detached mode")
):
    """Start a container from config."""
    config = load_config()
    if image not in config:
        raise typer.BadParameter(f"Image {image} not found in config.")
    
    img_data = config[image]
    try:
        container = docker_client.containers.run(
            img_data["image"],
            detach=detach,
            name=f"playground-{image}",
            environment=img_data.get("environment", {}),
            ports={p.split(":")[1]: p.split(":")[0] for p in img_data.get("ports", [])},
            volumes=[f"{Path.cwd() / 'shared-volumes'}:/shared"],
            command=img_data["keep_alive_cmd"],
            labels={"playground.independent": "true"}
        )
        typer.echo(f"Started container: {container.name}")
        if post_script := img_data.get("scripts", {}).get("post_start", {}).get("inline"):
            typer.echo("Running post-start script...")
            # Esegui script inline in Bash (se necessario)
            docker_client.containers.get(container.name).exec_run(["bash", "-c", post_script])
    except docker.errors.DockerException as e:
        raise typer.Abort(f"Failed to start container: {str(e)}")

@app.command()
def stop(
    container: str = typer.Argument(..., help="Container name")
):
    """Stop a container."""
    try:
        cont = docker_client.containers.get(container)
        if "playground.independent" in cont.labels:
            cont.stop()
            typer.echo(f"Stopped {container}")
        else:
            raise typer.BadParameter("Container not managed by this CLI")
    except docker.errors.NotFound:
        raise typer.BadParameter(f"Container {container} not found.")

if __name__ == "__main__":
    app()