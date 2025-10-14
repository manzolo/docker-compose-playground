import re
from typing import Any

def natural_sort_key(key: str) -> list[Any]:
    """Convert string for natural sorting (10 > 2)"""
    def convert(text):
        return int(text) if text.isdigit() else text.lower()
    return [convert(c) for c in re.split('([0-9]+)', key)]

def format_motd_for_terminal(motd: str) -> str:
    """Format MOTD with ANSI colors for terminal"""
    if not motd:
        return ""
    
    formatted = motd.replace('\n', '\r\n')
    lines = formatted.split('\r\n')
    colored_lines = []
    
    for line in lines:
        if '═' in line or '║' in line:
            colored_lines.append(f'\x1b[36m{line}\x1b[0m')  # Cyan
        elif line.strip().startswith(('🔐', '📊', '📁')):
            colored_lines.append(f'\x1b[1;32m{line}\x1b[0m')  # Green bold
        elif line.strip().startswith(('💡', '⚠️')):
            colored_lines.append(f'\x1b[33m{line}\x1b[0m')  # Yellow
        else:
            colored_lines.append(line)
    
    return '\r\n'.join(colored_lines) + '\r\n'