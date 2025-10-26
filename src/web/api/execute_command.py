"""Execute commands in containers API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import docker
import logging
import threading

logger = logging.getLogger("uvicorn")
docker_client = docker.from_env()

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class ExecuteCommandRequest(BaseModel):
    """Request model for executing a command in a container"""
    command: str
    timeout: int = 30


class ExecuteCommandResponse(BaseModel):
    """Response model for command execution"""
    container: str
    command: str
    exit_code: int
    output: str
    success: bool


class DiagnosticResponse(BaseModel):
    """Response model for diagnostics"""
    container: str
    status: str
    message: str = None
    diagnostics: dict = None


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/api/execute-command/{container}", response_model=ExecuteCommandResponse)
async def execute_command(container: str, request_body: ExecuteCommandRequest):
    """Execute a command in a running container (non-interactive)
    
    This endpoint executes a single command in a Docker container with optional timeout.
    
    Args:
        container: Container name or ID (e.g., 'playground-ubuntu')
        request_body: JSON body containing command and optional timeout
    
    Request Body:
        {
            "command": "ls -la /home",
            "timeout": 30
        }
    
    Returns:
        ExecuteCommandResponse containing:
        - container: The container name
        - command: The executed command
        - exit_code: Command exit code (0 = success)
        - output: Combined stdout and stderr
        - success: Boolean flag (True if exit_code == 0)
    
    Status Codes:
        200: Command executed successfully
        400: Invalid command, missing command, or container not running
        404: Container not found
        500: Docker API error or other server error
        504: Command execution timeout exceeded
    
    Examples:
        curl -X POST "http://localhost:8000/api/execute-command/my-container" \\
             -H "Content-Type: application/json" \\
             -d '{"command": "apt list --installed", "timeout": 30}'
    """
    try:
        command = request_body.command
        timeout = request_body.timeout
        
        if not command or not isinstance(command, str):
            raise HTTPException(400, "Command must be a non-empty string")
        
        # Validate container exists and is running
        try:
            cont = docker_client.containers.get(container)
        except docker.errors.NotFound:
            raise HTTPException(404, f"Container '{container}' not found")
        
        if cont.status != "running":
            raise HTTPException(
                400,
                f"Container '{container}' is not running (current status: {cont.status})"
            )
        
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
        thread = threading.Thread(target=run_command, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            logger.error("Command timeout for %s after %d seconds", container, timeout)
            raise HTTPException(
                504,
                f"Command execution timeout after {timeout} seconds"
            )
        
        if error_holder:
            raise error_holder['error']
        
        exit_code = result_holder.get('exit_code', 1)
        output = result_holder.get('output', b'')
        
        # Decode output safely
        try:
            output_str = output.decode('utf-8', errors='replace')
        except Exception as e:
            logger.warning("Failed to decode output: %s", str(e))
            output_str = str(output)
        
        logger.info(
            "Command executed in %s with exit code %d",
            container,
            exit_code
        )
        
        return ExecuteCommandResponse(
            container=container,
            command=command,
            exit_code=exit_code,
            output=output_str,
            success=exit_code == 0
        )
    
    except HTTPException:
        raise
    except docker.errors.APIError as e:
        logger.error("Docker API error executing command in %s: %s", container, str(e))
        raise HTTPException(500, f"Docker API error: {str(e)}")
    except Exception as e:
        logger.error("Error executing command in %s: %s", container, str(e))
        raise HTTPException(500, f"Unexpected error: {str(e)}")


@router.post("/api/execute-diagnostic/{container}", response_model=DiagnosticResponse)
async def execute_diagnostic(container: str):
    """Run comprehensive diagnostics on a container
    
    This endpoint gathers detailed information about a container including:
    processes, disk usage, network info, environment variables, uptime, and logs.
    
    Args:
        container: Container name or ID to diagnose
    
    Returns:
        DiagnosticResponse containing:
        - container: The container name
        - status: Current container status (running, exited, etc.)
        - diagnostics: Dictionary with diagnostic data:
            - processes: Output of 'ps aux'
            - disk_usage: Output of 'df -h'
            - network: Output of 'netstat -tuln' or 'ss -tuln'
            - environment: Output of 'env'
            - uptime: Output of 'uptime'
            - recent_logs: Last 50 lines of container logs
        - message: Status message (e.g., if container not running)
    
    Status Codes:
        200: Diagnostics retrieved successfully
        404: Container not found
        500: Error running diagnostics
    
    Notes:
        - If container is not running, only basic info is returned
        - Each diagnostic has a 10-second timeout
        - Failed diagnostics return error messages instead of data
        - Output is decoded as UTF-8 with error replacement
    
    Examples:
        curl -X POST "http://localhost:8000/api/execute-diagnostic/my-container" \\
             -H "Accept: application/json"
    """
    try:
        # Validate container exists
        try:
            cont = docker_client.containers.get(container)
        except docker.errors.NotFound:
            raise HTTPException(404, f"Container '{container}' not found")
        
        diagnostics = {
            "container": container,
            "status": cont.status,
            "diagnostics": {}
        }
        
        # Return early if container not running
        if cont.status != "running":
            logger.warning("Container %s is not running, skipping diagnostics", container)
            diagnostics["message"] = f"Container is {cont.status}"
            return diagnostics
        
        logger.info("Running diagnostics for container %s", container)
        
        # Helper function to run diagnostic command with timeout
        def run_diag_command(cmd: str, cmd_name: str, timeout_secs: int = 10) -> str:
            """
            Execute a diagnostic command in the container with timeout.
            
            Args:
                cmd: Command to execute
                cmd_name: Name of the diagnostic for logging
                timeout_secs: Timeout in seconds (default: 10)
            
            Returns:
                Command output as string or error message
            """
            result = {}
            
            def exec_cmd():
                try:
                    exit_code, cmd_output = cont.exec_run(
                        cmd,
                        stdout=True,
                        stderr=True
                    )
                    result['exit_code'] = exit_code
                    result['output'] = cmd_output
                except Exception as e:
                    result['error'] = str(e)
            
            thread = threading.Thread(target=exec_cmd, daemon=True)
            thread.start()
            thread.join(timeout=timeout_secs)
            
            if thread.is_alive():
                msg = f"Timeout getting {cmd_name} (>{timeout_secs}s)"
                logger.warning(msg)
                return msg
            
            if 'error' in result:
                error_msg = f"Error getting {cmd_name}: {result['error']}"
                logger.warning(error_msg)
                return error_msg
            
            exit_code = result.get('exit_code', 1)
            output = result.get('output', b'')
            
            if exit_code == 0:
                return output.decode('utf-8', errors='replace')
            else:
                msg = f"Failed to get {cmd_name} (exit code: {exit_code})"
                logger.warning(msg)
                return msg
        
        # Collect diagnostic data
        try:
            diagnostics["diagnostics"]["processes"] = run_diag_command(
                "ps aux",
                "processes"
            )
        except Exception as e:
            logger.warning("Failed to get processes: %s", str(e))
            diagnostics["diagnostics"]["processes"] = f"Error: {str(e)}"
        
        try:
            diagnostics["diagnostics"]["disk_usage"] = run_diag_command(
                "df -h",
                "disk usage"
            )
        except Exception as e:
            logger.warning("Failed to get disk usage: %s", str(e))
            diagnostics["diagnostics"]["disk_usage"] = f"Error: {str(e)}"
        
        try:
            # Try netstat first, fallback to ss if not available
            net_output = run_diag_command("netstat -tuln", "network info")
            if any(err in net_output for err in ["Error", "Timeout", "Failed"]):
                net_output = run_diag_command("ss -tuln", "network info (ss)")
            diagnostics["diagnostics"]["network"] = net_output
        except Exception as e:
            logger.warning("Failed to get network info: %s", str(e))
            diagnostics["diagnostics"]["network"] = f"Error: {str(e)}"
        
        try:
            diagnostics["diagnostics"]["environment"] = run_diag_command(
                "env",
                "environment variables"
            )
        except Exception as e:
            logger.warning("Failed to get environment: %s", str(e))
            diagnostics["diagnostics"]["environment"] = f"Error: {str(e)}"
        
        try:
            uptime = run_diag_command("uptime", "uptime")
            diagnostics["diagnostics"]["uptime"] = uptime.strip() if isinstance(uptime, str) else uptime
        except Exception as e:
            logger.warning("Failed to get uptime: %s", str(e))
            diagnostics["diagnostics"]["uptime"] = f"Error: {str(e)}"
        
        try:
            logs = cont.logs(tail=50).decode('utf-8', errors='replace')
            diagnostics["diagnostics"]["recent_logs"] = logs
        except Exception as e:
            logger.warning("Failed to get logs: %s", str(e))
            diagnostics["diagnostics"]["recent_logs"] = f"Error: {str(e)}"
        
        logger.info("Diagnostics completed for container %s", container)
        
        return diagnostics
    
    except HTTPException:
        raise
    except docker.errors.APIError as e:
        logger.error("Docker API error running diagnostics for %s: %s", container, str(e))
        raise HTTPException(500, f"Docker API error: {str(e)}")
    except Exception as e:
        logger.error("Error running diagnostics for %s: %s", container, str(e))
        raise HTTPException(500, f"Unexpected error: {str(e)}")