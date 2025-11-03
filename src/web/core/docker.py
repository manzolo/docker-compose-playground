"""Docker client management and container utilities"""
import os
from typing import Dict, Any
import docker
import socket
import logging
from typing import Dict, Any, List, Tuple
from pathlib import Path
import time

from .docker_compose_params import extract_docker_params
from .logging_config import get_module_logger
from src.web.utils import to_full_name, to_display_name

# Use centralized logger
logger = get_module_logger("docker")

docker_client = docker.from_env()

# Paths and configurations
BASE_DIR = Path(__file__).parent.parent.parent.parent
SHARED_DIR = BASE_DIR / "shared-volumes"
NETWORK_NAME = "playground-network"
SCRIPTS_DIR = BASE_DIR / "scripts"

# Detect if running in Docker and get host paths
RUNNING_IN_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"
HOST_SHARED_VOLUMES_PATH = os.getenv("HOST_SHARED_VOLUMES_PATH")

if RUNNING_IN_DOCKER:
    logger.info("Running in Docker mode - will use host paths for volumes")
    logger.info("Host shared volumes path: %s", HOST_SHARED_VOLUMES_PATH)

class TimeoutConfig:
    """Centralized timeout configuration"""
    
    # Container startup
    CONTAINER_START_TIMEOUT = int(os.getenv('PLAYGROUND_START_TIMEOUT', '60'))  # Default 60s, up from 30s
    CONTAINER_START_POLL_INTERVAL = 0.5  # seconds
    
    # Container stop
    CONTAINER_STOP_TIMEOUT_DEFAULT = int(os.getenv('PLAYGROUND_STOP_TIMEOUT', '10'))  # Default 10s
    CONTAINER_STOP_TIMEOUT_WITH_SCRIPTS = int(os.getenv('PLAYGROUND_STOP_TIMEOUT_SCRIPTS', '30'))  # Default 30s
    
    # Script execution
    SCRIPT_EXECUTION_TIMEOUT = int(os.getenv('PLAYGROUND_SCRIPT_TIMEOUT', '300'))  # Default 300s (5 min)
    
    # Docker API calls
    DOCKER_API_TIMEOUT = int(os.getenv('PLAYGROUND_API_TIMEOUT', '30'))
    
    # Port check
    PORT_CHECK_TIMEOUT = int(os.getenv('PLAYGROUND_PORT_CHECK_TIMEOUT', '1'))
    
    @classmethod
    def log_config(cls):
        """Log current timeout configuration"""
        logger.info("Timeout Configuration:")
        logger.info("  Container Start: %ds (poll interval: %.2fs)", 
                   cls.CONTAINER_START_TIMEOUT, cls.CONTAINER_START_POLL_INTERVAL)
        logger.info("  Container Stop (default): %ds", cls.CONTAINER_STOP_TIMEOUT_DEFAULT)
        logger.info("  Container Stop (with scripts): %ds", cls.CONTAINER_STOP_TIMEOUT_WITH_SCRIPTS)
        logger.info("  Script Execution: %ds", cls.SCRIPT_EXECUTION_TIMEOUT)
        logger.info("  Docker API: %ds", cls.DOCKER_API_TIMEOUT)
        logger.info("  Port Check: %ds", cls.PORT_CHECK_TIMEOUT)


# Log configuration on module load
TimeoutConfig.log_config()

def ensure_network():
    """Ensure playground network exists"""
    try:
        docker_client.networks.get(NETWORK_NAME)
        logger.info("Network %s already exists", NETWORK_NAME)
    except docker.errors.NotFound:
        logger.info("Creating network %s", NETWORK_NAME)
        docker_client.networks.create(NETWORK_NAME, driver="bridge")
        logger.info("Network %s created", NETWORK_NAME)


def ensure_named_volumes(volumes_config: List[Dict[str, Any]]):
    """Create named volumes if they don't exist"""
    if not volumes_config:
        return
    
    for vol_data in volumes_config:
        if vol_data.get("type") == "named":
            vol_name = vol_data.get("name")
            if vol_name:
                try:
                    docker_client.volumes.get(vol_name)
                except docker.errors.NotFound:
                    logger.info("Creating named volume: %s", vol_name)
                    docker_client.volumes.create(name=vol_name, driver="local")


