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
from src.web.core.state import create_operation, update_operation, complete_operation, fail_operation, get_operation

router = APIRouter()
logger = logging.getLogger("uvicorn")


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
                operation_id = str(uuid.uuid4())
                create_operation(
                    operation_id,
                    "start",
                    total=1,
                    container=container_name
                )
                complete_operation(operation_id, started=0, already_running=1, failed=0)
                
                return {
                    "operation_id": operation_id,
                    "status": "already_running",
                    "container": container_name,
                    "message": f"Container {container_name} is already running"
                }
            else:
                existing.remove()
        except docker.errors.NotFound:
            pass
        
        # Create operation
        operation_id = str(uuid.uuid4())
        create_operation(
            operation_id,
            "start",
            total=1,
            container=container_name
        )
        
        # Start container in background
        asyncio.create_task(start_container_background(operation_id, image_name, img_data, container_name))
        
        return {
            "operation_id": operation_id,
            "status": "started",
            "message": f"Starting container {container_name}..."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start {image_name}: {str(e)}")
        raise HTTPException(500, f"Failed to start container: {str(e)}")


async def start_container_background(operation_id: str, image_name: str, img_data: dict, container_name: str):
    """Background task to start a single container with volume support"""
    try:
        loop = asyncio.get_event_loop()
        
        # Esegui il container start in executor (non-bloccante)
        # La funzione start_single_container_sync gestisce tutto: container startup, polling, script tracking
        result = await loop.run_in_executor(
            None,
            start_single_container_sync,
            image_name,
            img_data,
            operation_id
        )
        
        if result["status"] == "started":
            complete_operation(operation_id, started=1, already_running=0, failed=0)
            logger.info(f"Container {container_name} started successfully")
        elif result["status"] == "already_running":
            complete_operation(operation_id, started=0, already_running=1, failed=0)
            logger.info(f"Container {container_name} was already running")
        else:
            fail_operation(
                operation_id, 
                result.get("error", "Unknown error"),
                started=0,
                already_running=0,
                failed=1
            )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to start {image_name}: {error_msg}")
        fail_operation(operation_id, error_msg, started=0, already_running=0, failed=1)

@router.post("/api/stop/{container_name}")
async def stop_container(container_name: str):
    """Stop a single container - returns operation_id for async tracking"""
    try:
        container = docker_client.containers.get(container_name)
        
        # Check if it's a playground container
        if "playground.managed" not in container.labels:
            raise HTTPException(403, "Cannot stop non-playground containers")
        
        # Create operation
        operation_id = str(uuid.uuid4())
        create_operation(
            operation_id,
            "stop",
            total=1,
            container=container_name
        )
        
        # Start background task
        asyncio.create_task(stop_container_background(operation_id, container_name))
        
        return {
            "operation_id": operation_id,
            "status": "started",
            "message": f"Stopping container {container_name}..."
        }
    
    except HTTPException:
        raise
    except docker.errors.NotFound:
        raise HTTPException(404, f"Container {container_name} not found")
    except Exception as e:
        logger.error(f"Failed to stop {container_name}: {str(e)}")
        raise HTTPException(500, f"Failed to stop container: {str(e)}")


async def stop_container_background(operation_id: str, container_name: str):
    """Background task to stop a single container"""
    try:
        loop = asyncio.get_event_loop()
        
        config_data = load_config()
        image_name = container_name.replace("playground-", "")
        img_data = config_data["images"].get(image_name, {})
        
        result = await loop.run_in_executor(
            None,
            stop_single_container_sync,
            container_name,
            img_data,
            operation_id
        )
        
        if result["status"] == "stopped":
            complete_operation(operation_id, stopped=1, failed=0)
        else:
            fail_operation(operation_id, result.get("error", "Unknown error"))
        
    except Exception as e:
        logger.error(f"Failed to stop {container_name}: {str(e)}")
        fail_operation(operation_id, str(e))


@router.post("/api/restart/{image_name}")
async def restart_container(image_name: str):
    """Restart a single container by image name"""
    try:
        config_data = load_config()
        config = config_data["images"]
        
        if image_name not in config:
            raise HTTPException(404, f"Image '{image_name}' not found in configuration")
        
        img_data = config[image_name]
        container_name = f"playground-{image_name}"
        
        # Check if container exists
        try:
            existing = docker_client.containers.get(container_name)
            if "playground.managed" not in existing.labels:
                raise HTTPException(403, "Cannot restart non-playground containers")
        except docker.errors.NotFound:
            raise HTTPException(404, f"Container '{container_name}' not found")
        
        # Create operation
        operation_id = str(uuid.uuid4())
        create_operation(
            operation_id,
            "restart",
            total=1,
            container=container_name
        )
        
        # Restart container in background
        asyncio.create_task(restart_container_background(operation_id, image_name, img_data, container_name))
        
        return {
            "operation_id": operation_id,
            "status": "started",
            "message": f"Restarting container {container_name}..."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restart {image_name}: {str(e)}")
        raise HTTPException(500, f"Failed to restart container: {str(e)}")


async def restart_container_background(operation_id: str, image_name: str, img_data: dict, container_name: str):
    """Background task to restart a single container"""
    try:
        loop = asyncio.get_event_loop()
        
        def restart_cont():
            """Synchronous container restart function"""
            try:
                container = docker_client.containers.get(container_name)
                
                # Execute pre-stop script if container is running
                if container.status == "running":
                    try:
                        scripts = img_data.get("scripts", {})
                        if "pre_stop" in scripts:
                            execute_script(scripts["pre_stop"], container_name, image_name)
                    except Exception as e:
                        logger.warning(f"Pre-stop script error for {container_name}: {e}")
                
                # Stop the container
                timeout = get_stop_timeout(img_data)
                container.stop(timeout=timeout)
                logger.info(f"Container {container_name} stopped for restart")
                
                # Start the container again
                container.start()
                logger.info(f"Container {container_name} restarted successfully")
                
                return {
                    "status": "restarted",
                    "name": container_name,
                    "image_name": image_name
                }
            
            except docker.errors.NotFound:
                return {
                    "status": "failed",
                    "name": container_name,
                    "error": f"Container not found during restart"
                }
            except Exception as e:
                logger.error(f"Failed to restart {container_name}: {e}")
                return {
                    "status": "failed",
                    "name": container_name,
                    "error": str(e)
                }
        
        # Run restart in executor (non-blocking)
        result = await loop.run_in_executor(None, restart_cont)
        
        if result["status"] == "restarted":
            complete_operation(operation_id, restarted=1, failed=0)
            logger.info(f"Container {container_name} restart completed successfully")
        else:
            fail_operation(
                operation_id,
                result.get("error", "Unknown error"),
                restarted=0,
                failed=1
            )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to restart {image_name}: {error_msg}")
        fail_operation(operation_id, error_msg, restarted=0, failed=1)

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
                    
                    # Prepare volumes
                    volumes_config = img_data.get("volumes", [])
                    ensure_named_volumes(volumes_config)
                    compose_volumes = prepare_volumes(volumes_config)
                    
                    all_volumes = [f"{SHARED_DIR}:/shared"]
                    all_volumes.extend(compose_volumes)
                    
                    ports = {cp: hp for hp, cp in (p.split(":") for p in img_data.get("ports", []))}
                    
                    container = docker_client.containers.run(
                        img_data["image"],
                        detach=True,
                        name=container_name,
                        network=NETWORK_NAME,
                        volumes=all_volumes,
                        ports=ports,
                        environment=img_data.get("environment", []),
                        labels={"playground.managed": "true"},
                        remove=False
                    )
                    
                    started.append(img_name)
                    logger.info(f"Container {container_name} started (category: {category})")
                
                except Exception as e:
                    logger.error(f"Failed to start {img_name}: {e}")
    
    except Exception as e:
        logger.error(f"Failed to start category {category}: {e}")
        raise HTTPException(500, f"Failed to start category: {str(e)}")
    
    return {
        "status": "completed",
        "category": category,
        "started": started,
        "message": f"Started {len(started)} containers in category {category}"
    }

@router.post("/api/stop-category/{category}")
async def stop_category(category: str):
    """Stop all containers in a category"""
    containers = docker_client.containers.list(filters={"label": "playground.managed=true"})
    operation_id = str(uuid.uuid4())
    
    config_data = load_config()
    config = config_data["images"]
    containers_in_category = [img for img, data in config.items() if data.get('category') == category]
    
    containers_to_stop = [c for c in containers if any(ct in c.name for ct in containers_in_category)]
    
    if containers_to_stop:
        create_operation(
            operation_id,
            "stop",
            total=len(containers_to_stop),
            category=category
        )
        asyncio.create_task(stop_category_background(operation_id, containers_to_stop, category))
    else:
        create_operation(
            operation_id,
            "stop",
            total=0,
            category=category
        )
        complete_operation(operation_id, stopped=0, containers=[])
    
    return {"operation_id": operation_id, "status": "started" if containers_to_stop else "completed"}


async def stop_category_background(operation_id: str, containers, category: str):
    """Background task to stop all containers in a category"""
    stopped = []
    failed = []
    
    def stop_cont(c):
        try:
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
                
                c.stop(timeout=timeout)
            
            logger.info(f"Container stopped: {c.name}")
            return {"status": "stopped", "name": c.name}
        except Exception as e:
            logger.error(f"Failed to stop {c.name}: {e}")
            return {"status": "failed", "name": c.name, "error": str(e)}
    
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(containers))) as executor:
        futures = [loop.run_in_executor(executor, stop_cont, c) for c in containers]
        
        for future in asyncio.as_completed(futures):
            result = await future
            
            if result["status"] == "stopped":
                stopped.append(result["name"])
            elif result["status"] == "failed":
                failed.append(result["name"])
            
            update_operation(
                operation_id,
                stopped=len(stopped),
                failed=len(failed),
                containers=stopped
            )
    
    complete_operation(operation_id, stopped=len(stopped), failed=len(failed), containers=stopped)

