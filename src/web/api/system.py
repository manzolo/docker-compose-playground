from fastapi import APIRouter, HTTPException
import asyncio
import docker
import uuid
import concurrent.futures
import logging
import os
import time

from typing import List, Dict, Any

from src.web.api.cleanup import cleanup_old_backups
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
    max_workers = min(10, len(containers))  # Limit a 10 worker max
    
    logger.info("Stopping %d containers in category '%s' with %d workers", 
                len(containers), category, max_workers)
    
    def stop_cont(c):
        try:
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
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [loop.run_in_executor(executor, stop_cont, c) for c in containers]
        
        for future in asyncio.as_completed(futures):
            try:
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
            except Exception as e:
                logger.error(f"Error in stop_category_background: {e}")
                failed.append("unknown")
    
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
    max_workers = min(10, len(containers))  # Limit a 10 worker max
    
    logger.info("Restarting %d containers in category '%s' with %d workers",
                len(containers), category, max_workers)
    
    def restart_cont(c):
        try:
            config_data = load_config()
            image_name = c.name.replace("playground-", "")
            img_data = config_data["images"].get(image_name, {})
            scripts = img_data.get("scripts", {})
            
            if "pre_stop" in scripts:
                execute_script(scripts["pre_stop"], c.name, image_name)
            
            timeout = get_stop_timeout(img_data)
            c.restart(timeout=timeout)
            
            logger.info(f"Container restarted: {c.name}")
            return {"status": "restarted", "name": c.name}
        except Exception as e:
            logger.error(f"Failed to restart {c.name}: {e}")
            return {"status": "failed", "name": c.name, "error": str(e)}
    
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [loop.run_in_executor(executor, restart_cont, c) for c in containers]
        
        for future in asyncio.as_completed(futures):
            try:
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
            except Exception as e:
                logger.error(f"Error in restart_category_background: {e}")
                failed.append("unknown")
    
    complete_operation(operation_id, restarted=len(restarted), failed=len(failed), containers=restarted)

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


