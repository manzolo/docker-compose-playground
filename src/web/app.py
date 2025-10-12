from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import docker
from pathlib import Path
import yaml
import logging
import glob
import asyncio
import signal

# Configura logging
logging.basicConfig(
    filename="venv/web.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Docker Playground Web Dashboard")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "templates/static"), name="static")
docker_client = docker.from_env()

# Path alla directory config.d e al file config.yml
CONFIG_DIR = Path(__file__).parent.parent.parent / "config.d"
CONFIG_FILE = Path(__file__).parent.parent.parent / "config.yml"

# Lista per tracciare i socket attivi
active_sockets = []

# Gestore per Ctrl+C
def handle_shutdown(loop):
    tasks = [task for task in asyncio.all_tasks(loop) if task is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()

# Carica configurazioni da config.yml e config.d
def load_config():
    images = {}
    
    # Carica config.yml
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r") as f:
                config = yaml.safe_load(f)
                if config and isinstance(config, dict) and "images" in config:
                    images.update(config["images"])
                    logger.info("Loaded %d images from config.yml: %s", len(config["images"]), list(config["images"].keys()))
                else:
                    logger.warning("Invalid or empty config.yml at %s", CONFIG_FILE)
        except yaml.YAMLError as e:
            logger.error("Failed to parse config.yml: %s", str(e))
            raise HTTPException(500, f"Failed to parse config.yml: {str(e)}")
    else:
        logger.warning("Config file not found at %s", CONFIG_FILE)

    # Carica e unisce config.d
    if CONFIG_DIR.exists():
        config_files = glob.glob(str(CONFIG_DIR / "*.yml"))
        logger.info("Found %d config files in %s: %s", len(config_files), CONFIG_DIR, [Path(f).name for f in config_files])
        for config_file in config_files:
            try:
                with open(config_file, "r") as f:
                    config = yaml.safe_load(f)
                    if not config or not isinstance(config, dict):
                        logger.warning("Invalid or empty config file: %s", config_file)
                        continue
                    if "images" not in config:
                        logger.warning("Missing images key in config file: %s", config_file)
                        continue
                    images.update(config["images"])
                    logger.info("Loaded images from %s: %s", config_file, list(config["images"].keys()))
            except yaml.YAMLError as e:
                logger.error("Failed to parse config file %s: %s", config_file, str(e))
                continue
        if not config_files:
            logger.warning("No config files found in %s", CONFIG_DIR)
    else:
        logger.warning("Config directory not found at %s", CONFIG_DIR)

    if not images:
        logger.error("No valid configurations found in config.yml or config.d")
        raise HTTPException(500, "No valid configurations found")

    # Ordina le immagini alfabeticamente
    sorted_images = dict(sorted(images.items(), key=lambda x: x[0].lower()))
    logger.info("Final loaded images: %s", list(sorted_images.keys()))
    return sorted_images

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    try:
        config = load_config()
        running = docker_client.containers.list(all=True)
        running_dict = {}
        for c in running:
            if c.name.startswith("playground-"):
                image_name = c.name.replace("playground-", "", 1)
                running_dict[image_name] = {"name": c.name, "status": c.status}
        logger.info("Loaded %d running containers: %s", len(running_dict), list(running_dict.keys()))
        return templates.TemplateResponse("index.html", {
            "request": request,
            "images": config,
            "running": running_dict
        })
    except Exception as e:
        logger.error("Error loading dashboard: %s", str(e))
        raise HTTPException(500, f"Error loading dashboard: {str(e)}")

@app.post("/start/{image}")
async def start_container(image: str):
    logger.info("Attempting to start container for image: %s", image)
    config = load_config()
    if image not in config:
        logger.error("Image not found in config: %s", image)
        raise HTTPException(404, "Image not found")
    img_data = config[image]

    # Validazione dei dati
    if "image" not in img_data:
        logger.error("Missing 'image' key for %s", image)
        raise HTTPException(500, "Missing 'image' key in config")
    if "keep_alive_cmd" not in img_data:
        logger.error("Missing 'keep_alive_cmd' key for %s", image)
        raise HTTPException(500, "Missing 'keep_alive_cmd' key in config")

    container_name = f"playground-{image}"
    try:
        # Controlla se il container esiste
        try:
            existing_container = docker_client.containers.get(container_name)
            logger.info("Container %s already exists, stopping and removing it", container_name)
            existing_container.stop()
            existing_container.remove()
        except docker.errors.NotFound:
            logger.info("No existing container found for %s", container_name)

        # Gestione porte
        ports = {}
        for p in img_data.get("ports", []):
            try:
                host_port, container_port = p.split(":")
                ports[container_port] = host_port
            except ValueError:
                logger.error("Invalid port format for %s: %s", image, p)
                raise HTTPException(500, f"Invalid port format: {p}")

        container = docker_client.containers.run(
            img_data["image"],
            detach=True,
            name=container_name,
            environment=img_data.get("environment", {}),
            ports=ports,
            volumes=[f"{Path.cwd() / 'shared-volumes'}:/shared"],
            command=img_data["keep_alive_cmd"],
            labels={"playground.independent": "true"}
        )
        logger.info("Container started: %s", container.name)
        return {"status": "started", "container": container.name}
    except docker.errors.DockerException as e:
        logger.error("Failed to start container %s: %s", image, str(e))
        raise HTTPException(500, f"Failed to start container: {str(e)}")
    except Exception as e:
        logger.error("Unexpected error starting container %s: %s", image, str(e))
        raise HTTPException(500, f"Unexpected error: {str(e)}")

@app.post("/stop/{container}")
async def stop_container(container: str):
    logger.info("Attempting to stop container: %s", container)
    try:
        cont = docker_client.containers.get(container)
        if not container.startswith("playground-"):
            logger.error("Container not managed by this dashboard: %s", container)
            raise HTTPException(400, "Container not managed by this dashboard")
        cont.stop()
        cont.remove()
        logger.info("Container stopped and removed: %s", container)
        return {"status": "stopped"}
    except docker.errors.NotFound:
        logger.error("Container not found: %s", container)
        raise HTTPException(404, "Container not found")
    except Exception as e:
        logger.error("Error stopping container %s: %s", container, str(e))
        raise HTTPException(500, f"Error stopping container: {str(e)}")

@app.get("/logs/{container}")
async def get_logs(container: str):
    logger.info("Fetching logs for container: %s", container)
    try:
        cont = docker_client.containers.get(container)
        if not container.startswith("playground-"):
            logger.error("Container not managed by this dashboard: %s", container)
            raise HTTPException(400, "Container not managed by this dashboard")
        logs = cont.logs(tail=100).decode()
        logger.info("Logs retrieved for container: %s", container)
        return {"logs": logs}
    except docker.errors.NotFound:
        logger.error("Container not found: %s", container)
        raise HTTPException(404, "Container not found")
    except Exception as e:
        logger.error("Error fetching logs for container %s: %s", container, str(e))
        raise HTTPException(500, f"Error fetching logs: {str(e)}")

@app.websocket("/ws/console/{container}")
async def websocket_console(websocket: WebSocket, container: str):
    await websocket.accept()
    logger.info("WebSocket connection opened for %s", container)
    socket = None
    try:
        cont = docker_client.containers.get(container)
        if not container.startswith("playground-"):
            logger.error("Container not managed by this dashboard: %s", container)
            await websocket.send_json({"error": "Container not managed by this dashboard"})
            await websocket.close()
            return

        # Ottiene la shell dal config
        config = load_config()
        image_name = container.replace("playground-", "", 1)
        shell = config.get(image_name, {}).get("shell", "/bin/sh")
        logger.info("Opening console for container %s with shell %s", container, shell)

        # Avvia una sessione interattiva con docker-py
        try:
            exec_id = docker_client.api.exec_create(
                container,
                shell,
                stdin=True,
                tty=True,
                environment={"TERM": "xterm-256color"}
            )
            exec_stream = docker_client.api.exec_start(
                exec_id,
                socket=True,
                tty=True
            )
            socket = exec_stream._sock
            socket.settimeout(None)
            active_sockets.append(socket)
            logger.debug("Exec session started for %s with exec_id %s", container, exec_id['Id'])
        except docker.errors.APIError as e:
            logger.error("Failed to start exec session for %s: %s", container, str(e))
            await websocket.send_text(f"Error: Failed to start console: {str(e)}")
            await websocket.close()
            return

        async def forward_output():
            while True:
                try:
                    data = socket.recv(4096)
                    if not data:
                        logger.debug("No more data from %s, closing output", container)
                        break
                    decoded_data = data.decode('utf-8', errors='replace')
                    logger.debug("Output from %s: %s", container, decoded_data.strip())
                    await websocket.send_text(decoded_data)
                    logger.debug("Sent %d bytes to WebSocket for %s", len(decoded_data), container)
                except Exception as e:
                    logger.error("Error reading from container %s: %s", container, str(e))
                    await websocket.send_text(f"Error: {str(e)}")
                    break

        async def forward_input():
            while True:
                try:
                    data = await websocket.receive_text()
                    logger.debug("Input to %s: %s", container, data.strip())
                    socket.send(data.encode('utf-8'))
                    logger.debug("Sent %d bytes to container %s", len(data), container)
                except WebSocketDisconnect as e:
                    logger.info("WebSocket disconnected for %s: %s", container, str(e))
                    break
                except Exception as e:
                    logger.error("Error sending input to container %s: %s", container, str(e))
                    await websocket.send_text(f"Error: {str(e)}")
                    break

        async def keep_alive():
            while True:
                try:
                    await websocket.send_text("")
                    logger.debug("Sent keep-alive to WebSocket for %s", container)
                    await asyncio.sleep(30)
                except Exception as e:
                    logger.debug("Keep-alive failed for %s: %s", container, str(e))
                    break

        # Esegui input, output e keep-alive in parallelo
        tasks = [
            asyncio.create_task(forward_output()),
            asyncio.create_task(forward_input()),
            asyncio.create_task(keep_alive())
        ]
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # Pulizia
        logger.debug("Closing exec socket for %s", container)
        if socket:
            socket.close()
            if socket in active_sockets:
                active_sockets.remove(socket)
        logger.info("Console session for container %s closed", container)
    except docker.errors.NotFound:
        logger.error("Container not found for console: %s", container)
        await websocket.send_json({"error": "Container not found"})
    except Exception as e:
        logger.error("Error in console for container %s: %s", container, str(e))
        await websocket.send_text(f"Error: {str(e)}")
    finally:
        try:
            await websocket.close()
            logger.debug("WebSocket closed for %s", container)
            if socket and socket in active_sockets:
                socket.close()
                active_sockets.remove(socket)
        except Exception as e:
            logger.debug("Error closing WebSocket for %s: %s", container, str(e))

# Gestione shutdown pulito
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down server, closing all active sockets")
    for sock in active_sockets:
        try:
            sock.close()
        except Exception as e:
            logger.debug("Error closing socket: %s", str(e))
    active_sockets.clear()