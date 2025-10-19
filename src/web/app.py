from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging

# Import routers
from src.web.api import web, containers, groups, system, config_mgmt, websocket
from src.web.api import monitoring, execute_command, health_check

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
app.include_router(web.router, tags=["web"])
app.include_router(containers.router, tags=["containers"])
app.include_router(groups.router, tags=["groups"])
app.include_router(system.router, tags=["system"])
app.include_router(config_mgmt.router, tags=["config"])
app.include_router(websocket.router, tags=["websocket"])
app.include_router(monitoring.router, tags=["monitoring"])
app.include_router(execute_command.router, tags=["commands"])
app.include_router(health_check.router, tags=["health"])


@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    from src.web.api.config_mgmt import cleanup_temp_files
    from src.web.core.state import cleanup_old_operations
    
    # Cleanup old temp files
    removed_files = cleanup_temp_files()
    logger.info("Cleaned up %d old temp files", removed_files)
    
    # Cleanup old operations
    removed_ops = cleanup_old_operations(max_age_seconds=3600)
    logger.info("Cleaned up %d old operations", removed_ops)
    
    logger.info("Application started successfully")