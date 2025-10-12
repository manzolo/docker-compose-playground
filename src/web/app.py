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
import subprocess
import os

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
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
SHARED_DIR = Path(__file__).parent.parent.parent / "shared-volumes"

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

def execute_script(script_config, container_name, image_name):
    """Execute post-start or pre-stop script"""
    if not script_config:
        return
    
    try:
        # Check if it's inline script
        if isinstance(script_config, dict) and 'inline' in script_config:
            logger.info("Executing inline script for %s", container_name)
            script_content = script_config['inline']
            
            # Create temporary script file
            temp_script = f"/tmp/playground-script-{container_name}.sh"
            with open(temp_script, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write(f'CONTAINER_NAME="{container_name}"\n')
                f.write(f'SHARED_DIR="{SHARED_DIR}"\n')
                f.write(script_content)
            
            os.chmod(temp_script, 0o755)
            
            # Execute script
            result = subprocess.run(
                ['bash', temp_script, container_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.stdout:
                logger.info("Script output: %s", result.stdout)
            if result.stderr:
                logger.warning("Script stderr: %s", result.stderr)
            
            # Cleanup
            os.remove(temp_script)
            
        # Check if it's file-based script
        elif isinstance(script_config, str):
            script_path = SCRIPTS_DIR / script_config
            if script_path.exists():
                logger.info("Executing script file: %s", script_config)
                result = subprocess.run(
                    ['bash', str(script_path), container_name],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env={**os.environ, 'SHARED_DIR': str(SHARED_DIR)}
                )
                
                if result.stdout:
                    logger.info("Script output: %s", result.stdout)
                if result.stderr:
                    logger.warning("Script stderr: %s", result.stderr)
            else:
                logger.warning("Script file not found: %s", script_path)
    
    except subprocess.TimeoutExpired:
        logger.error("Script timeout for %s", container_name)
    except Exception as e:
        logger.error("Script execution failed for %s: %s", container_name, str(e))

def get_motd(image_name, config):
    """Get MOTD for image"""
    img_data = config.get(image_name, {})
    return img_data.get('motd', '')

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
            volumes=[f"{SHARED_DIR}:/shared"],
            command=img_data["keep_alive_cmd"],
            stdin_open=True,
            tty=True,
            labels={"playground.managed": "true"}
        )
        logger.info("Container started: %s", container.name)
        
        # Execute post-start script
        scripts = img_data.get('scripts', {})
        if 'post_start' in scripts:
            logger.info("Running post-start script for %s", image)
            execute_script(scripts['post_start'], container_name, image)
        
        return {"status": "started", "container": container.name}
    except Exception as e:
        logger.error("Failed to start %s: %s", image, str(e))
        raise HTTPException(500, str(e))

@app.post("/stop/{container}")
async def stop_container(container: str):
    logger.info("Stopping container: %s", container)
    try:
        # Get image name from container name
        image_name = container.replace("playground-", "", 1)
        config = load_config()
        
        # Execute pre-stop script
        if image_name in config:
            scripts = config[image_name].get('scripts', {})
            if 'pre_stop' in scripts:
                logger.info("Running pre-stop script for %s", image_name)
                execute_script(scripts['pre_stop'], container, image_name)
        
        # Stop and remove container
        cont = docker_client.containers.get(container)
        cont.stop()
        cont.remove()
        logger.info("Container stopped: %s", container)
        
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

@app.get("/motd/{image}")
async def get_motd_endpoint(image: str):
    """Get MOTD for an image"""
    try:
        config = load_config()
        motd = get_motd(image, config)
        return {"motd": motd}
    except Exception as e:
        logger.error("Error getting MOTD for %s: %s", image, str(e))
        return {"motd": ""}

@app.websocket("/ws/console/{container}")
async def websocket_console(websocket: WebSocket, container: str):
    await websocket.accept()
    logger.info("WebSocket opened for %s", container)
    
    try:
        cont = docker_client.containers.get(container)
        config = load_config()
        image_name = container.replace("playground-", "", 1)
        shell = config.get(image_name, {}).get("shell", "/bin/bash")
        
        # Get MOTD
        motd = get_motd(image_name, config)
        
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
        
        # Send MOTD if available
        if motd:
            await websocket.send_text(motd + "\r\n\r\n")
        
        async def read_from_container():
            """Read output from container and send to websocket"""
            while True:
                try:
                    await asyncio.sleep(0.01)
                    try:
                        data = socket.recv(4096)
                        if data:
                            text = data.decode('utf-8', errors='replace')
                            await websocket.send_text(text)
                    except BlockingIOError:
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
                except WebSocketDisconnect:
                    logger.info("WebSocket disconnected")
                    break
                except Exception as e:
                    logger.error("Error writing to container: %s", str(e))
                    break
        
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