from fastapi import APIRouter, Request, HTTPException
import asyncio
import logging

from src.web.core.config import load_config
from src.web.core.docker import start_single_container_sync, stop_single_container_sync, docker_client

router = APIRouter()
logger = logging.getLogger("uvicorn")

@router.post("/start/{image}")
async def start_container(image: str):
    """Start a single container"""
    logger.info("Starting container: %s", image)
    config_data = load_config()
    config = config_data["images"]
    
    if image not in config:
        raise HTTPException(404, "Image not found")
    
    img_data = config[image]
    
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, start_single_container_sync, image, img_data)
        
        if result["status"] == "started":
            return {"status": "started", "container": f"playground-{image}", "ready": True}
        elif result["status"] == "already_running":
            return {"status": "already_running", "container": f"playground-{image}", "ready": True}
        else:
            raise HTTPException(500, result.get("error", "Failed to start container"))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start %s: %s", image, str(e))
        raise HTTPException(500, str(e))

@router.post("/stop/{container}")
async def stop_container(container: str):
    """Stop a single container"""
    logger.info("Stopping container: %s", container)
    
    try:
        image_name = container.replace("playground-", "", 1)
        config_data = load_config()
        img_data = config_data["images"].get(image_name, {})
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, stop_single_container_sync, image_name, img_data)
        
        if result["status"] in ["stopped", "not_running"]:
            return {"status": "stopped"}
        else:
            raise HTTPException(500, result.get("error", "Failed to stop container"))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error stopping %s: %s", container, str(e))
        raise HTTPException(500, str(e))

@router.get("/logs/{container}")
async def get_logs(container: str):
    """Get container logs"""
    try:
        cont = docker_client.containers.get(container)
        logs = cont.logs(tail=100).decode()
        return {"logs": logs}
    except Exception as e:
        logger.error("Error getting logs: %s", str(e))
        raise HTTPException(500, str(e))