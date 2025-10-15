"""
Script execution utilities for CLI
Handles post-start and pre-stop scripts
"""

import subprocess
from pathlib import Path
from rich.console import Console

console = Console()

# Paths
BASE_PATH = Path(__file__).parent.parent.parent.parent
SCRIPTS_DIR = BASE_PATH / "scripts"
SHARED_DIR = BASE_PATH / "shared-volumes"


def execute_script(script_config, container_name: str, image_name: str):
    """Execute post-start or pre-stop script"""
    if not script_config:
        return
    
    try:
        if isinstance(script_config, dict) and 'inline' in script_config:
            # Inline script
            script_content = script_config['inline']
            temp_script = f"/tmp/playground-script-{container_name}.sh"
            
            with open(temp_script, 'w') as f:
                f.write("#!/bin/bash\n")
                f.write(f'CONTAINER_NAME="{container_name}"\n')
                f.write(f'SHARED_DIR="{SHARED_DIR}"\n')
                f.write(script_content)
            
            Path(temp_script).chmod(0o755)
            
            result = subprocess.run(
                ['bash', temp_script, container_name],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                console.print("[green]✓ Script executed successfully[/green]")
            else:
                console.print(f"[yellow]⚠ Script exited with code {result.returncode}[/yellow]")
            
            Path(temp_script).unlink()
            
        elif isinstance(script_config, str):
            # File-based script
            script_path = SCRIPTS_DIR / script_config
            if script_path.exists():
                result = subprocess.run(
                    ['bash', str(script_path), container_name],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env={'SHARED_DIR': str(SHARED_DIR)}
                )
                
                if result.returncode == 0:
                    console.print(f"[green]✓ Script {script_config} executed[/green]")
                else:
                    console.print(f"[yellow]⚠ Script exited with code {result.returncode}[/yellow]")
            else:
                console.print(f"[yellow]⚠ Script file not found: {script_path}[/yellow]")
    
    except subprocess.TimeoutExpired:
        console.print(f"[red]❌ Script timeout for {container_name}[/red]")
    except Exception as e:
        console.print(f"[red]❌ Script execution failed: {e}[/red]")