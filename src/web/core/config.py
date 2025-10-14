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
    """Process a single config file"""
    if not config or not isinstance(config, dict):
        return
    
    # Load group if present
    if "group" in config and isinstance(config["group"], dict):
        group_name = config["group"].get("name", f"group_{len(groups)}")
        groups[group_name] = config["group"]
        groups[group_name]["source"] = source_name
        logger.debug("Loaded group '%s' from %s", group_name, source_name)
    
    # Load images
    if "images" in config and isinstance(config["images"], dict):
        images.update(config["images"])
        logger.debug("Loaded %d images from 'images' key in %s", len(config["images"]), source_name)
    else:
        for key, value in config.items():
            if key != "group" and isinstance(value, dict) and "image" in value:
                images[key] = value
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