def convert_to_host_path(container_path: str) -> str:
    """Convert container-internal path to host path when running in Docker

    Args:
        container_path: Path that may be inside the playground container

    Returns:
        str: Host path for volume mounting
    """
    if not RUNNING_IN_DOCKER or not HOST_SHARED_VOLUMES_PATH:
        return container_path

    # Convert /app/shared-volumes/... to host path
    container_shared_dir = str(SHARED_DIR)
    if container_path.startswith(container_shared_dir):
        # Replace /app/shared-volumes with the actual host path
        relative_path = container_path[len(container_shared_dir):].lstrip('/')
        host_path = os.path.join(HOST_SHARED_VOLUMES_PATH, relative_path)
        logger.debug("Converted path: %s -> %s", container_path, host_path)
        return host_path

    return container_path


def prepare_volumes(volumes_config: List[Dict[str, Any]]) -> List[str]:
    """Prepare volumes for docker-compose format"""
    if not volumes_config:
        return []

    compose_volumes = []

    for vol_data in volumes_config:
        vol_type = vol_data.get("type", "named")
        vol_path = vol_data.get("path", "")
        readonly = vol_data.get("readonly", False)

        if not vol_path:
            logger.warning("Volume missing path: %s", vol_data)
            continue

        if vol_type == "named":
            vol_name = vol_data.get("name")
            if vol_name:
                vol_str = f"{vol_name}:{vol_path}"
                if readonly:
                    vol_str += ":ro"
                compose_volumes.append(vol_str)

        elif vol_type in ("bind", "file"):
            host_path = vol_data.get("host")
            if host_path:
                if not host_path.startswith("/"):
                    host_path = str(BASE_DIR / host_path)

                # Convert to host path if running in Docker
                host_path = convert_to_host_path(host_path)

                try:
                    if vol_type == "bind":
                        Path(host_path).mkdir(parents=True, exist_ok=True)
                    elif vol_type == "file":
                        Path(host_path).parent.mkdir(parents=True, exist_ok=True)
                        Path(host_path).touch(exist_ok=True)
                except Exception as e:
                    logger.warning("Failed to prepare volume path %s: %s", host_path, str(e))

                vol_str = f"{host_path}:{vol_path}"
                if readonly:
                    vol_str += ":ro"
                compose_volumes.append(vol_str)

    return compose_volumes


def check_port_available(port: int) -> Tuple[bool, str]:
    """Check if a port is available on the host
    
    Args:
        port: Port number to check
    
    Returns:
        Tuple[bool, str]: (is_available, used_by_container_or_system)
    """
    try:
        all_containers = docker_client.containers.list(all=True)
        for container in all_containers:
            ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            if ports:
                for container_port, bindings in ports.items():
                    if bindings:
                        for binding in bindings:
                            if binding and binding.get('HostPort') == str(port):
                                return False, container.name
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TimeoutConfig.PORT_CHECK_TIMEOUT)
        result = sock.connect_ex(('0.0.0.0', port))
        sock.close()
        
        if result == 0:
            return False, "host system"
        
        return True, ""
    except Exception as e:
        logger.warning("Error checking port %d: %s", port, str(e))
        return True, ""

