from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
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
from datetime import datetime

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
NETWORK_NAME = "playground-network"

# Create playground network if not exists
def ensure_network():
    """Ensure playground network exists"""
    try:
        docker_client.networks.get(NETWORK_NAME)
        logger.info("Network %s already exists", NETWORK_NAME)
    except docker.errors.NotFound:
        logger.info("Creating network %s", NETWORK_NAME)
        docker_client.networks.create(NETWORK_NAME, driver="bridge")
        logger.info("Network %s created", NETWORK_NAME)

# Call on startup
ensure_network()

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

def format_motd_for_terminal(motd):
    """Format MOTD with proper ANSI colors and line endings"""
    if not motd:
        return ""
    
    # Replace line endings with \r\n for terminal
    formatted = motd.replace('\n', '\r\n')
    
    # Add some ANSI colors for better readability
    # Headers with ═ get cyan color
    lines = formatted.split('\r\n')
    colored_lines = []
    for line in lines:
        if '═' in line or '║' in line:
            # Box drawing characters - cyan
            colored_lines.append(f'\x1b[36m{line}\x1b[0m')
        elif line.strip().startswith('🔐') or line.strip().startswith('📊') or line.strip().startswith('📁'):
            # Section headers - green bold
            colored_lines.append(f'\x1b[1;32m{line}\x1b[0m')
        elif line.strip().startswith('💡') or line.strip().startswith('⚠️'):
            # Tips/warnings - yellow
            colored_lines.append(f'\x1b[33m{line}\x1b[0m')
        else:
            colored_lines.append(line)
    
    return '\r\n'.join(colored_lines) + '\r\n'

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
        
        # Get all unique categories and their counts
        categories = set()
        category_counts = {}
        for img_name, img_data in config.items():
            cat = img_data.get('category', 'other')
            categories.add(cat)
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "images": config,
            "running": running_dict,
            "categories": sorted(categories),
            "category_counts": category_counts
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
        # Ensure network exists
        ensure_network()
        
        # Remove existing container
        try:
            existing = docker_client.containers.get(container_name)
            logger.info("Removing existing container: %s", container_name)
            existing.stop(timeout=10)
            existing.remove()
        except docker.errors.NotFound:
            pass
        
        # Parse ports
        ports = {}
        for p in img_data.get("ports", []):
            host_port, container_port = p.split(":")
            ports[container_port] = host_port
        
        # Start container
        logger.info("Starting new container: %s", container_name)
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
        logger.info("Container created: %s", container.name)
        
        # Wait for container to be running (with timeout)
        max_wait = 30  # 30 seconds max
        wait_interval = 0.5  # Check every 500ms
        elapsed = 0
        
        while elapsed < max_wait:
            try:
                container.reload()  # Refresh container state
                if container.status == "running":
                    logger.info("Container %s is now running after %.1fs", container_name, elapsed)
                    break
                elif container.status in ["exited", "dead"]:
                    logger.error("Container %s failed to start: %s", container_name, container.status)
                    # Get logs for debugging
                    logs = container.logs(tail=50).decode('utf-8', errors='replace')
                    logger.error("Container logs: %s", logs)
                    raise HTTPException(500, f"Container failed to start: {container.status}")
            except docker.errors.NotFound:
                logger.error("Container %s not found after creation", container_name)
                raise HTTPException(500, "Container disappeared after creation")
            
            await asyncio.sleep(wait_interval)
            elapsed += wait_interval
        
        # Check final status
        container.reload()
        if container.status != "running":
            logger.warning("Container %s not running after %ds (status: %s)", 
                          container_name, max_wait, container.status)
            raise HTTPException(500, f"Container did not start in time (status: {container.status})")
        
        # Execute post-start script (async, don't wait)
        scripts = img_data.get('scripts', {})
        if 'post_start' in scripts:
            logger.info("Scheduling post-start script for %s", image)
            # Run in background
            asyncio.create_task(run_script_async(scripts['post_start'], container_name, image))
        
        return {
            "status": "started", 
            "container": container.name,
            "ready": True
        }
        
    except docker.errors.ImageNotFound:
        logger.error("Image not found: %s", img_data["image"])
        raise HTTPException(404, f"Docker image not found: {img_data['image']}")
    except docker.errors.APIError as e:
        logger.error("Docker API error starting %s: %s", image, str(e))
        raise HTTPException(500, f"Docker error: {str(e)}")
    except Exception as e:
        logger.error("Failed to start %s: %s", image, str(e))
        raise HTTPException(500, str(e))

