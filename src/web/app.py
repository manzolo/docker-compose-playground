from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
<<<<<<< Updated upstream
=======
from fastapi.responses import PlainTextResponse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict
import time
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
=======
    groups = {}
    
    def process_config(config, source_name):
        """Process a single config file"""
        if not config or not isinstance(config, dict):
            return
        
        # Load group if present
        if "group" in config and isinstance(config["group"], dict):
            group_name = config["group"].get("name", f"group_{len(groups)}")
            groups[group_name] = config["group"]
            groups[group_name]["source"] = source_name
            logger.info("Loaded group '%s' from %s", group_name, source_name)
        
        # Load images - support both "images:" key and direct container keys
        if "images" in config and isinstance(config["images"], dict):
            # New structure: images: { container1: {...}, container2: {...} }
            images.update(config["images"])
            logger.info("Loaded %d images from 'images' key in %s", len(config["images"]), source_name)
        else:
            # Old structure: direct container keys (skip 'group' key)
            for key, value in config.items():
                if key != "group" and isinstance(value, dict) and "image" in value:
                    images[key] = value
            logger.info("Loaded images from direct keys in %s", source_name)
    
    # 1. Load from config.yml
>>>>>>> Stashed changes
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r") as f:
                config = yaml.safe_load(f)
                process_config(config, "config.yml")
        except yaml.YAMLError as e:
            logger.error("Failed to parse config.yml: %s", str(e))
            raise HTTPException(500, f"Failed to parse config.yml: {str(e)}")
    
<<<<<<< Updated upstream
=======
    # 2. Load from config.d
>>>>>>> Stashed changes
    if CONFIG_DIR.exists():
        for config_file in sorted(CONFIG_DIR.glob("*.yml")):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    process_config(config, config_file.name)
            except yaml.YAMLError as e:
                logger.error("Failed to parse %s: %s", config_file, str(e))
                continue
    
<<<<<<< Updated upstream
=======
    # 3. Load from custom.d
    if CUSTOM_CONFIG_DIR.exists():
        for config_file in sorted(CUSTOM_CONFIG_DIR.glob("*.yml")):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    process_config(config, config_file.name)
            except yaml.YAMLError as e:
                logger.error("Failed to parse %s: %s", config_file, str(e))
                continue
    
>>>>>>> Stashed changes
    if not images:
        logger.error("No valid configurations found")
        raise HTTPException(500, "No valid configurations found")
    
    logger.info("Total loaded: %d images, %d groups", len(images), len(groups))
    
    return {
        "images": dict(sorted(images.items(), key=lambda x: x[0].lower())),
        "groups": groups
    }

async def run_script_async(script_config, container_name, image_name):
    """Run script asynchronously without blocking response"""
    try:
        logger.info("Running post-start script for %s", image_name)
        await asyncio.to_thread(execute_script, script_config, container_name, image_name)
        logger.info("Post-start script completed for %s", image_name)
    except Exception as e:
        logger.error("Post-start script failed for %s: %s", image_name, str(e))
        
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
<<<<<<< Updated upstream
        config = load_config()
=======
        config_data = load_config()  # Now returns dict with images and groups
        config = config_data["images"]
        groups = config_data["groups"]  # NEW: Get groups
        
>>>>>>> Stashed changes
        running = docker_client.containers.list(all=True)
        running_dict = {}
        for c in running:
            if c.name.startswith("playground-"):
                image_name = c.name.replace("playground-", "", 1)
                running_dict[image_name] = {"name": c.name, "status": c.status}
        
<<<<<<< Updated upstream
=======
        for img_name in config.keys():
            features_dict[img_name] = get_container_features(img_name, config)
        
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
=======
            "groups": groups,  # NEW: Pass groups to template
>>>>>>> Stashed changes
            "running": running_dict,
            "categories": sorted(categories),
            "category_counts": category_counts
        })
    except Exception as e:
        logger.error("Error loading dashboard: %s", str(e))
        raise HTTPException(500, f"Error loading dashboard: {str(e)}")