async def stop_all_background(operation_id: str, containers: List[Any]):
    """
    Background task to stop all containers with proper handling of edge cases.
    
    Args:
        operation_id: Unique operation identifier
        containers: List of Docker container objects to stop
    """
    
    # Initialize counters
    stopped = []      # Successfully stopped
    failed = []       # Failed to stop
    not_running = []  # Were already stopped
    
    # Edge case: no containers to stop
    if not containers:
        logger.info("No containers to stop")
        complete_operation(
            operation_id,
            stopped=0,
            not_running=0,
            failed=0,
            containers=[]
        )
        return
    
    max_workers = min(10, len(containers))
    logger.info(
        "Stopping all %d container(s) with %d worker(s)",
        len(containers),
        max_workers
    )
    
    def stop_and_remove(container):
        """
        Stop and remove a single container.
        
        Returns:
            dict: {status, name, [error]}
        """
        container_name = container.name
        
        try:
            # Step 1: Execute pre-stop script if defined
            try:
                config_data = load_config()
                image_name = container_name.replace("playground-", "")
                img_data = config_data.get("images", {}).get(image_name, {})
                scripts = img_data.get("scripts", {})
                
                if "pre_stop" in scripts:
                    logger.debug(
                        f"Executing pre-stop script for {container_name}"
                    )
                    execute_script(
                        scripts["pre_stop"],
                        container_name,
                        image_name
                    )
                
                timeout = get_stop_timeout(img_data)
                logger.debug(f"Stop timeout for {container_name}: {timeout}s")
                
            except Exception as e:
                logger.warning(
                    f"Pre-stop script error for {container_name}: {e}",
                    exc_info=False
                )
                timeout = 10  # Default timeout
            
            # Step 2: Check current container state
            try:
                # Reload container state from Docker daemon
                container.reload()
                current_state = container.status
                logger.debug(f"Container {container_name} current state: {current_state}")
                
                # If already stopped, just remove it
                if current_state in ["exited", "stopped", "paused"]:
                    logger.info(f"Container {container_name} is already {current_state}")
                    try:
                        container.remove(force=True)
                        logger.info(f"Removed stopped container: {container_name}")
                    except docker.errors.NotFound:
                        logger.debug(f"Container already removed: {container_name}")
                    
                    return {
                        "status": "not_running",
                        "name": container_name,
                        "previous_state": current_state
                    }
                
            except docker.errors.NotFound:
                # Container doesn't exist
                logger.warning(f"Container not found: {container_name}")
                return {
                    "status": "not_running",
                    "name": container_name,
                    "reason": "not_found"
                }
            
            # Step 3: Stop the container
            logger.info(f"Stopping container {container_name} (timeout: {timeout}s)")
            container.stop(timeout=timeout)
            logger.info(f"Container stopped: {container_name}")
            
            # Step 4: Remove the container
            try:
                container.remove()
                logger.info(f"Container removed: {container_name}")
            except docker.errors.NotFound:
                logger.debug(f"Container already removed: {container_name}")
            
            return {
                "status": "stopped",
                "name": container_name
            }
        
        except docker.errors.NotFound:
            """
            Container doesn't exist - might have been removed by another process
            """
            logger.warning(f"Container disappeared during stop: {container_name}")
            return {
                "status": "not_running",
                "name": container_name,
                "reason": "disappeared"
            }
        
        except docker.errors.APIError as e:
            """
            Docker API error (e.g., permission denied, resource busy)
            """
            logger.error(
                f"Docker API error stopping {container_name}: {e}",
                exc_info=False
            )
            return {
                "status": "failed",
                "name": container_name,
                "error": f"API error: {str(e)}"
            }
        
        except Exception as e:
            """
            Unexpected error
            """
            logger.error(
                f"Unexpected error stopping {container_name}: {e}",
                exc_info=True
            )
            return {
                "status": "failed",
                "name": container_name,
                "error": f"Unexpected error: {str(e)}"
            }
    
    # Execute stop operations in parallel
    loop = asyncio.get_event_loop()
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = [
                loop.run_in_executor(executor, stop_and_remove, container)
                for container in containers
            ]
            
            # Process results as they complete
            for future in asyncio.as_completed(futures):
                try:
                    result = await future
                    
                    if result["status"] == "stopped":
                        stopped.append(result["name"])
                        logger.debug(f"Result: stopped - {result['name']}")
                    
                    elif result["status"] == "not_running":
                        not_running.append(result["name"])
                        reason = result.get("reason", result.get("previous_state", "unknown"))
                        logger.debug(f"Result: not_running - {result['name']} ({reason})")
                    
                    elif result["status"] == "failed":
                        failed.append(result["name"])
                        error = result.get("error", "unknown error")
                        logger.debug(f"Result: failed - {result['name']} ({error})")
                    
                    # Update operation progress
                    update_operation(
                        operation_id,
                        stopped=len(stopped),
                        not_running=len(not_running),
                        failed=len(failed),
                        containers=stopped  # Only the stopped ones
                    )
                
                except Exception as e:
                    logger.error(
                        f"Error processing result in stop_all_background: {e}",
                        exc_info=True
                    )
                    # Don't count as failed if we can't process result
                    # The operation will show what we know about
    
    except Exception as e:
        logger.error(
            f"Critical error in ThreadPoolExecutor: {e}",
            exc_info=True
        )
    
    # Log final summary
    total_processed = len(stopped) + len(not_running) + len(failed)
    logger.info(
        "stop_all_background completed: "
        "processed=%d/%d, stopped=%d, not_running=%d, failed=%d",
        total_processed,
        len(containers),
        len(stopped),
        len(not_running),
        len(failed)
    )
    
    # Log details
    if stopped:
        logger.info(f"Successfully stopped: {', '.join(stopped)}")
    if not_running:
        logger.info(f"Already not running: {', '.join(not_running)}")
    if failed:
        logger.warning(f"Failed to stop: {', '.join(failed)}")
    
    # Complete the operation with final results
    complete_operation(
        operation_id,
        stopped=len(stopped),
        not_running=len(not_running),
        failed=len(failed),
        containers=stopped,
        summary={
            "stopped": stopped,
            "not_running": not_running,
            "failed": failed
        }
    )


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


