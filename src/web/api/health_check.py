"""Health check and system diagnostics APIs"""
from fastapi import APIRouter, HTTPException
import docker
import logging
from datetime import datetime
import socket
import subprocess
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("uvicorn")
docker_client = docker.from_env()

router = APIRouter()


# ============================================================
# PORT CONFLICT DETECTION - Enhanced
# ============================================================

def check_system_port_usage(port: int, known_docker_ports: List[str] = None) -> Tuple[bool, str]:
    """Check if port is in use by system process (excluding Docker containers)
    
    Args:
        port: Port number to check
        known_docker_ports: List of ports already used by Docker containers to exclude
    
    Returns:
        Tuple[bool, str]: (is_in_use_by_system, process_info)
    """
    if known_docker_ports is None:
        known_docker_ports = []
    
    port_str = str(port)
    
    try:
        # Try ss first (faster on Linux, more reliable than netstat)
        result = subprocess.run(
            ["ss", "-tuln"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                # Check if this port line is NOT a Docker port we already know about
                if f":{port}" in line and "LISTEN" in line:
                    # Only report if NOT a known Docker port
                    if port_str not in known_docker_ports:
                        return True, line.strip()
        
        # Fallback: try netstat (works on Linux/Mac/Windows)
        result = subprocess.run(
            ["netstat", "-tuln"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if f":{port}" in line and ("LISTEN" in line or "ESTABLISHED" in line):
                    # Only report if NOT a known Docker port
                    if port_str not in known_docker_ports:
                        return True, line.strip()
        
        return False, ""
    
    except Exception as e:
        logger.debug("Error checking system port with netstat/ss: %s", str(e))
        
        # Fallback: try lsof (more process-specific, shows PID and process name)
        try:
            result = subprocess.run(
                ["lsof", "-i", f":{port}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                # Filter out Docker-related processes
                lines = result.stdout.split('\n')
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        # Extract process info (e.g., "python   12345  user    5u  IPv4  0x12345...")
                        parts = line.split()
                        if parts:
                            process_name = parts[0]
                            
                            # Check if it's NOT a Docker process AND not a known Docker port
                            if 'docker' not in process_name.lower() and port_str not in known_docker_ports:
                                # Extract PID for better info
                                try:
                                    pid = parts[1]
                                    return True, f"{process_name} (PID {pid}): {line.strip()}"
                                except:
                                    return True, line.strip()
                
                return False, ""
            
            return False, ""
        
        except Exception as e:
            logger.debug("Error checking system port with lsof: %s", str(e))
        
        # Last resort: socket connection test
        # Only return True if port responds AND it's not a known Docker port
        try:
            if port_str in known_docker_ports:
                return False, ""
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                return True, f"Port {port} responds to connection (non-Docker process)"
            return False, ""
        except Exception as e:
            logger.debug("Error in socket port check fallback: %s", str(e))
            return False, ""


# ============================================================
# ENHANCED: get_system_health
# ============================================================

@router.get("/api/system-health")
async def get_system_health():
    """Get overall system health and diagnostics
    
    Comprehensive health check including:
    - Docker daemon status
    - Container health
    - Network status
    - Disk/Volume usage
    - Memory availability
    - Port conflicts
    
    Returns:
        dict: System health status, warnings, recommendations, metrics
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
        
        # ====================================================
        # 1. CHECK DOCKER DAEMON
        # ====================================================
        try:
            docker_info = docker_client.info()
            health_report["metrics"]["docker"] = {
                "version": docker_info.get('ServerVersion', 'unknown'),
                "containers_total": docker_info.get('Containers', 0),
                "containers_running": docker_info.get('ContainersRunning', 0),
                "containers_paused": docker_info.get('ContainersPaused', 0),
                "images": docker_info.get('Images', 0),
                "memory_available_gb": round(docker_info.get('MemTotal', 0) / (1024**3), 2),
                "driver": docker_info.get('Driver', 'unknown'),
                "kernel_version": docker_info.get('KernelVersion', 'unknown')
            }
            
            logger.debug("Docker info: %s", health_report["metrics"]["docker"])
        
        except Exception as e:
            health_report["critical"].append(f"Docker daemon error: {str(e)}")
            health_report["status"] = "critical"
            logger.error("Docker daemon check failed: %s", str(e))
            return health_report
        
        # ====================================================
        # 2. CHECK MANAGED CONTAINERS
        # ====================================================
        try:
            containers = docker_client.containers.list(filters={"label": "playground.managed=true"})
            running = sum(1 for c in containers if c.status == "running")
            paused = sum(1 for c in containers if c.status == "paused")
            stopped = len(containers) - running - paused
            
            health_report["metrics"]["containers"] = {
                "total": len(containers),
                "running": running,
                "paused": paused,
                "stopped": stopped
            }
            
            # Warnings
            if len(containers) > 0 and running == 0:
                health_report["warnings"].append("All managed containers are stopped")
                health_report["recommendations"].append("Start containers from the dashboard")
            
            if stopped > 0 and len(containers) > 0:
                health_report["warnings"].append(f"{stopped} container(s) are stopped")
            
            if paused > 0:
                health_report["warnings"].append(f"{paused} container(s) are paused")
            
            logger.debug("Container status: %d running, %d stopped, %d paused", running, stopped, paused)
        
        except Exception as e:
            logger.warning("Failed to check container status: %s", str(e))
            health_report["warnings"].append(f"Could not check container status: {str(e)}")
        
        # ====================================================
        # 3. CHECK NETWORK
        # ====================================================
        try:
            from src.web.core.docker import NETWORK_NAME
            network = docker_client.networks.get(NETWORK_NAME)
            containers_in_network = len(network.containers)
            
            health_report["metrics"]["network"] = {
                "name": network.name,
                "driver": network.attrs.get('Driver', 'unknown'),
                "containers_connected": containers_in_network,
                "ipam_config": str(network.attrs.get('IPAM', {}).get('Config', []))
            }
            
            logger.debug("Network status: %d containers connected", containers_in_network)
        
        except Exception as e:
            logger.warning("Failed to check network: %s", str(e))
            health_report["warnings"].append(f"Network check failed: {str(e)}")
        
        # ====================================================
        # 4. CHECK SHARED VOLUME
        # ====================================================
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
                
                # Warnings
                if volume_size_gb > 10:
                    health_report["warnings"].append(f"Shared volume is large ({volume_size_gb:.2f} GB)")
                    health_report["recommendations"].append("Consider cleaning up old files in shared volume")
                
                logger.debug("Volume size: %.2f GB", volume_size_gb)
            else:
                health_report["warnings"].append("Shared volume directory not found")
        
        except Exception as e:
            logger.warning("Failed to check volume: %s", str(e))
            health_report["warnings"].append(f"Volume check error: {str(e)}")
        
        # ====================================================
        # 5. CHECK DISK SPACE
        # ====================================================
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
            
            # Critical if very low
            if disk_free_gb < 0.5:
                health_report["critical"].append("CRITICAL: Less than 500MB disk space available")
                health_report["status"] = "critical"
                health_report["recommendations"].append("Free up disk space immediately")
            
            # Warning if moderate
            elif disk_free_gb < 2:
                health_report["warnings"].append(f"Low disk space ({disk_free_gb:.2f} GB free)")
                health_report["recommendations"].append("Consider freeing up disk space")
            
            elif disk_free_gb < 5:
                health_report["warnings"].append(f"Moderate disk usage ({disk_percent:.1f}%)")
            
            logger.debug("Disk usage: %.1f%% used, %.2f GB free", disk_percent, disk_free_gb)
        
        except Exception as e:
            logger.warning("Failed to check disk: %s", str(e))
            health_report["warnings"].append(f"Disk check error: {str(e)}")
        
        # ====================================================
        # 6. CHECK MEMORY
        # ====================================================
        try:
            import psutil
            memory = psutil.virtual_memory()
            memory_available_gb = memory.available / (1024**3)
            memory_percent = memory.percent
            
            health_report["metrics"]["memory"] = {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory_available_gb, 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent_used": round(memory_percent, 1)
            }
            
            if memory_percent > 90:
                health_report["critical"].append("CRITICAL: System memory usage is critical (>90%)")
                health_report["status"] = "critical"
            elif memory_percent > 75:
                health_report["warnings"].append(f"High memory usage ({memory_percent:.1f}%)")
            
            logger.debug("Memory usage: %.1f%% used", memory_percent)
        
        except ImportError:
            logger.debug("psutil not installed, skipping memory check")
        except Exception as e:
            logger.warning("Failed to check memory: %s", str(e))
        
        # ====================================================
        # 7. CHECK PORT CONFLICTS
        # ====================================================
        try:
            ports_in_use = {}
            port_conflicts = []
            
            # Get all container ports
            all_containers = docker_client.containers.list(all=True)
            
            for container in all_containers:
                ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                if ports:
                    for container_port, bindings in ports.items():
                        if bindings:
                            for binding in bindings:
                                if binding:
                                    host_port = binding.get('HostPort')
                                    if host_port:
                                        if host_port not in ports_in_use:
                                            ports_in_use[host_port] = []
                                        # Only add container if not already in list (avoid duplicates)
                                        if container.name not in ports_in_use[host_port]:
                                            ports_in_use[host_port].append(container.name)
            
            # Check for duplicates
            for port, containers_list in ports_in_use.items():
                if len(containers_list) > 1:
                    port_conflicts.append({
                        "port": port,
                        "containers": containers_list,
                        "severity": "error"
                    })
                    health_report["critical"].append(f"Port {port} is used by multiple containers: {containers_list}")
            
            # Check system ports - passing known Docker ports to avoid false positives
            system_conflicts = []
            docker_ports_list = list(ports_in_use.keys())
            
            for port in docker_ports_list:
                in_use, info = check_system_port_usage(
                    int(port), 
                    known_docker_ports=docker_ports_list
                )
                if in_use:
                    system_conflicts.append({
                        "port": port,
                        "source": "system_process",
                        "severity": "warning",
                        "details": info
                    })
            
            health_report["metrics"]["ports"] = {
                "in_use": docker_ports_list,
                "total_in_use": len(ports_in_use),
                "conflicts": len(port_conflicts),
                "system_conflicts": len(system_conflicts)
            }
            
            if port_conflicts or system_conflicts:
                if port_conflicts:
                    health_report["warnings"].append(f"{len(port_conflicts)} port conflict(s) detected")
                if system_conflicts:
                    health_report["warnings"].append(f"{len(system_conflicts)} port(s) may conflict with system")
            
            logger.debug("Ports: %d in use, %d conflicts", len(ports_in_use), len(port_conflicts))
        
        except Exception as e:
            logger.warning("Failed to check port conflicts: %s", str(e))
        
        # ====================================================
        # 8. DETERMINE OVERALL STATUS
        # ====================================================
        if health_report["critical"]:
            health_report["status"] = "critical"
        elif health_report["warnings"]:
            health_report["status"] = "warning"
        else:
            health_report["status"] = "healthy"
        
        logger.info("System health check complete: %s (%d warnings, %d critical)",
                   health_report["status"],
                   len(health_report["warnings"]),
                   len(health_report["critical"]))
        
        return health_report
    
    except Exception as e:
        logger.error("Error getting system health: %s", str(e), exc_info=True)
        raise HTTPException(500, str(e))


# ============================================================
# ENHANCED: check_port_conflicts
# ============================================================

@router.get("/api/port-conflicts")
async def check_port_conflicts():
    """Check for port conflicts among containers and system
    
    Detailed port conflict analysis including:
    - Container-to-container conflicts
    - System process conflicts
    - Available port suggestions
    
    Returns:
        dict: Detailed conflict report
    """
    try:
        conflicts = []
        port_map = {}
        port_details = {}
        
        # Get all containers
        all_containers = docker_client.containers.list(all=True)
        
        # Analyze port usage
        for container in all_containers:
            ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            
            if ports:
                for container_port, bindings in ports.items():
                    if bindings:
                        for binding in bindings:
                            if binding:
                                host_port = binding.get('HostPort')
                                if host_port:
                                    if host_port not in port_map:
                                        port_map[host_port] = []
                                        port_details[host_port] = {
                                            "container_port": container_port,
                                            "protocol": binding.get('HostIp', '0.0.0.0')
                                        }
                                    # Only add container if not already in list (avoid duplicates)
                                    if container.name not in port_map[host_port]:
                                        port_map[host_port].append(container.name)
        
        # Check for duplicates (container conflicts)
        for port, containers_list in port_map.items():
            if len(containers_list) > 1:
                conflicts.append({
                    "port": port,
                    "containers": containers_list,
                    "severity": "critical",
                    "type": "container_conflict"
                })
        
        # Check system-level conflicts - passing known Docker ports
        system_conflicts = []
        docker_ports_list = list(port_map.keys())
        
        for port in docker_ports_list:
            try:
                in_use, info = check_system_port_usage(
                    int(port), 
                    known_docker_ports=docker_ports_list
                )
                if in_use:
                    system_conflicts.append({
                        "port": port,
                        "source": "system_process",
                        "severity": "warning",
                        "type": "system_conflict",
                        "details": info
                    })
            except Exception as e:
                logger.debug("Error checking port %s: %s", port, str(e))
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_conflicts": len(conflicts) + len(system_conflicts),
            "container_conflicts": conflicts,
            "system_conflicts": system_conflicts,
            "ports_in_use": docker_ports_list,
            "total_ports_in_use": len(port_map),
            "status": "conflict" if conflicts else "ok",
            "details": port_details
        }
    
    except Exception as e:
        logger.error("Error checking port conflicts: %s", str(e))
        raise HTTPException(500, str(e))


# ============================================================
# ENHANCED: validate_config
# ============================================================

@router.post("/api/validate-config/{image}")
async def validate_config(image: str):
    """Validate container configuration before starting
    
    Comprehensive validation including:
    - Docker image availability
    - Port availability
    - Required fields
    - Volume accessibility
    - Script existence
    
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
            "errors": [],
            "checks": {}
        }
        
        # ====================================================
        # 1. Check if Docker image exists
        # ====================================================
        try:
            docker_client.images.get(img_data["image"])
            validation["checks"]["docker_image"] = "ok"
        except docker.errors.ImageNotFound:
            validation["errors"].append(f"Docker image '{img_data['image']}' not found locally")
            validation["checks"]["docker_image"] = "failed"
            validation["valid"] = False
        except Exception as e:
            validation["errors"].append(f"Error checking Docker image: {str(e)}")
            validation["checks"]["docker_image"] = "error"
        
        # ====================================================
        # 2. Check ports
        # ====================================================
        ports_ok, conflicts = validate_ports_available(img_data, image)
        if not ports_ok:
            conflict_info = [f"{c['host_port']} (used by {c['used_by']})" for c in conflicts]
            validation["errors"].append(f"Port conflicts: {', '.join(conflict_info)}")
            validation["checks"]["ports"] = "failed"
            validation["valid"] = False
        else:
            validation["checks"]["ports"] = "ok"
        
        # ====================================================
        # 3. Check required fields
        # ====================================================
        required_fields = ["image", "category", "description"]
        for field in required_fields:
            if field not in img_data or not img_data[field]:
                validation["errors"].append(f"Missing required field: {field}")
                validation["checks"]["required_fields"] = "failed"
                validation["valid"] = False
        
        if validation["checks"].get("required_fields") != "failed":
            validation["checks"]["required_fields"] = "ok"
        
        # ====================================================
        # 4. Check optional configurations
        # ====================================================
        if not img_data.get("keep_alive_cmd"):
            validation["warnings"].append("No keep_alive_cmd specified, using default 'sleep infinity'")
        
        if not img_data.get("shell"):
            validation["warnings"].append("No shell specified, using default '/bin/bash'")
        
        # ====================================================
        # 5. Check volumes
        # ====================================================
        volumes = img_data.get("volumes", [])
        if volumes:
            validation["checks"]["volumes_defined"] = "ok"
            for vol in volumes:
                if vol.get("type") == "bind" and vol.get("host"):
                    host_path = vol.get("host")
                    if not host_path.startswith("/"):
                        host_path = f"/path/{host_path}"
                    # Just warn, don't error
                    validation["warnings"].append(f"Bind volume '{host_path}' will be created if missing")
        else:
            validation["checks"]["volumes"] = "none"
        
        # ====================================================
        # 6. Check scripts
        # ====================================================
        from src.web.core.docker import has_default_script
        
        scripts = img_data.get("scripts", {})
        has_post_start = bool(scripts.get("post_start")) or has_default_script(image, "init")
        has_pre_stop = bool(scripts.get("pre_stop")) or has_default_script(image, "halt")
        
        validation["checks"]["scripts"] = {
            "post_start": "configured" if has_post_start else "none",
            "pre_stop": "configured" if has_pre_stop else "none"
        }
        
        logger.info("Validation for '%s': %s (%d errors, %d warnings)",
                   image,
                   "VALID" if validation["valid"] else "INVALID",
                   len(validation["errors"]),
                   len(validation["warnings"]))
        
        return validation
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error validating config for %s: %s", image, str(e), exc_info=True)
        raise HTTPException(500, str(e))