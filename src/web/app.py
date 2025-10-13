from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict
import docker
import yaml
import tempfile
import logging
import glob
import asyncio
import subprocess
import os
import json
import concurrent.futures
import asyncio
import uuid

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
CUSTOM_CONFIG_DIR = Path(__file__).parent.parent.parent / "custom.d"
CONFIG_FILE = Path(__file__).parent.parent.parent / "config.yml"
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
SHARED_DIR = Path(__file__).parent.parent.parent / "shared-volumes"
NETWORK_NAME = "playground-network"

active_operations: Dict[str, dict] = {}

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

# Config loading from config.yml and config.d
def load_config():
    images = {}
    
    # 1. Load from config.yml (base configuration from Git)
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
    
    # 2. Load from config.d (additional configurations from Git)
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
    
    # 3. Load from custom.d (user-created configurations, not in Git)
    if CUSTOM_CONFIG_DIR.exists():
        custom_files = glob.glob(str(CUSTOM_CONFIG_DIR / "*.yml"))
        for config_file in custom_files:
            try:
                with open(config_file, "r") as f:
                    config = yaml.safe_load(f)
                    if config and isinstance(config, dict) and "images" in config:
                        images.update(config["images"])
                        logger.info("Loaded custom images from %s", config_file)
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
        features_dict = {}  # NEW: Store features for each container
        
        for c in running:
            if c.name.startswith("playground-"):
                image_name = c.name.replace("playground-", "", 1)
                running_dict[image_name] = {"name": c.name, "status": c.status}
        
        # NEW: Get features for all containers
        for img_name in config.keys():
            features_dict[img_name] = get_container_features(img_name, config)
        
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
            "features": features_dict,  # NEW: Pass features to template
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
        # Get container object FIRST
        cont = docker_client.containers.get(container)
        
        # Get image name from container name
        image_name = container.replace("playground-", "", 1)
        config = load_config()
        
        # Execute pre-stop script WHILE container is still running
        if image_name in config:
            scripts = config[image_name].get('scripts', {})
            if 'pre_stop' in scripts:
                logger.info("Running pre-stop script for %s", image_name)
                # Esegui in modo SINCRONO per assicurarsi che finisca prima dello stop
                await asyncio.to_thread(execute_script, scripts['pre_stop'], container, image_name)
                logger.info("Pre-stop script completed for %s", image_name)
        
        # NOW stop and remove container
        logger.info("Stopping container %s with 90s timeout", container)
        await asyncio.to_thread(cont.stop, timeout=90)
        await asyncio.to_thread(cont.remove)
        logger.info("Container stopped and removed: %s", container)
        
        return {"status": "stopped"}
    except docker.errors.NotFound:
        logger.error("Container not found: %s", container)
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
    """Stop all containers (non-blocking)"""
    try:
        containers = docker_client.containers.list(filters={"label": "playground.managed=true"})
        operation_id = str(uuid.uuid4())

        active_operations[operation_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "total": len(containers),
            "stopped": 0,
            "operation": "stop"
        }

        asyncio.create_task(stop_all_background(operation_id, containers))
        return {"operation_id": operation_id, "status": "started"}
    except Exception as e:
        logger.error("Error starting stop_all: %s", str(e))
        raise HTTPException(500, str(e))
   
