"""Container monitoring and statistics APIs"""
from fastapi import APIRouter, HTTPException
import docker
import logging
from src.web.core.logging_config import get_logger
from src.web.utils import to_full_name
from datetime import datetime

logger = get_logger(__name__)
docker_client = docker.from_env()

router = APIRouter()


def _calculate_cpu_percent(stats):
    try:
        cpu_stats = stats.get('cpu_stats', {})
        precpu_stats = stats.get('precpu_stats', {})
        
        cpu_delta = cpu_stats.get('cpu_usage', {}).get('total_usage', 0) - precpu_stats.get('cpu_usage', {}).get('total_usage', 0)
        system_delta = cpu_stats.get('system_cpu_usage', 0) - precpu_stats.get('system_cpu_usage', 0)
        
        if system_delta == 0:
            return 0.0
        
        return (cpu_delta / system_delta) * cpu_stats.get('online_cpus', 1) * 100.0
    except:
        return 0.0


@router.get("/api/container-stats/{container}")
async def get_container_stats(container: str):
    """
    Get container statistics.

    Args:
        container: Container name without 'playground-' prefix (e.g., 'alpine-3.22')
    """
    # Convert to full container name with prefix
    full_container_name = to_full_name(container)

    try:
        cont = docker_client.containers.get(full_container_name)

        if cont.status != "running":
            raise HTTPException(400, f"Container {full_container_name} not running")
        
        try:
            stats = cont.stats(stream=False)
        except Exception as e:
            raise HTTPException(500, str(e))
        
        if not stats or not isinstance(stats, dict):
            raise HTTPException(500, "Invalid stats")
        
        cpu_percent = _calculate_cpu_percent(stats)
        
        memory_stats = stats.get('memory_stats', {})
        memory_usage = (memory_stats.get('usage') or 0) / (1024 * 1024)
        memory_limit = (memory_stats.get('limit') or 1) / (1024 * 1024)
        memory_percent = (memory_usage / memory_limit * 100) if memory_limit > 0 else 0
        
        networks = stats.get('networks', {}) or {}
        total_rx_bytes = sum(net.get('rx_bytes', 0) for net in networks.values())
        total_tx_bytes = sum(net.get('tx_bytes', 0) for net in networks.values())
        
        blkio_stats = stats.get('blkio_stats', {}) or {}
        io_service = blkio_stats.get('io_service_bytes_recursive') or []
        io_read_bytes = sum(item.get('value', 0) for item in io_service if item.get('op') == 'Read')
        io_write_bytes = sum(item.get('value', 0) for item in io_service if item.get('op') == 'Write')
        
        return {
            "container": full_container_name,
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "percent": round(cpu_percent, 2),
                "cores": stats.get('cpu_stats', {}).get('online_cpus', 1)
            },
            "memory": {
                "usage_mb": round(memory_usage, 2),
                "limit_mb": round(memory_limit, 2),
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
        raise HTTPException(404, f"Container {full_container_name} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/api/containers-health")
async def get_containers_health():
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
                
                try:
                    inspect_data = docker_client.api.inspect_container(cont.name)
                    start_time = inspect_data['State']['StartedAt']
                    start_time_clean = start_time.replace('Z', '+00:00')
                    start_dt = datetime.fromisoformat(start_time_clean)
                    uptime = (datetime.now(start_dt.tzinfo) - start_dt).total_seconds()
                    cont_info["uptime_seconds"] = int(uptime)
                except:
                    cont_info["uptime_seconds"] = 0
                
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
        
        if health_data["running"] == 0 and len(containers) > 0:
            health_data["overall"] = "warning"
        elif health_data["running"] == len(containers):
            health_data["overall"] = "healthy"
        else:
            health_data["overall"] = "degraded"
        
        return health_data
    
    except Exception as e:
        raise HTTPException(500, str(e))