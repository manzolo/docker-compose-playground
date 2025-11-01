from fastapi import APIRouter, HTTPException
import logging
import docker

from src.web.core.docker import docker_client
from src.web.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/api/containers/{container}/info")
async def get_container_info(container: str):
    """
    Get container status and basic info.

    Returns 200 even if container doesn't exist, with status field indicating state:
    - "running", "exited", "paused", etc. if container exists
    - "not_found" if container doesn't exist
    """
    try:
        cont = docker_client.containers.get(container)
        return {
            "name": cont.name,
            "status": cont.status,
            "id": cont.short_id,
            "image": cont.image.tags[0] if cont.image.tags else "unknown",
            "exists": True
        }
    except docker.errors.NotFound:
        # Return 200 with not_found status instead of 404
        logger.info(f"Container '{container}' not found (stopped/removed)")
        return {
            "name": container,
            "status": "not_found",
            "id": None,
            "image": None,
            "exists": False
        }
    except Exception as e:
        logger.error("Error getting container info: %s", str(e))
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