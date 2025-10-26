from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
import logging

from src.web.core.config import load_config
from src.web.core.docker import docker_client, get_container_features
from src.web.utils.helpers import natural_sort_key
from src.web.utils.motd_processor import parse_motd_commands, clean_motd_text, motd_to_html

router = APIRouter()
logger = logging.getLogger("uvicorn")

# Templates setup
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Registra i filtri Jinja2
templates.env.filters['motd_to_html'] = motd_to_html



def enrich_image_data(config):
    """Add motd_commands and clean motd to each image config"""
    enriched = {}
    for img_name, img_data in config.items():
        enriched_data = img_data.copy()
        motd = img_data.get('motd', '')
        commands = parse_motd_commands(motd)
        enriched_data['motd_commands'] = commands
        enriched_data['motd_commands_json'] = json.dumps(commands)
        enriched_data['motd'] = clean_motd_text(motd)
        enriched[img_name] = enriched_data
    return enriched


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard"""
    try:
        config_data = load_config()
        config = config_data["images"]
        groups = config_data["groups"]
        
        # Natural sorting
        sorted_config = dict(sorted(config.items(), key=lambda x: natural_sort_key(x[0])))
        
        # Get running containers
        running = docker_client.containers.list(all=True)
        running_dict = {}
        features_dict = {}
        
        for c in running:
            if c.name.startswith("playground-"):
                image_name = c.name.replace("playground-", "", 1)
                running_dict[image_name] = {"name": c.name, "status": c.status}
        
        for img_name in sorted_config.keys():
            features_dict[img_name] = get_container_features(img_name, sorted_config)
        
        # Enrich config with parsed MOTD commands and cleaned text
        sorted_config = enrich_image_data(sorted_config)
        
        # Categories
        categories = set()
        category_counts = {}
        for img_name, img_data in sorted_config.items():
            cat = img_data.get('category', 'other')
            categories.add(cat)
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "images": sorted_config,
            "groups": groups,
            "running": running_dict,
            "features": features_dict,
            "categories": sorted(categories),
            "category_counts": category_counts
        })
    except Exception as e:
        logger.error("Error loading dashboard: %s", str(e))
        raise HTTPException(500, f"Error loading dashboard: {str(e)}")


@router.get("/manage", response_class=HTMLResponse)
async def manage_page(request: Request):
    """Advanced manager page"""
    try:
        from src.web.core.docker import NETWORK_NAME
        
        config_data = load_config()
        config = config_data["images"]
        groups = config_data["groups"]
        
        running = docker_client.containers.list(filters={"label": "playground.managed=true"})
        
        # Count by category
        categories = {}
        for img_name, img_data in config.items():
            cat = img_data.get('category', 'other')
            categories[cat] = categories.get(cat, 0) + 1
        
        # Network info
        try:
            network = docker_client.networks.get(NETWORK_NAME)
            network_info = {
                "name": network.name,
                "driver": network.attrs.get('Driver', 'N/A'),
                "subnet": network.attrs.get('IPAM', {}).get('Config', [{}])[0].get('Subnet', 'N/A')
            }
        except:
            network_info = {"name": "Not created", "driver": "N/A", "subnet": "N/A"}
        
        return templates.TemplateResponse("manage.html", {
            "request": request,
            "total_images": len(config),
            "running_count": len(running),
            "stopped_count": len(config) - len(running),
            "categories": categories,
            "groups": groups,
            "network_info": network_info
        })
    except Exception as e:
        logger.error("Error loading manage page: %s", str(e))
        raise HTTPException(500, str(e))


@router.get("/add-container", response_class=HTMLResponse)
async def add_container_page(request: Request):
    """Page to add new container"""
    try:
        config_data = load_config()
        config = config_data["images"]
        categories = sorted(set(img_data.get('category', 'other') for img_data in config.values()))
        
        return templates.TemplateResponse("add_container.html", {
            "request": request,
            "existing_categories": categories
        })
    except Exception as e:
        logger.error("Error loading add container page: %s", str(e))
        raise HTTPException(500, str(e))