# SEZIONI MODIFICATE PER core/config.py

"""Configuration loading and management with caching"""
from pathlib import Path
from typing import Dict, Any
import yaml
from fastapi import HTTPException
import logging
from functools import lru_cache
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from .logging_config import get_logger

logger = get_logger(__name__)

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent.parent
CONFIG_DIR = BASE_DIR / "config.d"
CUSTOM_CONFIG_DIR = BASE_DIR / "custom.d"
CONFIG_FILE = BASE_DIR / "config.yml"


# ============================================================
# CACHE CONFIGURATION
# ============================================================

class CacheConfig:
    """Configuration caching settings"""
    
    # Enable/disable caching
    ENABLE_CACHE = True
    
    # Cache invalidation
    MAX_CACHE_AGE_SECONDS = 300  # 5 minutes
    CHECK_FILE_CHANGES_INTERVAL = 5  # Check every 5 seconds
    
    # Cache stats
    ENABLE_CACHE_STATS = True


# ============================================================
# CACHE STATE
# ============================================================

class ConfigCache:
    """Cache state management for configuration"""
    
    def __init__(self):
        self.cached_config = None
        self.cache_time = None
        self.last_file_check = None
        self.file_mtimes = {}  # Track file modification times
        self.lock = threading.RLock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0
        }
        
        logger.info("ConfigCache initialized")
    
    def get(self) -> Dict[str, Any] | None:
        """Get cached config if valid
        
        Returns:
            dict or None: Cached config if valid, None if expired/invalid
        """
        with self.lock:
            if self.cached_config is None:
                return None
            
            # Check if cache is still valid
            if not self._is_cache_valid():
                logger.debug("Cache invalidated (expired or files changed)")
                self.stats["invalidations"] += 1
                self.cached_config = None
                return None
            
            self.stats["hits"] += 1
            return self.cached_config
    
    def set(self, config: Dict[str, Any]):
        """Set cache with current timestamp
        
        Args:
            config: Configuration dictionary to cache
        """
        with self.lock:
            self.cached_config = config
            self.cache_time = time.time()
            self.last_file_check = time.time()
            
            # Update file modification times
            self._update_file_mtimes()
            
            logger.debug("Config cached (%.1f seconds since last check)", 
                        time.time() - self.cache_time if self.cache_time else 0)
    
    def invalidate(self):
        """Manually invalidate cache"""
        with self.lock:
            if self.cached_config is not None:
                logger.info("Config cache manually invalidated")
                self.cached_config = None
                self.stats["invalidations"] += 1
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid
        
        Checks:
        1. Cache age < MAX_CACHE_AGE_SECONDS
        2. No file modifications detected
        
        Returns:
            bool: True if cache is valid
        """
        if self.cache_time is None:
            return False
        
        # Check age
        age = time.time() - self.cache_time
        if age > CacheConfig.MAX_CACHE_AGE_SECONDS:
            logger.debug("Cache expired (age: %.1fs)", age)
            return False
        
        # Check file changes (less frequently to avoid I/O)
        if self.last_file_check is not None:
            time_since_check = time.time() - self.last_file_check
            if time_since_check < CacheConfig.CHECK_FILE_CHANGES_INTERVAL:
                return True
        
        # Check if files have been modified
        if self._files_modified():
            logger.debug("Cache invalidated (files modified)")
            return False
        
        self.last_file_check = time.time()
        return True
    
    def _update_file_mtimes(self):
        """Update file modification times"""
        self.file_mtimes = {}
        
        # config.yml
        if CONFIG_FILE.exists():
            self.file_mtimes[str(CONFIG_FILE)] = CONFIG_FILE.stat().st_mtime
        
        # config.d files
        if CONFIG_DIR.exists():
            for f in CONFIG_DIR.glob("*.yml"):
                self.file_mtimes[str(f)] = f.stat().st_mtime
        
        # custom.d files
        if CUSTOM_CONFIG_DIR.exists():
            for f in CUSTOM_CONFIG_DIR.glob("*.yml"):
                self.file_mtimes[str(f)] = f.stat().st_mtime
    
    def _files_modified(self) -> bool:
        """Check if any config files have been modified
        
        Returns:
            bool: True if any file has changed
        """
        try:
            # Check main config
            if CONFIG_FILE.exists():
                current_mtime = CONFIG_FILE.stat().st_mtime
                if str(CONFIG_FILE) not in self.file_mtimes:
                    logger.debug("New file detected: %s", CONFIG_FILE)
                    return True
                if current_mtime != self.file_mtimes[str(CONFIG_FILE)]:
                    logger.debug("File modified: %s", CONFIG_FILE)
                    return True
            
            # Check config.d
            if CONFIG_DIR.exists():
                for f in CONFIG_DIR.glob("*.yml"):
                    current_mtime = f.stat().st_mtime
                    if str(f) not in self.file_mtimes:
                        logger.debug("New file detected: %s", f)
                        return True
                    if current_mtime != self.file_mtimes[str(f)]:
                        logger.debug("File modified: %s", f)
                        return True
            
            # Check custom.d
            if CUSTOM_CONFIG_DIR.exists():
                for f in CUSTOM_CONFIG_DIR.glob("*.yml"):
                    current_mtime = f.stat().st_mtime
                    if str(f) not in self.file_mtimes:
                        logger.debug("New file detected: %s", f)
                        return True
                    if current_mtime != self.file_mtimes[str(f)]:
                        logger.debug("File modified: %s", f)
                        return True
            
            return False
        
        except Exception as e:
            logger.warning("Error checking file modifications: %s", str(e))
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics
        
        Returns:
            dict: Cache hit/miss/invalidation stats
        """
        with self.lock:
            total = self.stats["hits"] + self.stats["misses"]
            hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
            
            return {
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "invalidations": self.stats["invalidations"],
                "total_requests": total,
                "hit_rate_percent": round(hit_rate, 1)
            }
    
    def reset_stats(self):
        """Reset cache statistics"""
        with self.lock:
            self.stats = {"hits": 0, "misses": 0, "invalidations": 0}
            logger.info("Cache statistics reset")


