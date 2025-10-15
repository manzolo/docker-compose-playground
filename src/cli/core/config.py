"""
Configuration management for CLI
Handles loading from config.yml, config.d, and custom.d
"""

import yaml
from pathlib import Path
from typing import Dict, Any
import typer
from rich.console import Console

console = Console()

# Paths
BASE_PATH = Path(__file__).parent.parent.parent.parent
CONFIG_FILE = BASE_PATH / "config.yml"
CONFIG_DIR = BASE_PATH / "config.d"
CUSTOM_CONFIG_DIR = BASE_PATH / "custom.d"


def load_config() -> Dict[str, Any]:
    """Load configuration from all sources"""
    images = {}
    
    # Load from config.yml
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r") as f:
                config = yaml.safe_load(f)
                if config and isinstance(config, dict) and "images" in config:
                    images.update(config["images"])
        except yaml.YAMLError as e:
            console.print(f"[red]❌ Failed to parse config.yml: {e}[/red]")
            raise typer.Exit(1)
    
    # Load from config.d
    if CONFIG_DIR.exists():
        for config_file in CONFIG_DIR.glob("*.yml"):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    if config and isinstance(config, dict) and "images" in config:
                        images.update(config["images"])
            except yaml.YAMLError as e:
                console.print(f"[yellow]⚠ Failed to parse {config_file}: {e}[/yellow]")
    
    # Load from custom.d
    if CUSTOM_CONFIG_DIR.exists():
        for config_file in CUSTOM_CONFIG_DIR.glob("*.yml"):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    if config and isinstance(config, dict) and "images" in config:
                        images.update(config["images"])
            except yaml.YAMLError as e:
                console.print(f"[yellow]⚠ Failed to parse {config_file}: {e}[/yellow]")
    
    if not images:
        console.print("[red]❌ No valid configurations found[/red]")
        raise typer.Exit(1)
    
    return dict(sorted(images.items(), key=lambda x: x[0].lower()))


def load_groups() -> Dict[str, Any]:
    """Load groups from all configuration sources"""
    groups = {}
    
    # Load from config.yml
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r") as f:
                config = yaml.safe_load(f)
                if config and isinstance(config, dict) and "group" in config:
                    group_name = config["group"].get("name", "main")
                    groups[group_name] = config["group"]
        except yaml.YAMLError as e:
            console.print(f"[yellow]⚠ Failed to parse groups from config.yml: {e}[/yellow]")
    
    # Load from config.d
    if CONFIG_DIR.exists():
        for config_file in CONFIG_DIR.glob("*.yml"):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    if config and isinstance(config, dict) and "group" in config:
                        group_name = config["group"].get("name", f"group_{len(groups)}")
                        groups[group_name] = config["group"]
                        groups[group_name]["source"] = config_file.name
            except yaml.YAMLError as e:
                console.print(f"[yellow]⚠ Failed to parse groups from {config_file}: {e}[/yellow]")
    
    # Load from custom.d
    if CUSTOM_CONFIG_DIR.exists():
        for config_file in CUSTOM_CONFIG_DIR.glob("*.yml"):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    if config and isinstance(config, dict) and "group" in config:
                        group_name = config["group"].get("name", f"group_{len(groups)}")
                        groups[group_name] = config["group"]
                        groups[group_name]["source"] = config_file.name
            except yaml.YAMLError as e:
                console.print(f"[yellow]⚠ Failed to parse groups from {config_file}: {e}[/yellow]")
    
    return groups


def get_image_config(image_name: str) -> Dict[str, Any]:
    """Get configuration for a specific image"""
    config = load_config()
    if image_name not in config:
        console.print(f"[red]❌ Container '{image_name}' not found in config[/red]")
        raise typer.Exit(1)
    return config[image_name]