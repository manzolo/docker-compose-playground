"""Container monitoring and statistics APIs"""
from fastapi import APIRouter, HTTPException
import docker
import logging
from datetime import datetime

logger = logging.getLogger("uvicorn")
docker_client = docker.from_env()

router = APIRouter()


@router.get("/api/container-stats/{container}")
async def get_container_stats(container: str):
    """Get real-time container statistics (CPU, memory, I/O)
    
    Args:
        container: Container name (e.g., 'playground-ubuntu')
    
    Returns:
        dict: Statistics including CPU %, memory usage, I/O stats
    """
    try:
        cont = docker_client.containers.get(container)
        
        if cont.status != "running":
            raise HTTPException(400, f"Container {container} is not running")
        
        # Get stats
        try:
            stats = cont.stats(stream=False)
        except Exception as e:
            logger.warning("Failed to get stats for %s: %s", container, str(e))
            raise HTTPException(500, f"Failed to retrieve container stats: {str(e)}")
        
        # Calculate CPU percentage
        cpu_percent = _calculate_cpu_percent(stats)
        
        # Calculate memory in MB
        memory_usage_mb = stats['memory_stats']['usage'] / (1024 * 1024)
        memory_limit_mb = stats['memory_stats']['limit'] / (1024 * 1024)
        memory_percent = (memory_usage_mb / memory_limit_mb * 100) if memory_limit_mb > 0 else 0
        
        # Get network stats
        networks = stats.get('networks', {})
        total_rx_bytes = sum(net.get('rx_bytes', 0) for net in networks.values())
        total_tx_bytes = sum(net.get('tx_bytes', 0) for net in networks.values())
        
        # Get block I/O stats
        blkio_stats = stats.get('blkio_stats', {}) or {}
        io_service = blkio_stats.get('io_service_bytes_recursive') or []
        io_read_bytes = sum(item.get('value', 0) for item in io_service if item.get('op') == 'Read')
        io_write_bytes = sum(item.get('value', 0) for item in io_service if item.get('op') == 'Write')
        
        return {
            "container": container,
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": round(cpu_percent, 2),
                "cores": stats['cpu_stats'].get('online_cpus', 1)
            },
            "memory": {
                "usage_mb": round(memory_usage_mb, 2),
                "limit_mb": round(memory_limit_mb, 2),
                "percent": round(memory_percent, 2)
            },
            "network": {
                "rx_bytes": total_rx_bytes,
                "tx_bytes": total_tx_bytes,
                "rx_mb": round(total_rx_bytes / (1024 * 1024), 2),
                "tx_mb": round(total_tx_bytes / (1024 * 1024), 2)
            },
            "io": {
                "read_bytes": io_read_bytes,
                "write_bytes": io_write_bytes,
                "read_mb": round(io_read_bytes / (1024 * 1024), 2),
                "write_mb": round(io_write_bytes / (1024 * 1024), 2)
            },
            "processes": stats.get('pids_stats', {}).get('pids_current', 0)
        }
    
    except docker.errors.NotFound:
        raise HTTPException(404, f"Container {container} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting stats for %s: %s", container, str(e))
        raise HTTPException(500, str(e))


@router.get("/api/containers-health")
async def get_containers_health():
    """Get health status of all managed containers
    
    Returns:
        dict: Health metrics for all containers
    """
    try:
        containers = docker_client.containers.list(filters={"label": "playground.managed=true"})
        
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "total": len(containers),
            "running": 0,
            "stopped": 0,
            "containers": []
        }
        
        for cont in containers:
            cont_info = {
                "name": cont.name,
                "status": cont.status,
                "image": cont.image.tags[0] if cont.image.tags else "unknown"
            }
            
            if cont.status == "running":
                health_data["running"] += 1
                
                # Calculate uptime - FIXED: Use standard library instead of dateutil
                try:
                    inspect_data = docker_client.api.inspect_container(cont.name)
                    start_time = inspect_data['State']['StartedAt']
                    
                    # Parse ISO format and calculate uptime
                    # Remove 'Z' suffix and parse as UTC
                    start_time_clean = start_time.replace('Z', '+00:00')
                    start_dt = datetime.fromisoformat(start_time_clean)
                    uptime = (datetime.now(start_dt.tzinfo) - start_dt).total_seconds()
                    cont_info["uptime_seconds"] = int(uptime)
                except Exception as e:
                    logger.warning("Failed to get uptime for %s: %s", cont.name, str(e))
                    cont_info["uptime_seconds"] = 0
                
                # Get health status if available
                try:
                    inspect = docker_client.api.inspect_container(cont.name)
                    health = inspect.get('State', {}).get('Health', {})
                    if health.get('Status'):
                        cont_info["health_status"] = health['Status']
                except:
                    pass
            
            else:
                health_data["stopped"] += 1
            
            health_data["containers"].append(cont_info)
        
        # Calculate overall health
        if health_data["running"] == 0 and len(containers) > 0:
            health_data["overall"] = "warning"
        elif health_data["running"] == len(containers):
            health_data["overall"] = "healthy"
        else:
            health_data["overall"] = "degraded"
        
        return health_data
    
    except Exception as e:
        logger.error("Error getting containers health: %s", str(e))
        raise HTTPException(500, str(e))


def _calculate_cpu_percent(stats):
    """Calculate CPU percentage from Docker stats
    
    Args:
        stats: Docker stats dict
    
    Returns:
        float: CPU percentage
    """
    try:
        cpu_stats = stats['cpu_stats']
        precpu_stats = stats['precpu_stats']
        
        cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
        system_delta = cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage']
        
        if system_delta == 0:
            return 0.0
        
        cpu_percent = (cpu_delta / system_delta) * cpu_stats.get('online_cpus', 1) * 100.0
        return cpu_percent
    except (KeyError, ZeroDivisionError):
        return 0.0