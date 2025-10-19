from fastapi import APIRouter, HTTPException
import asyncio
import uuid
import logging

from src.web.core.config import load_config
from src.web.core.docker import (
    start_single_container_sync, stop_single_container_sync,
    docker_client
)
from src.web.core.state import create_operation, update_operation, complete_operation, fail_operation

router = APIRouter()
logger = logging.getLogger("uvicorn")


@router.post("/api/start-group/{group_name}")
async def start_group(group_name: str):
    """Start all containers in a group"""
    try:
        config_data = load_config()
        groups = config_data["groups"]
        images = config_data["images"]
        
        if group_name not in groups:
            raise HTTPException(404, f"Group '{group_name}' not found")
        
        containers = groups[group_name].get("containers", [])
        if not containers:
            raise HTTPException(400, f"Group '{group_name}' has no containers")
        
        missing = [c for c in containers if c not in images]
        if missing:
            raise HTTPException(400, f"Containers not found: {', '.join(missing)}")
        
        logger.info("Starting group '%s' with %d containers", group_name, len(containers))
        
        operation_id = str(uuid.uuid4())
        create_operation(
            operation_id,
            "start_group",
            total=len(containers),
            group_name=group_name
        )
        
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
    """Background task to start group"""
    started = []
    already_running = []
    failed = []
    errors = []
    
    try:
        loop = asyncio.get_event_loop()
        
        for container_name in containers:
            try:
                img_data = images[container_name]
                result = await loop.run_in_executor(None, start_single_container_sync, container_name, img_data)
                
                if result["status"] == "started":
                    started.append(result["name"])
                elif result["status"] == "already_running":
                    already_running.append(result["name"])
                elif result["status"] == "failed":
                    failed.append(result["name"])
                    errors.append(f"{result['name']}: {result.get('error', 'Unknown')}")
                
                # Update progress
                update_operation(
                    operation_id,
                    started=len(started),
                    already_running=len(already_running),
                    failed=len(failed),
                    errors=errors,
                    containers=started + already_running
                )
            
            except Exception as e:
                error_msg = f"Error processing {container_name}: {str(e)}"
                logger.error(error_msg)
                failed.append(container_name)
                errors.append(error_msg)
        
        logger.info("Group '%s' completed: %d started, %d running, %d failed",
                   group_name, len(started), len(already_running), len(failed))
        
        complete_operation(operation_id)
    
    except Exception as e:
        logger.error("Error in start_group_background: %s", str(e))
        fail_operation(operation_id, str(e))


@router.post("/api/stop-group/{group_name}")
async def stop_group(group_name: str):
    """Stop all containers in a group"""
    try:
        config_data = load_config()
        groups = config_data["groups"]
        images = config_data["images"]
        
        if group_name not in groups:
            raise HTTPException(404, f"Group '{group_name}' not found")
        
        containers = groups[group_name].get("containers", [])
        if not containers:
            raise HTTPException(400, f"Group '{group_name}' has no containers")
        
        operation_id = str(uuid.uuid4())
        create_operation(
            operation_id,
            "stop_group",
            total=len(containers),
            group_name=group_name
        )
        
        asyncio.create_task(stop_group_background(operation_id, group_name, containers, images))
        
        return {"operation_id": operation_id, "status": "started", "total": len(containers)}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error stopping group: %s", str(e))
        raise HTTPException(500, str(e))


async def stop_group_background(operation_id: str, group_name: str, containers: list, images: dict):
    """Background task to stop group"""
    stopped = []
    not_running = []
    failed = []
    errors = []
    
    try:
        loop = asyncio.get_event_loop()
        
        # Stop in reverse order (dependencies)
        for container_name in reversed(containers):
            try:
                img_data = images.get(container_name, {})
                result = await loop.run_in_executor(None, stop_single_container_sync, container_name, img_data)
                
                if result["status"] == "stopped":
                    stopped.append(result["name"])
                elif result["status"] == "not_running":
                    not_running.append(result["name"])
                elif result["status"] == "failed":
                    failed.append(result["name"])
                    errors.append(result.get("error", f"Unknown error for {result['name']}"))
                
                update_operation(
                    operation_id,
                    stopped=len(stopped),
                    not_running=len(not_running),
                    failed=len(failed),
                    errors=errors,
                    containers=stopped
                )
            
            except Exception as e:
                error_msg = f"Error processing {container_name}: {str(e)}"
                logger.error(error_msg)
                failed.append(container_name)
                errors.append(error_msg)
        
        complete_operation(operation_id)
    
    except Exception as e:
        logger.error("Error in stop_group_background: %s", str(e))
        fail_operation(operation_id, str(e))


@router.get("/api/group-status/{group_name}")
async def get_group_status(group_name: str):
    """Get status of all containers in a group"""
    try:
        config_data = load_config()
        groups = config_data["groups"]
        
        if group_name not in groups:
            raise HTTPException(404, f"Group '{group_name}' not found")
        
        containers = groups[group_name].get("containers", [])
        statuses = []
        running_count = 0
        
        for container_name in containers:
            full_name = f"playground-{container_name}"
            try:
                cont = docker_client.containers.get(full_name)
                status = cont.status
                if status == "running":
                    running_count += 1
                statuses.append({"name": container_name, "status": status, "running": status == "running"})
            except:
                statuses.append({"name": container_name, "status": "not_found", "running": False})
        
        return {
            "group": group_name,
            "description": groups[group_name].get("description", ""),
            "total": len(containers),
            "running": running_count,
            "containers": statuses,
            "all_running": running_count == len(containers)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting group status: %s", str(e))
        raise HTTPException(500, str(e))


@router.get("/api/operation-status/{operation_id}")
async def get_operation_status(operation_id: str):
    """Get status of async operation"""
    from src.web.core.state import get_operation
    
    operation = get_operation(operation_id)
    if not operation:
        raise HTTPException(404, "Operation not found")
    
    return operation