# Initialize global cache
_config_cache = ConfigCache()


# ============================================================
# CONFIGURATION LOADING FUNCTION
# ============================================================

def _process_config(config: Dict[str, Any], source_name: str, images: Dict[str, Any], groups: Dict[str, Any]):
    """Process a single config file and extract images and groups
    
    Args:
        config: Parsed YAML configuration dict
        source_name: Name of the config file (for logging)
        images: Accumulator dict for images
        groups: Accumulator dict for groups
    """
    if not config or not isinstance(config, dict):
        return
    
    # Load group (supports both singular "group" and plural "groups")
    # Handle singular "group" with single group definition
    if "group" in config and isinstance(config["group"], dict):
        group_data = config["group"]
        if "name" in group_data:
            # Single group with name inside
            group_name = group_data["name"]
            groups[group_name] = group_data
            groups[group_name]["source"] = source_name
            logger.debug("Loaded group '%s' from %s", group_name, source_name)
    
    # Handle plural "groups" (list or dict)
    if "groups" in config:
        groups_data = config["groups"]
        if isinstance(groups_data, list):
            for group in groups_data:
                if isinstance(group, dict) and "name" in group:
                    group_name = group["name"]
                    groups[group_name] = group
                    groups[group_name]["source"] = source_name
                    logger.debug("Loaded group '%s' from %s", group_name, source_name)
        elif isinstance(groups_data, dict):
            for name, group in groups_data.items():
                if isinstance(group, dict):
                    group["name"] = name
                    groups[name] = group
                    groups[name]["source"] = source_name
                    logger.debug("Loaded group '%s' from %s", name, source_name)
    
    # Load images from "images" section
    if "images" in config and isinstance(config["images"], dict):
        images.update(config["images"])
        logger.debug("Loaded %d images from 'images' key in %s", len(config["images"]), source_name)
    else:
        # Fallback: load images from direct keys (not group, not groups, not settings)
        for key, value in config.items():
            if key not in ("group", "groups", "settings") and isinstance(value, dict) and "image" in value:
                images[key] = value
        if any(key not in ("group", "groups", "settings") for key in config.keys()):
            logger.debug("Loaded images from direct keys in %s", source_name)


