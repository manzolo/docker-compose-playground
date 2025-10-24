"""Docker client management and container utilities"""
import docker
import socket
import logging
from typing import Dict, Any, List, Tuple
from pathlib import Path
import time

# Logger che scrive direttamente su file
logger = logging.getLogger("docker_ops")
logger.setLevel(logging.DEBUG)

# Configura il file handler per scrivere su venv/web.log
LOG_FILE = Path(__file__).parent.parent.parent.parent / "venv" / "web.log"
if not logger.handlers:
    file_handler = logging.FileHandler(str(LOG_FILE), mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [DOCKER] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

docker_client = docker.from_env()

# Paths and configurations
BASE_DIR = Path(__file__).parent.parent.parent.parent
SHARED_DIR = BASE_DIR / "shared-volumes"
NETWORK_NAME = "playground-network"
SCRIPTS_DIR = BASE_DIR / "scripts"


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
                if not host_path.startswith("/"):
                    host_path = str(BASE_DIR / host_path)
                
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
    scripts = img_data.get("scripts", {})
    if scripts.get("pre_stop"):
        return 30
    return 10


def start_single_container_sync(container_name: str, img_data: Dict[str, Any], operation_id: str = None) -> Dict[str, Any]:
    """Start a single container synchronously with volume support"""
    from src.web.core.scripts import execute_script
    from src.web.core.state import add_script_tracking, complete_script_tracking
    
    full_container_name = f"playground-{container_name}"
    logger.info("Starting container: %s", container_name)
    
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
    
    ports_available, conflicts = validate_ports_available(img_data, container_name)
    if not ports_available:
        conflict_list = [f"{c['host_port']} (used by {c['used_by']})" for c in conflicts]
        error_msg = f"Port conflicts: {', '.join(conflict_list)}"
        logger.error("%s: %s", container_name, error_msg)
        return {"status": "failed", "name": container_name, "error": error_msg}
    
    volumes_config = img_data.get("volumes", [])
    ensure_named_volumes(volumes_config)
    
    compose_volumes = prepare_volumes(volumes_config)
    all_volumes = [f"{SHARED_DIR}:/shared"]
    all_volumes.extend(compose_volumes)
    
    ports = {cp: hp for hp, cp in (p.split(":") for p in img_data.get("ports", []))}
    
    try:
        logger.info("Running Docker image: %s as %s", img_data["image"], full_container_name)
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
    
    max_wait = 30
    elapsed = 0
    wait_interval = 0.5
    
    while elapsed < max_wait:
        try:
            container.reload()
            if container.status == "running":
                logger.info("Container %s is now running", full_container_name)
                
                scripts = img_data.get('scripts', {})
                post_start_script = scripts.get('post_start') if scripts else None
                
                try:
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
    
    container.reload()
    error_msg = f"Container did not start in time (status: {container.status})"
    logger.error("%s: %s", container_name, error_msg)
    return {"status": "failed", "name": container_name, "error": error_msg}


def stop_single_container_sync(container_name: str, img_data: Dict[str, Any], operation_id: str = None) -> Dict[str, Any]:
    """Stop a single container synchronously with proper timeout"""
    from src.web.core.scripts import execute_script
    from src.web.core.state import add_script_tracking, complete_script_tracking
    
    if container_name.startswith("playground-"):
        base_container_name = container_name.replace("playground-", "")
        full_container_name = container_name
    else:
        base_container_name = container_name
        full_container_name = f"playground-{container_name}"
    
    logger.info(">>> START stop_single_container_sync for: %s (full_name: %s)", base_container_name, full_container_name)
    
    try:
        cont = docker_client.containers.get(full_container_name)
        logger.info(">>> Container found, status: %s", cont.status)
        
        if cont.status != "running":
            logger.info(">>> Container not running, returning not_running")
            return {"status": "not_running", "name": base_container_name}
        
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
        
        timeout = get_stop_timeout(img_data)
        logger.info("Stopping container %s with timeout %d seconds", full_container_name, timeout)
        
        cont.stop(timeout=timeout)
        cont.remove()
        
        logger.info("Container %s stopped and removed", base_container_name)
        return {"status": "stopped", "name": base_container_name}
    
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
        container_name: Container name without 'playground-' prefix (e.g., 'mysql-8')
        script_type: 'init' or 'halt'
    
    Returns:
        bool: True if default script exists
    """
    full_container_name = f"playground-{container_name}" if not container_name.startswith("playground-") else container_name
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


ensure_network()