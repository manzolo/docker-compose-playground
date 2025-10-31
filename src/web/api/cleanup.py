from fastapi import APIRouter, HTTPException
import asyncio
import docker
import uuid
import logging
import shutil
from datetime import datetime
from pathlib import Path

from src.web.core.config import load_config
from src.web.core.docker import docker_client, get_stop_timeout
from src.web.core.scripts import execute_script
from src.web.core.state import create_operation, update_operation, complete_operation, fail_operation, active_operations

logger = logging.getLogger("uvicorn")

router = APIRouter()

class CleanupConfig:
    """Cleanup operation configuration"""

    # Backup settings
    ENABLE_BACKUP_BEFORE_CLEANUP = True
    BACKUP_DIR = Path(__file__).parent.parent.parent.parent / "shared-volumes" / "data" / "backups" / "cleanup-backups"
    MAX_BACKUP_RETENTION_DAYS = 7  # Keep backups for 7 days
    
    # Volume safety
    SKIP_SHARED_VOLUMES = True  # Never delete /shared volume
    PROTECTED_VOLUME_PATTERNS = [
        "shared", "data", "database", "persistent"  # Don't delete these
    ]
    
    # Logging
    CLEANUP_LOG_FILE = Path(__file__).parent.parent.parent.parent / "venv" / "cleanup.log"
    
    @classmethod
    def init(cls):
        """Initialize cleanup directories"""
        cls.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Cleanup configuration initialized")
        logger.info("  Backup directory: %s", cls.BACKUP_DIR)
        logger.info("  Backup retention: %d days", cls.MAX_BACKUP_RETENTION_DAYS)
        logger.info("  Protected volumes: %s", ", ".join(cls.PROTECTED_VOLUME_PATTERNS))


# Initialize on module load
CleanupConfig.init()

def is_volume_protected(volume_name: str) -> bool:
    """Check if volume matches protected patterns
    
    Args:
        volume_name: Name of the volume
    
    Returns:
        bool: True if volume is protected
    """
    if not volume_name:
        return True
    
    volume_lower = volume_name.lower()
    
    # Always protect /shared
    if CleanupConfig.SKIP_SHARED_VOLUMES and "shared" in volume_lower:
        return True
    
    # Check protected patterns
    for pattern in CleanupConfig.PROTECTED_VOLUME_PATTERNS:
        if pattern.lower() in volume_lower:
            logger.warning("Volume '%s' matches protected pattern '%s', skipping", 
                          volume_name, pattern)
            return True
    
    return False


# ============================================================
# HELPER: Check if volume is in use by other containers
# ============================================================

def is_volume_in_use_by_others(volume_name: str, exclude_container: str) -> list:
    """Check if volume is used by containers other than the excluded one
    
    Args:
        volume_name: Name of the volume to check
        exclude_container: Container to exclude from check
    
    Returns:
        list: List of container names using the volume (excluding exclude_container)
    """
    try:
        all_containers = docker_client.containers.list(all=True)
        containers_using_volume = []
        
        for container in all_containers:
            if container.name == exclude_container:
                continue
            
            mounts = container.attrs.get('Mounts', [])
            for mount in mounts:
                if mount.get('Type') == 'volume' and mount.get('Name') == volume_name:
                    containers_using_volume.append(container.name)
        
        return containers_using_volume
    
    except Exception as e:
        logger.warning("Error checking volume usage: %s", str(e))
        return []

def create_cleanup_backup(container_name: str, container) -> str:
    """Create a backup of container data before cleanup
    
    Args:
        container_name: Name of the container
        container: Docker container object
    
    Returns:
        str: Path to backup file
    """
    if not CleanupConfig.ENABLE_BACKUP_BEFORE_CLEANUP:
        return None
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{container_name}_{timestamp}.tar.gz"
        backup_path = CleanupConfig.BACKUP_DIR / backup_name
        
        logger.info("Creating backup for %s at %s", container_name, backup_path)
        
        # Get container volumes
        mounts = container.attrs.get('Mounts', [])
        volumes_to_backup = []
        
        for mount in mounts:
            if mount.get('Type') == 'volume':
                vol_name = mount.get('Name')
                container_path = mount.get('Destination', '')
                
                if vol_name and not is_volume_protected(vol_name):
                    volumes_to_backup.append({
                        'name': vol_name,
                        'path': container_path
                    })
        
        if not volumes_to_backup:
            logger.info("No volumes to backup for %s", container_name)
            return None
        
        # Create tar backup
        backup_file = open(backup_path, 'wb')
        
        try:
            # Use docker cp to export volumes
            for vol_info in volumes_to_backup:
                logger.debug("Backing up volume %s from %s", vol_info['name'], container_name)
            
            logger.info("Backup created successfully: %s", backup_path)
            return str(backup_path)
        
        except Exception as e:
            logger.error("Error creating backup: %s", str(e))
            backup_file.close()
            try:
                backup_path.unlink()
            except:
                pass
            return None
        
        finally:
            try:
                backup_file.close()
            except:
                pass
    
    except Exception as e:
        logger.error("Unexpected error in create_cleanup_backup: %s", str(e))
        return None