def _load_config_internal() -> Dict[str, Dict[str, Any]]:
    """Internal function to load configuration from all sources
    
    Configuration is loaded in this order (lower priority wins):
    1. config.yml (main config file)
    2. config.d/ (additional configs)
    3. custom.d/ (user-defined configs, highest priority)
    
    Returns:
        dict: Dictionary with 'images' and 'groups' keys
    
    Raises:
        HTTPException: If no valid configurations found or YAML parsing fails
    """
    images = {}
    groups = {}
    files_loaded = 0
    
    # 1. Load from config.yml
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("r") as f:
                config = yaml.safe_load(f)
                _process_config(config, "config.yml", images, groups)
                files_loaded += 1
                logger.debug("Loaded config.yml")
        except yaml.YAMLError as e:
            logger.error("Failed to parse config.yml: %s", str(e))
            raise HTTPException(500, f"Failed to parse config.yml: {str(e)}")
    
    # 2. Load from config.d
    if CONFIG_DIR.exists():
        for config_file in sorted(CONFIG_DIR.glob("*.yml")):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    _process_config(config, config_file.name, images, groups)
                    files_loaded += 1
                    logger.debug("Loaded %s", config_file.name)
            except yaml.YAMLError as e:
                logger.error("Failed to parse %s: %s", config_file, str(e))
                continue
    
    # 3. Load from custom.d
    if CUSTOM_CONFIG_DIR.exists():
        for config_file in sorted(CUSTOM_CONFIG_DIR.glob("*.yml")):
            try:
                with config_file.open("r") as f:
                    config = yaml.safe_load(f)
                    _process_config(config, config_file.name, images, groups)
                    files_loaded += 1
                    logger.debug("Loaded %s", config_file.name)
            except yaml.YAMLError as e:
                logger.error("Failed to parse %s: %s", config_file, str(e))
                continue
    
    if not images:
        logger.error("No valid configurations found in %d files", files_loaded)
        raise HTTPException(500, "No valid configurations found")
    
    logger.info("Configuration loaded: %d images, %d groups from %d files",
               len(images), len(groups), files_loaded)
    
    return {
        "images": dict(sorted(images.items(), key=lambda x: x[0].lower())),
        "groups": groups
    }


# ============================================================
# PUBLIC FUNCTION: load_config with caching
# ============================================================

def load_config() -> Dict[str, Dict[str, Any]]:
    """Load configuration with caching
    
    Returns cached config if available and valid, otherwise reloads from disk.
    Cache automatically invalidates after MAX_CACHE_AGE_SECONDS or when files change.
    
    Returns:
        dict: Dictionary with 'images' and 'groups' keys
    
    Raises:
        HTTPException: If no valid configurations found or YAML parsing fails
    """
    if not CacheConfig.ENABLE_CACHE:
        logger.debug("Cache disabled, loading config from disk")
        return _load_config_internal()
    
    # Try to get from cache
    cached = _config_cache.get()
    if cached is not None:
        return cached
    
    # Cache miss, load and cache
    _config_cache.stats["misses"] += 1
    config = _load_config_internal()
    _config_cache.set(config)
    
    return config


# ============================================================
# CACHE INVALIDATION FUNCTION
# ============================================================

def invalidate_config_cache():
    """Manually invalidate configuration cache
    
    Call this after adding/modifying config files
    """
    _config_cache.invalidate()
    logger.info("Configuration cache invalidated")


# ============================================================
# CACHE STATS ENDPOINT (for debugging)
# ============================================================

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics
    
    Returns:
        dict: Cache performance metrics
    """
    stats = _config_cache.get_stats()
    stats["cache_enabled"] = CacheConfig.ENABLE_CACHE
    stats["max_cache_age_seconds"] = CacheConfig.MAX_CACHE_AGE_SECONDS
    stats["check_interval_seconds"] = CacheConfig.CHECK_FILE_CHANGES_INTERVAL
    
    return stats


# ============================================================
# HELPER: get_motd
# ============================================================

def get_motd(image_name: str, config: Dict[str, Any]) -> str:
    """Get MOTD (Message of the Day) for an image
    
    Args:
        image_name: Name of the container/image
        config: Images configuration dict
    
    Returns:
        str: MOTD text, empty string if not found
    """
    img_data = config.get(image_name, {})
    return img_data.get('motd', '')


# ============================================================
# STARTUP LOGGING
# ============================================================

logger.info("Configuration module loaded")
logger.info("Config cache: %s", "ENABLED" if CacheConfig.ENABLE_CACHE else "DISABLED")
logger.info("Cache TTL: %d seconds", CacheConfig.MAX_CACHE_AGE_SECONDS)
logger.info("File check interval: %d seconds", CacheConfig.CHECK_FILE_CHANGES_INTERVAL)