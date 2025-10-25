from fastapi import APIRouter, HTTPException
import asyncio
import docker
import uuid
import logging

from src.web.core.config import load_config
from src.web.core.docker import docker_client, get_stop_timeout
from src.web.core.scripts import execute_script
from src.web.core.state import create_operation, update_operation, complete_operation, fail_operation, active_operations

logger = logging.getLogger("uvicorn")

router = APIRouter()

@router.post("/api/cleanup/{container_name}")
async def cleanup_single_container(container_name: str):
    """Cleanup a single managed container with its image and volumes"""
    try:
        container = None
        config_data = load_config()
        
        try:
            container = docker_client.containers.get(container_name)
            labels = container.labels or {}
            if labels.get("playground.managed") != "true":
                raise HTTPException(400, f"Container '{container_name}' is not managed by playground")
        except docker.errors.NotFound:
            image_name = container_name.replace("playground-", "")
            if image_name not in config_data.get("images", {}):
                raise HTTPException(404, f"Container '{container_name}' not found and not in config")
            logger.info(f"Container {container_name} not found, will use config data for cleanup")
        
        operation_id = str(uuid.uuid4())
        create_operation(operation_id, "cleanup", total=1)
        
        asyncio.create_task(cleanup_single_background(operation_id, container, container_name))
        
        return {
            "operation_id": operation_id,
            "status": "running",
            "operation": "cleanup",
            "total": 1,
            "removed": 0,
            "failed": 0
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleanup single container: {e}")
        raise HTTPException(500, f"Error: {str(e)}")


async def cleanup_single_background(operation_id: str, container, container_name: str):
    """Background cleanup of a single container, its image and volumes"""
    removed = []
    failed = []
    
    logger.info(f"Cleanup started for {container_name}")
    
    def cleanup_cont(c, name):
        try:
            config_data = load_config()
            image_name = name.replace("playground-", "")
            img_config = config_data.get("images", {}).get(image_name, {})
            
            removed_items = []
            image_id = None
            image_tags = []
            container_volumes = []
            
            if c:
                logger.info(f"Container {name} found, status: {c.status}")
                image_id = c.image.id
                image_tags = c.image.tags or []
                
                mounts = c.attrs.get('Mounts', [])
                for mount in mounts:
                    if mount.get('Type') == 'volume':
                        vol_name = mount.get('Name')
                        if vol_name:
                            container_volumes.append(vol_name)
                
                if c.status == "running":
                    logger.info(f"Container is running, stopping first")
                    try:
                        scripts = img_config.get("scripts", {})
                        if "pre_stop" in scripts:
                            execute_script(scripts["pre_stop"], c.name, image_name)
                        timeout = get_stop_timeout(img_config)
                    except Exception as e:
                        logger.warning(f"Pre-stop script error: {e}")
                        timeout = 10
                    
                    logger.info(f"Stopping container {name}")
                    c.stop(timeout=timeout)
                
                logger.info(f"Removing container {name}")
                c.remove(force=True)
                removed_items.append(name)
                
            else:
                logger.info(f"Container {name} not found, cleaning orphaned resources")
            
            if container_volumes:
                logger.info(f"Removing {len(container_volumes)} volumes")
                for vol_name in container_volumes:
                    try:
                        volume = docker_client.volumes.get(vol_name)
                        volume.remove(force=True)
                        removed_items.append(vol_name)
                        logger.info(f"Volume removed: {vol_name}")
                    except docker.errors.NotFound:
                        logger.info(f"Volume {vol_name} not found")
                    except Exception as e:
                        logger.warning(f"Cannot remove volume {vol_name}: {e}")
            
            if not image_id:
                image_ref = img_config.get("image")
                if image_ref:
                    try:
                        img_obj = docker_client.images.get(image_ref)
                        image_id = img_obj.id
                        image_tags = img_obj.tags or [image_ref]
                        logger.info(f"Found image {image_ref} from config")
                    except docker.errors.NotFound:
                        logger.info(f"Image {image_ref} not found")
                    except Exception as e:
                        logger.warning(f"Cannot find image {image_ref}: {e}")
            
            if image_id:
                logger.info(f"Removing image {image_tags[0] if image_tags else image_id[:12]}")
                try:
                    docker_client.images.remove(image_id, force=True, noprune=True)
                    image_name_removed = image_tags[0] if image_tags else image_id[:12]
                    removed_items.append(image_name_removed)
                    logger.info(f"Image removed: {image_name_removed}")
                except docker.errors.NotFound:
                    logger.info(f"Image not found")
                except Exception as e:
                    logger.warning(f"Cannot remove image: {e}")
            
            return {
                "status": "removed",
                "name": name,
                "removed_count": len(removed_items),
                "items": removed_items
            }
        except Exception as e:
            logger.error(f"Failed to cleanup {name}: {e}", exc_info=True)
            return {
                "status": "failed",
                "name": name,
                "error": str(e),
                "removed_count": 0
            }
    
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, cleanup_cont, container, container_name)
        
        logger.info(f"Cleanup result: {result}")
        
        if result["status"] == "removed":
            removed.append(result["name"])
            update_operation(operation_id, removed=len(removed), failed=len(failed))
        elif result["status"] == "failed":
            failed.append(result["name"])
            update_operation(operation_id, removed=len(removed), failed=len(failed))
        
        logger.info(f"Cleanup completed - removed={len(removed)}, failed={len(failed)}")
        complete_operation(operation_id, removed=len(removed), failed=len(failed))
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}", exc_info=True)
        fail_operation(operation_id, str(e))


@router.get("/api/cleanup/{container_name}/status/{operation_id}")
async def cleanup_status(container_name: str, operation_id: str):
    try:
        operation = active_operations.get(operation_id)
        if not operation:
            raise HTTPException(404, f"Operation not found")
        
        return operation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cleanup status: {e}")
        raise HTTPException(500, str(e))