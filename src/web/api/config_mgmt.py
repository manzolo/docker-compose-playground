from fastapi import APIRouter, Request, HTTPException, Path as PathParam
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field
from pathlib import Path
from datetime import datetime, timedelta
import yaml
import tempfile
import os
import glob
import logging
import docker

from src.web.core.config import load_config, CUSTOM_CONFIG_DIR, BASE_DIR
from src.web.core.docker import docker_client, SHARED_DIR

router = APIRouter()
logger = logging.getLogger("uvicorn")

# Ensure custom.d exists
CUSTOM_CONFIG_DIR.mkdir(exist_ok=True)

# ============================================
# Pydantic Models for Documentation
# ============================================

class AddContainerRequest(BaseModel):
    """Request model for adding a container"""
    name: str = Field(..., description="Container name", example="my-app", min_length=1, max_length=50)
    image: str = Field(..., description="Docker image", example="ubuntu:22.04")
    category: str = Field(..., description="Container category", example="tools")
    description: str = Field(..., description="Container description", example="My custom container")
    keep_alive_cmd: str = Field(default="tail -f /dev/null", description="Keep-alive command")
    shell: str = Field(default="/bin/bash", description="Default shell")
    ports: list = Field(default_factory=list, description="Ports to expose", example=[8000, 8080])
    environment: str = Field(default="", description="Environment variables (KEY=VALUE, one per line)")
    motd: str = Field(default="", description="Message of the day")

class ContainerConfigResponse(BaseModel):
    """Response after adding container"""
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Status message")
    name: str = Field(..., description="Container name")
    file: str = Field(..., description="Config file path")

class ValidateImageRequest(BaseModel):
    """Request model for image validation"""
    image: str = Field(..., description="Docker image name", example="ubuntu:22.04")

class ImageInfo(BaseModel):
    """Docker image information"""
    exists: bool = Field(..., description="Whether image exists")
    id: str = Field(..., description="Short image ID")
    tags: list = Field(default_factory=list, description="Image tags")
    size: str = Field(..., description="Image size in MB")
    created: str = Field(..., description="Creation date")

class ImageNotFound(BaseModel):
    """Response when image is not found"""
    exists: bool = Field(False)
    error: str = Field(..., description="Error message")

class DetectShellRequest(BaseModel):
    """Request for shell detection"""
    image: str = Field(..., description="Docker image name", example="ubuntu:22.04")

class DetectShellResponse(BaseModel):
    """Detected shell response"""
    shell: str = Field(..., description="Detected shell path", example="/bin/bash")

class BackupInfo(BaseModel):
    """Backup file information"""
    category: str = Field(..., description="Backup category")
    file: str = Field(..., description="Filename")
    size: int = Field(..., description="File size in bytes")
    modified: float = Field(..., description="Modification timestamp")

class BackupsList(BaseModel):
    """List of backups"""
    backups: list[BackupInfo] = Field(default_factory=list, description="List of backup files")

class DebugConfig(BaseModel):
    """Debug configuration response"""
    custom_dir: str = Field(..., description="Custom config directory path")
    custom_files: list = Field(default_factory=list, description="Custom config files")
    loaded_images: list = Field(default_factory=list, description="Sample of loaded images")
    total_loaded: int = Field(..., description="Total number of loaded images")
    groups: list = Field(default_factory=list, description="Configured groups")

# ============================================
# YAML Dumper
# ============================================

class CustomDumper(yaml.SafeDumper):
    """Custom YAML dumper for multiline strings"""
    def represent_str(self, data):
        if "\n" in data:
            return self.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return self.represent_scalar('tag:yaml.org,2002:str', data)

CustomDumper.add_representer(str, CustomDumper.represent_str)

# ============================================
# Endpoints
# ============================================