async def run_script_async(script_config, container_name, image_name):
    """Run script asynchronously without blocking response"""
    try:
        logger.info("Running post-start script for %s", image_name)
        await asyncio.to_thread(execute_script, script_config, container_name, image_name)
        logger.info("Post-start script completed for %s", image_name)
    except Exception as e:
        logger.error("Post-start script failed for %s: %s", image_name, str(e))

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
        cont.stop(timeout=60)  # Aumentato a 60 secondi
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

@app.get("/manage", response_class=HTMLResponse)
async def manage_page(request: Request):
    """Advanced manager page"""
    try:
        config = load_config()
        running = docker_client.containers.list(filters={"label": "playground.managed=true"})
        
        # Count by category
        categories = {}
        for img_name, img_data in config.items():
            cat = img_data.get('category', 'other')
            categories[cat] = categories.get(cat, 0) + 1
        
        # Network info
        try:
            network = docker_client.networks.get(NETWORK_NAME)
            network_info = {"name": network.name, "driver": network.attrs.get('Driver', 'N/A')}
        except:
            network_info = {"name": "Not created", "driver": "N/A"}
        
        return templates.TemplateResponse("manage.html", {
            "request": request,
            "total_images": len(config),
            "running_count": len(running),
            "stopped_count": len(config) - len(running),
            "categories": categories,
            "network_info": network_info
        })
    except Exception as e:
        logger.error("Error loading manage page: %s", str(e))
        raise HTTPException(500, str(e))

@app.post("/api/start-category/{category}")
async def start_category(category: str):
    """Start all containers in a category"""
    try:
        config = load_config()
        started = []
        
        for img_name, img_data in config.items():
            if img_data.get('category') == category:
                container_name = f"playground-{img_name}"
                
                # Check if already running
                try:
                    existing = docker_client.containers.get(container_name)
                    if existing.status == "running":
                        continue
                except docker.errors.NotFound:
                    pass
                
                # Start container
                try:
                    ensure_network()
                    ports = {}
                    for p in img_data.get("ports", []):
                        host_port, container_port = p.split(":")
                        ports[container_port] = host_port
                    
                    container = docker_client.containers.run(
                        img_data["image"],
                        detach=True,
                        name=container_name,
                        hostname=img_name,
                        environment=img_data.get("environment", {}),
                        ports=ports,
                        volumes=[f"{SHARED_DIR}:/shared"],
                        command=img_data["keep_alive_cmd"],
                        network=NETWORK_NAME,
                        stdin_open=True,
                        tty=True,
                        labels={"playground.managed": "true"}
                    )
                    started.append(container_name)
                    logger.info("Started %s in category %s", container_name, category)
                except Exception as e:
                    logger.error("Failed to start %s: %s", img_name, str(e))
        
        return {"status": "ok", "started": len(started), "containers": started}
    except Exception as e:
        logger.error("Error starting category %s: %s", category, str(e))
        raise HTTPException(500, str(e))

@app.post("/api/stop-all")
async def stop_all():
    """Stop all running playground containers"""
    try:
        containers = docker_client.containers.list(filters={"label": "playground.managed=true"})
        stopped = []
        
        for container in containers:
            try:
                container.stop(timeout=30)
                container.remove()
                stopped.append(container.name)
                logger.info("Stopped %s", container.name)
            except Exception as e:
                logger.error("Failed to stop %s: %s", container.name, str(e))
        
        return {"status": "ok", "stopped": len(stopped), "containers": stopped}
    except Exception as e:
        logger.error("Error stopping all: %s", str(e))
        raise HTTPException(500, str(e))

@app.post("/api/restart-all")
async def restart_all():
    """Restart all running playground containers"""
    try:
        containers = docker_client.containers.list(filters={"label": "playground.managed=true"})
        restarted = []
        
        for container in containers:
            try:
                container.restart(timeout=10)
                restarted.append(container.name)
                logger.info("Restarted %s", container.name)
            except Exception as e:
                logger.error("Failed to restart %s: %s", container.name, str(e))
        
        return {"status": "ok", "restarted": len(restarted), "containers": restarted}
    except Exception as e:
        logger.error("Error restarting all: %s", str(e))
        raise HTTPException(500, str(e))