@app.post("/api/start-group/{group_name}")
async def start_group(group_name: str):
    """Start all containers in a group (async with operation tracking)"""
    try:
        config_data = load_config()
        groups = config_data["groups"]
        images = config_data["images"]
        
        if group_name not in groups:
            raise HTTPException(404, f"Group '{group_name}' not found")
        
        group = groups[group_name]
        containers = group.get("containers", [])
        
        if not containers:
            raise HTTPException(400, f"Group '{group_name}' has no containers defined")
        
        # Validate that all containers exist in config
        missing = [c for c in containers if c not in images]
        if missing:
            raise HTTPException(400, f"Containers not found in config: {', '.join(missing)}")
        
        logger.info("Starting group '%s' with %d containers", group_name, len(containers))
        
        # Create operation tracking
        operation_id = str(uuid.uuid4())
        active_operations[operation_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "total": len(containers),
            "started": 0,
            "already_running": 0,
            "failed": 0,
            "operation": "start_group",
            "group_name": group_name,
            "containers": [],
            "errors": []
        }
        
        # Start background task
        asyncio.create_task(start_group_background(operation_id, group_name, containers, images))
        
        return {
            "operation_id": operation_id,
            "status": "started",
            "total": len(containers),
            "group": group_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error starting group %s: %s", group_name, str(e))
        raise HTTPException(500, str(e))


async def start_group_background(operation_id: str, group_name: str, containers: list, images: dict):
    """Background task to start all containers in a group"""
    started = []
    already_running = []
    failed = []
    errors = []
    
    def start_single_container(container_name):
        """Start a single container"""
        try:
            full_container_name = f"playground-{container_name}"
            logger.info("Starting container: %s", container_name)
            
            # Check if already running
            try:
                existing = docker_client.containers.get(full_container_name)
                if existing.status == "running":
                    logger.info("Container %s already running", container_name)
                    return {"status": "already_running", "name": container_name}
                else:
                    # Remove stopped container
                    logger.info("Removing stopped container %s", container_name)
                    existing.remove(force=True)
            except docker.errors.NotFound:
                pass
            
            # Get container config
            img_data = images[container_name]
            
            # Ensure network exists
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
            wait_interval = 0.5
            
            while elapsed < max_wait:
                try:
                    container.reload()
                    if container.status == "running":
                        logger.info("Container %s is now running", full_container_name)
                        
                        # Execute post-start script if exists
                        scripts = img_data.get('scripts', {})
                        if 'post_start' in scripts:
                            try:
                                logger.info("Executing post-start script for %s", container_name)
                                execute_script(scripts['post_start'], full_container_name, container_name)
                            except Exception as script_error:
                                logger.warning("Post-start script error for %s: %s", container_name, str(script_error))
                        
                        return {"status": "started", "name": container_name}
                    elif container.status in ["exited", "dead"]:
                        error_msg = f"Container failed to start: {container.status}"
                        logger.error("%s: %s", container_name, error_msg)
                        return {"status": "failed", "name": container_name, "error": error_msg}
                except docker.errors.NotFound:
                    error_msg = "Container disappeared after creation"
                    logger.error("%s: %s", container_name, error_msg)
                    return {"status": "failed", "name": container_name, "error": error_msg}
                
                time.sleep(wait_interval)
                elapsed += wait_interval
            
            # Timeout
            container.reload()
            if container.status != "running":
                error_msg = f"Container did not start in time (status: {container.status})"
                logger.error("%s: %s", container_name, error_msg)
                return {"status": "failed", "name": container_name, "error": error_msg}
            
            return {"status": "started", "name": container_name}
            
        except docker.errors.ImageNotFound:
            error_msg = f"Docker image not found: {images.get(container_name, {}).get('image', 'unknown')}"
            logger.error("%s: %s", container_name, error_msg)
            return {"status": "failed", "name": container_name, "error": error_msg}
        except docker.errors.APIError as e:
            error_msg = f"Docker API error: {str(e)}"
            logger.error("%s: %s", container_name, error_msg)
            return {"status": "failed", "name": container_name, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error("%s: %s", container_name, error_msg)
            return {"status": "failed", "name": container_name, "error": error_msg}
    
    try:
        loop = asyncio.get_event_loop()
        
        # Start containers sequentially (not parallel) to avoid resource conflicts
        for container_name in containers:
            try:
                # Run in thread pool to avoid blocking
                result = await loop.run_in_executor(None, start_single_container, container_name)
                
                if result["status"] == "started":
                    started.append(result["name"])
                    active_operations[operation_id]["started"] = len(started)
                elif result["status"] == "already_running":
                    already_running.append(result["name"])
                    active_operations[operation_id]["already_running"] = len(already_running)
                elif result["status"] == "failed":
                    failed.append(result["name"])
                    errors.append(f"{result['name']}: {result.get('error', 'Unknown error')}")
                    active_operations[operation_id]["failed"] = len(failed)
                    active_operations[operation_id]["errors"] = errors
                
                # Update progress
                completed = len(started) + len(already_running) + len(failed)
                active_operations[operation_id]["containers"] = started + already_running
                
                logger.info("Group start progress: %d/%d (started=%d, running=%d, failed=%d)",
                           completed, len(containers), len(started), len(already_running), len(failed))
                
            except Exception as e:
                error_msg = f"Error processing {container_name}: {str(e)}"
                logger.error(error_msg)
                failed.append(container_name)
                errors.append(error_msg)
                active_operations[operation_id]["failed"] = len(failed)
                active_operations[operation_id]["errors"] = errors
        
        logger.info("Group '%s' start completed: %d started, %d already running, %d failed",
                   group_name, len(started), len(already_running), len(failed))
        
        # Update final status
        active_operations[operation_id].update({
            "status": "completed",
            "started": len(started),
            "already_running": len(already_running),
            "failed": len(failed),
            "containers": started + already_running,
            "errors": errors,
            "completed_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error("Error in start_group_background for '%s': %s", group_name, str(e))
        active_operations[operation_id].update({
            "status": "error",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        })
    
@app.post("/api/stop-group/{group_name}")
async def stop_group(group_name: str):
    """Stop all containers in a group (async with operation tracking)"""
    try:
        config_data = load_config()
        groups = config_data["groups"]
        
        if group_name not in groups:
            raise HTTPException(404, f"Group '{group_name}' not found")
        
        group = groups[group_name]
        containers = group.get("containers", [])
        
        if not containers:
            raise HTTPException(400, f"Group '{group_name}' has no containers defined")
        
        logger.info("Stopping group '%s' with %d containers", group_name, len(containers))
        
        # Create operation tracking
        operation_id = str(uuid.uuid4())
        active_operations[operation_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "total": len(containers),
            "stopped": 0,
            "not_running": 0,
            "failed": 0,
            "operation": "stop_group",
            "group_name": group_name,
            "containers": [],
            "errors": []
        }
        
        # Start background task
        asyncio.create_task(stop_group_background(operation_id, group_name, containers, config_data["images"]))
        
        return {
            "operation_id": operation_id,
            "status": "started",
            "total": len(containers),
            "group": group_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error stopping group %s: %s", group_name, str(e))
        raise HTTPException(500, str(e))


async def stop_group_background(operation_id: str, group_name: str, containers: list, images: dict):
    """Background task to stop all containers in a group"""
    stopped = []
    not_running = []
    failed = []
    errors = []
    
    def stop_single_container(container_name):
        """Stop a single container"""
        try:
            full_container_name = f"playground-{container_name}"
            
            try:
                cont = docker_client.containers.get(full_container_name)
                
                if cont.status != "running":
                    logger.info("Container %s not running", container_name)
                    return {"status": "not_running", "name": container_name}
                
                # Execute pre-stop script
                if container_name in images:
                    scripts = images[container_name].get('scripts', {})
                    if 'pre_stop' in scripts:
                        try:
                            logger.info("Running pre-stop script for %s", container_name)
                            execute_script(scripts['pre_stop'], full_container_name, container_name)
                        except Exception as script_error:
                            logger.warning("Pre-stop script error for %s: %s", container_name, str(script_error))
                
                # Stop and remove container
                logger.info("Stopping container %s", full_container_name)
                cont.stop(timeout=90)
                cont.remove()
                
                logger.info("Container %s stopped", container_name)
                return {"status": "stopped", "name": container_name}
                
            except docker.errors.NotFound:
                logger.warning("Container %s not found", container_name)
                return {"status": "not_running", "name": container_name}
                
        except Exception as e:
            error_msg = f"Error stopping {container_name}: {str(e)}"
            logger.error(error_msg)
            return {"status": "failed", "name": container_name, "error": error_msg}
    
    try:
        loop = asyncio.get_event_loop()
        
        # Stop containers in reverse order
        for container_name in reversed(containers):
            try:
                result = await loop.run_in_executor(None, stop_single_container, container_name)
                
                if result["status"] == "stopped":
                    stopped.append(result["name"])
                elif result["status"] == "not_running":
                    not_running.append(result["name"])
                elif result["status"] == "failed":
                    failed.append(result["name"])
                    errors.append(result.get("error", f"Unknown error for {result['name']}"))
                
                # *** FIX: Aggiorna SEMPRE tutti i campi ***
                active_operations[operation_id].update({
                    "stopped": len(stopped),
                    "not_running": len(not_running),
                    "failed": len(failed),
                    "errors": errors,
                    "containers": stopped
                })
                
                # Update progress
                completed = len(stopped) + len(not_running) + len(failed)
                
                logger.info("Group stop progress: %d/%d (stopped=%d, not_running=%d, failed=%d)",
                           completed, len(containers), len(stopped), len(not_running), len(failed))
                
            except Exception as e:
                error_msg = f"Error processing {container_name}: {str(e)}"
                logger.error(error_msg)
                failed.append(container_name)
                errors.append(error_msg)
                
                # *** FIX: Aggiorna anche in caso di errore ***
                active_operations[operation_id].update({
                    "stopped": len(stopped),
                    "not_running": len(not_running),
                    "failed": len(failed),
                    "errors": errors
                })
        
        logger.info("Group '%s' stop completed: %d stopped, %d not running, %d failed",
                   group_name, len(stopped), len(not_running), len(failed))
        
        # Update final status
        active_operations[operation_id].update({
            "status": "completed",
            "stopped": len(stopped),
            "not_running": len(not_running),
            "failed": len(failed),
            "containers": stopped,
            "errors": errors,
            "completed_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error("Error in stop_group_background for '%s': %s", group_name, str(e))
        active_operations[operation_id].update({
            "status": "error",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        })

@app.get("/api/group-status/{group_name}")
async def get_group_status(group_name: str):
    """Get status of all containers in a group"""
    try:
        config_data = load_config()
        groups = config_data["groups"]
        
        if group_name not in groups:
            raise HTTPException(404, f"Group '{group_name}' not found")
        
        group = groups[group_name]
        containers = group.get("containers", [])
        
        statuses = []
        running_count = 0
        
        for container_name in containers:
            full_container_name = f"playground-{container_name}"
            
            try:
                cont = docker_client.containers.get(full_container_name)
                status = cont.status
                if status == "running":
                    running_count += 1
                
                statuses.append({
                    "name": container_name,
                    "status": status,
                    "running": status == "running"
                })
            except docker.errors.NotFound:
                statuses.append({
                    "name": container_name,
                    "status": "not_found",
                    "running": False
                })
        
        return {
            "group": group_name,
            "description": group.get("description", ""),
            "total": len(containers),
            "running": running_count,
            "containers": statuses,
            "all_running": running_count == len(containers)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting group status %s: %s", group_name, str(e))
        raise HTTPException(500, str(e))
        
@app.post("/start/{image}")
async def start_container(image: str):
    logger.info("Starting container: %s", image)
    config_data = load_config()  # FIX: Ottieni il dict completo
    config = config_data["images"]  # FIX: Estrai solo le images
    
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


@app.post("/stop/{container}")
async def stop_container(container: str):
    logger.info("Stopping container: %s", container)
    try:
        # Get image name from container name
        image_name = container.replace("playground-", "", 1)
        config_data = load_config()  # FIX: Ottieni il dict completo
        config = config_data["images"]  # FIX: Estrai solo le images
        
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

@app.get("/manage", response_class=HTMLResponse)
async def manage_page(request: Request):
    """Advanced manager page"""
    try:
        config_data = load_config()
        config = config_data["images"]
        groups = config_data["groups"]
        
        running = docker_client.containers.list(filters={"label": "playground.managed=true"})
        
        # Count by category - FIXED: considera sia singoli che gruppi
        categories = {}
        
        # 1. Conta i container singoli
        for img_name, img_data in config.items():
            cat = img_data.get('category', 'other')
            categories[cat] = categories.get(cat, 0) + 1
        
        # 2. NON contare i gruppi come categoria separata
        # I container dei gruppi sono già contati sopra
        
        # Network info
        try:
            network = docker_client.networks.get(NETWORK_NAME)
            network_info = {
                "name": network.name, 
                "driver": network.attrs.get('Driver', 'N/A'),
                "subnet": network.attrs.get('IPAM', {}).get('Config', [{}])[0].get('Subnet', 'N/A')
            }
        except:
            network_info = {"name": "Not created", "driver": "N/A", "subnet": "N/A"}
        
        return templates.TemplateResponse("manage.html", {
            "request": request,
            "total_images": len(config),
            "running_count": len(running),
            "stopped_count": len(config) - len(running),
            "categories": categories,
            "groups": groups,  # Passa anche i gruppi
            "network_info": network_info
        })
    except Exception as e:
        logger.error("Error loading manage page: %s", str(e))
        raise HTTPException(500, str(e))
    
@app.post("/api/start-category/{category}")
async def start_category(category: str):
    """Start all containers in a category"""
    try:
        config_data = load_config()  # FIX: Ottieni il dict completo
        config = config_data["images"]  # FIX: Estrai solo le images
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
                container.stop(timeout=10)
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
        # Get ALL containers with playground label
        containers = docker_client.containers.list(
            all=True,  # Include stopped containers
            filters={"label": "playground.managed=true"}
        )
<<<<<<< Updated upstream
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
=======
        
        logger.info("Cleanup-all: Found %d containers to cleanup", len(containers))
        for c in containers:
            logger.info("  - %s (status: %s)", c.name, c.status)
        
        if len(containers) == 0:
            return {"status": "completed", "removed": 0, "containers": [], "message": "No containers to cleanup"}
        
        operation_id = str(uuid.uuid4())

        active_operations[operation_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "total": len(containers),
            "removed": 0,
            "operation": "cleanup"
        }

        asyncio.create_task(cleanup_all_background(operation_id, containers))
        return {"operation_id": operation_id, "status": "started", "total": len(containers)}
>>>>>>> Stashed changes
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
        
<<<<<<< Updated upstream
=======
        # Total containers count from config
        config_data = load_config()  # FIX: Ottieni il dict completo
        config = config_data["images"]  # FIX: Estrai solo le images
        total_containers = len(config)
        running_count = len(active)
        stopped_count = total_containers - running_count
        
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
        config = load_config()
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as f:
            yaml.dump({"images": config}, f, default_flow_style=False)
            temp_path = f.name
        
=======
        # Carica la configurazione
        config_data = load_config()  # FIX: Ottieni il dict completo
        images = config_data["images"]  # FIX: Estrai solo le images

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
>>>>>>> Stashed changes
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
        config_data = load_config()
        config = config_data["images"]  # FIX: Prendi solo images, non tutto il dict
        
        image_name = container.replace("playground-", "", 1)
        
        # FIX: Prendi la shell dal config, con fallback corretto
        shell = config.get(image_name, {}).get("shell", "/bin/bash")
        logger.info("Using shell %s for %s", shell, image_name)
        
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
        
        logger.info("Console session started for %s with shell %s", container, shell)
        
        # Send formatted MOTD if available
        if formatted_motd:
            # FIX: Aspetta un momento prima di inviare il MOTD
            await asyncio.sleep(0.1)
            await websocket.send_text(formatted_motd)
            logger.info("Sent MOTD (%d chars) for %s", len(formatted_motd), image_name)
        else:
            logger.warning("No MOTD found for %s", image_name)
        
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
<<<<<<< Updated upstream
        logger.info("Console session closed for %s", container)
=======
        logger.info("Console session closed for %s", container)

@app.get("/add-container", response_class=HTMLResponse)
async def add_container_page(request: Request):
    """Page to add new container configuration"""
    try:
        config_data = load_config()  # FIX: Ottieni il dict completo
        config = config_data["images"]  # FIX: Estrai solo le images
        
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
        config_data = load_config()  # FIX: Ottieni il dict completo
        existing_config = config_data["images"]  # FIX: Estrai solo le images
        
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

def natural_sort_key(key):
    """Convert string to tuple for natural sorting (10 > 2)"""
    import re
    def convert(text):
        return int(text) if text.isdigit() else text.lower()
    
    return [convert(c) for c in re.split('([0-9]+)', key)]

@app.get("/debug-config")
async def debug_config():
    """Debug endpoint to check config loading"""
    try:
        config_files = []
        
        # Check custom.d files
        if CUSTOM_CONFIG_DIR.exists():
            for config_file in CUSTOM_CONFIG_DIR.glob("*.yml"):
                try:
                    with open(config_file, "r") as f:
                        content = f.read()
                        config_files.append({
                            "file": config_file.name,
                            "exists": True,
                            "content_preview": content[:500] + "..." if len(content) > 500 else content
                        })
                except Exception as e:
                    config_files.append({
                        "file": config_file.name,
                        "exists": True,
                        "error": str(e)
                    })
        
        # Load final config
        config_data = load_config()  # FIX: Ottieni il dict completo
        final_config = config_data["images"]  # FIX: Estrai solo le images
        
        return {
            "custom_dir": str(CUSTOM_CONFIG_DIR),
            "custom_files": config_files,
            "loaded_images": list(final_config.keys())[:10],  # First 10 images
            "total_loaded": len(final_config),
            "groups": list(config_data["groups"].keys())  # Mostra anche i gruppi
        }
    except Exception as e:
        return {"error": str(e)}
>>>>>>> Stashed changes
