"""Script execution for container lifecycle management"""
from pathlib import Path
import subprocess
import os
import logging

# Logger che scrive direttamente su file (non dipende da uvicorn)
logger = logging.getLogger("scripts")
logger.setLevel(logging.DEBUG)

# Configura il file handler per scrivere su venv/web.log
LOG_FILE = Path(__file__).parent.parent.parent.parent / "venv" / "web.log"
if not logger.handlers:
    file_handler = logging.FileHandler(str(LOG_FILE), mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] [SCRIPTS] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

BASE_DIR = Path(__file__).parent.parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
SHARED_DIR = BASE_DIR / "shared-volumes"


def execute_script(script_config, container_name: str, image_name: str) -> None:
    """Execute post-start or pre-stop script
    
    Supports two types of scripts:
    1. Inline scripts: dict with 'inline' key containing bash code
    2. File-based scripts: string path to bash script file
    
    Args:
        script_config: Script configuration (dict or str)
        container_name: Full container name (e.g., 'playground-ubuntu')
        image_name: Image name without 'playground-' prefix
    
    Raises:
        subprocess.TimeoutExpired: If script execution times out
        Exception: On other script execution errors
    """
    if not script_config:
        return
    
    try:
        # Inline script
        if isinstance(script_config, dict) and 'inline' in script_config:
            script_content = script_config['inline']
            
            temp_script = f"/tmp/playground-script-{container_name}.sh"
            with open(temp_script, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write(f'CONTAINER_NAME="{container_name}"\n')
                f.write(f'SHARED_DIR="{SHARED_DIR}"\n')
                f.write(script_content)
            
            os.chmod(temp_script, 0o755)
            
            result = subprocess.run(
                ['bash', temp_script, container_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Log only essentials
            if result.returncode == 0:
                logger.info("Script executed successfully (exit code: 0)")
                if result.stdout:
                    logger.info("Output: %s", result.stdout.strip())
            else:
                logger.error("Script failed with exit code: %d", result.returncode)
                if result.stderr:
                    logger.error("Error: %s", result.stderr.strip())
            
            os.remove(temp_script)
        
        # File-based script
        elif isinstance(script_config, str):
            script_path = SCRIPTS_DIR / script_config
            if script_path.exists():
                logger.info("Executing script file: %s", script_config)
                
                result = subprocess.run(
                    ['bash', str(script_path), container_name],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env={**os.environ, 'SHARED_DIR': str(SHARED_DIR)}
                )
                
                # Log only essentials
                if result.returncode == 0:
                    logger.info("Script executed successfully (exit code: 0)")
                    if result.stdout:
                        logger.info("Output: %s", result.stdout.strip())
                else:
                    logger.error("Script failed with exit code: %d", result.returncode)
                    if result.stderr:
                        logger.error("Error: %s", result.stderr.strip())
            else:
                logger.warning("Script file not found: %s", script_path)
    
    except subprocess.TimeoutExpired:
        logger.error("Script timeout for %s (exceeded 60 seconds)", container_name)
        raise
    except Exception as e:
        logger.error("Script execution failed: %s", str(e))
        raise