@router.post("/api/restart-category/{category}")
async def restart_category(category: str):
    """Restart all containers in a category"""
    containers = docker_client.containers.list(filters={"label": "playground.managed=true"})
    operation_id = str(uuid.uuid4())
    
    config_data = load_config()
    config = config_data["images"]
    containers_in_category = [img for img, data in config.items() if data.get('category') == category]
    
    containers_to_restart = [c for c in containers if any(ct in c.name for ct in containers_in_category)]
    
    if containers_to_restart:
        create_operation(
            operation_id,
            "restart",
            total=len(containers_to_restart),
            category=category
        )
        asyncio.create_task(restart_category_background(operation_id, containers_to_restart, category))
    else:
        create_operation(
            operation_id,
            "restart",
            total=0,
            category=category
        )
        complete_operation(operation_id, restarted=0, containers=[])
    
    return {"operation_id": operation_id, "status": "started" if containers_to_restart else "completed"}


async def restart_category_background(operation_id: str, containers, category: str):
    """Background task to restart all containers in a category"""
    restarted = []
    failed = []
    
    def restart_cont(c):
        try:
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
                
                c.stop(timeout=timeout)
            
            c.start()
            logger.info(f"Container restarted: {c.name}")
            return {"status": "restarted", "name": c.name}
        except Exception as e:
            logger.error(f"Failed to restart {c.name}: {e}")
            return {"status": "failed", "name": c.name, "error": str(e)}
    
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(containers))) as executor:
        futures = [loop.run_in_executor(executor, restart_cont, c) for c in containers]
        
        for future in asyncio.as_completed(futures):
            result = await future
            
            if result["status"] == "restarted":
                restarted.append(result["name"])
            elif result["status"] == "failed":
                failed.append(result["name"])
            
            update_operation(
                operation_id,
                restarted=len(restarted),
                failed=len(failed),
                containers=restarted
            )
    
    complete_operation(operation_id, restarted=len(restarted), failed=len(failed), containers=restarted)

