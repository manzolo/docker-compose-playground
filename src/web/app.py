from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from pathlib import Path
import logging
from pydantic import BaseModel

# Import routers
from src.web.api import web, containers, groups, system, config_mgmt, websocket
from src.web.api import cleanup, monitoring, execute_command, health_check

# Configure logging
logging.basicConfig(
    filename="venv/web.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)
logger.info("Starting Docker Playground Web Dashboard...")

# Define response models for documentation
class APIStatus(BaseModel):
    """API status response"""
    status: str
    message: str

# Initialize FastAPI with Swagger documentation
app = FastAPI(
    title="Docker Playground Web Dashboard",
    description="""
    ## Complete API for managing Docker containers and configurations
    
    ### Features:
    - 🐳 **Containers**: Manage Docker containers
    - 📦 **Groups**: Organize containers in groups
    - ⚙️ **Configuration**: Manage system configuration
    - 🔍 **Monitoring**: Monitor container performance
    - 🔧 **System**: System administration tools
    - 📡 **WebSocket**: Real-time updates
    
    ### Documentation:
    - **Swagger UI**: `/docs` - Interactive API documentation
    - **ReDoc**: `/redoc` - Alternative documentation format
    - **OpenAPI Schema**: `/openapi.json` - Raw OpenAPI specification
    """,
    version="1.0.0",
    contact={
        "name": "Support",
        "url": "http://localhost:8000",
        "email": "support@manzolo.it"
    },
    license_info={
        "name": "MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Setup paths
APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "templates" / "static"

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include routers with tags for organization in Swagger
app.include_router(web.router, tags=["web"])
app.include_router(containers.router, tags=["containers"])
app.include_router(groups.router, tags=["groups"])
app.include_router(system.router, tags=["system"])
app.include_router(config_mgmt.router, tags=["config"])
app.include_router(websocket.router, tags=["websocket"])
app.include_router(monitoring.router, tags=["monitoring"])
app.include_router(execute_command.router, tags=["commands"])
app.include_router(cleanup.router, tags=["commands"])
app.include_router(health_check.router, tags=["health"])

# Custom OpenAPI schema configuration
def custom_openapi():
    """Generate custom OpenAPI schema"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Docker Playground Web Dashboard",
        version="1.0.0",
        description="Complete API for managing Docker containers and configurations",
        routes=app.routes,
    )
    
    # Add custom metadata
    openapi_schema["info"]["x-logo"] = {
        "url": "https://www.docker.com/wp-content/uploads/2023/08/docker-logo-blue.svg",
        "altText": "Docker Logo"
    }
    
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Playground Server"
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get(
    "/",
    summary="API Status",
    tags=["health"],
    response_model=APIStatus
)
async def root():
    """
    Root endpoint that provides API status.
    
    This is used by the health check in the startup script.
    Returns 'healthy' if the service is running.
    """
    return APIStatus(
        status="healthy",
        message="Docker Playground API is running. Visit /docs for documentation"
    )

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
    logger.info("Swagger UI available at: http://localhost:8000/docs")