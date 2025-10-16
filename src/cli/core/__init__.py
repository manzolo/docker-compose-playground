"""
CLI Core Package
Configuration and Docker operations with volume support
"""

from .config import (
    load_config,
    load_groups,
    get_image_config,
    validate_image_config,
    list_all_images,
    list_images_by_category,
    get_all_categories
)
from .docker_ops import (
    ensure_network,
    get_playground_containers,
    get_container,
    start_container,
    stop_container,
    restart_container,
    get_container_logs,
    get_running_containers_dict,
    remove_all_containers,
    docker_client,
    get_container_volumes,
    prepare_volumes,
    ensure_named_volumes
)
from .volumes import (
    Volume,
    VolumeManager,
    parse_volume_string,
    validate_and_prepare_volumes
)

__all__ = [
    # Config
    'load_config',
    'load_groups',
    'get_image_config',
    'validate_image_config',
    'list_all_images',
    'list_images_by_category',
    'get_all_categories',
    
    # Docker operations
    'ensure_network',
    'get_playground_containers',
    'get_container',
    'start_container',
    'stop_container',
    'restart_container',
    'get_container_logs',
    'get_running_containers_dict',
    'remove_all_containers',
    'docker_client',
    'get_container_volumes',
    'prepare_volumes',
    'ensure_named_volumes',
    
    # Volume management
    'Volume',
    'VolumeManager',
    'parse_volume_string',
    'validate_and_prepare_volumes'
]