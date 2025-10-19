from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from pathlib import Path
from datetime import datetime, timedelta
import yaml
import tempfile
import os
import glob
import logging

from src.web.core.config import load_config, CUSTOM_CONFIG_DIR, BASE_DIR
from src.web.core.docker import docker_client, SHARED_DIR

router = APIRouter()
logger = logging.getLogger("uvicorn")

# Ensure custom.d exists
CUSTOM_CONFIG_DIR.mkdir(exist_ok=True)


class CustomDumper(yaml.SafeDumper):
    """Custom YAML dumper for multiline strings"""
    def represent_str(self, data):
        if "\n" in data:
            return self.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return self.represent_scalar('tag:yaml.org,2002:str', data)

CustomDumper.add_representer(str, CustomDumper.represent_str)


@router.get("/api/export-config")
async def export_config():
    """Export configuration as YAML"""
    try:
        config_data = load_config()
        images = config_data["images"]
        
        config = {"images": images}
        yaml_content = yaml.dump(
            config,
            Dumper=CustomDumper,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            indent=2
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
        return FileResponse(
            path=temp_file_path,
            filename=filename,
            media_type="application/x-yaml",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error("Error exporting config: %s", str(e))
        raise HTTPException(500, f"Error exporting config: {str(e)}")


@router.post("/api/add-container")
async def add_container_config(request: Request):
    """Add new container configuration"""
    try:
        data = await request.json()
        
        required_fields = ['name', 'image', 'category', 'description']
        for field in required_fields:
            if not data.get(field):
                raise HTTPException(400, f"Missing required field: {field}")
        
        config_data = load_config()
        if data['name'] in config_data["images"]:
            raise HTTPException(400, f"Container '{data['name']}' already exists")
        
        new_config = {
            "images": {
                data['name']: {
                    "image": data['image'],
                    "category": data['category'],
                    "description": data['description'],
                    "keep_alive_cmd": data.get('keep_alive_cmd', 'tail -f /dev/null'),
                    "shell": data.get('shell', '/bin/bash'),
                    "ports": data.get('ports', []),
                    "environment": {}
                }
            }
        }
        
        if data.get('environment'):
            env_lines = data['environment'].strip().split('\n')
            for line in env_lines:
                if '=' in line:
                    key, value = line.split('=', 1)
                    new_config['images'][data['name']]['environment'][key.strip()] = value.strip()
        
        if data.get('motd'):
            new_config['images'][data['name']]['motd'] = data['motd']
        
        safe_name = data['name'].replace('_', '-').lower()
        config_file_path = CUSTOM_CONFIG_DIR / f"{safe_name}.yml"
        
        if config_file_path.exists():
            raise HTTPException(400, f"Configuration file for '{data['name']}' already exists")
        
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
        
        logger.info("Added new container config: %s", data['name'])
        
        return {
            "status": "success",
            "message": f"Container '{data['name']}' added successfully",
            "name": data['name'],
            "file": f"custom.d/{safe_name}.yml"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error adding container: %s", str(e))
        raise HTTPException(500, f"Failed to add container: {str(e)}")


@router.post("/api/validate-image")
async def validate_image(request: Request):
    """Validate Docker image"""
    try:
        data = await request.json()
        image_name = data.get('image')
        
        if not image_name:
            raise HTTPException(400, "Image name required")
        
        try:
            image = docker_client.images.pull(image_name)
            return {
                "exists": True,
                "id": image.id[:12],
                "tags": image.tags,
                "size": f"{image.attrs['Size'] / (1024*1024):.2f} MB",
                "created": image.attrs['Created'][:10]
            }
        except Exception as e:
            logger.warning("Image validation failed for %s: %s", image_name, str(e))
            return {"exists": False, "error": str(e)}
    
    except Exception as e:
        logger.error("Error validating image: %s", str(e))
        raise HTTPException(500, str(e))


@router.post("/api/detect-shell")
async def detect_shell(request: Request):
    """Detect available shell in image"""
    try:
        data = await request.json()
        image_name = data.get('image')
        
        if not image_name:
            raise HTTPException(400, "Image name required")
        
        shells = ['/bin/bash', '/bin/sh', '/bin/ash', '/usr/bin/bash']
        
        try:
            container = docker_client.containers.run(
                image_name,
                command='sleep 5',
                detach=True,
                remove=True
            )
            
            detected_shell = '/bin/sh'
            for shell in shells:
                try:
                    exit_code, _ = container.exec_run(f'test -f {shell}')
                    if exit_code == 0:
                        detected_shell = shell
                        break
                except:
                    continue
            
            container.stop()
            return {"shell": detected_shell}
        
        except Exception as e:
            logger.warning("Could not detect shell: %s", str(e))
            return {"shell": "/bin/sh"}
    
    except Exception as e:
        logger.error("Error detecting shell: %s", str(e))
        return {"shell": "/bin/sh"}


@router.get("/api/logs")
async def get_server_logs():
    """Get server logs"""
    log_path = Path("venv/web.log")
    if log_path.exists():
        with log_path.open("r") as f:
            logs = f.read()
        return PlainTextResponse(logs)
    return PlainTextResponse("No logs found")


@router.get("/api/backups")
async def get_backups():
    """Get list of backups"""
    try:
        backups = []
        backup_dir = SHARED_DIR / "backups"
        
        if not backup_dir.exists():
            return {"backups": []}
        
        for category_dir in backup_dir.iterdir():
            if category_dir.is_dir():
                for file_path in category_dir.iterdir():
                    if file_path.is_file():
                        try:
                            stat = file_path.stat()
                            backups.append({
                                "category": category_dir.name,
                                "file": file_path.name,
                                "size": stat.st_size,
                                "modified": stat.st_mtime
                            })
                        except Exception as e:
                            logger.error("Error reading file %s: %s", file_path, str(e))
        
        return {"backups": backups}
    except Exception as e:
        logger.error("Error listing backups: %s", str(e))
        raise HTTPException(500, str(e))


@router.get("/api/download-backup/{category}/{filename}")
async def download_backup(category: str, filename: str):
    """Download backup file"""
    backup_path = SHARED_DIR / "backups" / category / filename
    if not backup_path.exists():
        raise HTTPException(404, "Backup not found")
    return FileResponse(str(backup_path), filename=filename, media_type="application/octet-stream")


@router.get("/debug-config")
async def debug_config():
    """Debug endpoint for config"""
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
        
        return {
            "custom_dir": str(CUSTOM_CONFIG_DIR),
            "custom_files": config_files,
            "loaded_images": list(config_data["images"].keys())[:10],
            "total_loaded": len(config_data["images"]),
            "groups": list(config_data["groups"].keys())
        }
    except Exception as e:
        return {"error": str(e)}


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