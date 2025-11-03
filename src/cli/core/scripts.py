"""Script execution for container lifecycle management - CLI version"""
from pathlib import Path
import subprocess
import os
import logging

# Logger
logger = logging.getLogger("scripts")
# Don't set level here - let it inherit from root logger

# Configura il file handler per scrivere su venv/cli.log
LOG_FILE = Path(__file__).parent.parent.parent.parent / "venv" / "cli.log"
if not logger.handlers:
    file_handler = logging.FileHandler(str(LOG_FILE), mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [SCRIPTS] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

BASE_DIR = Path(__file__).parent.parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
SHARED_DIR = BASE_DIR / "shared-volumes"


def execute_script(script_config, full_container_name: str, container_name: str, script_type: str = "init") -> None:
    """Execute post-start or pre-stop script

    Executes scripts in the following order:
    1. Default script if exists (using standardized structure)
    2. Custom script from YAML config if provided

    Both scripts are executed if they exist.

    Args:
        script_config: Script configuration (dict, str, or None)
        full_container_name: Full container name (e.g., 'playground-mysql-8')
        container_name: Container name without prefix (e.g., 'mysql-8.0')
        script_type: Type of script - 'init' (post-start) or 'halt' (pre-stop)
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
            'label': 'default'
        })
    
    # 2. Add custom script if provided
    if script_config:
        scripts_to_execute.append({
            'config': script_config,
            'label': 'custom'
        })
    
    # If no scripts to execute, return early
    if not scripts_to_execute:
        logger.debug("No scripts found (default or config) for %s", full_container_name)
        return
    
    # Execute all scripts in order
    try:
        for script_entry in scripts_to_execute:
            script_to_execute = script_entry['config']
            script_label = script_entry['label']
            
            try:
                # Inline script
                if isinstance(script_to_execute, dict) and 'inline' in script_to_execute:
                    script_content = script_to_execute['inline']
                    
                    temp_script = f"/tmp/playground-script-{full_container_name}-{script_label}.sh"
                    with open(temp_script, 'w') as f:
                        f.write("#!/bin/bash\n")
                        f.write(f'CONTAINER_NAME="{full_container_name}"\n')
                        f.write(f'SHARED_DIR="{SHARED_DIR}"\n')
                        f.write(script_content)
                    
                    os.chmod(temp_script, 0o755)
                    
                    logger.info("Executing %s inline %s script", script_label, script_type)
                    
                    result = subprocess.run(
                        ['bash', temp_script, full_container_name],
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    if result.returncode == 0:
                        logger.info("✓ %s inline script executed successfully (exit code: 0)", script_label)
                        if result.stdout:
                            logger.debug("Output: %s", result.stdout.strip())
                    else:
                        logger.error("✗ %s inline script failed with exit code: %d", script_label, result.returncode)
                        if result.stderr:
                            logger.error("Error: %s", result.stderr.strip())
                    
                    os.remove(temp_script)
                
                # File-based script
                elif isinstance(script_to_execute, str):
                    script_path = SCRIPTS_DIR / script_to_execute
                    if script_path.exists():
                        logger.info("Executing %s file %s script: %s", script_label, script_type, script_to_execute)
                        
                        result = subprocess.run(
                            ['bash', str(script_path), full_container_name],
                            capture_output=True,
                            text=True,
                            timeout=300,
                            env={**os.environ, 'SHARED_DIR': str(SHARED_DIR)}
                        )
                        
                        if result.returncode == 0:
                            logger.info("✓ %s file script executed successfully (exit code: 0)", script_label)
                            if result.stdout:
                                logger.debug("Output: %s", result.stdout.strip())
                        else:
                            logger.error("✗ %s file script failed with exit code: %d", script_label, result.returncode)
                            if result.stderr:
                                logger.error("Error: %s", result.stderr.strip())
                    else:
                        logger.warning("Script file not found: %s", script_path)
            
            except subprocess.TimeoutExpired:
                logger.error("✗ %s script timeout for %s (exceeded 300 seconds)", script_label, full_container_name)
                raise
            except Exception as e:
                logger.error("✗ %s script execution failed: %s", script_label, str(e))
                raise
    
    except Exception as e:
        logger.error("Script execution error: %s", str(e))
        raise