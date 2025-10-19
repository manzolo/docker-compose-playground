"""General utility helper functions"""
import re
from typing import Any


def natural_sort_key(key: str) -> list[Any]:
    """Convert string for natural sorting (10 > 2)
    
    Example:
        sorted(['img10', 'img2', 'img1'], key=natural_sort_key)
        # Returns ['img1', 'img2', 'img10']
    """
    def convert(text):
        return int(text) if text.isdigit() else text.lower()
    return [convert(c) for c in re.split('([0-9]+)', key)]