@router.get(
    "/api/export-config",
    summary="Export Configuration",
    description="Export current configuration as YAML file",
    responses={
        200: {"description": "Configuration file exported"},
        500: {"description": "Error exporting configuration"}
    }
)
async def export_config():
    """
    Export the entire configuration as a YAML file.
    
    Returns the configuration in YAML format as a downloadable file.
    Includes both images and groups with proper character encoding.
    """
    try:
        config_data = load_config()
        images = config_data.get("images", {})
        groups = config_data.get("groups", {})
        
        # Build config with both images and groups
        config = {}
        
        if images:
            config["images"] = images
        
        if groups:
            # Clean groups data - remove 'source' field as it's not needed in export
            clean_groups = {}
            for group_name, group_data in groups.items():
                clean_group = {k: v for k, v in group_data.items() if k != "source"}
                clean_groups[group_name] = clean_group
            config["groups"] = clean_groups
        
        # Use safe dumper to properly handle special characters
        yaml_content = yaml.dump(
            config,
            Dumper=CustomDumper,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            indent=2,
            encoding=None  # Return string, not bytes
        )
        
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".yml",
            delete=False,
            dir=tempfile.gettempdir()
        ) as temp_file:
            temp_file.write(yaml_content)
            temp_file_path = temp_file.name
        
        filename = f"playground-config-{datetime.now().strftime('%Y%m%d_%H%M%S')}.yml"
        logger.info("Exported config with %d images and %d groups", len(images), len(groups))
        
        return FileResponse(
            path=temp_file_path,
            filename=filename,
            media_type="application/x-yaml",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error("Error exporting config: %s", str(e))
        raise HTTPException(500, f"Error exporting config: {str(e)}")


@router.post(
    "/api/add-container",
    response_model=ContainerConfigResponse,
    status_code=201,
    summary="Add Container Configuration",
    description="Add a new container configuration",
    responses={
        201: {"description": "Container added successfully"},
        400: {"description": "Invalid request or container already exists"},
        500: {"description": "Server error"}
    }
)
async def add_container_config(request: AddContainerRequest):
    """
    Add a new container configuration.
    
    Creates a new container configuration file in the custom.d directory.
    
    **Request Body:**
    - `name`: Unique container name
    - `image`: Docker image to use
    - `category`: Category for organization
    - `description`: Container description
    - `keep_alive_cmd`: Command to keep container running
    - `shell`: Default shell for the container
    - `ports`: Ports to expose
    - `environment`: Environment variables (KEY=VALUE format, one per line)
    - `motd`: Message of the day
    
    **Response:**
    - `status`: "success" if created
    - `message`: Confirmation message
    - `name`: Container name
    - `file`: Path to created config file
    """
    try:
        # Validate required fields
        if not request.name or not request.image or not request.category or not request.description:
            raise HTTPException(400, "Missing required fields")
        
        config_data = load_config()
        if request.name in config_data["images"]:
            raise HTTPException(400, f"Container '{request.name}' already exists")
        
        new_config = {
            "images": {
                request.name: {
                    "image": request.image,
                    "category": request.category,
                    "description": request.description,
                    "keep_alive_cmd": request.keep_alive_cmd,
                    "shell": request.shell,
                    "ports": request.ports,
                    "environment": {}
                }
            }
        }
        
        # Parse environment variables
        if request.environment:
            env_lines = request.environment.strip().split('\n')
            for line in env_lines:
                if '=' in line:
                    key, value = line.split('=', 1)
                    new_config['images'][request.name]['environment'][key.strip()] = value.strip()
        
        # Add MOTD if provided
        if request.motd:
            new_config['images'][request.name]['motd'] = request.motd
        
        # Create config file
        safe_name = request.name.replace('_', '-').lower()
        config_file_path = CUSTOM_CONFIG_DIR / f"{safe_name}.yml"
        
        if config_file_path.exists():
            raise HTTPException(400, f"Configuration file for '{request.name}' already exists")
        
        yaml_content = yaml.dump(
            new_config,
            Dumper=CustomDumper,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            indent=2
        )
        
        with config_file_path.open("w") as f:
            f.write(yaml_content)
        
        logger.info("Added new container config: %s", request.name)
        
        return ContainerConfigResponse(
            status="success",
            message=f"Container '{request.name}' added successfully",
            name=request.name,
            file=f"custom.d/{safe_name}.yml"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error adding container: %s", str(e))
        raise HTTPException(500, f"Failed to add container: {str(e)}")


@router.post(
    "/api/validate-image",
    response_model=ImageInfo | ImageNotFound,
    summary="Validate Docker Image",
    description="Check if a Docker image exists and retrieve its information",
    responses={
        200: {"description": "Image validation completed"},
        400: {"description": "Image name required"},
        500: {"description": "Server error"}
    }
)
async def validate_image(request: ValidateImageRequest):
    """
    Validate and retrieve information about a Docker image.
    
    This endpoint pulls the specified image and returns its metadata.
    
    **Request Body:**
    - `image`: Docker image name (e.g., ubuntu:22.04, minio/minio:latest)
    
    **Response (if image exists):**
    - `exists`: true
    - `id`: Short image ID
    - `tags`: Image tags
    - `size`: Image size in MB
    - `created`: Creation date
    
    **Response (if image not found):**
    - `exists`: false
    - `error`: Error message
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/validate-image \\
      -H "Content-Type: application/json" \\
      -d '{"image": "ubuntu:22.04"}'
    ```
    """
    try:
        image_name = request.image
        
        if not image_name:
            raise HTTPException(400, "Image name required")
        
        logger.info("Validating image: %s", image_name)
        
        try:
            image = docker_client.images.pull(image_name)
            logger.info("Image validated successfully: %s", image_name)
            
            return ImageInfo(
                exists=True,
                id=image.id[:12],
                tags=image.tags if image.tags else [],
                size=f"{image.attrs['Size'] / (1024*1024):.2f} MB",
                created=image.attrs['Created'][:10]
            )
        except docker.errors.ImageNotFound:
            logger.warning("Image not found: %s", image_name)
            return ImageNotFound(
                exists=False,
                error=f"Image '{image_name}' not found"
            )
        except Exception as e:
            logger.warning("Image validation failed for %s: %s", image_name, str(e))
            return ImageNotFound(
                exists=False,
                error=str(e)
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error validating image: %s", str(e))
        raise HTTPException(500, f"Error validating image: {str(e)}")


@router.post(
    "/api/detect-shell",
    response_model=DetectShellResponse,
    summary="Detect Shell in Running Container",
    description="Detect available shell in a running container instance",
    responses={
        200: {"description": "Shell detected"},
        400: {"description": "Container name required or not running"},
        404: {"description": "Container not found"},
        500: {"description": "Server error"}
    }
)
async def detect_shell(request: DetectShellRequest):
    """
    Detect the available shell in a running container.
    
    This endpoint connects to an already running container and
    attempts to find an available shell by testing common locations.
    Falls back to /bin/sh if detection fails.
    
    **Request Body:**
    - `image`: Container name (e.g., 'playground-ubuntu-24')
    
    **Response:**
    - `shell`: Detected or default shell path
    
    **Example:**
    ```bash
    curl -X POST http://localhost:8000/api/detect-shell \\
      -H "Content-Type: application/json" \\
      -d '{"image": "playground-ubuntu-24"}'
    ```
    """
    try:
        container_name = request.image
        
        if not container_name:
            raise HTTPException(400, "Container name required")
        
        logger.info("Detecting shell for container: %s", container_name)
        
        # Try to get the running container
        try:
            container = docker_client.containers.get(container_name)
            logger.debug("Container found: %s (status: %s)", container_name, container.status)
        except docker.errors.NotFound as e:
            logger.warning("Container not found: %s", container_name)
            raise HTTPException(404, f"Container '{container_name}' not found")
        except Exception as e:
            logger.error("Error getting container %s: %s", container_name, str(e))
            raise HTTPException(500, f"Error accessing container: {str(e)}")
        
        # Check if container is running
        if container.status != 'running':
            logger.warning("Container is not running: %s (status: %s)", container_name, container.status)
            raise HTTPException(400, f"Container '{container_name}' is not running (current status: {container.status})")
        
        shells = ['/bin/bash', '/bin/sh', '/bin/ash', '/usr/bin/bash']
        detected_shell = '/bin/sh'  # Default fallback
        
        logger.debug("Testing shells for container %s: %s", container_name, shells)
        
        try:
            # Test each shell in the running container
            for shell in shells:
                try:
                    exit_code, output = container.exec_run(f'test -f {shell}')
                    logger.debug("Testing shell %s in %s: exit_code=%d", shell, container_name, exit_code)
                    
                    if exit_code == 0:
                        detected_shell = shell
                        logger.info("Found shell %s in container %s", shell, container_name)
                        break
                except Exception as e:
                    logger.debug("Error testing shell %s in container %s: %s", shell, container_name, str(e))
                    continue
            
            logger.info("Detected shell for container %s: %s", container_name, detected_shell)
            return DetectShellResponse(shell=detected_shell)
        
        except Exception as e:
            logger.warning("Could not detect shell for container %s: %s", container_name, str(e))
            # Return default shell on detection error, but log it
            logger.warning("Returning default shell /bin/sh for container %s", container_name)
            return DetectShellResponse(shell="/bin/sh")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in detect_shell: %s", str(e))
        raise HTTPException(500, f"Error detecting shell: {str(e)}")


@router.get(
    "/api/logs",
    summary="Get Server Logs",
    description="Retrieve server logs in plain text",
    responses={
        200: {"description": "Server logs"}
    }
)
async def get_server_logs():
    """
    Get the server logs.
    
    Returns the content of the web server log file.
    """
    log_path = Path("venv/web.log")
    if log_path.exists():
        with log_path.open("r") as f:
            logs = f.read()
        return PlainTextResponse(logs)
    return PlainTextResponse("No logs found")


@router.get(
    "/api/backups",
    response_model=BackupsList,
    summary="List Backups",
    description="Get list of available backups",
    responses={
        200: {"description": "List of backups"},
        500: {"description": "Server error"}
    }
)
async def get_backups():
    """
    Get list of all available backups.
    
    Returns information about backup files in the shared directory.
    """
    try:
        backups = []
        backup_dir = SHARED_DIR / "backups"
        
        if not backup_dir.exists():
            return BackupsList(backups=[])
        
        for category_dir in backup_dir.iterdir():
            if category_dir.is_dir():
                for file_path in category_dir.iterdir():
                    if file_path.is_file():
                        try:
                            stat = file_path.stat()
                            backups.append(BackupInfo(
                                category=category_dir.name,
                                file=file_path.name,
                                size=stat.st_size,
                                modified=stat.st_mtime
                            ))
                        except Exception as e:
                            logger.error("Error reading file %s: %s", file_path, str(e))
        
        return BackupsList(backups=backups)
    except Exception as e:
        logger.error("Error listing backups: %s", str(e))
        raise HTTPException(500, f"Error listing backups: {str(e)}")


@router.get(
    "/api/download-backup/{category}/{filename}",
    summary="Download Backup",
    description="Download a specific backup file",
    responses={
        200: {"description": "Backup file"},
        404: {"description": "Backup not found"},
        500: {"description": "Server error"}
    }
)
async def download_backup(
    category: str = PathParam(..., description="Backup category"),
    filename: str = PathParam(..., description="Backup filename")
):
    """
    Download a backup file.
    
    **Path Parameters:**
    - `category`: Category directory name
    - `filename`: Filename to download
    """
    backup_path = SHARED_DIR / "backups" / category / filename
    if not backup_path.exists():
        raise HTTPException(404, "Backup not found")
    return FileResponse(str(backup_path), filename=filename, media_type="application/octet-stream")


@router.get(
    "/debug-config",
    response_model=DebugConfig,
    summary="Debug Configuration",
    description="Debug endpoint to inspect configuration",
    tags=["debug"]
)
async def debug_config():
    """
    Debug endpoint for configuration inspection.
    
    Shows loaded config files, images, and groups.
    Useful for troubleshooting configuration issues.
    """
    try:
        config_files = []
        
        if CUSTOM_CONFIG_DIR.exists():
            for config_file in CUSTOM_CONFIG_DIR.glob("*.yml"):
                try:
                    with open(config_file, "r") as f:
                        content = f.read()
                        config_files.append({
                            "file": config_file.name,
                            "exists": True,
                            "content_preview": content[:500] + "..." if len(content) > 500 else content
                        })
                except Exception as e:
                    config_files.append({"file": config_file.name, "exists": True, "error": str(e)})
        
        config_data = load_config()
        
        return DebugConfig(
            custom_dir=str(CUSTOM_CONFIG_DIR),
            custom_files=config_files,
            loaded_images=list(config_data["images"].keys())[:10],
            total_loaded=len(config_data["images"]),
            groups=list(config_data["groups"].keys())
        )
    except Exception as e:
        logger.error("Error in debug_config: %s", str(e))
        raise HTTPException(500, f"Debug error: {str(e)}")


def cleanup_temp_files(age_hours: int = 1) -> int:
    """Cleanup old temp files and return count removed"""
    temp_dir = tempfile.gettempdir()
    cutoff = datetime.now() - timedelta(hours=age_hours)
    removed_count = 0
    
    for temp_file in glob.glob(f"{temp_dir}/*.yml"):
        try:
            if os.path.getmtime(temp_file) < cutoff.timestamp():
                os.unlink(temp_file)
                logger.info("Deleted old temp file: %s", temp_file)
                removed_count += 1
        except Exception as e:
            logger.warning("Error deleting temp file %s: %s", temp_file, str(e))
    
    return removed_count