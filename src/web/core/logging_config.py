"""Centralized logging configuration for the application"""
import logging
import sys
from pathlib import Path
from typing import Optional


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[0;36m',    # Cyan
        'INFO': '\033[0;32m',     # Green
        'WARNING': '\033[0;33m',  # Yellow
        'ERROR': '\033[0;31m',    # Red
        'CRITICAL': '\033[1;31m', # Bold Red
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logging(
    log_file: Optional[Path] = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    format_style: str = "standard"
) -> None:
    """
    Setup centralized logging configuration for the entire application.

    Args:
        log_file: Path to log file. If None, uses default venv/web.log
        console_level: Logging level for console output
        file_level: Logging level for file output
        format_style: Format style ('standard' or 'detailed')
    """

    # Default log file location
    if log_file is None:
        log_file = Path(__file__).parent.parent.parent.parent / "venv" / "web.log"

    # Create log directory if it doesn't exist
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Define format strings
    if format_style == "detailed":
        # Detailed format with module name, function, and line number
        file_format = "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(funcName)s:%(lineno)d - %(message)s"
        console_format = "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s"
    else:
        # Standard format - clean and consistent
        file_format = "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s"
        console_format = "[%(asctime)s] [%(levelname)-8s] [%(name)s] %(message)s"

    date_format = "%Y-%m-%d %H:%M:%S"

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything, handlers will filter

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create file handler
    file_handler = logging.FileHandler(str(log_file), mode='a', encoding='utf-8')
    file_handler.setLevel(file_level)
    file_formatter = logging.Formatter(file_format, datefmt=date_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Create console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_formatter = ColoredFormatter(console_format, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Set levels for noisy third-party libraries
    logging.getLogger("docker").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("Logging system initialized")
    logger.info("  Log file: %s", log_file)
    logger.info("  Console level: %s", logging.getLevelName(console_level))
    logger.info("  File level: %s", logging.getLevelName(file_level))
    logger.info("  Format style: %s", format_style)
    logger.info("=" * 80)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    This ensures all loggers use the centralized configuration.

    Args:
        name: Logger name (usually __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)


# Convenience function for module-specific loggers
def get_module_logger(module_name: str) -> logging.Logger:
    """
    Get a logger for a specific module with a consistent naming convention.

    Args:
        module_name: Module name (e.g., 'docker', 'scripts', 'api')

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(f"playground.{module_name}")
