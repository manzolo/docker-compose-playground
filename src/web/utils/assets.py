"""
Asset versioning for cache busting.

Generates versioned URLs for static assets based on file content hash.
"""
import hashlib
import os
from pathlib import Path
from typing import Dict, Optional

class AssetVersionManager:
    """Manages versioning for static assets using content hashing."""

    def __init__(self, static_dir: str):
        """
        Initialize asset version manager.

        Args:
            static_dir: Path to static files directory
        """
        self.static_dir = Path(static_dir)
        self._cache: Dict[str, str] = {}
        self._enabled = True

    def get_version(self, asset_path: str) -> str:
        """
        Get version hash for an asset file.

        Args:
            asset_path: Relative path to asset (e.g., 'css/base.css')

        Returns:
            8-character hash of file content, or empty string if file not found
        """
        # Check cache first
        if asset_path in self._cache:
            return self._cache[asset_path]

        # Calculate hash
        full_path = self.static_dir / asset_path

        if not full_path.exists():
            return ""

        try:
            with open(full_path, 'rb') as f:
                content = f.read()
                hash_obj = hashlib.md5(content)
                version = hash_obj.hexdigest()[:8]

                # Cache the result
                self._cache[asset_path] = version
                return version
        except Exception:
            return ""

    def get_versioned_url(self, asset_path: str) -> str:
        """
        Get versioned URL for an asset.

        Args:
            asset_path: Relative path to asset (e.g., 'css/base.css')

        Returns:
            URL with version query parameter (e.g., '/static/css/base.css?v=abc12345')
        """
        if not self._enabled:
            return f"/static/{asset_path}"

        version = self.get_version(asset_path)

        if version:
            return f"/static/{asset_path}?v={version}"
        else:
            return f"/static/{asset_path}"

    def clear_cache(self):
        """Clear the version cache. Useful in development."""
        self._cache.clear()

    def disable(self):
        """Disable versioning (for development)."""
        self._enabled = False

    def enable(self):
        """Enable versioning (for production)."""
        self._enabled = True


# Global instance
_asset_manager: Optional[AssetVersionManager] = None


def init_asset_manager(static_dir: str) -> AssetVersionManager:
    """
    Initialize global asset manager.

    Args:
        static_dir: Path to static files directory

    Returns:
        Initialized AssetVersionManager instance
    """
    global _asset_manager
    _asset_manager = AssetVersionManager(static_dir)
    return _asset_manager


def get_asset_manager() -> Optional[AssetVersionManager]:
    """Get global asset manager instance."""
    return _asset_manager


def asset_url(asset_path: str) -> str:
    """
    Get versioned URL for an asset (template helper).

    Args:
        asset_path: Relative path to asset (e.g., 'css/base.css')

    Returns:
        Versioned URL
    """
    if _asset_manager:
        return _asset_manager.get_versioned_url(asset_path)
    else:
        return f"/static/{asset_path}"
