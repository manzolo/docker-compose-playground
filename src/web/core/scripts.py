# SEZIONI MODIFICATE PER core/scripts.py

"""Script execution for container lifecycle management"""
from pathlib import Path
import subprocess
import os
import logging
import time
from typing import Optional

from .logging_config import get_module_logger

# Use centralized logger
logger = get_module_logger("scripts")

# ============================================================
# SCRIPT EXECUTION CONFIGURATION
# ============================================================

class ScriptConfig:
    """Script execution configuration"""

    # Timeout settings (in seconds)
    SCRIPT_EXECUTION_TIMEOUT = int(os.getenv('PLAYGROUND_SCRIPT_TIMEOUT', '300'))  # 5 min default
    SCRIPT_INIT_TIMEOUT = int(os.getenv('PLAYGROUND_SCRIPT_INIT_TIMEOUT', '300'))   # post-start
    SCRIPT_HALT_TIMEOUT = int(os.getenv('PLAYGROUND_SCRIPT_HALT_TIMEOUT', '300'))   # pre-stop

    # Retry settings
    ENABLE_SCRIPT_RETRY = True
    MAX_SCRIPT_RETRIES = 2
    RETRY_DELAY_SECONDS = 2

    # Logging
    ENABLE_SCRIPT_OUTPUT_LOGGING = os.getenv('PLAYGROUND_SCRIPT_OUTPUT_LOGGING', 'true').lower() == 'true'
    MAX_OUTPUT_LINES = int(os.getenv('PLAYGROUND_SCRIPT_MAX_OUTPUT_LINES', '100'))  # Max lines to log

    # Environment
    PRESERVE_ENV = True  # Preserve parent environment variables

    @classmethod
    def get_timeout(cls, script_type: str) -> int:
        """Get appropriate timeout based on script type

        Args:
            script_type: 'init', 'halt', or generic script type

        Returns:
            int: Timeout in seconds
        """
        if script_type == "init":
            return cls.SCRIPT_INIT_TIMEOUT
        elif script_type == "halt":
            return cls.SCRIPT_HALT_TIMEOUT
        else:
            return cls.SCRIPT_EXECUTION_TIMEOUT

    @classmethod
    def log_config(cls):
        """Log configuration on startup"""
        logger.info("Script Configuration:")
        logger.info("  Default timeout: %ds", cls.SCRIPT_EXECUTION_TIMEOUT)
        logger.info("  Init (post-start) timeout: %ds", cls.SCRIPT_INIT_TIMEOUT)
        logger.info("  Halt (pre-stop) timeout: %ds", cls.SCRIPT_HALT_TIMEOUT)
        logger.info("  Retry: %s (max %d retries, %ds delay)",
                   "ENABLED" if cls.ENABLE_SCRIPT_RETRY else "DISABLED",
                   cls.MAX_SCRIPT_RETRIES,
                   cls.RETRY_DELAY_SECONDS)
        logger.info("  Output logging: %s (max %d lines per script)",
                   "ENABLED" if cls.ENABLE_SCRIPT_OUTPUT_LOGGING else "DISABLED",
                   cls.MAX_OUTPUT_LINES)

BASE_DIR = Path(__file__).parent.parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
SHARED_DIR = BASE_DIR / "shared-volumes"

# Log config on module load
ScriptConfig.log_config()


# ============================================================
# HELPER: Build script environment
# ============================================================

def build_script_environment(container_name: str) -> dict:
    """Build environment variables for script execution
    
    Args:
        container_name: Full container name (e.g., 'playground-mysql-8.0')
    
    Returns:
        dict: Environment variables
    """
    env = {}
    
    # Preserve parent environment if enabled
    if ScriptConfig.PRESERVE_ENV:
        env.update(os.environ)
    
    # Add custom variables
    env['CONTAINER_NAME'] = container_name
    env['SHARED_DIR'] = str(SHARED_DIR)
    env['SCRIPTS_DIR'] = str(SCRIPTS_DIR)
    env['TIMESTAMP'] = str(int(time.time()))
    
    return env


# ============================================================
# HELPER: Execute script with error handling
# ============================================================

