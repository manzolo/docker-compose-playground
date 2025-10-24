"""Execute commands in containers API"""
from fastapi import APIRouter, Request, HTTPException
import docker
import logging
import threading
from datetime import datetime

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
        
        # Execute command with thread-based timeout
        result_holder = {}
        error_holder = {}
        
        def run_command():
            try:
                exit_code, output = cont.exec_run(
                    command,
                    stdout=True,
                    stderr=True
                )
                result_holder['exit_code'] = exit_code
                result_holder['output'] = output
            except Exception as e:
                error_holder['error'] = e
        
        # Run command in thread with timeout
        thread = threading.Thread(target=run_command)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            logger.error("Command timeout for %s after %d seconds", container, timeout)
            raise HTTPException(504, f"Command execution timeout after {timeout} seconds")
        
        if error_holder:
            raise error_holder['error']
        
        exit_code = result_holder.get('exit_code', 1)
        output = result_holder.get('output', b'')
        
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
    except docker.errors.APIError as e:
        logger.error("Docker API error executing command in %s: %s", container, str(e))
        raise HTTPException(500, f"Failed to execute command: {str(e)}")
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
        
        # Helper function to run diagnostic command with timeout
        def run_diag_command(cmd, cmd_name, timeout_secs=10):
            """Run a diagnostic command with timeout handling"""
            result = {}
            
            def exec_cmd():
                try:
                    exit_code, cmd_output = cont.exec_run(cmd, stdout=True, stderr=True)
                    result['exit_code'] = exit_code
                    result['output'] = cmd_output
                except Exception as e:
                    result['error'] = str(e)
            
            thread = threading.Thread(target=exec_cmd)
            thread.daemon = True
            thread.start()
            thread.join(timeout=timeout_secs)
            
            if thread.is_alive():
                return f"Timeout getting {cmd_name}"
            
            if 'error' in result:
                return f"Error: {result['error']}"
            
            exit_code = result.get('exit_code', 1)
            output = result.get('output', b'')
            
            if exit_code == 0:
                return output.decode('utf-8', errors='replace')
            else:
                return f"Failed to get {cmd_name}"
        
        # Get processes
        try:
            diagnostics["diagnostics"]["processes"] = run_diag_command("ps aux", "processes")
        except Exception as e:
            logger.warning("Failed to get processes: %s", str(e))
            diagnostics["diagnostics"]["processes"] = f"Error: {str(e)}"
        
        # Get disk usage
        try:
            diagnostics["diagnostics"]["disk_usage"] = run_diag_command("df -h", "disk usage")
        except Exception as e:
            logger.warning("Failed to get disk usage: %s", str(e))
            diagnostics["diagnostics"]["disk_usage"] = f"Error: {str(e)}"
        
        # Get network info
        try:
            net_output = run_diag_command("netstat -tuln", "network info")
            if "Error" in net_output or "Timeout" in net_output or "Failed" in net_output:
                # Fallback to ss if netstat not available
                net_output = run_diag_command("ss -tuln", "network info")
            diagnostics["diagnostics"]["network"] = net_output
        except Exception as e:
            logger.warning("Failed to get network info: %s", str(e))
            diagnostics["diagnostics"]["network"] = f"Error: {str(e)}"
        
        # Get environment variables
        try:
            diagnostics["diagnostics"]["environment"] = run_diag_command("env", "environment")
        except Exception as e:
            logger.warning("Failed to get environment: %s", str(e))
            diagnostics["diagnostics"]["environment"] = f"Error: {str(e)}"
        
        # Get uptime
        try:
            uptime = run_diag_command("uptime", "uptime")
            diagnostics["diagnostics"]["uptime"] = uptime.strip() if isinstance(uptime, str) else uptime
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