"""Health check and system diagnostics APIs"""
from fastapi import APIRouter, HTTPException
import docker
import logging
from datetime import datetime

logger = logging.getLogger("uvicorn")
docker_client = docker.from_env()

router = APIRouter()


@router.get("/api/system-health")
async def get_system_health():
    """Get overall system health and diagnostics
    
    Returns:
        dict: System health status, warnings, recommendations
    """
    try:
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "warnings": [],
            "critical": [],
            "metrics": {},
            "recommendations": []
        }
        
        # Check Docker daemon
        try:
            docker_info = docker_client.info()
            health_report["metrics"]["docker"] = {
                "version": docker_info.get('ServerVersion', 'unknown'),
                "containers_total": docker_info.get('Containers', 0),
                "containers_running": docker_info.get('ContainersRunning', 0),
                "images": docker_info.get('Images', 0),
                "memory_available_gb": round(docker_info.get('MemTotal', 0) / (1024**3), 2)
            }
        except Exception as e:
            health_report["critical"].append(f"Docker daemon error: {str(e)}")
            health_report["status"] = "critical"
            return health_report
        
        # Check managed containers
        try:
            containers = docker_client.containers.list(filters={"label": "playground.managed=true"})
            running = sum(1 for c in containers if c.status == "running")
            stopped = len(containers) - running
            
            health_report["metrics"]["containers"] = {
                "total": len(containers),
                "running": running,
                "stopped": stopped
            }
            
            # Warning if all stopped
            if len(containers) > 0 and running == 0:
                health_report["warnings"].append("All containers are stopped")
                health_report["recommendations"].append("Start containers from the dashboard")
            
            # Warning if some stopped
            if stopped > 0:
                health_report["warnings"].append(f"{stopped} container(s) are stopped")
        
        except Exception as e:
            logger.warning("Failed to check container status: %s", str(e))
            health_report["warnings"].append(f"Could not check container status: {str(e)}")
        
        # Check network
        try:
            from src.web.core.docker import NETWORK_NAME
            network = docker_client.networks.get(NETWORK_NAME)
            containers_in_network = len(network.containers)
            
            health_report["metrics"]["network"] = {
                "name": network.name,
                "driver": network.attrs.get('Driver', 'unknown'),
                "containers_connected": containers_in_network
            }
        except Exception as e:
            logger.warning("Failed to check network: %s", str(e))
            health_report["warnings"].append(f"Network issue: {str(e)}")
        
        # Check shared volume
        try:
            from src.web.core.docker import SHARED_DIR
            import os
            
            if SHARED_DIR.exists():
                volume_size = sum(
                    os.path.getsize(os.path.join(dp, f))
                    for dp, _, fns in os.walk(SHARED_DIR)
                    for f in fns
                )
                volume_size_gb = volume_size / (1024**3)
                
                health_report["metrics"]["volume"] = {
                    "path": str(SHARED_DIR),
                    "size_gb": round(volume_size_gb, 2),
                    "accessible": True
                }
                
                # Warning if volume getting large
                if volume_size_gb > 5:
                    health_report["warnings"].append(f"Shared volume is large ({volume_size_gb:.2f} GB)")
                    health_report["recommendations"].append("Consider cleaning up old files in shared volume")
            else:
                health_report["warnings"].append("Shared volume directory not found")
        
        except Exception as e:
            logger.warning("Failed to check volume: %s", str(e))
            health_report["warnings"].append(f"Volume check error: {str(e)}")
        
        # Check disk space
        try:
            import shutil
            disk_usage = shutil.disk_usage("/")
            disk_free_gb = disk_usage.free / (1024**3)
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            health_report["metrics"]["disk"] = {
                "total_gb": round(disk_usage.total / (1024**3), 2),
                "used_gb": round(disk_usage.used / (1024**3), 2),
                "free_gb": round(disk_free_gb, 2),
                "percent_used": round(disk_percent, 1)
            }
            
            # Critical if low disk space
            if disk_free_gb < 1:
                health_report["critical"].append("Critically low disk space (<1 GB)")
                health_report["status"] = "critical"
                health_report["recommendations"].append("Free up disk space immediately")
            
            # Warning if moderate
            elif disk_free_gb < 5:
                health_report["warnings"].append(f"Low disk space ({disk_free_gb:.2f} GB free)")
                health_report["recommendations"].append("Consider freeing up disk space")
        
        except Exception as e:
            logger.warning("Failed to check disk: %s", str(e))
            health_report["warnings"].append(f"Disk check error: {str(e)}")
        
        # Determine overall status
        if health_report["critical"]:
            health_report["status"] = "critical"
        elif health_report["warnings"]:
            health_report["status"] = "warning"
        else:
            health_report["status"] = "healthy"
        
        return health_report
    
    except Exception as e:
        logger.error("Error getting system health: %s", str(e))
        raise HTTPException(500, str(e))


