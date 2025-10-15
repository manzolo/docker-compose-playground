"""
CLI Core Package
Configuration and Docker operations
"""

from .config import load_config, load_groups, get_image_config
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
    docker_client
)

__all__ = [
    'load_config',
    'load_groups',
    'get_image_config',
    'ensure_network',
    'get_playground_containers',
    'get_container',
    'start_container',
    'stop_container',
    'restart_container',
    'get_container_logs',
    'get_running_containers_dict',
    'remove_all_containers',
    'docker_client'
]