async def restart_all_background(operation_id: str, containers: List[Any]):
    """
    Background task to restart all containers with proper error handling.
    
    Restart process:
    1. Execute pre_stop script (if configured)
    2. Restart the container
    3. Wait for container to be ready (post_start wait time)
    4. Execute post_start script (if configured)
    
    Args:
        operation_id: Unique operation identifier
        containers: List of Docker container objects to restart
    """
    
    restarted = []
    failed = []
    not_found = []
    already_running = []  # For containers already running (edge case)
    
    # Edge case: no containers to restart
    if not containers:
        logger.info("No containers to restart")
        complete_operation(
            operation_id,
            restarted=0,
            failed=0,
            containers=[]
        )
        return
    
    max_workers = min(10, len(containers))
    logger.info(
        "Restarting %d container(s) with %d worker(s)",
        len(containers),
        max_workers
    )
    
    def restart_container(container):
        """
        Restart a single container with pre/post scripts.
        
        Returns:
            dict: {status, name, [error]}
        """
        container_name = container.name
        
        try:
            # Step 1: Reload and check current state
            try:
                container.reload()
                current_state = container.status
                logger.debug(f"{container_name}: current state = {current_state}")
            except docker.errors.NotFound:
                logger.warning(f"{container_name}: container not found")
                return {
                    "status": "not_found",
                    "name": container_name,
                    "reason": "not_found"
                }
            
            # Step 2: Load configuration
            try:
                config_data = load_config()
                image_name = container_name.replace("playground-", "")
                img_data = config_data.get("images", {}).get(image_name, {})
                scripts = img_data.get("scripts", {})
                post_start_wait = img_data.get("post_start_wait", 2)  # Default 2s
                
                logger.debug(f"{container_name}: post_start_wait = {post_start_wait}s")
                
            except Exception as e:
                logger.warning(f"{container_name}: config load error: {e}")
                scripts = {}
                post_start_wait = 2
            
            # Step 3: Execute pre_stop script if defined
            if "pre_stop" in scripts:
                try:
                    logger.debug(f"{container_name}: executing pre_stop script")
                    execute_script(scripts["pre_stop"], container_name, image_name)
                    logger.debug(f"{container_name}: pre_stop script completed")
                except Exception as e:
                    logger.warning(f"{container_name}: pre_stop script failed: {e}")
                    # Continue even if pre_stop fails
            
            # Step 4: Get stop timeout
            try:
                timeout = get_stop_timeout(img_data)
            except Exception as e:
                logger.debug(f"{container_name}: timeout config error: {e}")
                timeout = 10  # Default timeout
            
            # Step 5: Restart the container
            try:
                logger.info(f"{container_name}: restarting (timeout: {timeout}s)")
                container.restart(timeout=timeout)
                logger.info(f"{container_name}: restart completed")
            
            except docker.errors.NotFound:
                logger.warning(f"{container_name}: disappeared during restart")
                return {
                    "status": "not_found",
                    "name": container_name,
                    "reason": "disappeared"
                }
            
            except docker.errors.APIError as e:
                logger.error(f"{container_name}: Docker API error: {e}")
                return {
                    "status": "failed",
                    "name": container_name,
                    "error": f"API error: {str(e)}"
                }
            
            # Step 6: Wait for post_start (if configured)
            if post_start_wait > 0:
                logger.debug(f"{container_name}: waiting {post_start_wait}s before post_start")
                time.sleep(post_start_wait)
            
            # Step 7: Execute post_start script if defined
            if "post_start" in scripts:
                try:
                    logger.debug(f"{container_name}: executing post_start script")
                    execute_script(scripts["post_start"], container_name, image_name)
                    logger.debug(f"{container_name}: post_start script completed")
                except Exception as e:
                    logger.warning(f"{container_name}: post_start script failed: {e}")
                    # Don't fail the whole restart just because post_start failed
                    # The container is running, the script just failed
            
            # Step 8: Verify container is running
            try:
                container.reload()
                final_state = container.status
                
                if final_state == "running":
                    logger.info(f"{container_name}: successfully restarted and verified running")
                    return {
                        "status": "restarted",
                        "name": container_name
                    }
                else:
                    logger.warning(f"{container_name}: restart complete but state is {final_state}")
                    return {
                        "status": "restarted",
                        "name": container_name,
                        "state": final_state
                    }
            
            except docker.errors.NotFound:
                logger.error(f"{container_name}: disappeared after restart!")
                return {
                    "status": "failed",
                    "name": container_name,
                    "error": "Container disappeared after restart"
                }
        
        except docker.errors.NotFound:
            logger.warning(f"{container_name}: container not found")
            return {
                "status": "not_found",
                "name": container_name,
                "reason": "not_found"
            }
        
        except Exception as e:
            logger.error(f"{container_name}: unexpected error: {e}", exc_info=True)
            return {
                "status": "failed",
                "name": container_name,
                "error": f"Unexpected error: {str(e)}"
            }
    
    # Execute restart operations in parallel
    loop = asyncio.get_event_loop()
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            futures = [
                loop.run_in_executor(executor, restart_container, container)
                for container in containers
            ]
            
            # Process results as they complete
            for future in asyncio.as_completed(futures):
                try:
                    result = await future
                    
                    if result["status"] == "restarted":
                        restarted.append(result["name"])
                        logger.debug(f"Result: restarted - {result['name']}")
                    
                    elif result["status"] == "not_found":
                        not_found.append(result["name"])
                        reason = result.get("reason", "unknown")
                        logger.debug(f"Result: not_found - {result['name']} ({reason})")
                    
                    elif result["status"] == "failed":
                        failed.append(result["name"])
                        error = result.get("error", "unknown error")
                        logger.debug(f"Result: failed - {result['name']} ({error})")
                    
                    # Update operation progress
                    update_operation(
                        operation_id,
                        restarted=len(restarted),
                        failed=len(failed) + len(not_found),  # not_found is also a failure
                        containers=restarted
                    )
                
                except Exception as e:
                    logger.error(
                        f"Error processing result in restart_all_background: {e}",
                        exc_info=True
                    )
                    # Don't add "unknown" to failed - we don't know which container it is
    
    except Exception as e:
        logger.error(
            f"Critical error in ThreadPoolExecutor: {e}",
            exc_info=True
        )
    
    # Log final summary
    total_processed = len(restarted) + len(not_found) + len(failed)
    logger.info(
        "restart_all_background completed: "
        "processed=%d/%d, restarted=%d, not_found=%d, failed=%d",
        total_processed,
        len(containers),
        len(restarted),
        len(not_found),
        len(failed)
    )
    
    # Log details
    if restarted:
        logger.info(f"Successfully restarted: {', '.join(restarted)}")
    if not_found:
        logger.warning(f"Not found: {', '.join(not_found)}")
    if failed:
        logger.error(f"Failed to restart: {', '.join(failed)}")
    
    # Complete the operation with final results
    complete_operation(
        operation_id,
        restarted=len(restarted),
        failed=len(failed) + len(not_found),
        containers=restarted,
        summary={
            "restarted": restarted,
            "not_found": not_found,
            "failed": failed
        }
    )
    
