# SEZIONI MODIFICATE PER app.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time
import docker

# ============================================================
# RATE LIMITING SETUP
# ============================================================

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Rate limit configuration
RATE_LIMIT_CONFIG = {
    "default": "100/minute",  # 100 requests per minute by default
    "strict": "10/minute",    # 10 requests per minute for resource-intensive ops
    "loose": "1000/minute",   # 1000 requests per minute for lightweight ops
}


# ============================================================
# CUSTOM EXCEPTION HANDLER FOR RATE LIMITING
# ============================================================

def rate_limit_error_handler(request: Request, exc: RateLimitExceeded):
    """Custom error response for rate limit exceeded"""
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": str(exc.detail),
            "retry_after": 60
        }
    )


# ============================================================
# APPLICATION INITIALIZATION
# ============================================================

from pathlib import Path
import logging
from pydantic import BaseModel

# Import routers
from src.web.api import web, containers, groups, system, config_mgmt, websocket
from src.web.api import cleanup, monitoring, execute_command, health_check

# Configure logging with better formatting
logging.basicConfig(
    filename="venv/web.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('[%(levelname)s] %(name)s: %(message)s')
console_handler.setFormatter(console_formatter)
logging.getLogger().addHandler(console_handler)

logger.info("=" * 80)
logger.info("Starting Docker Playground Web Dashboard...")
logger.info("=" * 80)


# ============================================================
# RESPONSE MODELS
# ============================================================

class APIStatus(BaseModel):
    """API status response"""
    status: str
    message: str
    version: str
    timestamp: str


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    uptime_seconds: float
    timestamp: str
    checks: dict


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Docker Playground Web Dashboard",
    description="""
    ## Complete API for managing Docker containers and configurations
    
    ### Features:
    - 🐳 **Containers**: Manage Docker containers (start, stop, restart, logs)
    - 📦 **Groups**: Organize containers in groups for batch operations
    - ⚙️ **Configuration**: Manage system configuration and custom containers
    - 🔍 **Monitoring**: Monitor container performance and health
    - 🔧 **System**: System administration tools (cleanup, validation)
    - 📡 **WebSocket**: Real-time terminal access to containers
    - 🏥 **Health**: System health checks and diagnostics
    
    ### Rate Limiting:
    - Default: 100 requests/minute
    - Strict (resource-intensive): 10 requests/minute
    - Loose (lightweight): 1000 requests/minute
    
    ### Documentation:
    - **Swagger UI**: `/docs` - Interactive API documentation
    - **ReDoc**: `/redoc` - Alternative documentation format
    - **OpenAPI Schema**: `/openapi.json` - Raw OpenAPI specification
    """,
    version="2.0.0",
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

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)

# Setup paths
APP_DIR = Path(__file__).parent
STATIC_DIR = APP_DIR / "templates" / "static"

# Mount static files
from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ============================================================
# MIDDLEWARE
# ============================================================

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST/RESPONSE LOGGING MIDDLEWARE
# ============================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests and responses"""
    
    # Skip logging for static files and health checks to reduce noise
    if request.url.path.startswith("/static") or request.url.path == "/":
        return await call_next(request)
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log request details
        logger.debug(
            "%s %s - Status: %d - Time: %.3fs",
            request.method,
            request.url.path,
            response.status_code,
            process_time
        )
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
    
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            "%s %s - Error: %s - Time: %.3fs",
            request.method,
            request.url.path,
            str(e),
            process_time,
            exc_info=True
        )
        raise


# ============================================================
# INCLUDE ROUTERS
# ============================================================

app.include_router(web.router, tags=["web"])
app.include_router(containers.router, tags=["containers"])
app.include_router(groups.router, tags=["groups"])
app.include_router(system.router, tags=["system"])
app.include_router(config_mgmt.router, tags=["config"])
app.include_router(websocket.router, tags=["websocket"])
app.include_router(monitoring.router, tags=["monitoring"])
app.include_router(execute_command.router, tags=["commands"])
app.include_router(cleanup.router, tags=["cleanup"])
app.include_router(health_check.router, tags=["health"])

logger.info("All routers registered successfully")


# ============================================================
# CUSTOM OPENAPI SCHEMA
# ============================================================

def custom_openapi():
    """Generate custom OpenAPI schema with better metadata"""
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title="Docker Playground Web Dashboard",
        version="2.0.0",
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
            "description": "Development Server"
        },
        {
            "url": "http://{host}:{port}",
            "description": "Custom Server",
            "variables": {
                "host": {"default": "localhost"},
                "port": {"default": "8000"}
            }
        }
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


# ============================================================
# STARTUP TIMESTAMP
# ============================================================

startup_time = None


# ============================================================
# ROOT ENDPOINT WITH RATE LIMITING
# ============================================================