def _execute_script_internal(
    script_path: str,
    container_name: str,
    script_type: str = "init",
    retry_attempt: int = 1
) -> dict:
    """Execute a single script with timeout and error handling
    
    Args:
        script_path: Path to script file
        container_name: Full container name
        script_type: 'init' or 'halt'
        retry_attempt: Current retry attempt number
    
    Returns:
        dict: Execution result with status, exit_code, stdout, stderr
    """
    timeout = ScriptConfig.get_timeout(script_type)
    script_name = Path(script_path).name
    
    logger.info(">> Executing %s script: %s (attempt %d/%d, timeout: %ds)",
               script_type, script_name, retry_attempt,
               ScriptConfig.MAX_SCRIPT_RETRIES + 1, timeout)
    
    try:
        # Build environment
        env = build_script_environment(container_name)
        
        # Execute script
        start_time = time.time()
        result = subprocess.run(
            ['bash', script_path, container_name],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=SCRIPTS_DIR
        )
        elapsed = time.time() - start_time
        
        # Log results
        if result.returncode == 0:
            logger.info("✓ %s script succeeded (exit code: 0, elapsed: %.2fs)", script_type, elapsed)

            # Log output if configured - now at INFO level for visibility
            if ScriptConfig.ENABLE_SCRIPT_OUTPUT_LOGGING and result.stdout:
                logger.info("=" * 60)
                logger.info("%s SCRIPT OUTPUT:", script_type.upper())
                logger.info("=" * 60)

                # Split output into lines and log each line
                output_lines = result.stdout.strip().split('\n')
                for line in output_lines[:ScriptConfig.MAX_OUTPUT_LINES]:
                    if line.strip():
                        logger.info("  %s", line)

                if len(output_lines) > ScriptConfig.MAX_OUTPUT_LINES:
                    logger.info("  ... (%d more lines omitted)", len(output_lines) - ScriptConfig.MAX_OUTPUT_LINES)

                logger.info("=" * 60)
        else:
            logger.error("✗ %s script failed (exit code: %d, elapsed: %.2fs)",
                        script_type, result.returncode, elapsed)

            if result.stderr:
                logger.error("=" * 60)
                logger.error("%s SCRIPT ERROR OUTPUT:", script_type.upper())
                logger.error("=" * 60)

                error_lines = result.stderr.strip().split('\n')
                for line in error_lines[:ScriptConfig.MAX_OUTPUT_LINES]:
                    if line.strip():
                        logger.error("  %s", line)

                if len(error_lines) > ScriptConfig.MAX_OUTPUT_LINES:
                    logger.error("  ... (%d more lines omitted)", len(error_lines) - ScriptConfig.MAX_OUTPUT_LINES)

                logger.error("=" * 60)
        
        return {
            "status": "success" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "elapsed": elapsed
        }
    
    except subprocess.TimeoutExpired:
        logger.error("✗ %s script TIMEOUT (exceeded %ds)", script_type, timeout)
        return {
            "status": "timeout",
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Script execution timeout after {timeout} seconds",
            "elapsed": timeout
        }
    
    except Exception as e:
        logger.error("✗ %s script execution error: %s", script_type, str(e))
        return {
            "status": "error",
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "elapsed": 0
        }


# ============================================================
# MAIN: execute_script with retry logic
# ============================================================

