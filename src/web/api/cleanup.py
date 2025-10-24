from fastapi import APIRouter, HTTPException
import asyncio
import docker
import uuid
import concurrent.futures
import logging
import os

from src.web.core.config import load_config
from src.web.core.docker import (
    docker_client, ensure_network, SHARED_DIR, NETWORK_NAME,
    get_stop_timeout, prepare_volumes, ensure_named_volumes,
    start_single_container_sync, stop_single_container_sync
)
from src.web.core.scripts import execute_script
from src.web.core.state import create_operation, update_operation, complete_operation, fail_operation, get_operation, active_operations

logger = logging.getLogger("uvicorn")

router = APIRouter()

@router.post("/api/cleanup/{container_name}")
async def cleanup_single_container(container_name: str):
    """Cleanup a single managed container with its image and volumes"""
    try:
        # Verifica che il container esista e sia gestito
        container = docker_client.containers.get(container_name)
        
        # Verifica il label
        labels = container.labels or {}
        if labels.get("playground.managed") != "true":
            raise HTTPException(
                400,
                f"Container '{container_name}' is not managed by playground"
            )
        
        operation_id = str(uuid.uuid4())
        create_operation(
            operation_id,
            "cleanup",
            total=1
        )
        
        # Esegui il cleanup in background
        asyncio.create_task(cleanup_single_background(operation_id, container))
        
        # Ritorna il formato che il frontend si aspetta
        return {
            "operation_id": operation_id,
            "status": "running",
            "operation": "cleanup",
            "total": 1,
            "removed": 0,
            "failed": 0
        }
    
    except docker.errors.NotFound:
        raise HTTPException(404, f"Container '{container_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleanup single container: {e}")
        raise HTTPException(500, f"Error: {str(e)}")


async def cleanup_single_background(operation_id: str, container):
    """Background cleanup of a single container, its image and volumes"""
    removed = []
    failed = []
    
    logger.info(f"🧹 CLEANUP STARTED for {container.name} (operation_id: {operation_id})")
    
    def cleanup_cont(c):
        try:
            container_name = c.name
            image_id = c.image.id
            image_tags = c.image.tags or []
            
            # Estrai i volumi collegati al container
            container_volumes = []
            mounts = c.attrs.get('Mounts', [])
            for mount in mounts:
                if mount.get('Type') == 'volume':
                    vol_name = mount.get('Name')
                    if vol_name:
                        container_volumes.append(vol_name)
            
            # Esegui script pre-stop se il container è in running
            if c.status == "running":
                try:
                    config_data = load_config()
                    image_name = c.name.replace("playground-", "")
                    img_data = config_data["images"].get(image_name, {})
                    scripts = img_data.get("scripts", {})
                    
                    if "pre_stop" in scripts:
                        execute_script(scripts["pre_stop"], c.name, image_name)
                    
                    timeout = get_stop_timeout(img_data)
                except Exception as e:
                    logger.warning(f"Pre-stop script error: {e}")
                    timeout = 10
                
                logger.info(f"🧹 Stopping container {container_name}")
                c.stop(timeout=timeout)
            
            # Rimuovi il container
            logger.info(f"🧹 Removing container {container_name}")
            c.remove(force=True)
            removed_items = [container_name]
            
            # Rimuovi i volumi
            logger.info(f"🧹 Removing {len(container_volumes)} volumes")
            for vol_name in container_volumes:
                try:
                    volume = docker_client.volumes.get(vol_name)
                    volume.remove(force=True)
                    removed_items.append(vol_name)
                    logger.info(f"🧹 Volume removed: {vol_name}")
                except Exception as e:
                    logger.warning(f"Cannot remove volume {vol_name}: {e}")
            
            # Rimuovi l'immagine
            logger.info(f"🧹 Removing image")
            image_removed = False
            try:
                docker_client.images.remove(image_id, force=True, noprune=False)
                image_removed = True
                image_name_removed = image_tags[0] if image_tags else image_id[:12]
                removed_items.append(image_name_removed)
                logger.info(f"🧹 Image removed: {image_name_removed}")
            except Exception as e:
                logger.warning(f"Cannot remove image {image_id}: {e}")
            
            return {
                "status": "removed",
                "name": container_name,
                "removed_count": len(removed_items)
            }
        except Exception as e:
            logger.error(f"Failed to cleanup {c.name}: {e}")
            return {
                "status": "failed",
                "name": c.name,
                "error": str(e),
                "removed_count": 0
            }
    
    try:
        loop = asyncio.get_event_loop()
        
        # Esegui il cleanup in executor (non-bloccante)
        result = await loop.run_in_executor(None, cleanup_cont, container)
        
        logger.info(f"🧹 Cleanup result: {result}")
        
        if result["status"] == "removed":
            removed.append(result["name"])
            logger.info(f"🧹 UPDATE: removed={len(removed)}, failed={len(failed)}")
            update_operation(operation_id, removed=len(removed), failed=len(failed))
        elif result["status"] == "failed":
            failed.append(result["name"])
            logger.info(f"🧹 UPDATE: removed={len(removed)}, failed={len(failed)}")
            update_operation(operation_id, removed=len(removed), failed=len(failed))
        
        # Operazione completata
        logger.info(f"🧹 CLEANUP COMPLETED - removed={len(removed)}, failed={len(failed)}")
        complete_operation(operation_id, removed=len(removed), failed=len(failed))
        
    except Exception as e:
        logger.error(f"🧹 CLEANUP ERROR: {e}")
        fail_operation(operation_id, str(e))


@router.get("/api/cleanup/{container_name}/status/{operation_id}")
async def cleanup_status(container_name: str, operation_id: str):
    """Get status of cleanup operation for a single container"""
    try:
        operation = active_operations.get(operation_id)
        if not operation:
            raise HTTPException(404, f"Operation '{operation_id}' not found")
        
        if operation.get("container_name") != container_name:
            raise HTTPException(
                400,
                f"Operation '{operation_id}' is not for container '{container_name}'"
            )
        
        return operation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cleanup status: {e}")
        raise HTTPException(500, str(e))
