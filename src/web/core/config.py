from pathlib import Path
from typing import Dict, Any
import yaml
from fastapi import HTTPException
import logging

logger = logging.getLogger("uvicorn")

# Percorsi base
BASE_DIR = Path(__file__).parent.parent.parent.parent
CONFIG_DIR = BASE_DIR / "config.d"
CUSTOM_CONFIG_DIR = BASE_DIR / "custom.d"
CONFIG_FILE = BASE_DIR / "config.yml"


def _process_config(config: Dict[str, Any], source_name: str, images: Dict[str, Any], groups: Dict[str, Any]):
    """Process a single config file and extract images and groups"""
    if not config or not isinstance(config, dict):
        return
    
    # Load group (supports both singular "group" and plural "groups")
    # Handle singular "group" with single group definition
    if "group" in config and isinstance(config["group"], dict):
        group_data = config["group"]
        if "name" in group_data:
            # Single group with name inside
            group_name = group_data["name"]
            groups[group_name] = group_data
            groups[group_name]["source"] = source_name
            logger.debug("Loaded group '%s' from %s", group_name, source_name)
    
    # Handle plural "groups" (list or dict)
    if "groups" in config:
        groups_data = config["groups"]
        if isinstance(groups_data, list):
            for group in groups_data:
                if isinstance(group, dict) and "name" in group:
                    group_name = group["name"]
                    groups[group_name] = group
                    groups[group_name]["source"] = source_name
                    logger.debug("Loaded group '%s' from %s", group_name, source_name)
        elif isinstance(groups_data, dict):
            for name, group in groups_data.items():
                if isinstance(group, dict):
                    group["name"] = name
                    groups[name] = group
                    groups[name]["source"] = source_name
                    logger.debug("Loaded group '%s' from %s", name, source_name)
    
    # Load images from "images" section
    if "images" in config and isinstance(config["images"], dict):
        images.update(config["images"])
        logger.debug("Loaded %d images from 'images' key in %s", len(config["images"]), source_name)
    else:
        # Fallback: load images from direct keys (not group, not groups, not settings)
        for key, value in config.items():
            if key not in ("group", "groups", "settings") and isinstance(value, dict) and "image" in value:
                images[key] = value
        if any(key not in ("group", "groups", "settings") for key in config.keys()):
            logger.debug("Loaded images from direct keys in %s", source_name)


def load_config() -> Dict[str, Dict[str, Any]]:
    """Load configuration from config.yml, config.d and custom.d"""
    images = {}
    groups = {}
    
    # 1. Load from config.yml
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r") as f:
                config = yaml.safe_load(f)
                _process_config(config, "config.yml", images, groups)
        except yaml.YAMLError as e:
            logger.error("Failed to parse config.yml: %s", str(e))
            raise HTTPException(500, f"Failed to parse config.yml: {str(e)}")
    
    # 2. Load from config.d
    if CONFIG_DIR.exists():
        for config_file in sorted(CONFIG_DIR.glob("*.yml")):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    _process_config(config, config_file.name, images, groups)
            except yaml.YAMLError as e:
                logger.error("Failed to parse %s: %s", config_file, str(e))
                continue
    
    # 3. Load from custom.d
    if CUSTOM_CONFIG_DIR.exists():
        for config_file in sorted(CUSTOM_CONFIG_DIR.glob("*.yml")):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    _process_config(config, config_file.name, images, groups)
            except yaml.YAMLError as e:
                logger.error("Failed to parse %s: %s", config_file, str(e))
                continue
    
    if not images:
        logger.error("No valid configurations found")
        raise HTTPException(500, "No valid configurations found")
    
    logger.info("Total loaded: %d images, %d groups", len(images), len(groups))
    
    return {
        "images": dict(sorted(images.items(), key=lambda x: x[0].lower())),
        "groups": groups
    }


def get_motd(image_name: str, config: Dict[str, Any]) -> str:
    """Get MOTD for image"""
    img_data = config.get(image_name, {})
    return img_data.get('motd', '')