# AGGIUNGI QUESTO CODICE PRIMA DELLA RIGA 524 (prima di @router.post("/api/cleanup-all"))

@router.post("/api/stop-all")
async def stop_all():
    """Stop all running containers"""
    containers = docker_client.containers.list(filters={"label": "playground.managed=true"})
    operation_id = str(uuid.uuid4())
    
    create_operation(
        operation_id,
        "stop_all",
        total=len(containers)
    )
    
    asyncio.create_task(stop_all_background(operation_id, containers))
    return {"operation_id": operation_id, "status": "started"}


async def stop_all_background(operation_id: str, containers):
    """Background task to stop all containers"""
    stopped = []
    failed = []
    not_running = []
    
    def stop_and_remove(container):
        try:
            try:
                config_data = load_config()
                image_name = container.name.replace("playground-", "")
                img_data = config_data["images"].get(image_name, {})
                scripts = img_data.get("scripts", {})
                
                # Execute pre-stop script if exists
                if "pre_stop" in scripts:
                    execute_script(scripts["pre_stop"], container.name, image_name)
                
                timeout = get_stop_timeout(img_data)
            except Exception as e:
                logger.warning(f"Pre-stop script error for {container.name}: {e}")
                timeout = 10
            
            # Stop container
            container.stop(timeout=timeout)
            container.remove()
            return {"status": "stopped", "name": container.name}
        except Exception as e:
            logger.error(f"Failed to stop {container.name}: {e}")
            return {"status": "failed", "name": container.name, "error": str(e)}
    
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(containers))) as executor:
        futures = [loop.run_in_executor(executor, stop_and_remove, c) for c in containers]
        
        # Process results as they complete
        for future in asyncio.as_completed(futures):
            result = await future
            
            if result["status"] == "stopped":
                stopped.append(result["name"])
            elif result["status"] == "failed":
                failed.append(result["name"])
            
            # Update progress after each container
            update_operation(
                operation_id,
                stopped=len(stopped),
                not_running=len(not_running),
                failed=len(failed),
                containers=stopped
            )
    
    complete_operation(operation_id, stopped=len(stopped), not_running=len(not_running), failed=len(failed), containers=stopped)


