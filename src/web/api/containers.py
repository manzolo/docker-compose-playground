from fastapi import APIRouter, HTTPException
import logging

from src.web.core.docker import docker_client

router = APIRouter()
logger = logging.getLogger("uvicorn")


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