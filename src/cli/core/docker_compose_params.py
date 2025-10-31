"""
Docker Compose parameter definitions and validation

This module defines all Docker Compose parameters supported in playground
configuration files and validates them against the Docker SDK specification.
"""

from typing import Dict, Any, List, Tuple, Set

# =============================================================================
# DOCKER COMPOSE PARAMETER DEFINITIONS
# =============================================================================

# Parameters that map directly from Docker Compose to Docker SDK
# Format: {compose_key: (sdk_key, type, description)}
DOCKER_COMPOSE_PARAMS = {
    # Network and Connectivity
    "extra_hosts": ("extra_hosts", dict, "Add hostname mappings (hostname: ip)"),
    "dns": ("dns", list, "Custom DNS servers"),
    "dns_search": ("dns_search", list, "Custom DNS search domains"),
    "mac_address": ("mac_address", str, "Container MAC address"),
    "hostname": ("hostname", str, "Container host name"),

    # Security
    "cap_add": ("cap_add", list, "Add Linux capabilities"),
    "cap_drop": ("cap_drop", list, "Drop Linux capabilities"),
    "privileged": ("privileged", bool, "Give extended privileges to this container"),
    "security_opt": ("security_opt", list, "Security options (e.g., seccomp, apparmor)"),
    "user": ("user", str, "Username or UID (format: <name|uid>[:<group|gid>])"),

    # Resources
    "mem_limit": ("mem_limit", (str, int), "Memory limit (e.g., '512m', '2g')"),
    "memswap_limit": ("memswap_limit", (str, int), "Swap limit (e.g., '1g')"),
    "shm_size": ("shm_size", (str, int), "Size of /dev/shm (e.g., '64m')"),
    "cpu_shares": ("cpu_shares", int, "CPU shares (relative weight)"),
    "cpuset_cpus": ("cpuset_cpus", str, "CPUs in which to allow execution (e.g., '0-3', '0,1')"),
    "cpu_quota": ("cpu_quota", int, "Limit CPU CFS quota"),
    "cpu_period": ("cpu_period", int, "Limit CPU CFS period"),
    "pids_limit": ("pids_limit", int, "Tune container pids limit"),

    # Process Management
    "oom_kill_disable": ("oom_kill_disable", bool, "Disable OOM Killer"),
    "oom_score_adj": ("oom_score_adj", int, "Tune container's OOM preferences (-1000 to 1000)"),
    "pid_mode": ("pid_mode", str, "PID namespace to use (e.g., 'host')"),
    "ipc_mode": ("ipc_mode", str, "IPC mode to use (e.g., 'host', 'shareable')"),
    "init": ("init", bool, "Run an init inside the container"),

    # Storage
    "tmpfs": ("tmpfs", dict, "Mount tmpfs directories (path: options)"),
    "devices": ("devices", list, "List of device mappings (e.g., '/dev/sda:/dev/xvda:rwm')"),
    "device_read_bps": ("device_read_bps", list, "Limit read rate from device"),
    "device_write_bps": ("device_write_bps", list, "Limit write rate to device"),
    "device_read_iops": ("device_read_iops", list, "Limit read rate (IO per second) from device"),
    "device_write_iops": ("device_write_iops", list, "Limit write rate (IO per second) to device"),

    # System
    "sysctls": ("sysctls", dict, "Kernel parameters (key: value)"),
    "ulimits": ("ulimits", list, "Ulimit options"),
    "read_only": ("read_only", bool, "Mount container's root filesystem as read only"),
    "working_dir": ("working_dir", str, "Working directory inside the container"),
    "runtime": ("runtime", str, "Runtime to use for this container (e.g., 'nvidia')"),

    # Health and Monitoring
    "healthcheck": ("healthcheck", dict, "Healthcheck configuration"),

    # Restart Policy
    "restart_policy": ("restart_policy", dict, "Restart policy configuration"),

    # Logging
    "log_config": ("log_config", dict, "Logging configuration"),

    # Groups and Namespaces
    "group_add": ("group_add", list, "Additional groups for the container user"),
    "userns_mode": ("userns_mode", str, "User namespace to use"),

    # Network Mode
    "network_mode": ("network_mode", str, "Network mode (e.g., 'bridge', 'host', 'none')"),

    # Storage Driver
    "storage_opt": ("storage_opt", dict, "Storage driver options"),
}

