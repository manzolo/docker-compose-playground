from fastapi import APIRouter, HTTPException
from datetime import datetime
import asyncio
import docker
import uuid
import concurrent.futures
import logging
import os

from src.web.core.config import load_config
from src.web.core.docker import docker_client, ensure_network, SHARED_DIR, NETWORK_NAME
from src.web.core.scripts import execute_script  # ✅ AGGIUNTO IMPORT

router = APIRouter()
logger = logging.getLogger("uvicorn")

# Import from groups for shared state
from src.web.api.groups import active_operations


@router.post("/api/start/{image_name}")
async def start_container(image_name: str):
    """Start a single container by image name"""
    try:
        config_data = load_config()
        config = config_data["images"]
        
        if image_name not in config:
            raise HTTPException(404, f"Image '{image_name}' not found in configuration")
        
        img_data = config[image_name]
        container_name = f"playground-{image_name}"
        
        # Check if already running
        try:
            existing = docker_client.containers.get(container_name)
            if existing.status == "running":
                # Create a completed operation for already running
                operation_id = str(uuid.uuid4())
                active_operations[operation_id] = {
                    "status": "completed",
                    "started_at": datetime.now().isoformat(),
                    "completed_at": datetime.now().isoformat(),
                    "total": 1,
                    "started": 0,
                    "already_running": 1,
                    "failed": 0,
                    "operation": "start",
                    "container": container_name,
                    "errors": []
                }
                return {
                    "operation_id": operation_id,
                    "status": "already_running",
                    "container": container_name,
                    "message": f"Container {container_name} is already running"
                }
            else:
                # Remove stopped container
                existing.remove()
        except docker.errors.NotFound:
            pass
        
        # Create operation
        operation_id = str(uuid.uuid4())
        active_operations[operation_id] = {
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "total": 1,
            "started": 0,
            "already_running": 0,
            "failed": 0,
            "operation": "start",
            "container": container_name,
            "errors": []
        }
        
        # Start container in background
        asyncio.create_task(start_container_background(operation_id, image_name, img_data, container_name))
        
        return {
            "operation_id": operation_id,
            "status": "started",
            "message": f"Starting container {container_name}..."
        }
        
    except Exception as e:
        logger.error(f"Failed to start {image_name}: {str(e)}")
        raise HTTPException(500, f"Failed to start container: {str(e)}")


async def start_container_background(operation_id: str, image_name: str, img_data: dict, container_name: str):
    """Background task to start a single container"""
    try:
        # Ensure network exists
        ensure_network()
        
        # Parse ports
        ports = {}
        for port_mapping in img_data.get("ports", []):
            host_port, container_port = port_mapping.split(":")
            ports[container_port] = host_port
        
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
        
        # Wait for container to be ready (max 30 seconds)
        max_wait = 60  # 60 attempts * 0.5s = 30 seconds
        for i in range(max_wait):
            await asyncio.sleep(0.5)
            container.reload()
            
            if container.status == "running":
                # Execute post-start script
                scripts = img_data.get("scripts", {})
                if "post_start" in scripts:
                    try:
                        logger.info(f"Executing post-start script for {container_name}")
                        execute_script(scripts["post_start"], container_name, image_name)
                        logger.info(f"Post-start script completed for {container_name}")
                    except Exception as e:
                        logger.warning(f"Failed to execute post-start script for {container_name}: {e}")
                        active_operations[operation_id]["errors"].append(f"Post-start script error: {str(e)}")
                
                # Success!
                active_operations[operation_id].update({
                    "status": "completed",
                    "started": 1,
                    "completed_at": datetime.now().isoformat()
                })
                logger.info(f"Container {container_name} started successfully")
                return
            
            elif container.status in ["exited", "dead"]:
                raise Exception(f"Container failed to start: {container.status}")
        
        # Timeout
        raise Exception(f"Container did not start in time (status: {container.status})")
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to start {image_name}: {error_msg}")
        active_operations[operation_id].update({
            "status": "error",
            "failed": 1,
            "error": error_msg,
            "errors": [error_msg],
            "completed_at": datetime.now().isoformat()
        })


