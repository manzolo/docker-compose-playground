"""Execute commands in containers API"""
from fastapi import APIRouter, Request, HTTPException
import docker
import logging
import json

logger = logging.getLogger("uvicorn")
docker_client = docker.from_env()

router = APIRouter()


@router.post("/api/execute-command/{container}")
async def execute_command(container: str, request: Request):
    """Execute a command in a running container (non-interactive)
    
    Args:
        container: Container name (e.g., 'playground-ubuntu')
        request body: {
            "command": "apt list --installed",
            "timeout": 30  # optional, default 30 seconds
        }
    
    Returns:
        dict: Command output and exit code
    """
    try:
        data = await request.json()
        command = data.get('command')
        timeout = data.get('timeout', 30)
        
        if not command:
            raise HTTPException(400, "Command is required")
        
        if not isinstance(command, str):
            raise HTTPException(400, "Command must be a string")
        
        # Validate container exists and is running
        try:
            cont = docker_client.containers.get(container)
        except docker.errors.NotFound:
            raise HTTPException(404, f"Container {container} not found")
        
        if cont.status != "running":
            raise HTTPException(400, f"Container {container} is not running")
        
        logger.info("Executing command in %s: %s", container, command)
        
        # Execute command
        try:
            exit_code, output = cont.exec_run(
                command,
                stdout=True,
                stderr=True,
                timeout=timeout
            )
        except docker.errors.APIError as e:
            logger.error("Docker API error executing command in %s: %s", container, str(e))
            raise HTTPException(500, f"Failed to execute command: {str(e)}")
        
        # Decode output
        try:
            output_str = output.decode('utf-8', errors='replace')
        except Exception as e:
            logger.warning("Failed to decode output: %s", str(e))
            output_str = str(output)
        
        return {
            "container": container,
            "command": command,
            "exit_code": exit_code,
            "output": output_str,
            "success": exit_code == 0
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error executing command in %s: %s", container, str(e))
        raise HTTPException(500, str(e))


@router.post("/api/execute-diagnostic/{container}")
async def execute_diagnostic(container: str):
    """Run comprehensive diagnostics on a container
    
    Args:
        container: Container name
    
    Returns:
        dict: Diagnostic information (processes, disk, network, etc.)
    """
    try:
        # Validate container exists
        try:
            cont = docker_client.containers.get(container)
        except docker.errors.NotFound:
            raise HTTPException(404, f"Container {container} not found")
        
        diagnostics = {
            "container": container,
            "status": cont.status,
            "diagnostics": {}
        }
        
        if cont.status != "running":
            logger.warning("Container %s is not running, skipping diagnostics", container)
            diagnostics["message"] = "Container is not running"
            return diagnostics
        
        # Get processes
        try:
            exit_code, ps_output = cont.exec_run("ps aux", stdout=True, stderr=True, timeout=10)
            diagnostics["diagnostics"]["processes"] = ps_output.decode('utf-8', errors='replace') if exit_code == 0 else "Failed to get processes"
        except Exception as e:
            logger.warning("Failed to get processes: %s", str(e))
            diagnostics["diagnostics"]["processes"] = f"Error: {str(e)}"
        
        # Get disk usage
        try:
            exit_code, df_output = cont.exec_run("df -h", stdout=True, stderr=True, timeout=10)
            diagnostics["diagnostics"]["disk_usage"] = df_output.decode('utf-8', errors='replace') if exit_code == 0 else "Failed to get disk usage"
        except Exception as e:
            logger.warning("Failed to get disk usage: %s", str(e))
            diagnostics["diagnostics"]["disk_usage"] = f"Error: {str(e)}"
        
        # Get network info
        try:
            exit_code, netstat_output = cont.exec_run("netstat -tuln", stdout=True, stderr=True, timeout=10)
            if exit_code != 0:
                # Fallback to ss if netstat not available
                exit_code, netstat_output = cont.exec_run("ss -tuln", stdout=True, stderr=True, timeout=10)
            diagnostics["diagnostics"]["network"] = netstat_output.decode('utf-8', errors='replace') if exit_code == 0 else "Failed to get network info"
        except Exception as e:
            logger.warning("Failed to get network info: %s", str(e))
            diagnostics["diagnostics"]["network"] = f"Error: {str(e)}"
        
        # Get environment variables
        try:
            exit_code, env_output = cont.exec_run("env", stdout=True, stderr=True, timeout=10)
            diagnostics["diagnostics"]["environment"] = env_output.decode('utf-8', errors='replace') if exit_code == 0 else "Failed to get environment"
        except Exception as e:
            logger.warning("Failed to get environment: %s", str(e))
            diagnostics["diagnostics"]["environment"] = f"Error: {str(e)}"
        
        # Get uptime
        try:
            exit_code, uptime_output = cont.exec_run("uptime", stdout=True, stderr=True, timeout=10)
            diagnostics["diagnostics"]["uptime"] = uptime_output.decode('utf-8', errors='replace').strip() if exit_code == 0 else "Failed to get uptime"
        except Exception as e:
            logger.warning("Failed to get uptime: %s", str(e))
            diagnostics["diagnostics"]["uptime"] = f"Error: {str(e)}"
        
        # Get container logs snippet
        try:
            logs = cont.logs(tail=50).decode('utf-8', errors='replace')
            diagnostics["diagnostics"]["recent_logs"] = logs
        except Exception as e:
            logger.warning("Failed to get logs: %s", str(e))
            diagnostics["diagnostics"]["recent_logs"] = f"Error: {str(e)}"
        
        return diagnostics
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error running diagnostics for %s: %s", container, str(e))
        raise HTTPException(500, str(e))