@router.post("/api/cleanup-all")
async def cleanup_all():
    """Cleanup all managed containers with volume safety checks
    
    Returns:
        dict: Operation tracking info
    """
    containers = docker_client.containers.list(all=True, filters={"label": "playground.managed=true"})
    operation_id = str(uuid.uuid4())
    
    if containers:
        logger.info("Starting cleanup-all for %d containers", len(containers))
        create_operation(
            operation_id,
            "cleanup_all",
            total=len(containers)
        )
        asyncio.create_task(cleanup_all_background(operation_id, containers))
    else:
        logger.info("No containers to cleanup")
        create_operation(
            operation_id,
            "cleanup_all",
            total=0
        )
        complete_operation(operation_id, removed=0, containers=[])
    
    return {"operation_id": operation_id, "status": "started" if containers else "completed"}

async def cleanup_all_background(operation_id: str, containers):
    """Background cleanup of all containers with volume safety
    
    Args:
        operation_id: Operation tracking ID
        containers: List of Docker container objects
    """
    removed = []
    failed = []
    images_removed = []
    volumes_removed = []
    volumes_protected = []
    max_workers = min(10, len(containers))
    
    logger.info("Cleanup all started: %d containers, %d workers", len(containers), max_workers)
    
    def cleanup_cont(c):
        try:
            container_name = c.name
            image_id = c.image.id
            
            # Collect volumes
            container_volumes = []
            mounts = c.attrs.get('Mounts', [])
            for mount in mounts:
                if mount.get('Type') == 'volume':
                    vol_name = mount.get('Name')
                    if vol_name:
                        container_volumes.append(vol_name)
            
            # Stop if running
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
            
            # Remove container
            c.remove(force=True)
            logger.info(f"Container rimosso: {container_name}")
            
            removed_items = []
            protected_items = []
            
            # Remove volumes safely
            for vol_name in container_volumes:
                try:
                    # Check protection
                    if is_volume_protected(vol_name):
                        logger.warning(f"Volume {vol_name} is protected, skipping")
                        protected_items.append(vol_name)
                        continue
                    
                    # Check usage
                    other_users = is_volume_in_use_by_others(vol_name, container_name)
                    if other_users:
                        logger.warning(f"Volume {vol_name} in use by {other_users}, skipping")
                        protected_items.append(vol_name)
                        continue
                    
                    # Remove
                    volume = docker_client.volumes.get(vol_name)
                    volume.remove(force=True)
                    removed_items.append(vol_name)
                    logger.info(f"Volume rimosso: {vol_name}")
                
                except docker.errors.NotFound:
                    logger.info(f"Volume {vol_name} not found")
                except Exception as e:
                    logger.warning(f"Cannot remove volume {vol_name}: {e}")
            
            # Remove image
            image_removed = False
            try:
                docker_client.images.remove(image_id, force=True, noprune=True)
                image_removed = True
                logger.info(f"Immagine rimossa: {image_id}")
            except Exception as e:
                logger.warning(f"Cannot remove image {image_id}: {e}")
            
            return {
                "status": "removed",
                "name": container_name,
                "image_removed": image_removed,
                "volumes_removed": removed_items,
                "volumes_protected": protected_items
            }
        
        except Exception as e:
            logger.error(f"Failed to cleanup {c.name}: {e}")
            return {
                "status": "failed",
                "name": c.name,
                "error": str(e),
                "image_removed": False,
                "volumes_removed": [],
                "volumes_protected": []
            }
    
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [loop.run_in_executor(executor, cleanup_cont, c) for c in containers]
        
        for future in asyncio.as_completed(futures):
            try:
                result = await future
                
                if result["status"] == "removed":
                    removed.append(result["name"])
                    if result.get("image_removed"):
                        images_removed.append(result["name"])
                    volumes_removed.extend(result.get("volumes_removed", []))
                    volumes_protected.extend(result.get("volumes_protected", []))
                
                elif result["status"] == "failed":
                    failed.append(result["name"])
                
                update_operation(
                    operation_id,
                    removed=len(removed),
                    failed=len(failed),
                    images_removed=len(images_removed),
                    volumes_removed=len(volumes_removed),
                    volumes_protected=len(volumes_protected),
                    containers=removed
                )
            
            except Exception as e:
                logger.error(f"Error in cleanup_all_background: {e}")
                failed.append("unknown")
    
    logger.info("cleanup_all completed: %d removed, %d failed, %d volumes protected",
                len(removed), len(failed), len(volumes_protected))
    
    complete_operation(
        operation_id,
        removed=len(removed),
        failed=len(failed),
        images_removed=len(images_removed),
        volumes_removed=len(volumes_removed),
        volumes_protected=len(volumes_protected),
        containers=removed
    )
    
    # Cleanup old backups
    old_backups_removed = cleanup_old_backups()
    if old_backups_removed > 0:
        logger.info(f"Cleaned up {old_backups_removed} old backups")

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