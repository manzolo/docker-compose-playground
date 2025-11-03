"""
Enhanced error handling utilities for web API
Provides detailed error responses with stack traces in debug mode
"""

import traceback
import sys
from typing import Dict, Any, Optional
from fastapi import HTTPException
from pathlib import Path

# Global debug mode flag
_DEBUG_MODE = False


def set_debug_mode(debug: bool):
    """Enable or disable debug mode globally"""
    global _DEBUG_MODE
    _DEBUG_MODE = debug


def is_debug_mode() -> bool:
    """Check if debug mode is enabled"""
    return _DEBUG_MODE


def format_exception_details(e: Exception, context: str = "") -> Dict[str, Any]:
    """
    Format exception details with full stack trace and context

    Args:
        e: The exception to format
        context: Additional context about where the error occurred

    Returns:
        Dict containing error details
    """
    error_type = type(e).__name__
    error_message = str(e)

    # Build basic error response
    error_details = {
        "error": error_message,
        "error_type": error_type,
        "context": context if context else None
    }

    # Add detailed debug information if debug mode is enabled
    if _DEBUG_MODE:
        # Get the traceback
        tb_lines = traceback.format_exception(type(e), e, e.__traceback__)
        error_details["stack_trace"] = "".join(tb_lines)

        # Get the frame where the error occurred
        tb = e.__traceback__
        while tb.tb_next:
            tb = tb.tb_next

        frame = tb.tb_frame
        error_details["error_location"] = {
            "file": frame.f_code.co_filename,
            "line": tb.tb_lineno,
            "function": frame.f_code.co_name
        }

        # Add local variables (limited and sanitized)
        try:
            locals_dict = {}
            for var_name, var_value in list(frame.f_locals.items())[:10]:  # Limit to 10
                try:
                    value_str = repr(var_value)
                    if len(value_str) > 200:
                        value_str = value_str[:200] + "..."
                    locals_dict[var_name] = value_str
                except:
                    locals_dict[var_name] = "<unable to display>"

            if locals_dict:
                error_details["local_variables"] = locals_dict
        except:
            pass

        # Add helpful debugging tips
        error_details["debug_tips"] = get_debug_tips(e)

    return error_details


def get_debug_tips(e: Exception) -> list:
    """Get helpful debugging tips based on the exception type"""
    tips = []

    error_msg = str(e).lower()

    # Common error patterns and tips
    if "not iterable" in error_msg and "int" in error_msg:
        tips.append("Check if YAML values need to be quoted (e.g., port mappings like '2222:22')")
        tips.append("YAML may be parsing numbers as integers instead of strings")

    if "port is already allocated" in error_msg:
        tips.append("Another container or process is using this port")
        tips.append("Use 'docker ps' or 'netstat -tuln' to find what's using the port")

    if "permission denied" in error_msg:
        tips.append("Check file/directory permissions")
        tips.append("May need to run with appropriate user permissions")

    if "connection refused" in error_msg or "cannot connect" in error_msg:
        tips.append("Check if Docker daemon is running")
        tips.append("Verify Docker socket permissions")

    if "image not found" in error_msg:
        tips.append("Try pulling the image first with 'docker pull <image>'")
        tips.append("Check if the image name and tag are correct")

    if "file exists" in error_msg:
        tips.append("The file or directory already exists")
        tips.append("Check if it's the correct path and type (file vs directory)")

    return tips


def create_error_response(
    e: Exception,
    context: str = "",
    status_code: int = 500,
    logger=None
) -> HTTPException:
    """
    Create an enhanced HTTP error response with debugging information

    Args:
        e: The exception
        context: Context about where the error occurred
        status_code: HTTP status code
        logger: Optional logger to log the error

    Returns:
        HTTPException with detailed error information
    """
    error_details = format_exception_details(e, context)

    # Log the error if logger provided
    if logger:
        if _DEBUG_MODE:
            logger.error(
                "%s: %s\n%s",
                context if context else "Error",
                str(e),
                error_details.get("stack_trace", ""),
                exc_info=True
            )
        else:
            logger.error("%s: %s", context if context else "Error", str(e))

    # Create response content
    response_content = {
        "error": error_details["error"],
        "error_type": error_details["error_type"]
    }

    if context:
        response_content["context"] = context

    # Include debug information if debug mode is enabled
    if _DEBUG_MODE:
        response_content["debug_info"] = {
            "stack_trace": error_details.get("stack_trace"),
            "error_location": error_details.get("error_location"),
            "local_variables": error_details.get("local_variables"),
            "debug_tips": error_details.get("debug_tips", [])
        }
        response_content["_debug_mode"] = True
        response_content["_message"] = "Debug mode is enabled - detailed error information included"

    return HTTPException(status_code=status_code, detail=response_content)


def log_exception(e: Exception, context: str = "", logger=None):
    """
    Log an exception with full details in debug mode

    Args:
        e: The exception
        context: Context about where the error occurred
        logger: Logger instance to use
    """
    if not logger:
        import logging
        logger = logging.getLogger(__name__)

    error_details = format_exception_details(e, context)

    if _DEBUG_MODE:
        logger.error(
            "%s: %s\nLocation: %s:%s in %s()\nStack trace:\n%s",
            context if context else "Exception",
            error_details["error"],
            error_details.get("error_location", {}).get("file", "unknown"),
            error_details.get("error_location", {}).get("line", "?"),
            error_details.get("error_location", {}).get("function", "?"),
            error_details.get("stack_trace", "")
        )

        if error_details.get("debug_tips"):
            logger.info("Debug tips:")
            for tip in error_details["debug_tips"]:
                logger.info("  💡 %s", tip)
    else:
        logger.error("%s: %s", context if context else "Exception", str(e))
