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
                # Convert relative paths to absolute
                if not host_path.startswith("/"):
                    host_path = str(BASE_DIR / host_path)
                
                # Create directory/file if needed
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


def get_stop_timeout(img_data: Dict[str, Any]) -> int:
    """Get appropriate stop timeout based on scripts"""
    # If there's a pre-stop script, give it more time
    scripts = img_data.get("scripts", {})
    if scripts.get("pre_stop"):
        return 30  # 30 seconds for containers with pre-stop scripts
    return 10  # 10 seconds default


def start_single_container_sync(container_name: str, img_data: Dict[str, Any]) -> Dict[str, Any]:
    """Start a single container synchronously with volume support"""
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
    
    # Prepare volumes
    volumes_config = img_data.get("volumes", [])
    ensure_named_volumes(volumes_config)
    compose_volumes = prepare_volumes(volumes_config)
    
    # Build final volumes list
    all_volumes = [f"{SHARED_DIR}:/shared"]
    all_volumes.extend(compose_volumes)
    
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
            ports=ports if ports else None,
            volumes=all_volumes,
            command=img_data.get("keep_alive_cmd", "sleep infinity"),
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
    """Stop a single container synchronously with proper timeout"""
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
                logger.info("Executing pre-stop script for %s", container_name)
                execute_script(scripts['pre_stop'], full_container_name, container_name)
                logger.info("Pre-stop script completed for %s", container_name)
            except Exception as script_error:
                logger.warning("Pre-stop script error for %s: %s", container_name, str(script_error))
        
        # Get appropriate timeout
        timeout = get_stop_timeout(img_data)
        logger.info("Stopping container %s with timeout %d seconds", full_container_name, timeout)
        
        cont.stop(timeout=timeout)
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
        'has_pre_stop': bool(img_data.get('scripts', {}).get('pre_stop')),
        'has_volumes': bool(img_data.get('volumes'))
    }


def get_container_volumes(container_name: str) -> Dict[str, str]:
    """Get volumes mounted in a container"""
    if not container_name.startswith("playground-"):
        container_name = f"playground-{container_name}"
    
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


# Initialize network on import
ensure_network()