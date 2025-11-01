from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import docker
import logging
from src.web.core.logging_config import get_logger

# Importazioni dalla logica refactorizzata
from src.web.core.config import load_config
from src.web.core.docker import get_running_container_features
from src.web.utils.helpers import natural_sort_key

router = APIRouter()
logger = get_logger(__name__)
docker_client = docker.from_env()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
NETWORK_NAME = "playground-network"

@router.get("/manage", response_class=HTMLResponse)
async def manage_page(request: Request):
    """Advanced manager page"""
    try:
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