def execute_script(
    script_config,
    full_container_name: str,
    container_name: str,
    script_type: str = "init"
) -> None:
    """Execute post-start or pre-stop script with retry logic

    Executes scripts in the following order:
    1. Default script if exists (using standardized structure)
    2. Custom script from YAML config if provided

    Both scripts are executed if they exist. Failed scripts trigger retries if enabled.

    Args:
        script_config: Script configuration (dict, str, or None)
        full_container_name: Full container name (e.g., 'playground-mysql-8.0')
        container_name: Container name without prefix (e.g., 'mysql-8.0')
        script_type: Type of script - 'init' (post-start) or 'halt' (pre-stop)

    Raises:
        Exception: If script execution fails after all retries
    """

    # Default script lookup paths (in order of preference)
    default_script_paths = [
        # 1. Stack-specific scripts: stacks/{container_name}/init.sh or halt.sh
        SCRIPTS_DIR / "stacks" / container_name / f"{script_type}.sh",
        # 2. Simple init/halt scripts: init/{container_name}.sh or halt/{container_name}.sh
        SCRIPTS_DIR / script_type / f"{container_name}.sh",
    ]

    # Find the first existing default script
    default_script_path = None
    default_script_name = None

    for script_path in default_script_paths:
        if script_path.exists():
            default_script_path = script_path
            default_script_name = str(script_path.relative_to(SCRIPTS_DIR))
            logger.info("Found default %s script: %s", script_type, default_script_name)
            break

    # List to hold scripts to execute in order
    scripts_to_execute = []

    # 1. Add default script if it exists
    if default_script_path:
        scripts_to_execute.append({
            'config': default_script_name,
            'label': 'default',
            'path': default_script_path
        })

    
    # 2. Add custom script if provided
    if script_config:
        scripts_to_execute.append({
            'config': script_config,
            'label': 'custom',
            'path': None
        })
    
    # If no scripts to execute, return early
    if not scripts_to_execute:
        logger.debug("No scripts found (default or config) for %s (type: %s)",
                    full_container_name, script_type)
        return
    
    logger.info("=" * 80)
    logger.info("SCRIPT EXECUTION START")
    logger.info("  Container: %s", full_container_name)
    logger.info("  Type: %s (%s)", script_type, "post_start" if script_type == "init" else "pre_stop")
    logger.info("  Scripts to execute: %d", len(scripts_to_execute))
    for idx, script in enumerate(scripts_to_execute, 1):
        logger.info("    %d. %s (%s)", idx, script['label'], script['config'] if isinstance(script['config'], str) else 'inline')
    logger.info("=" * 80)
    
    # Execute all scripts in order
    script_results = []
    
    try:
        for script_entry in scripts_to_execute:
            script_to_execute = script_entry['config']
            script_label = script_entry['label']
            
            result_entry = {
                'label': script_label,
                'config': script_to_execute,
                'attempts': 0,
                'results': []
            }
            
            try:
                # ====================================================
                # INLINE SCRIPT EXECUTION
                # ====================================================
                if isinstance(script_to_execute, dict) and 'inline' in script_to_execute:
                    script_content = script_to_execute['inline']
                    
                    # Retry loop for inline scripts
                    for attempt in range(1, ScriptConfig.MAX_SCRIPT_RETRIES + 2):
                        result_entry['attempts'] = attempt
                        
                        # Create temporary script file
                        temp_script = f"/tmp/playground-script-{full_container_name}-{script_label}-{attempt}.sh"
                        try:
                            with open(temp_script, 'w') as f:
                                f.write("#!/bin/bash\n")
                                f.write(f'CONTAINER_NAME="{full_container_name}"\n')
                                f.write(f'SHARED_DIR="{SHARED_DIR}"\n')
                                f.write(script_content)
                            
                            os.chmod(temp_script, 0o755)
                            
                            logger.info("Executing %s inline %s script (attempt %d)",
                                       script_label, script_type, attempt)
                            
                            result = _execute_script_internal(
                                temp_script,
                                full_container_name,
                                script_type,
                                attempt
                            )
                            
                            result_entry['results'].append(result)
                            
                            # Check result
                            if result['status'] == 'success':
                                logger.info("✓ %s inline script SUCCEEDED", script_label)
                                break
                            else:
                                if attempt < ScriptConfig.MAX_SCRIPT_RETRIES + 1 and ScriptConfig.ENABLE_SCRIPT_RETRY:
                                    logger.warning("Retrying %s script after %.1fs delay (attempt %d/%d)",
                                                 script_label, ScriptConfig.RETRY_DELAY_SECONDS,
                                                 attempt, ScriptConfig.MAX_SCRIPT_RETRIES + 1)
                                    time.sleep(ScriptConfig.RETRY_DELAY_SECONDS)
                                else:
                                    logger.error("✗ %s inline script FAILED after %d attempt(s)",
                                               script_label, attempt)
                                    raise Exception(f"{script_label} inline script failed: {result['stderr']}")
                        
                        finally:
                            try:
                                os.remove(temp_script)
                            except:
                                pass
                
                # ====================================================
                # FILE-BASED SCRIPT EXECUTION
                # ====================================================
                elif isinstance(script_to_execute, str):
                    script_path = SCRIPTS_DIR / script_to_execute
                    
                    if not script_path.exists():
                        logger.warning("Script file not found: %s", script_path)
                        continue
                    
                    # Retry loop for file scripts
                    for attempt in range(1, ScriptConfig.MAX_SCRIPT_RETRIES + 2):
                        result_entry['attempts'] = attempt
                        
                        logger.info("Executing %s file %s script: %s (attempt %d)",
                                   script_label, script_type, script_to_execute, attempt)
                        
                        result = _execute_script_internal(
                            str(script_path),
                            full_container_name,
                            script_type,
                            attempt
                        )
                        
                        result_entry['results'].append(result)
                        
                        # Check result
                        if result['status'] == 'success':
                            logger.info("✓ %s file script SUCCEEDED", script_label)
                            break
                        else:
                            if attempt < ScriptConfig.MAX_SCRIPT_RETRIES + 1 and ScriptConfig.ENABLE_SCRIPT_RETRY:
                                logger.warning("Retrying %s script after %.1fs delay (attempt %d/%d)",
                                             script_label, ScriptConfig.RETRY_DELAY_SECONDS,
                                             attempt, ScriptConfig.MAX_SCRIPT_RETRIES + 1)
                                time.sleep(ScriptConfig.RETRY_DELAY_SECONDS)
                            else:
                                logger.error("✗ %s file script FAILED after %d attempt(s)",
                                           script_label, attempt)
                                raise Exception(f"{script_label} file script failed: {result['stderr']}")
            
            except Exception as e:
                script_results.append(result_entry)
                logger.error("✗ %s script execution error: %s", script_label, str(e))
                raise
            
            script_results.append(result_entry)
        
        logger.info("=" * 80)
        logger.info("SCRIPT EXECUTION COMPLETED - All scripts succeeded")
        logger.info("  Container: %s", full_container_name)
        logger.info("  Type: %s", script_type)
        logger.info("  Total scripts executed: %d", len(script_results))
        logger.info("=" * 80)
    
    except Exception as e:
        logger.error("=" * 80)
        logger.error("SCRIPT EXECUTION FAILED")
        logger.error("Container: %s, Type: %s", full_container_name, script_type)
        logger.error("Error: %s", str(e))
        logger.error("=" * 80)
        raise