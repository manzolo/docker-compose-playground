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

# Carica configurazioni da config.yml e config.d
def load_config():
    images = {}
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r") as f:
                config = yaml.safe_load(f)
                if config and isinstance(config, dict) and "images" in config:
                    images.update(config["images"])
                    logger.info("Loaded %d images from config.yml", len(config["images"]))
        except yaml.YAMLError as e:
            logger.error("Failed to parse config.yml: %s", str(e))
            raise HTTPException(500, f"Failed to parse config.yml: {str(e)}")
    
    if CONFIG_DIR.exists():
        config_files = glob.glob(str(CONFIG_DIR / "*.yml"))
        for config_file in config_files:
            try:
                with open(config_file, "r") as f:
                    config = yaml.safe_load(f)
                    if config and isinstance(config, dict) and "images" in config:
                        images.update(config["images"])
                        logger.info("Loaded images from %s", config_file)
            except yaml.YAMLError as e:
                logger.error("Failed to parse %s: %s", config_file, str(e))
                continue
    
    if not images:
        logger.error("No valid configurations found")
        raise HTTPException(500, "No valid configurations found")
    
    return dict(sorted(images.items(), key=lambda x: x[0].lower()))

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
    logger.info("Starting container: %s", image)
    config = load_config()
    if image not in config:
        raise HTTPException(404, "Image not found")
    
    img_data = config[image]
    container_name = f"playground-{image}"
    
    try:
        # Remove existing container
        try:
            existing = docker_client.containers.get(container_name)
            existing.stop()
            existing.remove()
        except docker.errors.NotFound:
            pass
        
        # Parse ports
        ports = {}
        for p in img_data.get("ports", []):
            host_port, container_port = p.split(":")
            ports[container_port] = host_port
        
        # Start container
        container = docker_client.containers.run(
            img_data["image"],
            detach=True,
            name=container_name,
            environment=img_data.get("environment", {}),
            ports=ports,
            volumes=[f"{Path.cwd() / 'shared-volumes'}:/shared"],
            command=img_data["keep_alive_cmd"],
            stdin_open=True,
            tty=True,
            labels={"playground.managed": "true"}
        )
        logger.info("Container started: %s", container.name)
        return {"status": "started", "container": container.name}
    except Exception as e:
        logger.error("Failed to start %s: %s", image, str(e))
        raise HTTPException(500, str(e))

@app.post("/stop/{container}")
async def stop_container(container: str):
    logger.info("Stopping container: %s", container)
    try:
        cont = docker_client.containers.get(container)
        cont.stop()
        cont.remove()
        return {"status": "stopped"}
    except docker.errors.NotFound:
        raise HTTPException(404, "Container not found")
    except Exception as e:
        logger.error("Error stopping %s: %s", container, str(e))
        raise HTTPException(500, str(e))

@app.get("/logs/{container}")
async def get_logs(container: str):
    try:
        cont = docker_client.containers.get(container)
        logs = cont.logs(tail=100).decode()
        return {"logs": logs}
    except docker.errors.NotFound:
        raise HTTPException(404, "Container not found")
    except Exception as e:
        raise HTTPException(500, str(e))

@app.websocket("/ws/console/{container}")
async def websocket_console(websocket: WebSocket, container: str):
    await websocket.accept()
    logger.info("WebSocket opened for %s", container)
    
    try:
        cont = docker_client.containers.get(container)
        config = load_config()
        image_name = container.replace("playground-", "", 1)
        shell = config.get(image_name, {}).get("shell", "/bin/bash")
        
        # Create exec instance
        exec_instance = docker_client.api.exec_create(
            container,
            shell,
            stdin=True,
            tty=True,
            environment={"TERM": "xterm-256color"}
        )
        
        exec_stream = docker_client.api.exec_start(
            exec_instance['Id'],
            socket=True,
            tty=True
        )
        
        socket = exec_stream._sock
        socket.setblocking(False)
        
        logger.info("Console session started for %s", container)
        
        async def read_from_container():
            """Read output from container and send to websocket"""
            while True:
                try:
                    await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
                    try:
                        data = socket.recv(4096)
                        if data:
                            # Decode and send to websocket
                            text = data.decode('utf-8', errors='replace')
                            await websocket.send_text(text)
                            logger.debug("Sent %d bytes to websocket", len(text))
                    except BlockingIOError:
                        # No data available, continue
                        continue
                except Exception as e:
                    logger.error("Error reading from container: %s", str(e))
                    break
        
        async def write_to_container():
            """Read input from websocket and send to container"""
            while True:
                try:
                    data = await websocket.receive_text()
                    if data:
                        socket.send(data.encode('utf-8'))
                        logger.debug("Sent %d bytes to container", len(data))
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected")
                    break
                except Exception as e:
                    logger.error("Error writing to container: %s", str(e))
                    break
        
        # Run both tasks concurrently
        await asyncio.gather(
            read_from_container(),
            write_to_container(),
            return_exceptions=True
        )
        
    except docker.errors.NotFound:
        await websocket.send_json({"error": "Container not found"})
    except Exception as e:
        logger.error("Console error for %s: %s", container, str(e))
        await websocket.send_json({"error": str(e)})
    finally:
        try:
            socket.close()
        except:
            pass
        try:
            await websocket.close()
        except:
            pass
        logger.info("Console session closed for %s", container)