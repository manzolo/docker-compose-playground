from fastapi import APIRouter, HTTPException
import asyncio
import uuid
import logging
from src.web.core.logging_config import get_logger

from src.web.core.config import load_config
from src.web.core.docker import (
    start_single_container_sync, stop_single_container_sync,
    docker_client
)
from src.web.core.state import create_operation, update_operation, complete_operation, fail_operation, get_operation
from src.web.utils import to_full_name, to_display_name

router = APIRouter()
logger = get_logger(__name__)

@router.get("/api/groups")
async def list_groups():
    """
    Get list of all configured groups
    
    Response:
    {
        "groups": [
            {
                "name": "MinIO-S3-Stack",
                "containers": ["minio-s3-stack", "php-minio-stack", "mysql-minio-stack"],
                "description": "MinIO S3 object storage with PHP and MySQL"
            }
        ],
        "total": 1
    }
    """
    try:
        config_data = load_config()
        groups = config_data.get("groups", {})
        
        group_list = []
        for group_name, group_data in groups.items():
            # Extract containers - supporta diversi formati
            containers = []
            if "containers" in group_data:
                containers = group_data["containers"] if isinstance(group_data["containers"], list) else [group_data["containers"]]
            elif "images" in group_data:
                containers = group_data["images"] if isinstance(group_data["images"], list) else [group_data["images"]]
            
            group_info = {
                "name": group_name,
                "containers": containers,
                "description": group_data.get("description", ""),
                "source": group_data.get("source", ""),
            }
            group_list.append(group_info)
        
        logger.info("Listed %d groups", len(group_list))
        
        return {
            "groups": group_list,
            "total": len(group_list)
        }
    except Exception as e:
        logger.error("Error listing groups: %s", str(e))
        raise HTTPException(500, f"Error listing groups: {str(e)}")


@router.get("/api/groups/{group_name}")
async def get_group_details(group_name: str):
    """
    Get detailed information about a specific group
    
    Parameters:
        group_name: Name of the group (e.g., "MinIO-S3-Stack")
    
    Response:
    {
        "name": "MinIO-S3-Stack",
        "containers": [
            {
                "name": "minio-s3-stack",
                "image": "minio/minio",
                "status": "running",
                "running": true
            }
        ],
        "status": "running",
        "running_count": 3,
        "total_count": 3
    }
    """
    try:
        config_data = load_config()
        groups = config_data.get("groups", {})
        images = config_data.get("images", {})
        
        if group_name not in groups:
            raise HTTPException(404, f"Group '{group_name}' not found")
        
        group_data = groups[group_name]
        containers = group_data.get("containers", [])
        
        # Get status of each container in group
        running_containers = docker_client.containers.list(filters={"label": "playground.managed=true"})
        running_names = [c.name for c in running_containers]
        
        container_status = []
        running_count = 0
        
        for container_name in containers:
            # Convert to full container name with prefix
            full_name = to_full_name(container_name)

            is_running = full_name in running_names
            if is_running:
                running_count += 1
            
            image_name = "N/A"
            if container_name in images:
                image_name = images[container_name].get("image", "N/A")
            
            container_status.append({
                "name": container_name,
                "full_name": full_name,
                "image": image_name,
                "running": is_running,
                "status": "running" if is_running else "stopped"
            })
        
        logger.info("Retrieved details for group '%s'", group_name)
        
        return {
            "name": group_name,
            "containers": container_status,
            "status": "running" if running_count == len(containers) else (
                "partial" if running_count > 0 else "stopped"
            ),
            "running_count": running_count,
            "total_count": len(containers),
            "description": group_data.get("description", "")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting group details: %s", str(e))
        raise HTTPException(500, f"Error getting group details: {str(e)}")

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
                # Pass operation_id for script tracking
                result = await loop.run_in_executor(
                    None, 
                    start_single_container_sync, 
                    container_name, 
                    img_data,
                    operation_id
                )
                
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
        
        # Crea lista di task per esecuzione parallela
        tasks = []
        for container_name in containers:
            img_data = images.get(container_name, {})
            full_container_name = to_full_name(container_name)

            task = loop.run_in_executor(
                None,
                stop_single_container_sync,
                full_container_name,
                img_data,
                operation_id
            )
            tasks.append(task)
        
        # Esegui tutti in parallelo
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Elabora i risultati man mano
        for result in results:
            if isinstance(result, Exception):
                failed.append(str(result))
                errors.append(str(result))
                continue
            
            if result["status"] == "stopped":
                stopped.append(result["name"])
            elif result["status"] == "not_running":
                not_running.append(result["name"])
            elif result["status"] == "failed":
                failed.append(result["name"])
                errors.append(result.get("error", f"Unknown error for {result['name']}"))
            
            # Aggiorna progress dopo ogni risultato
            update_operation(
                operation_id,
                stopped=len(stopped),
                not_running=len(not_running),
                failed=len(failed),
                errors=errors,
                containers=stopped
            )
        
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
            full_name = to_full_name(container_name)
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