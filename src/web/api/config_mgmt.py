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
from src.web.core.logging_config import get_logger
import docker
import re
from typing import Tuple

from src.web.core.config import load_config, CUSTOM_CONFIG_DIR, BASE_DIR
from src.web.core.docker import docker_client, SHARED_DIR

router = APIRouter()
logger = get_logger(__name__)

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
    description="Add a new container configuration with full validation",
    responses={
        201: {"description": "Container added successfully"},
        400: {"description": "Invalid request or validation failed"},
        409: {"description": "Container already exists"},
        500: {"description": "Server error"}
    }
)

async def add_container_config(request: AddContainerRequest):
    """
    Add a new container configuration with comprehensive validation.
    
    **Request Body:**
    - `name`: Container name (alphanumeric, hyphens, underscores; 1-50 chars)
    - `image`: Docker image (e.g., ubuntu:22.04, docker.io/ubuntu:latest)
    - `category`: Category (1-30 chars, alphanumeric + spaces/hyphens)
    - `description`: Description (max 500 chars)
    - `keep_alive_cmd`: Command to keep container running
    - `shell`: Shell path (e.g., /bin/bash)
    - `ports`: Port mappings (list of "host:container")
    - `environment`: Environment variables (KEY=VALUE, one per line)
    - `motd`: Message of the day
    
    **Validation checks:**
    - Container name format and uniqueness
    - Docker image format
    - Category and description validity
    - Port range and format
    - Environment variable syntax
    - Shell path format
    
    **Response:**
    - `status`: "success" if created
    - `message`: Confirmation message
    - `name`: Container name
    - `file`: Path to created config file
    
    **Status Codes:**
    - 201: Created successfully
    - 400: Validation failed
    - 409: Container already exists
    - 500: Server error
    """
    try:
        # Validate container name
        is_valid, error_msg = validate_container_name(request.name)
        if not is_valid:
            logger.warning("Invalid container name: %s - %s", request.name, error_msg)
            raise HTTPException(400, f"Invalid container name: {error_msg}")
        
        # Validate Docker image
        is_valid, error_msg = validate_docker_image(request.image)
        if not is_valid:
            logger.warning("Invalid Docker image: %s - %s", request.image, error_msg)
            raise HTTPException(400, f"Invalid Docker image: {error_msg}")
        
        # Validate category
        is_valid, error_msg = validate_category(request.category)
        if not is_valid:
            logger.warning("Invalid category: %s - %s", request.category, error_msg)
            raise HTTPException(400, f"Invalid category: {error_msg}")
        
        # Validate description
        is_valid, error_msg = validate_description(request.description)
        if not is_valid:
            logger.warning("Invalid description - %s", error_msg)
            raise HTTPException(400, f"Invalid description: {error_msg}")
        
        # Validate shell
        is_valid, error_msg = validate_shell(request.shell)
        if not is_valid:
            logger.warning("Invalid shell: %s - %s", request.shell, error_msg)
            raise HTTPException(400, f"Invalid shell: {error_msg}")
        
        # Validate ports
        is_valid, error_msg = validate_ports(request.ports)
        if not is_valid:
            logger.warning("Invalid ports: %s", error_msg)
            raise HTTPException(400, f"Invalid ports: {error_msg}")
        
        # Validate environment variables
        is_valid, error_msg, env_dict = validate_environment_variables(request.environment)
        if not is_valid:
            logger.warning("Invalid environment variables: %s", error_msg)
            raise HTTPException(400, f"Invalid environment: {error_msg}")
        
        # Check if container already exists
        config_data = load_config()
        if request.name in config_data["images"]:
            logger.warning("Container already exists: %s", request.name)
            raise HTTPException(409, f"Container '{request.name}' already exists")
        
        # Build configuration
        new_config = {
            "images": {
                request.name: {
                    "image": request.image,
                    "category": request.category,
                    "description": request.description,
                    "keep_alive_cmd": request.keep_alive_cmd,
                    "shell": request.shell,
                    "ports": request.ports,
                    "environment": env_dict
                }
            }
        }
        
        # Add MOTD if provided
        if request.motd and len(request.motd) <= 5000:  # Max 5000 chars for MOTD
            new_config['images'][request.name]['motd'] = request.motd
        elif request.motd:
            logger.warning("MOTD too long for %s", request.name)
            raise HTTPException(400, "MOTD cannot exceed 5000 characters")
        
        # Create config file with safe name
        safe_name = request.name.replace('_', '-').lower()
        config_file_path = CUSTOM_CONFIG_DIR / f"{safe_name}.yml"
        
        if config_file_path.exists():
            logger.error("Config file already exists: %s", config_file_path)
            raise HTTPException(409, f"Configuration file for '{request.name}' already exists")
        
        # Write YAML
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
        
        logger.info("Successfully added container config: %s (file: %s)", request.name, config_file_path)
        
        return ContainerConfigResponse(
            status="success",
            message=f"Container '{request.name}' added successfully with {len(env_dict)} environment variables",
            name=request.name,
            file=f"custom.d/{safe_name}.yml"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error adding container: %s", str(e), exc_info=True)
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
    curl -X POST http://localhost:${PORT:-8000}/api/validate-image \\
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
    curl -X POST http://localhost:${PORT:-8000}/api/detect-shell \\
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
        backup_dir = SHARED_DIR / "data" / "backups"
        
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
    backup_path = SHARED_DIR / "data" / "backups" / category / filename
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


def validate_container_name(name: str) -> Tuple[bool, str]:
    """Validate container name format
    
    Rules:
    - Alphanumeric, hyphens, underscores only
    - Start with letter or digit
    - 1-50 characters
    - No consecutive hyphens or underscores
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not name:
        return False, "Container name cannot be empty"
    
    if len(name) > 50:
        return False, "Container name cannot exceed 50 characters"
    
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$', name) and len(name) > 1:
        return False, "Container name must start/end with alphanumeric, contain only [a-z0-9_-]"
    
    if re.search(r'[-_]{2,}', name):
        return False, "Container name cannot have consecutive hyphens or underscores"
    
    return True, ""


def validate_docker_image(image: str) -> Tuple[bool, str]:
    """Validate Docker image name format
    
    Accepts formats:
    - ubuntu
    - ubuntu:22.04
    - docker.io/ubuntu:latest
    - gcr.io/project/image:tag
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not image or not isinstance(image, str):
        return False, "Image name cannot be empty"
    
    if len(image) > 255:
        return False, "Image name too long (max 255 chars)"
    
    # Basic pattern: [registry/]name[:tag]
    pattern = r'^([a-z0-9\-._]+/)?[a-z0-9\-._]+(@[a-z0-9:._-]+)?(:[\w.-]+)?$'
    if not re.match(pattern, image, re.IGNORECASE):
        return False, "Invalid Docker image format"
    
    return True, ""


def validate_category(category: str) -> Tuple[bool, str]:
    """Validate category name
    
    Rules:
    - Alphanumeric, spaces, hyphens only
    - 1-30 characters
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not category or not isinstance(category, str):
        return False, "Category cannot be empty"
    
    if len(category) > 30:
        return False, "Category name cannot exceed 30 characters"
    
    if not re.match(r'^[a-zA-Z0-9\s\-]+$', category):
        return False, "Category can only contain letters, numbers, spaces, and hyphens"
    
    return True, ""


def validate_description(desc: str) -> Tuple[bool, str]:
    """Validate description field
    
    Rules:
    - Max 500 characters
    - No null bytes
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not isinstance(desc, str):
        return False, "Description must be a string"
    
    if len(desc) > 500:
        return False, "Description cannot exceed 500 characters"
    
    if '\x00' in desc:
        return False, "Description contains invalid characters"
    
    return True, ""


def validate_shell(shell: str) -> Tuple[bool, str]:
    """Validate shell path
    
    Rules:
    - Must start with /
    - Only alphanumeric and slashes
    - Max 50 characters
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not shell or not isinstance(shell, str):
        return False, "Shell cannot be empty"
    
    if len(shell) > 50:
        return False, "Shell path too long"
    
    if not shell.startswith('/'):
        return False, "Shell path must start with /"
    
    if not re.match(r'^/[a-zA-Z0-9/_-]+$', shell):
        return False, "Shell path contains invalid characters"
    
    return True, ""


def validate_ports(ports: list) -> Tuple[bool, str]:
    """Validate port mappings
    
    Format: "host_port:container_port" or "container_port"
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if not isinstance(ports, list):
        return False, "Ports must be a list"
    
    if len(ports) > 20:
        return False, "Cannot expose more than 20 ports"
    
    for port_mapping in ports:
        if not isinstance(port_mapping, (int, str)):
            return False, f"Invalid port format: {port_mapping}"
        
        port_str = str(port_mapping)
        
        if ':' in port_str:
            parts = port_str.split(':')
            if len(parts) != 2:
                return False, f"Invalid port mapping: {port_mapping}"
            
            try:
                host_port = int(parts[0])
                container_port = int(parts[1])
                
                if host_port < 1 or host_port > 65535:
                    return False, f"Host port out of range: {host_port}"
                
                if container_port < 1 or container_port > 65535:
                    return False, f"Container port out of range: {container_port}"
            except ValueError:
                return False, f"Ports must be numeric: {port_mapping}"
        else:
            try:
                port = int(port_str)
                if port < 1 or port > 65535:
                    return False, f"Port out of range: {port}"
            except ValueError:
                return False, f"Port must be numeric: {port_mapping}"
    
    return True, ""


def validate_environment_variables(env_string: str) -> Tuple[bool, str, dict]:
    """Validate environment variables format
    
    Format: KEY=VALUE, one per line
    
    Returns:
        Tuple[bool, str, dict]: (is_valid, error_message, parsed_env_dict)
    """
    if not env_string:
        return True, "", {}
    
    if not isinstance(env_string, str):
        return False, "Environment must be a string", {}
    
    env_dict = {}
    lines = env_string.strip().split('\n')
    
    if len(lines) > 50:
        return False, "Cannot set more than 50 environment variables", {}
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith('#'):  # Allow comments
            continue
        
        if '=' not in line:
            return False, f"Line {i}: Invalid format, must be KEY=VALUE", {}
        
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        # Validate key
        if not re.match(r'^[A-Z_][A-Z0-9_]*$', key):
            return False, f"Line {i}: Invalid variable name '{key}' (must be UPPERCASE_SNAKE_CASE)", {}
        
        if len(key) > 50:
            return False, f"Line {i}: Variable name too long", {}
        
        if len(value) > 500:
            return False, f"Line {i}: Variable value too long", {}
        
        env_dict[key] = value
    
    return True, "", env_dict

