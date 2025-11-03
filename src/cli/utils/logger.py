"""
Logging utilities for CLI debugging
"""

import logging
import sys
from pathlib import Path
from rich.console import Console
from rich.logging import RichHandler

console = Console(stderr=True)

# Global debug flag
_DEBUG_MODE = False


def set_debug_mode(debug: bool):
    """Enable or disable debug mode globally"""
    global _DEBUG_MODE
    _DEBUG_MODE = debug

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)


def is_debug_mode() -> bool:
    """Check if debug mode is enabled"""
    return _DEBUG_MODE


def setup_logging(debug: bool = False):
    """Setup logging configuration"""
    set_debug_mode(debug)

    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=console,
                rich_tracebacks=True,
                tracebacks_show_locals=debug,
                show_time=debug,
                show_path=debug
            )
        ]
    )


def log_exception(e: Exception, context: str = ""):
    """Log an exception with context and stack trace in debug mode"""
    import traceback

    error_msg = str(e)
    error_type = type(e).__name__

    if context:
        console.print(f"[red]❌ {context}[/red]")

    console.print(f"[red]Error: {error_type}: {error_msg}[/red]")

    if _DEBUG_MODE:
        console.print("[dim]Stack trace:[/dim]")
        console.print("[dim]" + "".join(traceback.format_tb(e.__traceback__)) + "[/dim]")

        # Show locals at the point of error
        tb = e.__traceback__
        while tb.tb_next:
            tb = tb.tb_next

        frame = tb.tb_frame
        console.print(f"[dim]Error occurred in: {frame.f_code.co_filename}:{tb.tb_lineno} in {frame.f_code.co_name}()[/dim]")

        if frame.f_locals:
            console.print("[dim]Local variables:[/dim]")
            for var_name, var_value in list(frame.f_locals.items())[:10]:  # Limit to first 10
                try:
                    value_str = repr(var_value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                    console.print(f"[dim]  {var_name} = {value_str}[/dim]")
                except:
                    console.print(f"[dim]  {var_name} = <unable to display>[/dim]")
    else:
        console.print("[yellow]💡 Tip: Run with --debug flag for detailed stack trace[/yellow]")


def debug_print(message: str):
    """Print debug message only in debug mode"""
    if _DEBUG_MODE:
        console.print(f"[dim cyan]DEBUG: {message}[/dim cyan]")