@router.post("/stop/{container_name}")
async def stop_container(container_name: str):
    """Stop a single container"""
    try:
        container = docker_client.containers.get(container_name)
        
        # Check if it's a playground container
        if "playground.managed" not in container.labels:
            raise HTTPException(403, "Cannot stop non-playground containers")
        
        # ✅ FIXED: Execute pre-stop script correttamente
        try:
            config_data = load_config()
            # Extract image name from container name (remove 'playground-' prefix)
            image_name = container_name.replace("playground-", "")
            img_data = config_data["images"].get(image_name, {})
            
            # ✅ CORREZIONE: Cerca in scripts.pre_stop invece di pre_stop
            scripts = img_data.get("scripts", {})
            if "pre_stop" in scripts:
                try:
                    logger.info(f"Executing pre-stop script for {container_name}")
                    execute_script(scripts["pre_stop"], container_name, image_name)
                    logger.info(f"Pre-stop script completed for {container_name}")
                    # Give it a moment to complete
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.warning(f"Failed to execute pre-stop script for {container_name}: {e}")
        except Exception as e:
            logger.warning(f"Could not check for pre-stop script: {e}")
        
        # Stop and remove container
        container.stop(timeout=60)
        container.remove()
        
        return {
            "status": "stopped",
            "container": container_name,
            "message": f"Container {container_name} stopped successfully"
        }
        
    except docker.errors.NotFound:
        raise HTTPException(404, f"Container {container_name} not found")
    except Exception as e:
        logger.error(f"Failed to stop {container_name}: {str(e)}")
        raise HTTPException(500, f"Failed to stop container: {str(e)}")


@router.post("/api/start-category/{category}")
async def start_category(category: str):
    """Start all containers in a category"""
    try:
        config_data = load_config()
        config = config_data["images"]
        started = []
        
        for img_name, img_data in config.items():
            if img_data.get('category') == category:
                container_name = f"playground-{img_name}"
                
                try:
                    existing = docker_client.containers.get(container_name)
                    if existing.status == "running":
                        continue
                except:
                    pass
                
                try:
                    ensure_network()
                    ports = {cp: hp for hp, cp in (p.split(":") for p in img_data.get("ports", []))}
                    
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
                    
                    # ✅ AGGIUNTO: Execute post-start script
                    scripts = img_data.get("scripts", {})
                    if "post_start" in scripts:
                        try:
                            execute_script(scripts["post_start"], container_name, img_name)
                        except Exception as e:
                            logger.warning(f"Post-start script error for {img_name}: {e}")
                    
                    started.append(container_name)
                except Exception as e:
                    logger.error("Failed to start %s: %s", img_name, str(e))
        
        return {"status": "ok", "started": len(started), "containers": started}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/api/stop-all")
async def stop_all():
    """Stop all containers"""
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


async def stop_all_background(operation_id: str, containers):
    """Background task to stop all"""
    stopped = []
    
    def stop_and_remove(container):
        try:
            # ✅ AGGIUNTO: Execute pre-stop script per ogni container
            try:
                config_data = load_config()
                image_name = container.name.replace("playground-", "")
                img_data = config_data["images"].get(image_name, {})
                scripts = img_data.get("scripts", {})
                
                if "pre_stop" in scripts:
                    execute_script(scripts["pre_stop"], container.name, image_name)
            except Exception as e:
                logger.warning(f"Pre-stop script error for {container.name}: {e}")
            
            container.stop(timeout=60)
            container.remove()
            return container.name
        except:
            return None
    
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(containers))) as executor:
        futures = [loop.run_in_executor(executor, stop_and_remove, c) for c in containers]
        results = await asyncio.gather(*futures, return_exceptions=True)
        stopped = [r for r in results if r and not isinstance(r, Exception)]
    
    active_operations[operation_id].update({
        "status": "completed",
        "stopped": len(stopped),
        "containers": stopped,
        "completed_at": datetime.now().isoformat()
    })


@router.post("/api/restart-all")
async def restart_all():
    """Restart all containers"""
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


