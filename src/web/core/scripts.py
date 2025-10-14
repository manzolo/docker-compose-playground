from pathlib import Path
import subprocess
import os
import logging

logger = logging.getLogger("uvicorn")

BASE_DIR = Path(__file__).parent.parent.parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
SHARED_DIR = BASE_DIR / "shared-volumes"

def execute_script(script_config, container_name: str, image_name: str):
    """Execute post-start or pre-stop script"""
    if not script_config:
        return
    
    try:
        # Inline script
        if isinstance(script_config, dict) and 'inline' in script_config:
            logger.info("Executing inline script for %s", container_name)
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
            
            if result.stdout:
                logger.info("Script output: %s", result.stdout)
            if result.stderr:
                logger.warning("Script stderr: %s", result.stderr)
            
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
                
                if result.stdout:
                    logger.info("Script output: %s", result.stdout)
                if result.stderr:
                    logger.warning("Script stderr: %s", result.stderr)
            else:
                logger.warning("Script file not found: %s", script_path)
    
    except subprocess.TimeoutExpired:
        logger.error("Script timeout for %s", container_name)
        raise
    except Exception as e:
        logger.error("Script execution failed for %s: %s", container_name, str(e))
        raise