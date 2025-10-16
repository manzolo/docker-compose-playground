"""
Script execution utilities for CLI
Handles post-start and pre-stop scripts with inline and file-based support
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
    """
    Execute post-start or pre-stop script
    Supports both inline scripts and file-based scripts
    """
    if not script_config:
        return
    
    try:
        if isinstance(script_config, dict) and 'inline' in script_config:
            # Inline script
            execute_inline_script(script_config['inline'], container_name, image_name)
        elif isinstance(script_config, str):
            # File-based script
            execute_file_script(script_config, container_name, image_name)
    
    except subprocess.TimeoutExpired:
        console.print(f"[red]❌ Script timeout for {container_name}[/red]")
    except Exception as e:
        console.print(f"[red]❌ Script execution failed: {e}[/red]")


def execute_inline_script(script_content: str, container_name: str, image_name: str):
    """Execute inline script from config"""
    temp_script = f"/tmp/playground-script-{container_name}.sh"
    
    try:
        # Create temporary script file
        with open(temp_script, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write(f'CONTAINER_NAME="{container_name}"\n')
            f.write(f'IMAGE_NAME="{image_name}"\n')
            f.write(f'SHARED_DIR="{SHARED_DIR}"\n')
            f.write(script_content)
        
        Path(temp_script).chmod(0o755)
        
        # Execute inline script
        result = subprocess.run(
            ['bash', temp_script, container_name],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            console.print("[green]✓ Script executed successfully[/green]")
            if result.stdout:
                console.print(f"[dim]{result.stdout}[/dim]")
        else:
            console.print(f"[yellow]⚠ Script exited with code {result.returncode}[/yellow]")
            if result.stderr:
                console.print(f"[dim]{result.stderr}[/dim]")
        
        # Cleanup
        Path(temp_script).unlink(missing_ok=True)
        
    except subprocess.TimeoutExpired:
        console.print(f"[red]❌ Inline script timeout for {container_name}[/red]")
        Path(temp_script).unlink(missing_ok=True)
    except Exception as e:
        console.print(f"[red]❌ Inline script execution failed: {e}[/red]")
        Path(temp_script).unlink(missing_ok=True)


def execute_file_script(script_path: str, container_name: str, image_name: str):
    """Execute file-based script"""
    full_script_path = SCRIPTS_DIR / script_path
    
    if not full_script_path.exists():
        console.print(f"[yellow]⚠ Script file not found: {full_script_path}[/yellow]")
        return
    
    try:
        result = subprocess.run(
            ['bash', str(full_script_path), container_name],
            capture_output=True,
            text=True,
            timeout=60,
            env={
                'SHARED_DIR': str(SHARED_DIR),
                'CONTAINER_NAME': container_name,
                'IMAGE_NAME': image_name
            }
        )
        
        if result.returncode == 0:
            console.print(f"[green]✓ Script {script_path} executed[/green]")
            if result.stdout:
                console.print(f"[dim]{result.stdout}[/dim]")
        else:
            console.print(f"[yellow]⚠ Script exited with code {result.returncode}[/yellow]")
            if result.stderr:
                console.print(f"[dim]{result.stderr}[/dim]")
    
    except subprocess.TimeoutExpired:
        console.print(f"[red]❌ Script timeout for {container_name}[/red]")
    except Exception as e:
        console.print(f"[red]❌ Script execution failed: {e}[/red]")