import docker
import socket
import logging
from typing import Dict, Any, List, Tuple
from pathlib import Path
import time

logger = logging.getLogger("uvicorn")
docker_client = docker.from_env()

# Percorsi e configurazioni
BASE_DIR = Path(__file__).parent.parent.parent.parent
SHARED_DIR = BASE_DIR / "shared-volumes"
NETWORK_NAME = "playground-network"

def ensure_network():
    """Ensure playground network exists"""
    try:
        docker_client.networks.get(NETWORK_NAME)
        logger.info("Network %s already exists", NETWORK_NAME)
    except docker.errors.NotFound:
        logger.info("Creating network %s", NETWORK_NAME)
        docker_client.networks.create(NETWORK_NAME, driver="bridge")
        logger.info("Network %s created", NETWORK_NAME)

def check_port_available(port: int) -> Tuple[bool, str]:
    """Check if a port is available on the host"""
    try:
        # Check containers
        all_containers = docker_client.containers.list(all=True)
        for container in all_containers:
            ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            if ports:
                for container_port, bindings in ports.items():
                    if bindings:
                        for binding in bindings:
                            if binding and binding.get('HostPort') == str(port):
                                return False, container.name
        
        # Check host system
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
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
    
    for port_mapping in ports:
        try:
            host_port, container_port = port_mapping.split(":")
            host_port_int = int(host_port)
            
            is_available, used_by = check_port_available(host_port_int)
            if not is_available:
                conflicts.append({
                    "host_port": host_port_int,
                    "container_port": container_port,
                    "used_by": used_by
                })
        except ValueError:
            logger.warning("Invalid port mapping: %s", port_mapping)
    
    return len(conflicts) == 0, conflicts

def start_single_container_sync(container_name: str, img_data: Dict[str, Any]) -> Dict[str, Any]:
    """Start a single container synchronously"""
    from src.web.core.scripts import execute_script
    
    full_container_name = f"playground-{container_name}"
    logger.info("Starting container: %s", container_name)
    
    # Check if already running
    try:
        existing = docker_client.containers.get(full_container_name)
        if existing.status == "running":
            logger.info("Container %s already running", container_name)
            return {"status": "already_running", "name": container_name}
        else:
            logger.info("Removing stopped container %s", container_name)
            existing.remove(force=True)
    except docker.errors.NotFound:
        pass
    
    # Check port availability
    ports_available, conflicts = validate_ports_available(img_data, container_name)
    if not ports_available:
        conflict_details = ", ".join([f"port {c['host_port']} (used by {c['used_by']})" for c in conflicts])
        error_msg = f"Port conflict: {conflict_details}"
        logger.error("%s: %s", container_name, error_msg)
        return {"status": "failed", "name": container_name, "error": error_msg, "conflicts": conflicts}
    
    # Ensure network
    ensure_network()
    
    # Parse ports
    ports = {cp: hp for hp, cp in (p.split(":") for p in img_data.get("ports", []))}
    
    # Start container
    try:
        container = docker_client.containers.run(
            img_data["image"],
            detach=True,
            name=full_container_name,
            hostname=container_name,
            environment=img_data.get("environment", {}),
            ports=ports,
            volumes=[f"{SHARED_DIR}:/shared"],
            command=img_data["keep_alive_cmd"],
            network=NETWORK_NAME,
            stdin_open=True,
            tty=True,
            labels={"playground.managed": "true"}
        )
    except docker.errors.ImageNotFound:
        error_msg = f"Docker image not found: {img_data.get('image', 'unknown')}"
        logger.error("%s: %s", container_name, error_msg)
        return {"status": "failed", "name": container_name, "error": error_msg}
    except docker.errors.APIError as e:
        error_msg = f"Docker API error: {str(e)}"
        logger.error("%s: %s", container_name, error_msg)
        return {"status": "failed", "name": container_name, "error": error_msg}
    
    # Wait for running
    max_wait = 30
    elapsed = 0
    wait_interval = 0.5
    
    while elapsed < max_wait:
        try:
            container.reload()
            if container.status == "running":
                logger.info("Container %s is now running", full_container_name)
                
                # Execute post-start script
                scripts = img_data.get('scripts', {})
                if 'post_start' in scripts:
                    try:
                        execute_script(scripts['post_start'], full_container_name, container_name)
                    except Exception as script_error:
                        logger.warning("Post-start script error for %s: %s", container_name, str(script_error))
                
                return {"status": "started", "name": container_name}
            
            elif container.status in ["exited", "dead"]:
                error_msg = f"Container failed to start: {container.status}"
                logger.error("%s: %s", container_name, error_msg)
                return {"status": "failed", "name": container_name, "error": error_msg}
        
        except docker.errors.NotFound:
            error_msg = "Container disappeared after creation"
            logger.error("%s: %s", container_name, error_msg)
            return {"status": "failed", "name": container_name, "error": error_msg}
        
        time.sleep(wait_interval)
        elapsed += wait_interval
    
    # Timeout
    container.reload()
    error_msg = f"Container did not start in time (status: {container.status})"
    logger.error("%s: %s", container_name, error_msg)
    return {"status": "failed", "name": container_name, "error": error_msg}

def stop_single_container_sync(container_name: str, img_data: Dict[str, Any]) -> Dict[str, Any]:
    """Stop a single container synchronously"""
    from src.web.core.scripts import execute_script
    
    full_container_name = f"playground-{container_name}"
    
    try:
        cont = docker_client.containers.get(full_container_name)
        
        if cont.status != "running":
            logger.info("Container %s not running (status: %s)", container_name, cont.status)
            return {"status": "not_running", "name": container_name}
        
        # Execute pre-stop script
        scripts = img_data.get('scripts', {})
        if 'pre_stop' in scripts:
            try:
                execute_script(scripts['pre_stop'], full_container_name, container_name)
            except Exception as script_error:
                logger.warning("Pre-stop script error for %s: %s", container_name, str(script_error))
        
        # Stop and remove
        logger.info("Stopping container %s", full_container_name)
        cont.stop(timeout=90)
        cont.remove()
        
        logger.info("Container %s stopped and removed", container_name)
        return {"status": "stopped", "name": container_name}
    
    except docker.errors.NotFound:
        logger.warning("Container %s not found", container_name)
        return {"status": "not_running", "name": container_name}
    
    except Exception as e:
        error_msg = f"Error stopping {container_name}: {str(e)}"
        logger.error(error_msg)
        return {"status": "failed", "name": container_name, "error": error_msg}

def get_container_features(image_name: str, config: Dict[str, Any]) -> Dict[str, bool]:
    """Get special features of a container"""
    img_data = config.get(image_name, {})
    return {
        'has_motd': bool(img_data.get('motd')),
        'has_scripts': bool(img_data.get('scripts')),
        'has_post_start': bool(img_data.get('scripts', {}).get('post_start')),
        'has_pre_stop': bool(img_data.get('scripts', {}).get('pre_stop'))
    }

# Initialize network on import
ensure_network()