async def restart_all_background(operation_id: str, containers):
    """Background restart all"""
    def restart_cont(c):
        try:
            # ✅ AGGIUNTO: Execute pre-stop and post-start scripts
            config_data = load_config()
            image_name = c.name.replace("playground-", "")
            img_data = config_data["images"].get(image_name, {})
            scripts = img_data.get("scripts", {})
            
            # Pre-stop
            if "pre_stop" in scripts:
                try:
                    execute_script(scripts["pre_stop"], c.name, image_name)
                except Exception as e:
                    logger.warning(f"Pre-stop script error: {e}")
            
            c.restart(timeout=30)
            
            # Post-start
            if "post_start" in scripts:
                try:
                    import time
                    time.sleep(2)  # Wait for container to be ready
                    execute_script(scripts["post_start"], c.name, image_name)
                except Exception as e:
                    logger.warning(f"Post-start script error: {e}")
            
            return c.name
        except:
            return None
    
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(containers))) as executor:
        futures = [loop.run_in_executor(executor, restart_cont, c) for c in containers]
        results = await asyncio.gather(*futures, return_exceptions=True)
        restarted = [r for r in results if r and not isinstance(r, Exception)]
    
    active_operations[operation_id].update({
        "status": "completed",
        "restarted": len(restarted),
        "containers": restarted,
        "completed_at": datetime.now().isoformat()
    })


@router.post("/api/cleanup-all")
async def cleanup_all():
    """Cleanup all containers"""
    containers = docker_client.containers.list(all=True, filters={"label": "playground.managed=true"})
    operation_id = str(uuid.uuid4())
    
    active_operations[operation_id] = {
        "status": "running" if containers else "completed",
        "started_at": datetime.now().isoformat(),
        "total": len(containers),
        "removed": 0,
        "operation": "cleanup",
        "completed_at": datetime.now().isoformat() if not containers else None
    }
    
    if containers:
        asyncio.create_task(cleanup_all_background(operation_id, containers))
    
    return {"operation_id": operation_id, "status": "started" if containers else "completed"}


async def cleanup_all_background(operation_id: str, containers):
    """Background cleanup"""
    def cleanup_cont(c):
        try:
            # ✅ AGGIUNTO: Execute pre-stop if running
            if c.status == "running":
                try:
                    config_data = load_config()
                    image_name = c.name.replace("playground-", "")
                    img_data = config_data["images"].get(image_name, {})
                    scripts = img_data.get("scripts", {})
                    
                    if "pre_stop" in scripts:
                        execute_script(scripts["pre_stop"], c.name, image_name)
                except Exception as e:
                    logger.warning(f"Pre-stop script error: {e}")
                
                c.stop(timeout=30)
            c.remove()
            return c.name
        except:
            return None
    
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(containers))) as executor:
        futures = [loop.run_in_executor(executor, cleanup_cont, c) for c in containers]
        results = await asyncio.gather(*futures, return_exceptions=True)
        removed = [r for r in results if r and not isinstance(r, Exception)]
    
    active_operations[operation_id].update({
        "status": "completed",
        "removed": len(removed),
        "containers": removed,
        "completed_at": datetime.now().isoformat()
    })


@router.get("/api/system-info")
async def system_info():
    """Get system information"""
    docker_info = docker_client.info()
    
    try:
        network = docker_client.networks.get(NETWORK_NAME)
        network_data = {
            "name": network.name,
            "driver": network.attrs.get('Driver', 'bridge'),
            "subnet": network.attrs.get('IPAM', {}).get('Config', [{}])[0].get('Subnet', 'N/A')
        }
    except:
        network_data = {"name": "Not found", "driver": "N/A", "subnet": "N/A"}
    
    volume_size = "N/A"
    if SHARED_DIR.exists():
        try:
            total_size = sum(
                os.path.getsize(os.path.join(dp, _, f))
                for dp, _, fns in os.walk(SHARED_DIR)
                for f in fns
            )
            volume_size = f"{total_size / (1024*1024):.2f} MB"
        except:
            pass
    
    containers = docker_client.containers.list(filters={"label": "playground.managed=true"})
    active = [{"name": c.name, "status": c.status} for c in containers]
    
    config_data = load_config()
    total_containers = len(config_data["images"])
    
    return {
        "docker": {
            "version": docker_info.get('ServerVersion', 'N/A'),
            "containers": docker_info.get('Containers', 0),
            "images": docker_info.get('Images', 0)
        },
        "network": network_data,
        "volume": {"path": str(SHARED_DIR), "size": volume_size},
        "active_containers": active,
        "counts": {
            "total": total_containers,
            "running": len(active),
            "stopped": total_containers - len(active)
        }
    }