async def stop_all_background(operation_id: str, containers):
    """Background task to stop all containers"""
    stopped = []
    
    def stop_and_remove_container(container):
        try:
            logger.info("Stopping container: %s", container.name)
            container.stop(timeout=60)
            container.remove()
            logger.info("Stopped and removed: %s", container.name)
            return container.name
        except Exception as e:
            logger.error("Failed to stop %s: %s", container.name, str(e))
            return None
    
    try:
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(containers))) as executor:
            futures = [
                loop.run_in_executor(executor, stop_and_remove_container, cont) 
                for cont in containers
            ]
            
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            for result in results:
                if result and not isinstance(result, Exception):
                    stopped.append(result)
                    # Aggiorna lo stato
                    active_operations[operation_id]["stopped"] = len(stopped)
        
        logger.info("Stopped %d containers successfully", len(stopped))
        
        # Aggiorna lo stato finale
        active_operations[operation_id].update({
            "status": "completed",
            "stopped": len(stopped),
            "containers": stopped,
            "completed_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error("Error in stop_all_background: %s", str(e))
        active_operations[operation_id].update({
            "status": "error",
            "error": str(e)
        })

@app.post("/api/restart-all")
async def restart_all():
    """Restart all containers (async with operation tracking)"""
    try:
        containers = docker_client.containers.list(filters={"label": "playground.managed=true"})
        operation_id = str(uuid.uuid4())

        active_operations[operation_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "total": len(containers),
            "restarted": 0,
            "operation": "restart"
        }

        asyncio.create_task(restart_all_background(operation_id, containers))
        return {"operation_id": operation_id, "status": "started"}
    except Exception as e:
        logger.error("Error starting restart_all: %s", str(e))
        raise HTTPException(500, str(e))

async def restart_all_background(operation_id: str, containers):
    """Background task to restart all containers"""
    restarted = []
    
    def restart_container(container):
        try:
            logger.info("Restarting container: %s", container.name)
            container.restart(timeout=30)
            logger.info("Restarted: %s", container.name)
            return container.name
        except Exception as e:
            logger.error("Failed to restart %s: %s", container.name, str(e))
            return None
    
    try:
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(containers))) as executor:
            futures = [
                loop.run_in_executor(executor, restart_container, cont) 
                for cont in containers
            ]
            
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            for result in results:
                if result and not isinstance(result, Exception):
                    restarted.append(result)
                    # Aggiorna lo stato
                    active_operations[operation_id]["restarted"] = len(restarted)
        
        logger.info("Restarted %d containers successfully", len(restarted))
        
        # Aggiorna lo stato finale
        active_operations[operation_id].update({
            "status": "completed",
            "restarted": len(restarted),
            "containers": restarted,
            "completed_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error("Error in restart_all_background: %s", str(e))
        active_operations[operation_id].update({
            "status": "error",
            "error": str(e)
        })

@app.post("/api/cleanup-all")
async def cleanup_all():
    """Cleanup all containers (async with operation tracking)"""
    try:
        containers = docker_client.containers.list(
            all=True, 
            filters={"label": "playground.managed=true"}
        )
        operation_id = str(uuid.uuid4())

        active_operations[operation_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "total": len(containers),
            "removed": 0,
            "operation": "cleanup"
        }

        asyncio.create_task(cleanup_all_background(operation_id, containers))
        return {"operation_id": operation_id, "status": "started"}
    except Exception as e:
        logger.error("Error starting cleanup_all: %s", str(e))
        raise HTTPException(500, str(e))

async def cleanup_all_background(operation_id: str, containers):
    """Background task to cleanup all containers"""
    removed = []
    
    def cleanup_container(container):
        try:
            logger.info("Cleaning up container: %s", container.name)
            if container.status == "running":
                container.stop(timeout=30)
            container.remove()
            logger.info("Removed: %s", container.name)
            return container.name
        except Exception as e:
            logger.error("Failed to cleanup %s: %s", container.name, str(e))
            return None
    
    try:
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(containers))) as executor:
            futures = [
                loop.run_in_executor(executor, cleanup_container, cont) 
                for cont in containers
            ]
            
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            for result in results:
                if result and not isinstance(result, Exception):
                    removed.append(result)
                    # Aggiorna lo stato
                    active_operations[operation_id]["removed"] = len(removed)
        
        logger.info("Cleaned up %d containers successfully", len(removed))
        
        # Aggiorna lo stato finale
        active_operations[operation_id].update({
            "status": "completed",
            "removed": len(removed),
            "containers": removed,
            "completed_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error("Error in cleanup_all_background: %s", str(e))
        active_operations[operation_id].update({
            "status": "error",
            "error": str(e)
        })

@app.get("/api/operation-status/{operation_id}")
async def get_operation_status(operation_id: str):
    """Get status of a background operation"""
    if operation_id not in active_operations:
        raise HTTPException(404, "Operation not found")
    
    return active_operations[operation_id]

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
        
        # Total containers count from config
        config = load_config()
        total_containers = len(config)
        running_count = len(active)
        stopped_count = total_containers - running_count
        
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
            "active_containers": active,
            "counts": {
                "total": total_containers,
                "running": running_count,
                "stopped": stopped_count
            }
        }
    except Exception as e:
        logger.error("Error getting system info: %s", str(e))
        raise HTTPException(500, str(e))

# Dumper personalizzato per gestire stringhe multilinea
class CustomDumper(yaml.SafeDumper):
    def represent_str(self, data):
        # Forza lo stile letterale (|) per stringhe multilinea
        if "\n" in data:
            return self.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return self.represent_scalar('tag:yaml.org,2002:str', data)

# Registra il rappresentatore per le stringhe
CustomDumper.add_representer(str, CustomDumper.represent_str)

@app.get("/api/export-config")
async def export_config():
    """Export the configuration as a formatted YAML file"""
    try:
        # Carica la configurazione
        images = load_config()

        # Struttura il dizionario per il file YAML
        config = {"images": images}

        # Serializza il file YAML con opzioni per leggibilità
        yaml_content = yaml.dump(
            config,
            Dumper=CustomDumper,  # Usa il dumper personalizzato
            allow_unicode=True,   # Preserva i caratteri Unicode (es. emoji)
            sort_keys=False,      # Mantiene l'ordine originale delle chiavi
            default_flow_style=False,  # Usa il formato a blocchi per chiarezza
            indent=2              # Indentazione standard di 2 spazi
        )

        # Crea un file temporaneo usando tempfile
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".yml",
            delete=False,
            dir=tempfile.gettempdir()
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name  # Salva il percorso del file temporaneo

        # Restituisci il file come FileResponse
        return FileResponse(
            path=temp_file_path,
            filename=f"playground-config-{datetime.now().strftime('%Y%m%d_%H%M%S')}.yml",
            media_type="application/x-yaml",
            headers={
                "Content-Disposition": f"attachment; filename=playground-config-{datetime.now().strftime('%Y%m%d_%H%M%S')}.yml"
            }
        )
    except Exception as e:
        logger.error("Error exporting config: %s", str(e))
        raise HTTPException(500, f"Error exporting config: {str(e)}")
    finally:
        # Nota: Non eliminiamo il file temporaneo qui per evitare FileNotFoundError
        pass

def cleanup_temp_files(age_hours=1):
    temp_dir = tempfile.gettempdir()
    cutoff = datetime.now() - timedelta(hours=age_hours)
    for temp_file in glob.glob(f"{temp_dir}/*.yml"):
        if os.path.getmtime(temp_file) < cutoff.timestamp():
            try:
                os.unlink(temp_file)
                logger.info("Deleted old temp file: %s", temp_file)
            except Exception as e:
                logger.warning("Error deleting temp file %s: %s", temp_file, str(e))

@app.on_event("startup")
async def startup_event():
    cleanup_temp_files()

@app.get("/api/logs")
async def get_server_logs():
    log_path = Path("venv/web.log")
    if log_path.exists():
        with log_path.open("r") as f:
            logs = f.read()
        return PlainTextResponse(logs)
    else:
        return PlainTextResponse("No logs found")

@app.get("/api/download-backup/{category}/{filename}")
async def download_backup(category: str, filename: str):
    backup_path = SHARED_DIR / "backups" / category / filename
    if not backup_path.exists():
        raise HTTPException(404, "Backup not found")
    return FileResponse(str(backup_path), filename=filename, media_type="application/octet-stream")

@app.get("/api/backups")
async def get_backups():
    """Get list of backup files with their details"""
    try:
        backups = []
        backup_dir = SHARED_DIR / "backups"
        if not backup_dir.exists():
            logger.warning("Backup directory does not exist: %s", backup_dir)
            return {"backups": []}

        for category_dir in backup_dir.iterdir():
            if category_dir.is_dir():
                for file_path in category_dir.iterdir():
                    if file_path.is_file():
                        try:
                            stat = file_path.stat()
                            backups.append({
                                "category": category_dir.name,
                                "file": file_path.name,
                                "size": stat.st_size,  # Dimensione in byte
                                "modified": stat.st_mtime
                            })
                        except Exception as e:
                            logger.error("Error reading file %s: %s", file_path, str(e))
                            continue  # Salta file problematici
        return {"backups": backups}
    except Exception as e:
        logger.error("Error listing backups: %s", str(e))
        raise HTTPException(500, f"Error listing backups: {str(e)}")

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

# Aggiungi questi endpoint al file app.py esistente

@app.get("/add-container", response_class=HTMLResponse)
async def add_container_page(request: Request):
    """Page to add new container configuration"""
    try:
        config = load_config()
        # Get unique categories for dropdown
        categories = sorted(set(img_data.get('category', 'other') for img_data in config.values()))
        
        return templates.TemplateResponse("add_container.html", {
            "request": request,
            "existing_categories": categories
        })
    except Exception as e:
        logger.error("Error loading add container page: %s", str(e))
        raise HTTPException(500, str(e))

# Path alla directory config.d, custom.d e al file config.yml
CONFIG_DIR = Path(__file__).parent.parent.parent / "config.d"
CUSTOM_CONFIG_DIR = Path(__file__).parent.parent.parent / "custom.d"
CONFIG_FILE = Path(__file__).parent.parent.parent / "config.yml"

# Ensure custom.d directory exists
CUSTOM_CONFIG_DIR.mkdir(exist_ok=True)

@app.post("/api/add-container")
async def add_container_config(request: Request):
    """Add a new container configuration to custom.d directory"""
    try:
        data = await request.json()
        
        # Validate required fields
        required_fields = ['name', 'image', 'category', 'description']
        for field in required_fields:
            if not data.get(field):
                raise HTTPException(400, f"Missing required field: {field}")
        
        # Check if name already exists in any config
        existing_config = load_config()
        if data['name'] in existing_config:
            raise HTTPException(400, f"Container name '{data['name']}' already exists")
        
        # Build new container config
        new_config = {
            "images": {
                data['name']: {
                    "image": data['image'],
                    "category": data['category'],
                    "description": data['description'],
                    "keep_alive_cmd": data.get('keep_alive_cmd', 'tail -f /dev/null'),
                    "shell": data.get('shell', '/bin/bash'),
                    "ports": data.get('ports', []),
                    "environment": {}
                }
            }
        }
        
        # Add environment variables if provided
        if data.get('environment'):
            env_lines = data['environment'].strip().split('\n')
            for line in env_lines:
                if '=' in line:
                    key, value = line.split('=', 1)
                    new_config['images'][data['name']]['environment'][key.strip()] = value.strip()
        
        # Add MOTD if provided
        if data.get('motd'):
            new_config['images'][data['name']]['motd'] = data['motd']
        
        # Create filename: sanitize container name
        safe_name = data['name'].replace('_', '-').lower()
        config_file_path = CUSTOM_CONFIG_DIR / f"{safe_name}.yml"
        
        # Check if file already exists
        if config_file_path.exists():
            raise HTTPException(400, f"Configuration file for '{data['name']}' already exists")
        
        # Write to individual file in custom.d with proper formatting
        yaml_content = yaml.dump(
            new_config,
            Dumper=CustomDumper,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            indent=2
        )
        
        with config_file_path.open("w") as f:
            f.write(yaml_content)
        
        logger.info("Added new container config: %s to %s", data['name'], config_file_path)
        
        return {
            "status": "success",
            "message": f"Container '{data['name']}' added successfully to custom.d/{safe_name}.yml",
            "name": data['name'],
            "file": f"custom.d/{safe_name}.yml"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error adding container: %s", str(e))
        raise HTTPException(500, f"Failed to add container: {str(e)}")

@app.post("/api/validate-image")
async def validate_image(request: Request):
    """Validate if a Docker image exists and get its info"""
    try:
        data = await request.json()
        image_name = data.get('image')
        
        if not image_name:
            raise HTTPException(400, "Image name is required")
        
        try:
            # Try to pull/inspect the image
            image = docker_client.images.pull(image_name)
            
            # Get image info
            info = {
                "exists": True,
                "id": image.id[:12],
                "tags": image.tags,
                "size": f"{image.attrs['Size'] / (1024*1024):.2f} MB",
                "created": image.attrs['Created'][:10]
            }
            
            logger.info("Validated image: %s", image_name)
            return info
            
        except docker.errors.ImageNotFound:
            return {"exists": False, "error": "Image not found in Docker Hub"}
        except docker.errors.APIError as e:
            return {"exists": False, "error": str(e)}
            
    except Exception as e:
        logger.error("Error validating image: %s", str(e))
        raise HTTPException(500, str(e))

@app.post("/api/detect-shell")
async def detect_shell(request: Request):
    """Detect available shell in an image"""
    try:
        data = await request.json()
        image_name = data.get('image')
        
        if not image_name:
            raise HTTPException(400, "Image name is required")
        
        # Try common shells in order of preference
        shells = ['/bin/bash', '/bin/sh', '/bin/ash', '/usr/bin/bash']
        
        try:
            # Create temporary container to test
            container = docker_client.containers.run(
                image_name,
                command='sleep 5',
                detach=True,
                remove=True
            )
            
            detected_shell = '/bin/sh'  # default fallback
            
            for shell in shells:
                try:
                    exit_code, output = container.exec_run(f'test -f {shell}')
                    if exit_code == 0:
                        detected_shell = shell
                        break
                except:
                    continue
            
            container.stop()
            
            logger.info("Detected shell %s for image %s", detected_shell, image_name)
            return {"shell": detected_shell}
            
        except Exception as e:
            logger.warning("Could not detect shell for %s: %s", image_name, str(e))
            return {"shell": "/bin/sh"}  # Safe default
            
    except Exception as e:
        logger.error("Error detecting shell: %s", str(e))
        return {"shell": "/bin/sh"}

def get_container_features(image_name: str, config: dict) -> dict:
    """Get special features of a container (MOTD, scripts, etc.)"""
    img_data = config.get(image_name, {})
    features = {
        'has_motd': bool(img_data.get('motd')),
        'has_scripts': bool(img_data.get('scripts')),
        'has_post_start': bool(img_data.get('scripts', {}).get('post_start')),
        'has_pre_stop': bool(img_data.get('scripts', {}).get('pre_stop'))
    }
    return features