@router.post("/api/restart-all")
async def restart_all():
    """Restart all running containers"""
    containers = docker_client.containers.list(filters={"label": "playground.managed=true"})
    operation_id = str(uuid.uuid4())
    
    create_operation(
        operation_id,
        "restart_all",
        total=len(containers)
    )
    
    asyncio.create_task(restart_all_background(operation_id, containers))
    return {"operation_id": operation_id, "status": "started"}


async def restart_all_background(operation_id: str, containers):
    """Background task to restart all containers"""
    restarted = []
    failed = []
    
    def restart_cont(c):
        try:
            config_data = load_config()
            image_name = c.name.replace("playground-", "")
            img_data = config_data["images"].get(image_name, {})
            scripts = img_data.get("scripts", {})
            
            # Execute pre-stop script if exists
            if "pre_stop" in scripts:
                try:
                    execute_script(scripts["pre_stop"], c.name, image_name)
                except Exception as e:
                    logger.warning(f"Pre-stop script error: {e}")
            
            timeout = get_stop_timeout(img_data)
            c.restart(timeout=timeout)
            
            # Execute post-start script if exists
            if "post_start" in scripts:
                try:
                    import time
                    time.sleep(2)
                    execute_script(scripts["post_start"], c.name, image_name)
                except Exception as e:
                    logger.warning(f"Post-start script error: {e}")
            
            return {"status": "restarted", "name": c.name}
        except Exception as e:
            logger.error(f"Failed to restart {c.name}: {e}")
            return {"status": "failed", "name": c.name, "error": str(e)}
    
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(containers))) as executor:
        futures = [loop.run_in_executor(executor, restart_cont, c) for c in containers]
        
        # Process results as they complete
        for future in asyncio.as_completed(futures):
            result = await future
            
            if result["status"] == "restarted":
                restarted.append(result["name"])
            elif result["status"] == "failed":
                failed.append(result["name"])
            
            # Update progress after each container
            update_operation(
                operation_id,
                restarted=len(restarted),
                failed=len(failed),
                containers=restarted
            )
    
    complete_operation(operation_id, restarted=len(restarted), failed=len(failed), containers=restarted)
    