@router.get("/api/port-conflicts")
async def check_port_conflicts():
    """Check for port conflicts among containers and system
    
    Returns:
        dict: List of conflicts and available ports
    """
    try:
        conflicts = []
        port_map = {}
        
        # Get all containers
        all_containers = docker_client.containers.list(all=True)
        
        # Check port usage
        for container in all_containers:
            ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            
            if ports:
                for container_port, bindings in ports.items():
                    if bindings:
                        for binding in bindings:
                            if binding:
                                host_port = binding.get('HostPort')
                                if host_port:
                                    if host_port in port_map:
                                        conflicts.append({
                                            "port": host_port,
                                            "containers": [port_map[host_port], container.name],
                                            "severity": "critical"
                                        })
                                    else:
                                        port_map[host_port] = container.name
        
        # Check for system-level conflicts
        import socket
        system_conflicts = []
        
        for port in port_map.keys():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                result = sock.connect_ex(('0.0.0.0', int(port)))
                sock.close()
                
                if result == 0:
                    system_conflicts.append({
                        "port": port,
                        "source": "system_process",
                        "severity": "warning"
                    })
            except Exception as e:
                logger.debug("Error checking port %s: %s", port, str(e))
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_conflicts": len(conflicts) + len(system_conflicts),
            "container_conflicts": conflicts,
            "system_conflicts": system_conflicts,
            "ports_in_use": list(port_map.keys()),
            "status": "conflict" if conflicts else "ok"
        }
    
    except Exception as e:
        logger.error("Error checking port conflicts: %s", str(e))
        raise HTTPException(500, str(e))


@router.post("/api/validate-config/{image}")
async def validate_config(image: str):
    """Validate container configuration before starting
    
    Args:
        image: Image name to validate
    
    Returns:
        dict: Validation results and warnings
    """
    try:
        from src.web.core.config import load_config
        from src.web.core.docker import validate_ports_available
        
        config_data = load_config()
        images = config_data["images"]
        
        if image not in images:
            raise HTTPException(404, f"Image '{image}' not found in configuration")
        
        img_data = images[image]
        validation = {
            "image": image,
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Check if image exists
        try:
            docker_client.images.get(img_data["image"])
        except docker.errors.ImageNotFound:
            validation["errors"].append(f"Docker image '{img_data['image']}' not found locally")
            validation["valid"] = False
        
        # Check ports
        ports_ok, conflicts = validate_ports_available(img_data, image)
        if not ports_ok:
            validation["errors"].append(f"Port conflicts detected: {conflicts}")
            validation["valid"] = False
        
        # Check required fields
        required_fields = ["image", "category", "description"]
        for field in required_fields:
            if field not in img_data or not img_data[field]:
                validation["errors"].append(f"Missing required field: {field}")
                validation["valid"] = False
        
        # Warnings
        if not img_data.get("keep_alive_cmd"):
            validation["warnings"].append("No keep_alive_cmd specified, using default")
        
        if not img_data.get("shell"):
            validation["warnings"].append("No shell specified, using default")
        
        return validation
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error validating config for %s: %s", image, str(e))
        raise HTTPException(500, str(e))