"""
Volume management for Docker containers
Handles named volumes, bind mounts, and file mounts
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from rich.console import Console

console = Console()

# Get base path
BASE_PATH = Path(__file__).parent.parent.parent.parent


@dataclass
class Volume:
    """Represents a volume configuration"""
    name: str = ""
    path: str = ""
    volume_type: str = "named"
    host: str = ""
    readonly: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Volume':
        """Create Volume from config dict"""
        if isinstance(data, dict):
            return cls(
                name=data.get('name', ''),
                path=data.get('path', ''),
                volume_type=data.get('type', 'named'),
                host=data.get('host', ''),
                readonly=data.get('readonly', False)
            )
        return None
    
    def validate(self) -> Tuple[bool, str]:
        """Validate volume configuration"""
        if not self.path:
            return False, "Volume path is required"
        
        if self.volume_type == 'named':
            if not self.name:
                return False, "Named volume requires 'name' field"
        elif self.volume_type in ('bind', 'file'):
            if not self.host:
                return False, f"{self.volume_type} volume requires 'host' field"
        else:
            return False, f"Unknown volume type: {self.volume_type}"
        
        return True, ""
    
    def prepare(self) -> Tuple[bool, str]:
        """Prepare volume (create directories/files if needed)"""
        if self.volume_type == 'named':
            # Named volumes are managed by Docker
            return True, ""

        # Convert relative paths to absolute
        host_path = self.host
        if not host_path.startswith('/'):
            host_path = os.path.join(str(BASE_PATH), host_path)

        path_obj = Path(host_path)

        try:
            if self.volume_type == 'bind':
                # Check if directory already exists
                if path_obj.exists():
                    if path_obj.is_dir():
                        return True, f"Using existing directory: {host_path}"
                    else:
                        return False, f"Path exists but is not a directory: {host_path}"
                # Create directory
                path_obj.mkdir(parents=True, exist_ok=True)
                return True, f"Created bind mount directory: {host_path}"

            elif self.volume_type == 'file':
                # Check if file already exists
                if path_obj.exists():
                    if path_obj.is_file():
                        return True, f"Using existing file: {host_path}"
                    else:
                        return False, f"Path exists but is not a file: {host_path}"
                # Create file
                path_obj.parent.mkdir(parents=True, exist_ok=True)
                path_obj.touch(exist_ok=True)
                return True, f"Created file mount: {host_path}"

        except Exception as e:
            return False, f"Failed to prepare volume: {str(e)}"

        return True, ""
    
    def to_docker_compose(self) -> str:
        """Convert to docker-compose volume string"""
        if self.volume_type == 'named':
            volume_str = f"{self.name}:{self.path}"
        elif self.volume_type in ('bind', 'file'):
            host_path = self.host
            if not host_path.startswith('/'):
                host_path = os.path.join(str(BASE_PATH), host_path)
            volume_str = f"{host_path}:{self.path}"
        else:
            return ""
        
        if self.readonly:
            volume_str += ":ro"
        
        return volume_str
    
    def __str__(self) -> str:
        """String representation"""
        if self.volume_type == 'named':
            return f"[named] {self.name} → {self.path}"
        elif self.volume_type == 'bind':
            return f"[bind] {self.host} → {self.path}"
        elif self.volume_type == 'file':
            return f"[file] {self.host} → {self.path}"
        return ""


class VolumeManager:
    """Manages container volumes"""
    
    def __init__(self):
        self.volumes: List[Volume] = []
    
    def add_volume(self, volume_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Add a volume from config"""
        volume = Volume.from_dict(volume_data)
        
        if not volume:
            return False, "Invalid volume configuration"
        
        # Validate
        is_valid, error_msg = volume.validate()
        if not is_valid:
            return False, error_msg
        
        # Prepare
        success, prep_msg = volume.prepare()
        if not success:
            return False, prep_msg
        
        self.volumes.append(volume)
        return True, prep_msg
    
    def add_volumes_from_config(self, volumes_config: List[Dict]) -> Tuple[int, List[str]]:
        """Add multiple volumes from config"""
        added = 0
        errors = []
        
        if not volumes_config:
            return 0, []
        
        for vol_data in volumes_config:
            success, msg = self.add_volume(vol_data)
            if success:
                added += 1
            else:
                errors.append(msg)
        
        return added, errors
    
    def get_compose_volumes(self) -> List[str]:
        """Get volumes in docker-compose format"""
        return [v.to_docker_compose() for v in self.volumes]
    
    def get_named_volumes(self) -> Dict[str, str]:
        """Get named volumes for compose file top-level definition"""
        named = {}
        for v in self.volumes:
            if v.volume_type == 'named':
                named[v.name] = {}
        return named
    
    def list_volumes(self) -> List[str]:
        """Get human-readable list of volumes"""
        return [str(v) for v in self.volumes]
    
    def clear(self):
        """Clear all volumes"""
        self.volumes = []


def parse_volume_string(volume_str: str) -> Dict[str, Any]:
    """
    Parse volume string from command line
    Format: type:host:container[:ro]
    Examples:
      - named:nginx-config:/etc/nginx
      - bind:./configs/nginx:/etc/nginx/conf.d
      - bind:./configs/nginx:/etc/nginx/conf.d:ro
      - file:./nginx.conf:/etc/nginx/nginx.conf:ro
    """
    parts = volume_str.split(':')
    
    if len(parts) < 3:
        return None
    
    vol_type = parts[0]
    host = parts[1]
    container = parts[2]
    readonly = len(parts) > 3 and parts[3] == 'ro'
    
    if vol_type == 'named':
        return {
            'type': 'named',
            'name': host,
            'path': container,
            'readonly': readonly
        }
    elif vol_type in ('bind', 'file'):
        return {
            'type': vol_type,
            'host': host,
            'path': container,
            'readonly': readonly
        }
    
    return None


def validate_and_prepare_volumes(volumes_config: List[Dict]) -> Tuple[bool, VolumeManager, List[str]]:
    """
    Validate and prepare all volumes
    Returns: (success: bool, manager: VolumeManager, errors: List[str])
    """
    manager = VolumeManager()
    added, errors = manager.add_volumes_from_config(volumes_config)
    
    if errors:
        return False, manager, errors
    
    return True, manager, []