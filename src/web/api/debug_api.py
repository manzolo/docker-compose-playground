"""
Debug API endpoints for controlling debug mode and viewing system information
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import logging
import sys
from pathlib import Path

from src.web.utils.error_handler import set_debug_mode, is_debug_mode
from src.web.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


class DebugStatusResponse(BaseModel):
    """Debug status response"""
    debug_mode: bool
    log_level: str
    python_version: str
    log_file: Optional[str] = None


class DebugModeRequest(BaseModel):
    """Request to change debug mode"""
    enabled: bool


@router.get("/api/debug/status", response_model=DebugStatusResponse)
async def get_debug_status():
    """
    Get current debug mode status and logging configuration

    Returns debug information including:
    - Current debug mode state
    - Logging level
    - Python version
    - Log file location
    """
    root_logger = logging.getLogger()

    # Find the log file handler
    log_file = None
    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler):
            log_file = handler.baseFilename
            break

    return DebugStatusResponse(
        debug_mode=is_debug_mode(),
        log_level=logging.getLevelName(root_logger.level),
        python_version=sys.version,
        log_file=log_file
    )


@router.post("/api/debug/mode")
async def set_debug_mode_endpoint(request: DebugModeRequest):
    """
    Enable or disable debug mode

    When debug mode is enabled:
    - API error responses include full stack traces
    - Detailed error information is logged
    - Local variables are captured at error points
    - Debug tips are provided for common issues

    Args:
        request: Request body with `enabled` field

    Returns:
        Success message and new debug mode state
    """
    try:
        set_debug_mode(request.enabled)

        # Also update the logging level
        root_logger = logging.getLogger()
        if request.enabled:
            root_logger.setLevel(logging.DEBUG)
            logger.info("Debug mode ENABLED - detailed error information will be provided")
        else:
            root_logger.setLevel(logging.INFO)
            logger.info("Debug mode DISABLED - standard error reporting")

        return {
            "success": True,
            "debug_mode": is_debug_mode(),
            "message": f"Debug mode {'enabled' if request.enabled else 'disabled'}"
        }

    except Exception as e:
        logger.error(f"Failed to set debug mode: {str(e)}")
        raise HTTPException(500, f"Failed to set debug mode: {str(e)}")


@router.get("/api/debug/logs")
async def get_recent_logs(lines: int = 100):
    """
    Get recent log entries from the log file

    Args:
        lines: Number of lines to retrieve (default: 100, max: 1000)

    Returns:
        Recent log entries
    """
    try:
        # Limit lines to prevent abuse
        lines = min(lines, 1000)

        # Find the log file
        root_logger = logging.getLogger()
        log_file = None
        for handler in root_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                log_file = Path(handler.baseFilename)
                break

        if not log_file or not log_file.exists():
            return {
                "logs": [],
                "message": "Log file not found"
            }

        # Read last N lines
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        return {
            "logs": [line.rstrip() for line in recent_lines],
            "total_lines": len(recent_lines),
            "log_file": str(log_file)
        }

    except Exception as e:
        logger.error(f"Failed to read logs: {str(e)}")
        raise HTTPException(500, f"Failed to read logs: {str(e)}")


@router.get("/api/debug/test-error")
async def test_error_handling(error_type: str = "generic"):
    """
    Test endpoint to trigger different types of errors for testing debug mode

    This endpoint is useful for testing error handling and debug information display.
    Only use in development environments.

    Args:
        error_type: Type of error to trigger
            - generic: Generic exception
            - type: TypeError
            - value: ValueError
            - attribute: AttributeError
            - index: IndexError

    Returns:
        Never returns - always raises an exception
    """
    logger.warning(f"Test error triggered: {error_type}")

    if error_type == "type":
        # Simulate the YAML port parsing error
        port = 2222
        if ':' in port:  # This will cause TypeError: argument of type 'int' is not iterable
            pass
    elif error_type == "value":
        raise ValueError("This is a test ValueError for debugging")
    elif error_type == "attribute":
        obj = {}
        obj.nonexistent_attribute  # AttributeError
    elif error_type == "index":
        list_obj = [1, 2, 3]
        _ = list_obj[10]  # IndexError
    else:
        raise Exception("This is a test exception for debugging error handling")