@app.post("/api/cleanup-all")
async def cleanup_all():
    """Stop and remove ALL playground containers"""
    try:
        containers = docker_client.containers.list(
            all=True, 
            filters={"label": "playground.managed=true"}
        )
        removed = []
        
        for container in containers:
            try:
                if container.status == "running":
                    container.stop(timeout=10)
                container.remove()
                removed.append(container.name)
                logger.info("Removed %s", container.name)
            except Exception as e:
                logger.error("Failed to remove %s: %s", container.name, str(e))
        
        return {"status": "ok", "removed": len(removed), "containers": removed}
    except Exception as e:
        logger.error("Error cleaning up: %s", str(e))
        raise HTTPException(500, str(e))

@app.get("/api/system-info")
async def system_info():
    """Get system information"""
    try:
        # Docker info
        docker_info = docker_client.info()
        
        # Network info
        try:
            network = docker_client.networks.get(NETWORK_NAME)
            network_data = {
                "name": network.name,
                "driver": network.attrs.get('Driver', 'bridge'),
                "subnet": network.attrs.get('IPAM', {}).get('Config', [{}])[0].get('Subnet', 'N/A')
            }
        except:
            network_data = {"name": "Not found", "driver": "N/A", "subnet": "N/A"}
        
        # Volume info
        import os
        volume_size = "N/A"
        if SHARED_DIR.exists():
            try:
                total_size = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, dirnames, filenames in os.walk(SHARED_DIR)
                    for filename in filenames
                )
                volume_size = f"{total_size / (1024*1024):.2f} MB"
            except:
                pass
        
        # Active containers
        containers = docker_client.containers.list(filters={"label": "playground.managed=true"})
        active = [{"name": c.name, "status": c.status} for c in containers]
        
        return {
            "docker": {
                "version": docker_info.get('ServerVersion', 'N/A'),
                "containers": docker_info.get('Containers', 0),
                "images": docker_info.get('Images', 0)
            },
            "network": network_data,
            "volume": {
                "path": str(SHARED_DIR),
                "size": volume_size
            },
            "active_containers": active
        }
    except Exception as e:
        logger.error("Error getting system info: %s", str(e))
        raise HTTPException(500, str(e))

@app.get("/api/export-config")
async def export_config():
    """Export merged configuration"""
    from fastapi.responses import FileResponse
    import tempfile
    
    try:
        config = load_config()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as f:
            yaml.dump({"images": config}, f, default_flow_style=False)
            temp_path = f.name
        
        return FileResponse(
            temp_path,
            media_type='application/x-yaml',
            filename=f'playground-config-{datetime.now().strftime("%Y%m%d")}.yml'
        )
    except Exception as e:
        logger.error("Error exporting config: %s", str(e))
        raise HTTPException(500, str(e))

@app.get("/api/logs")
async def get_server_logs():
    """Get server logs"""
    try:
        if Path("venv/web.log").exists():
            with open("venv/web.log", "r") as f:
                logs = f.read()
            return HTMLResponse(f"<pre>{logs}</pre>")
        else:
            return HTMLResponse("<pre>No logs found</pre>")
    except Exception as e:
        return HTMLResponse(f"<pre>Error reading logs: {str(e)}</pre>")

@app.get("/api/backups")
async def list_backups():
    """List backup files"""
    try:
        backup_dir = SHARED_DIR / "backups"
        if not backup_dir.exists():
            return {"backups": []}
        
        backups = []
        for item in backup_dir.iterdir():
            if item.is_dir():
                for backup in item.iterdir():
                    backups.append({
                        "category": item.name,
                        "file": backup.name,
                        "size": backup.stat().st_size,
                        "modified": backup.stat().st_mtime
                    })
        
        return {"backups": sorted(backups, key=lambda x: x['modified'], reverse=True)}
    except Exception as e:
        logger.error("Error listing backups: %s", str(e))
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
        
        # Get and format MOTD
        motd = get_motd(image_name, config)
        formatted_motd = format_motd_for_terminal(motd)
        
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
        
        # Send formatted MOTD if available
        if formatted_motd:
            await websocket.send_text(formatted_motd)
            logger.debug("Sent MOTD (%d chars) for %s", len(formatted_motd), image_name)
        
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