@router.post("/api/cleanup-all")
async def cleanup_all():
    """Cleanup all managed containers, their images and volumes"""
    containers = docker_client.containers.list(all=True, filters={"label": "playground.managed=true"})
    operation_id = str(uuid.uuid4())
    
    if containers:
        create_operation(
            operation_id,
            "cleanup",
            total=len(containers)
        )
        asyncio.create_task(cleanup_all_background(operation_id, containers))
    else:
        create_operation(
            operation_id,
            "cleanup",
            total=0
        )
        complete_operation(operation_id, removed=0, containers=[])
    
    return {"operation_id": operation_id, "status": "started" if containers else "completed"}


async def cleanup_all_background(operation_id: str, containers):
    """Background cleanup of containers, images and volumes"""
    removed = []
    failed = []
    images_removed = []
    volumes_removed = []
    
    def cleanup_cont(c):
        try:
            # Raccogli info sul container prima di rimuoverlo
            container_name = c.name
            image_id = c.image.id
            
            # Estrai i volumi collegati al container
            container_volumes = []
            mounts = c.attrs.get('Mounts', [])
            for mount in mounts:
                if mount.get('Type') == 'volume':
                    vol_name = mount.get('Name')
                    if vol_name:
                        container_volumes.append(vol_name)
            
            # Esegui gli script pre-stop se il container è in running
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
                
                c.stop(timeout=timeout)
            
            # Rimuovi il container
            c.remove(force=True)
            logger.info(f"Container rimosso: {container_name}")
            
            # Rimuovi i volumi associati al container
            volumes_removed_for_container = []
            for vol_name in container_volumes:
                try:
                    volume = docker_client.volumes.get(vol_name)
                    volume.remove(force=True)
                    volumes_removed_for_container.append(vol_name)
                    logger.info(f"Volume rimosso: {vol_name}")
                except Exception as e:
                    logger.warning(f"Impossibile rimuovere volume {vol_name}: {e}")
            
            # Rimuovi l'immagine associata al container
            image_removed = False
            try:
                docker_client.images.remove(image_id, force=True, noprune=False)
                image_removed = True
                logger.info(f"Immagine rimossa: {image_id}")
            except Exception as e:
                logger.warning(f"Impossibile rimuovere immagine {image_id}: {e}")
            
            return {
                "status": "removed",
                "name": container_name,
                "image_removed": image_removed,
                "volumes_removed": volumes_removed_for_container
            }
        except Exception as e:
            logger.error(f"Failed to cleanup {c.name}: {e}")
            return {
                "status": "failed",
                "name": c.name,
                "error": str(e),
                "image_removed": False,
                "volumes_removed": []
            }
    
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(containers))) as executor:
        futures = [loop.run_in_executor(executor, cleanup_cont, c) for c in containers]
        
        for future in asyncio.as_completed(futures):
            result = await future
            
            if result["status"] == "removed":
                removed.append(result["name"])
                if result.get("image_removed"):
                    images_removed.append(result["name"])
                volumes_removed.extend(result.get("volumes_removed", []))
            elif result["status"] == "failed":
                failed.append(result["name"])
            
            update_operation(
                operation_id,
                removed=len(removed),
                failed=len(failed),
                images_removed=len(images_removed),
                volumes_removed=len(volumes_removed),
                containers=removed
            )
    
    complete_operation(
        operation_id,
        removed=len(removed),
        failed=len(failed),
        images_removed=len(images_removed),
        volumes_removed=len(volumes_removed),
        containers=removed
    )
    
    complete_operation(operation_id, removed=len(removed), failed=len(failed), containers=removed)

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
                os.path.getsize(os.path.join(dp, f))
                for dp, _, fns in os.walk(SHARED_DIR)
                for f in fns
            )
            volume_size = f"{total_size / (1024*1024):.2f} MB"
        except Exception as e:
            print(f"Error calculating volume size: {e}")
            volume_size = "N/A"
    
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
        "volume": {
            "path": str(SHARED_DIR), 
            "size": volume_size
        },
        "active_containers": active,
        "counts": {
            "total": total_containers,
            "running": len(active),
            "stopped": total_containers - len(active)
        }
    }