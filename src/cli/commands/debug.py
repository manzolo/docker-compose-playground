"""
Debug commands for troubleshooting CLI issues
"""

import typer
import yaml
from pathlib import Path
from rich.console import Console
from rich.syntax import Syntax

from ..core.config import (
    CONFIG_FILE, CONFIG_DIR, CUSTOM_CONFIG_DIR,
    load_config, load_groups
)

app = typer.Typer()
console = Console()


@app.command()
def config():
    """🔍 Show configuration structure"""
    console.print("[cyan bold]Configuration Debug Info[/cyan bold]\n")
    
    # Show paths
    console.print("[cyan]Config Paths:[/cyan]")
    console.print(f"  Base config: {CONFIG_FILE} - {'✓' if CONFIG_FILE.exists() else '✗'}")
    console.print(f"  Config.d:    {CONFIG_DIR} - {'✓' if CONFIG_DIR.exists() else '✗'}")
    console.print(f"  Custom.d:    {CUSTOM_CONFIG_DIR} - {'✓' if CUSTOM_CONFIG_DIR.exists() else '✗'}\n")
    
    # Show base config structure
    if CONFIG_FILE.exists():
        console.print("[cyan]Base Config (config.yml) structure:[/cyan]")
        try:
            with CONFIG_FILE.open("r") as f:
                config = yaml.safe_load(f)
            
            if config:
                for key in config.keys():
                    if key == "images":
                        img_count = len(config[key]) if isinstance(config[key], dict) else 0
                        console.print(f"  • images: {img_count} containers")
                    elif key == "group":
                        grp_count = len(config[key]) if isinstance(config[key], (dict, list)) else 0
                        console.print(f"  • group: {grp_count} group")
                    else:
                        console.print(f"  • {key}")
            else:
                console.print("  (empty file)")
        except Exception as e:
            console.print(f"  [red]Error reading config: {e}[/red]")
    
    console.print()
    
    # Show loaded images
    try:
        images = load_config()
        console.print(f"[cyan]Loaded Containers: {len(images)}[/cyan]")
        for name in list(images.keys())[:5]:
            console.print(f"  • {name}")
        if len(images) > 5:
            console.print(f"  ... and {len(images) - 5} more")
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
    
    console.print()
    
    # Show loaded groups
    try:
        groups = load_groups()
        console.print(f"[cyan]Loaded Groups: {len(groups)}[/cyan]")
        if groups:
            for name, group in list(groups.items())[:5]:
                containers_count = len(group.get("containers", []))
                console.print(f"  • {name} ({containers_count} containers)")
            if len(groups) > 5:
                console.print(f"  ... and {len(groups) - 5} more")
        else:
            console.print("  (no groups found)")
    except Exception as e:
        console.print(f"[red]Error loading groups: {e}[/red]")


@app.command()
def config_file(
    file: str = typer.Argument("config.yml", help="Config file to show (config.yml, config.d/*, custom.d/*)")
):
    """📄 Show config file content"""
    if file == "config.yml":
        filepath = CONFIG_FILE
    elif file.startswith("config.d/"):
        filepath = CONFIG_DIR / file.replace("config.d/", "")
    elif file.startswith("custom.d/"):
        filepath = CUSTOM_CONFIG_DIR / file.replace("custom.d/", "")
    else:
        filepath = CONFIG_DIR / file
    
    if not filepath.exists():
        console.print(f"[red]File not found: {filepath}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[cyan bold]Content of: {filepath.name}[/cyan bold]\n")
    
    try:
        with filepath.open("r") as f:
            content = f.read()
        
        syntax = Syntax(content, "yaml", theme="monokai", line_numbers=True)
        console.print(syntax)
    except Exception as e:
        console.print(f"[red]Error reading file: {e}[/red]")


@app.command()
def config_d():
    """📁 List files in config.d/"""
    console.print("[cyan bold]Files in config.d/[/cyan bold]\n")
    
    if not CONFIG_DIR.exists():
        console.print("[yellow]config.d/ directory does not exist[/yellow]")
        return
    
    files = list(CONFIG_DIR.glob("*.yml"))
    
    if not files:
        console.print("[yellow]No .yml files found in config.d/[/yellow]")
        return
    
    for filepath in sorted(files):
        size = filepath.stat().st_size
        console.print(f"  • {filepath.name} ({size} bytes)")
        
        try:
            with filepath.open("r") as f:
                data = yaml.safe_load(f)
            
            if data:
                if "images" in data:
                    console.print(f"    - images: {len(data['images'])} containers")
                if "group" in data:
                    console.print(f"    - groups: {len(data['group'])} group")
        except Exception as e:
            console.print(f"    [red]Error: {e}[/red]")


@app.command()
def test_groups():
    """🧪 Test groups loading"""
    console.print("[cyan bold]Testing Groups Loading[/cyan bold]\n")
    
    try:
        groups = load_groups()
        
        console.print(f"Total groups loaded: [green]{len(groups)}[/green]\n")
        
        if groups:
            for name, group in groups.items():
                console.print(f"[cyan]{name}[/cyan]")
                console.print(f"  Description: {group.get('description', 'N/A')}")
                
                containers = group.get("containers", [])
                console.print(f"  Containers: {len(containers)}")
                for cont in containers[:3]:
                    console.print(f"    • {cont}")
                if len(containers) > 3:
                    console.print(f"    ... and {len(containers) - 3} more")
                
                console.print(f"  Source: {group.get('source', 'config.yml')}")
                console.print()
        else:
            console.print("[yellow]No groups found in configuration[/yellow]\n")
            console.print("[yellow]To define groups, add them to config.yml:[/yellow]")
            console.print("""
[dim]groups:
  - name: MyGroup
    description: "Description here"
    category: "category"
    containers:
      - container1
      - container2[/dim]
""")
    
    except Exception as e:
        console.print(f"[red]Error loading groups: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")