@app.get(
    "/",
    summary="API Status",
    tags=["health"],
    response_model=APIStatus,
    include_in_schema=False
)
@limiter.limit(RATE_LIMIT_CONFIG["loose"])
async def root(request: Request):
    """
    Root endpoint that provides API status.
    
    This is used by health checks and load balancers.
    Returns 'healthy' if the service is running.
    """
    from datetime import datetime
    
    return APIStatus(
        status="healthy",
        message="Docker Playground API is running. Visit /docs for documentation",
        version="2.0.0",
        timestamp=datetime.now().isoformat()
    )


# ============================================================
# ENHANCED HEALTH CHECK ENDPOINT
# ============================================================

@app.get(
    "/health",
    summary="Health Check",
    tags=["health"],
    response_model=HealthCheckResponse
)
@limiter.limit(RATE_LIMIT_CONFIG["loose"])
async def health_check_endpoint(request: Request):
    """
    Health check endpoint with uptime and system status
    
    Returns detailed health information including:
    - API status
    - Uptime since startup
    - Docker daemon status
    - Database connectivity
    """
    global startup_time
    
    from datetime import datetime
    import docker
    
    if startup_time is None:
        uptime = 0
    else:
        uptime = time.time() - startup_time
    
    checks = {
        "api": "healthy",
        "docker": "unknown",
        "config": "unknown"
    }
    
    # Check Docker connection
    try:
        docker_client = docker.from_env()
        docker_client.ping()
        checks["docker"] = "healthy"
    except Exception as e:
        logger.warning("Docker health check failed: %s", str(e))
        checks["docker"] = "unhealthy"
    
    # Check configuration loading
    try:
        from src.web.core.config import load_config
        load_config()
        checks["config"] = "healthy"
    except Exception as e:
        logger.warning("Config health check failed: %s", str(e))
        checks["config"] = "unhealthy"
    
    # Determine overall status
    overall_status = "healthy" if all(v == "healthy" for v in checks.values()) else "degraded"
    
    return HealthCheckResponse(
        status=overall_status,
        uptime_seconds=uptime,
        timestamp=datetime.now().isoformat(),
        checks=checks
    )


# ============================================================
# STARTUP EVENTS
# ============================================================

@app.on_event("startup")
async def startup_event():
    """Startup tasks and initialization"""
    global startup_time
    startup_time = time.time()

    from src.web.api.config_mgmt import cleanup_temp_files
    from src.web.core.state import cleanup_old_operations
    from src.web.api.cleanup import cleanup_old_backups
    from src.web.utils.assets import init_asset_manager

    logger.info("=" * 80)
    logger.info("STARTUP SEQUENCE INITIATED")
    logger.info("=" * 80)

    # Initialize asset versioning manager
    try:
        asset_manager = init_asset_manager(str(STATIC_DIR))
        logger.info("✓ Asset versioning initialized")
    except Exception as e:
        logger.warning("! Failed to initialize asset manager: %s", str(e))
    
    # Cleanup old temp files
    try:
        removed_files = cleanup_temp_files()
        logger.info("✓ Cleaned up %d old temp files", removed_files)
    except Exception as e:
        logger.warning("! Failed to cleanup temp files: %s", str(e))
    
    # Cleanup old operations
    try:
        removed_ops = cleanup_old_operations(max_age_seconds=3600)
        logger.info("✓ Cleaned up %d old operations (>1 hour old)", removed_ops)
    except Exception as e:
        logger.warning("! Failed to cleanup operations: %s", str(e))
    
    # Cleanup old backups
    try:
        removed_backups = cleanup_old_backups()
        logger.info("✓ Cleaned up %d old backups (>7 days old)", removed_backups)
    except Exception as e:
        logger.warning("! Failed to cleanup backups: %s", str(e))
    
    # Load configuration
    try:
        from src.web.core.config import load_config
        config_data = load_config()
        logger.info("✓ Configuration loaded: %d images, %d groups",
                   len(config_data.get("images", {})),
                   len(config_data.get("groups", {})))
    except Exception as e:
        logger.error("✗ Failed to load configuration: %s", str(e))
    
    # Initialize Docker network
    try:
        from src.web.core.docker import ensure_network, TimeoutConfig
        ensure_network()
        TimeoutConfig.log_config()
        logger.info("✓ Docker network verified")
    except Exception as e:
        logger.warning("! Failed to initialize Docker network: %s", str(e))
    
    # Log rate limiting config
    logger.info("✓ Rate limiting configured:")
    for limit_type, limit_value in RATE_LIMIT_CONFIG.items():
        logger.info("  - %s: %s", limit_type, limit_value)
    
    logger.info("=" * 80)
    logger.info("STARTUP COMPLETE - API Ready")
    logger.info("Swagger UI: http://localhost:8000/docs")
    logger.info("=" * 80)


# ============================================================
# SHUTDOWN EVENTS
# ============================================================

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("=" * 80)
    logger.info("SHUTDOWN SEQUENCE INITIATED")
    logger.info("=" * 80)
    
    uptime = time.time() - startup_time if startup_time else 0
    logger.info("Application uptime: %.1f seconds (%.1f minutes)", uptime, uptime / 60)
    
    logger.info("=" * 80)
    logger.info("SHUTDOWN COMPLETE")
    logger.info("=" * 80)