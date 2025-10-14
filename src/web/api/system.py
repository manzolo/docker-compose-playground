from fastapi import APIRouter, HTTPException
from datetime import datetime
import asyncio
import uuid
import concurrent.futures
import logging
import os

from src.web.core.config import load_config
from src.web.core.docker import docker_client, ensure_network, SHARED_DIR, NETWORK_NAME

router = APIRouter()
logger = logging.getLogger("uvicorn")

# Import from groups for shared state
from src.web.api.groups import active_operations

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
                    
                    docker_client.containers.run(
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
            c.restart(timeout=30)
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
            if c.status == "running":
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