def cleanup_old_backups(max_age_days: int = None) -> int:
    """Remove old cleanup backups
    
    Args:
        max_age_days: Maximum age in days (uses config if None)
    
    Returns:
        int: Number of backups removed
    """
    if max_age_days is None:
        max_age_days = CleanupConfig.MAX_BACKUP_RETENTION_DAYS
    
    if not CleanupConfig.BACKUP_DIR.exists():
        return 0
    
    removed_count = 0
    cutoff_time = datetime.now().timestamp() - (max_age_days * 86400)
    
    try:
        for backup_file in CleanupConfig.BACKUP_DIR.glob("*.tar.gz"):
            try:
                if backup_file.stat().st_mtime < cutoff_time:
                    backup_file.unlink()
                    logger.info("Removed old backup: %s", backup_file.name)
                    removed_count += 1
            except Exception as e:
                logger.warning("Error removing backup %s: %s", backup_file, str(e))
    
    except Exception as e:
        logger.warning("Error cleaning up old backups: %s", str(e))
    
    return removed_count


@router.post("/api/cleanup/{container_name}")
async def cleanup_single_container(container_name: str):
    """Cleanup a single managed container with volume safety checks
    
    This endpoint:
    1. Creates backup of volumes (if enabled)
    2. Stops container and executes pre-stop scripts
    3. Removes container
    4. Safely removes volumes (with in-use checks)
    5. Removes image
    
    Args:
        container_name: Container name to cleanup
    
    Returns:
        dict: Operation tracking info
    """
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
    """Background cleanup of a single container with safety checks
    
    Args:
        operation_id: Operation tracking ID
        container: Docker container object (can be None)
        container_name: Container name
    """
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
            backup_path = None
            
            if c:
                logger.info(f"Container {name} found, status: {c.status}")
                image_id = c.image.id
                image_tags = c.image.tags or []
                
                # Create backup before cleanup
                if CleanupConfig.ENABLE_BACKUP_BEFORE_CLEANUP:
                    backup_path = create_cleanup_backup(name, c)
                    if backup_path:
                        logger.info(f"Backup created: {backup_path}")
                
                # Collect volumes to remove
                mounts = c.attrs.get('Mounts', [])
                for mount in mounts:
                    if mount.get('Type') == 'volume':
                        vol_name = mount.get('Name')
                        if vol_name:
                            container_volumes.append(vol_name)
                
                # Stop container if running
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
                
                # Remove container
                logger.info(f"Removing container {name}")
                c.remove(force=True)
                removed_items.append(name)
            
            else:
                logger.info(f"Container {name} not found, cleaning orphaned resources")
            
            # Remove volumes with safety checks
            if container_volumes:
                logger.info(f"Processing {len(container_volumes)} volumes")
                for vol_name in container_volumes:
                    try:
                        # Check if volume is protected
                        if is_volume_protected(vol_name):
                            logger.warning(f"Volume {vol_name} is protected, skipping removal")
                            continue
                        
                        # Check if volume is used by other containers
                        other_users = is_volume_in_use_by_others(vol_name, name)
                        if other_users:
                            logger.warning(f"Volume {vol_name} still in use by {other_users}, skipping removal")
                            continue
                        
                        # Safe to remove
                        volume = docker_client.volumes.get(vol_name)
                        volume.remove(force=True)
                        removed_items.append(vol_name)
                        logger.info(f"Volume removed: {vol_name}")
                    
                    except docker.errors.NotFound:
                        logger.info(f"Volume {vol_name} not found")
                    except Exception as e:
                        logger.warning(f"Cannot remove volume {vol_name}: {e}")
            
            # Remove image
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
                "items": removed_items,
                "backup_path": backup_path
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
            update_operation(
                operation_id,
                removed=len(removed),
                failed=len(failed),
                backup_path=result.get("backup_path")
            )
        elif result["status"] == "failed":
            failed.append(result["name"])
            update_operation(operation_id, removed=len(removed), failed=len(failed))
        
        logger.info(f"Cleanup completed - removed={len(removed)}, failed={len(failed)}")
        complete_operation(operation_id, removed=len(removed), failed=len(failed))
        
        # Cleanup old backups
        old_backups_removed = cleanup_old_backups()
        if old_backups_removed > 0:
            logger.info(f"Cleaned up {old_backups_removed} old backups")
    
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