"""
Configuration management for CLI
Handles loading from config.yml, config.d, and custom.d with volume support
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
    """Load configuration from all sources with volume support"""
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
        for config_file in sorted(CONFIG_DIR.glob("*.yml")):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    if config and isinstance(config, dict) and "images" in config:
                        images.update(config["images"])
            except yaml.YAMLError as e:
                console.print(f"[yellow]⚠ Failed to parse {config_file.name}: {e}[/yellow]")
    
    # Load from custom.d
    if CUSTOM_CONFIG_DIR.exists():
        for config_file in sorted(CUSTOM_CONFIG_DIR.glob("*.yml")):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    if config and isinstance(config, dict) and "images" in config:
                        images.update(config["images"])
            except yaml.YAMLError as e:
                console.print(f"[yellow]⚠ Failed to parse {config_file.name}: {e}[/yellow]")
    
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
                if config and isinstance(config, dict):
                    # Support both "groups" (plural) and "group" (singular) keys
                    groups_data = config.get("groups") or config.get("group")
                    if groups_data:
                        if isinstance(groups_data, list):
                            for group in groups_data:
                                if "name" in group:
                                    groups[group["name"]] = group
                        elif isinstance(groups_data, dict):
                            # Single group defined as "group:" with "name:" inside
                            if "name" in groups_data:
                                groups[groups_data["name"]] = groups_data
                            else:
                                # Multiple groups as dict keys
                                for name, group in groups_data.items():
                                    if isinstance(group, dict):
                                        group["name"] = name
                                        groups[name] = group
        except yaml.YAMLError as e:
            console.print(f"[yellow]⚠ Failed to parse groups from config.yml: {e}[/yellow]")
    
    # Load from config.d
    if CONFIG_DIR.exists():
        for config_file in sorted(CONFIG_DIR.glob("*.yml")):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    if config and isinstance(config, dict):
                        groups_data = config.get("groups") or config.get("group")
                        if groups_data:
                            if isinstance(groups_data, list):
                                # List of groups
                                for group in groups_data:
                                    if isinstance(group, dict) and "name" in group:
                                        group["source"] = config_file.name
                                        groups[group["name"]] = group
                            elif isinstance(groups_data, dict):
                                # Single group with "name" key inside
                                if "name" in groups_data:
                                    groups_data["source"] = config_file.name
                                    groups[groups_data["name"]] = groups_data
                                # Don't iterate - if it's a single group, it won't have other dict keys
            except yaml.YAMLError as e:
                console.print(f"[yellow]⚠ Failed to parse groups from {config_file.name}: {e}[/yellow]")
    
    # Load from custom.d
    if CUSTOM_CONFIG_DIR.exists():
        for config_file in sorted(CUSTOM_CONFIG_DIR.glob("*.yml")):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    if config and isinstance(config, dict):
                        groups_data = config.get("groups") or config.get("group")
                        if groups_data:
                            if isinstance(groups_data, list):
                                # List of groups
                                for group in groups_data:
                                    if isinstance(group, dict) and "name" in group:
                                        group["source"] = config_file.name
                                        groups[group["name"]] = group
                            elif isinstance(groups_data, dict):
                                # Single group with "name" key inside
                                if "name" in groups_data:
                                    groups_data["source"] = config_file.name
                                    groups[groups_data["name"]] = groups_data
                                # Don't iterate - if it's a single group, it won't have other dict keys
            except yaml.YAMLError as e:
                console.print(f"[yellow]⚠ Failed to parse groups from {config_file.name}: {e}[/yellow]")
    
    return groups


def get_image_config(image_name: str) -> Dict[str, Any]:
    """Get configuration for a specific image"""
    config = load_config()
    if image_name not in config:
        console.print(f"[red]❌ Container '{image_name}' not found in config[/red]")
        console.print(f"[yellow]Available containers: {', '.join(list(config.keys())[:5])}...")
        raise typer.Exit(1)
    return config[image_name]


def validate_image_config(image_name: str, img_data: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate image configuration"""
    errors = []
    
    # Check required fields
    if "image" not in img_data:
        errors.append(f"Missing 'image' field for {image_name}")
    
    if "keep_alive_cmd" not in img_data:
        errors.append(f"Missing 'keep_alive_cmd' field for {image_name}")
    
    # Validate volumes if present
    if "volumes" in img_data:
        volumes = img_data["volumes"]
        if isinstance(volumes, list):
            for i, vol in enumerate(volumes):
                if not isinstance(vol, dict):
                    errors.append(f"Volume {i} in {image_name} is not a dictionary")
                    continue
                
                vol_type = vol.get("type", "named")
                
                if not vol.get("path"):
                    errors.append(f"Volume {i} in {image_name} missing 'path'")
                
                if vol_type == "named" and not vol.get("name"):
                    errors.append(f"Named volume {i} in {image_name} missing 'name'")
                
                if vol_type in ("bind", "file") and not vol.get("host"):
                    errors.append(f"{vol_type.capitalize()} volume {i} in {image_name} missing 'host'")
    
    # Validate ports if present
    if "ports" in img_data:
        ports = img_data["ports"]
        if isinstance(ports, list):
            for i, port in enumerate(ports):
                if not isinstance(port, str) or ':' not in port:
                    errors.append(f"Port {i} in {image_name} has invalid format (use 'host:container')")
    
    return len(errors) == 0, errors


def list_all_images() -> Dict[str, Any]:
    """List all available images with metadata"""
    config = load_config()
    return config


def list_images_by_category(category: str) -> Dict[str, Any]:
    """List images filtered by category"""
    config = load_config()
    return {
        name: data 
        for name, data in config.items() 
        if data.get("category", "other") == category
    }


def get_all_categories() -> list[str]:
    """Get all unique categories"""
    config = load_config()
    categories = set()
    for img_data in config.values():
        categories.add(img_data.get("category", "other"))
    return sorted(list(categories))