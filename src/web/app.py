from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging

# Import routers
from src.web.api import web, containers, groups, system, config_mgmt, websocket

# Configure logging
logging.basicConfig(
    filename="venv/web.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)
logger.info("Starting Docker Playground Web Dashboard...")

# Initialize FastAPI
app = FastAPI(title="Docker Playground Web Dashboard")

# Setup paths
APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "templates" / "static"

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include routers
app.include_router(web.router)
app.include_router(containers.router)
app.include_router(groups.router)
app.include_router(system.router)
app.include_router(config_mgmt.router)
app.include_router(websocket.router)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    from src.web.api.config_mgmt import cleanup_temp_files
    cleanup_temp_files()
    logger.info("Application started successfully")