def validate_ports_available(img_data: Dict[str, Any], container_name: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """Validate all ports are available for a container"""
    conflicts = []
    ports = img_data.get("ports", [])

    for i, port_mapping in enumerate(ports):
        # Validate that port_mapping is a string
        if not isinstance(port_mapping, str):
            error_msg = f"Port mapping at index {i} must be a string, got {type(port_mapping).__name__}: {repr(port_mapping)}"
            logger.error("%s: %s", container_name, error_msg)
            logger.error("%s: This usually means the port wasn't quoted in YAML config", container_name)
            logger.error("%s: YAML may have parsed it as a number (e.g., 2222:22 as sexagesimal)", container_name)

            # Return a conflict with helpful error information
            conflicts.append({
                "host_port": "invalid",
                "container_port": "invalid",
                "used_by": f"Configuration Error: {error_msg}. Tip: Quote port mappings in YAML (e.g., \"3000:3000\")"
            })
            continue

        try:
            if ':' not in port_mapping:
                logger.warning("%s: Invalid port mapping format: %s", container_name, port_mapping)
                continue

            host_port, container_port = port_mapping.split(":", 1)
            host_port_int = int(host_port)

            is_available, used_by = check_port_available(host_port_int)
            if not is_available:
                conflicts.append({
                    "host_port": host_port_int,
                    "container_port": container_port,
                    "used_by": used_by
                })
        except ValueError as e:
            logger.warning("%s: Invalid port mapping: %s - %s", container_name, port_mapping, str(e))

    return len(conflicts) == 0, conflicts


def get_stop_timeout(img_data: Dict[str, Any]) -> int:
    """Get appropriate stop timeout based on scripts
    
    Args:
        img_data: Image configuration dict
    
    Returns:
        int: Stop timeout in seconds
    """
    scripts = img_data.get("scripts", {})
    
    if scripts.get("pre_stop"):
        timeout = TimeoutConfig.CONTAINER_STOP_TIMEOUT_WITH_SCRIPTS
        logger.debug("Using extended stop timeout (%.1fs) due to pre_stop script", timeout)
        return timeout
    
    return TimeoutConfig.CONTAINER_STOP_TIMEOUT_DEFAULT




def start_single_container_sync(container_name: str, img_data: Dict[str, Any], operation_id: str = None) -> Dict[str, Any]:
    """Start a single container synchronously with volume support
    
    Args:
        container_name: Container name (without 'playground-' prefix)
        img_data: Image configuration dict
        operation_id: Optional operation ID for tracking
    
    Returns:
        dict: Status dict with keys: status, name, error (if failed)
    
    Status codes:
        - "started": Container successfully started
        - "already_running": Container was already running
        - "failed": Container failed to start
    """
    from src.web.core.scripts import execute_script
    from src.web.core.state import add_script_tracking, complete_script_tracking, update_operation

    full_container_name = to_full_name(container_name)
    logger.info("Starting container: %s (timeout: %ds)", container_name, TimeoutConfig.CONTAINER_START_TIMEOUT)

    def update_phase(phase: str):
        """Helper to update operation phase"""
        if operation_id:
            update_operation(operation_id, operation_phase=phase, container_name=full_container_name)

    update_phase("starting_container")

    try:
        # Check if container already exists
        existing = docker_client.containers.get(full_container_name)
        if existing.status == "running":
            logger.info("Container %s already running", container_name)
            return {"status": "already_running", "name": container_name}
        else:
            update_phase("removing_existing")
            logger.info("Removing stopped container %s", container_name)
            existing.remove(force=True)
    except docker.errors.NotFound:
        pass

    # Validate ports
    ports_available, conflicts = validate_ports_available(img_data, container_name)
    if not ports_available:
        conflict_list = [f"{c['host_port']} (used by {c['used_by']})" for c in conflicts]
        error_msg = f"Port conflicts: {', '.join(conflict_list)}"
        logger.error("%s: %s", container_name, error_msg)

        # Check if this is a configuration error (invalid port type)
        port_list = img_data.get("ports", [])
        has_config_error = any(c['host_port'] == 'invalid' for c in conflicts)

        if has_config_error:
            # Build detailed debug information for configuration errors
            debug_info = {
                "error_type": "PortConfigurationError",
                "all_ports": [{"index": idx, "value": repr(port), "type": type(port).__name__}
                             for idx, port in enumerate(port_list)],
                "conflicts": conflicts,
                "tips": [
                    "Port mappings must be quoted strings in YAML (e.g., \"3000:3000\")",
                    "YAML interprets unquoted values like 2222:22 as sexagesimal (base-60) numbers",
                    "Fix: Add quotes around all port mappings in your YAML config file",
                ],
                "fix_example": {
                    "wrong": "ports:\n  - 3000:3000\n  - 2222:22",
                    "correct": "ports:\n  - \"3000:3000\"\n  - \"2222:22\""
                }
            }
            return {
                "status": "failed",
                "name": container_name,
                "error": error_msg,
                "debug_info": debug_info
            }

        return {"status": "failed", "name": container_name, "error": error_msg}

    # Prepare volumes
    update_phase("preparing_volumes")
    volumes_config = img_data.get("volumes", [])
    ensure_named_volumes(volumes_config)

    compose_volumes = prepare_volumes(volumes_config)

    # Use host path for shared directory when running in Docker
    shared_host_path = convert_to_host_path(str(SHARED_DIR))
    all_volumes = [f"{shared_host_path}:/shared"]
    all_volumes.extend(compose_volumes)

    # Parse and validate ports
    ports = {}
    port_list = img_data.get("ports", [])
    for i, p in enumerate(port_list):
        if not isinstance(p, str):
            error_msg = f"Port mapping must be a string, got {type(p).__name__}: {repr(p)}"
            logger.error("%s: Invalid port configuration at index %d: %s", container_name, i, error_msg)

            # Add helpful debug information
            debug_info = {
                "error_type": "InvalidPortConfiguration",
                "port_index": i,
                "port_value": repr(p),
                "port_type": type(p).__name__,
                "all_ports": [{"index": idx, "value": repr(port), "type": type(port).__name__}
                             for idx, port in enumerate(port_list)],
                "tips": [
                    "Port mappings must be quoted strings in YAML (e.g., \"3000:3000\")",
                    f"YAML parsed port at index {i} as {type(p).__name__} instead of string",
                    "Common issue: YAML interprets unquoted values like 2222:22 as sexagesimal numbers",
                    "Fix: Add quotes around all port mappings in your YAML config",
                ],
                "fix_example": {
                    "wrong": "ports:\n  - 3000:3000\n  - 2222:22",
                    "correct": "ports:\n  - \"3000:3000\"\n  - \"2222:22\""
                }
            }

            return {
                "status": "failed",
                "name": container_name,
                "error": error_msg,
                "debug_info": debug_info
            }

        if ':' not in p:
            error_msg = f"Port mapping must be in format 'host:container', got: {p}"
            logger.error("%s: %s", container_name, error_msg)
            return {
                "status": "failed",
                "name": container_name,
                "error": error_msg
            }

        hp, cp = p.split(":", 1)
        ports[cp] = hp

    # Extract Docker Compose parameters
    docker_params = extract_docker_params(img_data)

    if docker_params:
        logger.info("Using Docker Compose parameters: %s", list(docker_params.keys()))

    # Prepare base parameters
    base_params = {
        "detach": True,
        "name": full_container_name,
        "environment": img_data.get("environment", {}),
        "ports": ports if ports else None,
        "volumes": all_volumes,
        "command": img_data.get("keep_alive_cmd", "sleep infinity"),
        "network": NETWORK_NAME,
        "stdin_open": True,
        "tty": True,
        "labels": {"playground.managed": "true"}
    }

    # Only set hostname if not already in docker_params
    if "hostname" not in docker_params:
        base_params["hostname"] = container_name

    # Create and run container
    try:
        update_phase("launching")
        logger.info("Running Docker image: %s as %s", img_data["image"], full_container_name)
        container = docker_client.containers.run(
            img_data["image"],
            **base_params,
            **docker_params  # Pass through Docker Compose parameters
        )
    except docker.errors.ImageNotFound:
        update_phase("pulling_image")
        logger.info("Image not found locally, attempting to pull: %s", img_data["image"])
        try:
            docker_client.images.pull(img_data["image"])
            update_phase("launching")
            container = docker_client.containers.run(
                img_data["image"],
                **base_params,
                **docker_params
            )
        except Exception as pull_error:
            error_msg = f"Failed to pull/start image: {str(pull_error)}"
            logger.error("%s: %s", container_name, error_msg)
            return {"status": "failed", "name": container_name, "error": error_msg}
    except docker.errors.APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error("%s: %s", container_name, error_msg)
        return {"status": "failed", "name": container_name, "error": error_msg}

    # Wait for container to be running
    update_phase("waiting_ready")
    max_wait = TimeoutConfig.CONTAINER_START_TIMEOUT
    elapsed = 0
    wait_interval = TimeoutConfig.CONTAINER_START_POLL_INTERVAL
    start_time = time.time()

    logger.debug("Polling container status (max %ds, interval %.2fs)", max_wait, wait_interval)
    
    while elapsed < max_wait:
        try:
            container.reload()
            
            if container.status == "running":
                elapsed_time = time.time() - start_time
                logger.info("Container %s is now running (took %.2fs)", full_container_name, elapsed_time)
                
                # Execute post-start script
                scripts = img_data.get('scripts', {})
                post_start_script = scripts.get('post_start') if scripts else None

                try:
                    update_phase("running_post_start")
                    logger.info(">>> CALLING post_start script for %s", full_container_name)

                    if operation_id:
                        add_script_tracking(operation_id, full_container_name, "post_start")

                    execute_script(post_start_script, full_container_name, container_name, script_type="init")
                    logger.info(">>> post_start script COMPLETED successfully for %s", full_container_name)

                    if operation_id:
                        complete_script_tracking(operation_id, full_container_name)
                except Exception as script_error:
                    logger.error(">>> post_start script FAILED for %s: %s", full_container_name, str(script_error))

                    if operation_id:
                        complete_script_tracking(operation_id, full_container_name)

                update_phase("completed")
                return {"status": "started", "name": container_name}
            
            elif container.status in ["exited", "dead"]:
                error_msg = f"Container failed to start: {container.status}"
                logger.error("%s: %s", container_name, error_msg)
                
                # Try to get exit logs
                try:
                    logs = container.logs(tail=10).decode('utf-8', errors='replace')
                    logger.error("Container logs: %s", logs[:500])  # Log first 500 chars
                except Exception as e:
                    logger.warning("Could not get container logs: %s", str(e))
                
                return {"status": "failed", "name": container_name, "error": error_msg}
        
        except docker.errors.NotFound:
            error_msg = "Container disappeared after creation"
            logger.error("%s: %s", container_name, error_msg)
            return {"status": "failed", "name": container_name, "error": error_msg}
        except Exception as e:
            logger.warning("Error checking container status: %s", str(e))
        
        time.sleep(wait_interval)
        elapsed = time.time() - start_time
        
        if elapsed % 5 < wait_interval:  # Log every ~5 seconds
            logger.debug("Still waiting for %s (elapsed: %.1fs/%ds)", container_name, elapsed, max_wait)
    
    # Timeout reached
    try:
        container.reload()
        status = container.status
    except:
        status = "unknown"
    
    error_msg = f"Container did not start within {max_wait}s timeout (status: {status})"
    logger.error("%s: %s", container_name, error_msg)
    return {"status": "failed", "name": container_name, "error": error_msg}


def stop_single_container_sync(container_name: str, img_data: Dict[str, Any], operation_id: str = None) -> Dict[str, Any]:
    """Stop a single container synchronously with proper timeout
    
    Args:
        container_name: Container name (with or without 'playground-' prefix)
        img_data: Image configuration dict
        operation_id: Optional operation ID for tracking
    
    Returns:
        dict: Status dict with keys: status, name, error (if failed)
    
    Status codes:
        - "stopped": Container successfully stopped
        - "not_running": Container was not running
        - "failed": Container failed to stop
    """
    from src.web.core.scripts import execute_script
    from src.web.core.state import add_script_tracking, complete_script_tracking, update_operation

    base_container_name = to_display_name(container_name)
    full_container_name = to_full_name(container_name)

    def update_phase(phase: str):
        """Helper to update operation phase"""
        if operation_id:
            update_operation(operation_id, operation_phase=phase, container_name=full_container_name)

    logger.info(">>> START stop_single_container_sync for: %s (full_name: %s)",
                base_container_name, full_container_name)

    try:
        cont = docker_client.containers.get(full_container_name)
        logger.info(">>> Container found, status: %s", cont.status)

        if cont.status != "running":
            logger.info(">>> Container not running, returning not_running")
            return {"status": "not_running", "name": base_container_name}

        # Execute pre-stop script
        update_phase("running_pre_stop")
        scripts = img_data.get('scripts', {})
        pre_stop_script = scripts.get('pre_stop') if scripts else None

        try:
            logger.info(">>> CALLING pre_stop script for %s", full_container_name)

            if operation_id:
                add_script_tracking(operation_id, full_container_name, "pre_stop")

            execute_script(pre_stop_script, full_container_name, base_container_name, script_type="halt")
            logger.info(">>> pre_stop script COMPLETED successfully for %s", full_container_name)

            if operation_id:
                complete_script_tracking(operation_id, full_container_name)
        except Exception as script_error:
            logger.error(">>> pre_stop script FAILED for %s: %s", full_container_name, str(script_error))

            if operation_id:
                complete_script_tracking(operation_id, full_container_name)

        # Stop container with configured timeout
        update_phase("stopping")
        timeout = get_stop_timeout(img_data)
        logger.info("Stopping container %s with timeout %ds", full_container_name, timeout)

        try:
            cont.stop(timeout=timeout)
            update_phase("removing")
            cont.remove()
            logger.info("Container %s stopped and removed", base_container_name)
            update_phase("completed")
            return {"status": "stopped", "name": base_container_name}
        except Exception as e:
            logger.error("Error stopping container %s: %s", full_container_name, str(e))
            # Try force removal
            try:
                cont.remove(force=True)
                logger.warning("Container force removed after stop failure")
                update_phase("completed")
                return {"status": "stopped", "name": base_container_name}
            except Exception as force_error:
                raise Exception(f"Failed to stop and remove: {str(e)}, force failed: {str(force_error)}")
    
    except docker.errors.NotFound:
        logger.warning("Container %s not found", full_container_name)
        return {"status": "not_running", "name": base_container_name}
    
    except Exception as e:
        error_msg = f"Error stopping {base_container_name}: {str(e)}"
        logger.error(error_msg)
        return {"status": "failed", "name": base_container_name, "error": error_msg}


def has_default_script(container_name: str, script_type: str) -> bool:
    """Check if a default script exists for a container
    
    Args:
        container_name: Container name without 'playground-' prefix (e.g., 'mysql-8.0')
        script_type: 'init' or 'halt'
    
    Returns:
        bool: True if default script exists
    """
    full_container_name = to_full_name(container_name)
    script_name = f"{container_name}/{full_container_name}-{script_type}.sh"
    script_path = SCRIPTS_DIR / script_name
    return script_path.exists()


def get_container_features(image_name: str, config: Dict[str, Any]) -> Dict[str, bool]:
    """Get special features of a container, including default scripts"""
    img_data = config.get(image_name, {})
    
    # Check for YAML configured scripts
    has_yaml_post_start = bool(img_data.get('scripts', {}).get('post_start'))
    has_yaml_pre_stop = bool(img_data.get('scripts', {}).get('pre_stop'))
    
    # Check for default scripts
    has_default_post_start = has_default_script(image_name, 'init')
    has_default_pre_stop = has_default_script(image_name, 'halt')
    
    return {
        'has_motd': bool(img_data.get('motd')),
        'has_scripts': bool(img_data.get('scripts')) or has_default_post_start or has_default_pre_stop,
        'has_post_start': has_yaml_post_start or has_default_post_start,
        'has_pre_stop': has_yaml_pre_stop or has_default_pre_stop,
        'has_default_post_start': has_default_post_start,
        'has_default_pre_stop': has_default_pre_stop,
        'has_volumes': bool(img_data.get('volumes'))
    }


def get_container_volumes(container_name: str) -> Dict[str, str]:
    """Get volumes mounted in a container"""
    container_name = to_full_name(container_name)

    try:
        cont = docker_client.containers.get(container_name)
        mounts = cont.attrs.get('Mounts', [])
        
        volumes_info = {}
        for mount in mounts:
            container_path = mount.get('Destination', '')
            mount_type = mount.get('Type', '')
            
            if mount_type == 'volume':
                volume_name = mount.get('Name', '')
                volumes_info[container_path] = f"[volume] {volume_name}"
            elif mount_type == 'bind':
                source = mount.get('Source', '')
                volumes_info[container_path] = f"[bind] {source}"
        
        return volumes_info
    except:
        return {}


ensure_network()
logger.info("Docker operations module loaded successfully")
logger.info("Shared directory: %s", SHARED_DIR)
logger.info("Network: %s", NETWORK_NAME)
logger.info("Scripts directory: %s", SCRIPTS_DIR)