# Parameters that are already handled by playground (don't need to be passed through)
RESERVED_PARAMS = {
    "image",           # Handled by playground
    "container_name",  # Generated automatically
    "name",            # Generated automatically
    "ports",           # Handled by playground
    "volumes",         # Handled by playground
    "environment",     # Handled by playground
    "command",         # Mapped to keep_alive_cmd
    "keep_alive_cmd",  # Playground-specific
    "category",        # Playground-specific
    "description",     # Playground-specific
    "shell",           # Playground-specific
    "motd",            # Playground-specific
    "scripts",         # Playground-specific
    "labels",          # Partially handled (playground.managed label)
    "networks",        # Handled by playground (playground-network)
    "network",         # Handled by playground
    "detach",          # Always true in playground
    "stdin_open",      # Always true in playground
    "tty",             # Always true in playground
}

# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_docker_compose_key(key: str) -> Tuple[bool, str]:
    """Validate if a key is a valid Docker Compose parameter

    Args:
        key: Parameter key to validate

    Returns:
        Tuple[bool, str]: (is_valid, message)
            - is_valid: True if valid, False if invalid
            - message: Empty if valid, warning/error message if invalid
    """
    # Check if it's a reserved parameter (already handled)
    if key in RESERVED_PARAMS:
        return True, ""

    # Check if it's a supported Docker Compose parameter
    if key in DOCKER_COMPOSE_PARAMS:
        return True, ""

    # Unknown parameter
    return False, f"Unknown parameter '{key}' - not a standard Docker Compose option"


def validate_parameter_value(key: str, value: Any) -> Tuple[bool, str]:
    """Validate if a parameter value has the correct type

    Args:
        key: Parameter key
        value: Parameter value to validate

    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if key not in DOCKER_COMPOSE_PARAMS:
        return True, ""  # Skip validation for unknown params

    sdk_key, expected_type, description = DOCKER_COMPOSE_PARAMS[key]

    # Check type
    if isinstance(expected_type, tuple):
        # Multiple types accepted
        if not isinstance(value, expected_type):
            return False, f"Parameter '{key}' expects type {expected_type}, got {type(value).__name__}"
    else:
        # Single type
        if not isinstance(value, expected_type):
            return False, f"Parameter '{key}' expects type {expected_type.__name__}, got {type(value).__name__}"

    return True, ""


def extract_docker_params(img_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract Docker SDK parameters from image configuration

    Args:
        img_data: Image configuration dictionary

    Returns:
        Dict[str, Any]: Dictionary of parameters to pass to docker.containers.run()
    """
    docker_params = {}

    for key, value in img_data.items():
        # Skip reserved parameters
        if key in RESERVED_PARAMS:
            continue

        # Check if it's a supported Docker Compose parameter
        if key in DOCKER_COMPOSE_PARAMS:
            sdk_key, expected_type, description = DOCKER_COMPOSE_PARAMS[key]

            # Validate type
            is_valid, error_msg = validate_parameter_value(key, value)
            if not is_valid:
                # Log warning but don't fail
                print(f"Warning: {error_msg}")
                continue

            # Add to docker params with SDK key name
            docker_params[sdk_key] = value

    return docker_params


def validate_all_params(img_data: Dict[str, Any], strict: bool = False) -> Tuple[bool, List[str], List[str]]:
    """Validate all parameters in image configuration

    Args:
        img_data: Image configuration dictionary
        strict: If True, unknown parameters cause validation to fail

    Returns:
        Tuple[bool, List[str], List[str]]: (is_valid, errors, warnings)
    """
    errors = []
    warnings = []

    for key, value in img_data.items():
        # Check if key is valid
        is_valid, message = validate_docker_compose_key(key)

        if not is_valid:
            if strict:
                errors.append(message)
            else:
                warnings.append(message)
            continue

        # Validate value type
        is_valid, error_msg = validate_parameter_value(key, value)
        if not is_valid:
            errors.append(error_msg)

    return len(errors) == 0, errors, warnings


def get_supported_params() -> Dict[str, str]:
    """Get all supported Docker Compose parameters with descriptions

    Returns:
        Dict[str, str]: Dictionary mapping parameter names to descriptions
    """
    return {
        key: description
        for key, (_, _, description) in DOCKER_COMPOSE_PARAMS.items()
    }


def get_param_type(key: str) -> str:
    """Get expected type for a parameter

    Args:
        key: Parameter key

    Returns:
        str: Type description (e.g., 'dict', 'list', 'str', 'bool', 'int')
    """
    if key not in DOCKER_COMPOSE_PARAMS:
        return "unknown"

    _, expected_type, _ = DOCKER_COMPOSE_PARAMS[key]

    if isinstance(expected_type, tuple):
        types = [t.__name__ for t in expected_type]
        return " or ".join(types)
    else:
        return expected_type.__name__
