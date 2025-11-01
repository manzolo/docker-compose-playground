"""
Container Name Utilities - Standardize container naming

Backend (Docker) uses full names with 'playground-' prefix
Frontend displays short names without prefix

Examples:
    - Full name: "playground-php-8.4"
    - Display name: "php-8.4"
"""

PREFIX = "playground-"


def to_full_name(name: str) -> str:
    """
    Convert to full Docker container name (with playground- prefix)

    Args:
        name: Container name (with or without prefix)

    Returns:
        Full container name with playground- prefix

    Examples:
        >>> to_full_name("php-8.4")
        'playground-php-8.4'
        >>> to_full_name("playground-php-8.4")
        'playground-php-8.4'
    """
    if not name:
        return ""
    return name if name.startswith(PREFIX) else f"{PREFIX}{name}"


def to_display_name(name: str) -> str:
    """
    Convert to display name (without playground- prefix)

    Args:
        name: Container name (with or without prefix)

    Returns:
        Display name without playground- prefix

    Examples:
        >>> to_display_name("playground-php-8.4")
        'php-8.4'
        >>> to_display_name("php-8.4")
        'php-8.4'
    """
    if not name:
        return ""
    return name.removeprefix(PREFIX)


def has_prefix(name: str) -> bool:
    """
    Check if name has playground- prefix

    Args:
        name: Container name to check

    Returns:
        True if name starts with playground-

    Examples:
        >>> has_prefix("playground-php-8.4")
        True
        >>> has_prefix("php-8.4")
        False
    """
    if not name:
        return False
    return name.startswith(PREFIX)


def normalize(name: str) -> str:
    """
    Normalize name to display format (ensures consistent format)
    Removes prefix if present

    Args:
        name: Container name

    Returns:
        Normalized display name

    Examples:
        >>> normalize("playground-php-8.4")
        'php-8.4'
        >>> normalize("php-8.4")
        'php-8.4'
    """
    return to_display_name(name)


def to_image_name(container_name: str) -> str:
    """
    Extract image name from container name
    Alias for to_display_name for clarity in some contexts

    Args:
        container_name: Full or partial container name

    Returns:
        Image/display name

    Examples:
        >>> to_image_name("playground-php-8.4")
        'php-8.4'
    """
    return to_display_name(container_name)
