"""MOTD (Message of the Day) processing utilities"""


def parse_motd_commands(motd_text: str) -> list[str]:
    """Parse MOTD text and extract command lines (non-empty, non-title lines)"""
    if not motd_text:
        return []
    
    commands = []
    for line in motd_text.split('\n'):
        line = line.strip()
        # Extract lines that look like commands: contain 'apk ', 'apt ', 'npm ', '--', etc.
        # Exclude empty lines, title lines (with ║, ═), notes and sections
        if (line and 
            not any(c in line for c in ['║', '═', '╔', '╚', '╗', '╝']) and
            not line.startswith('Note:') and
            not line.startswith('⚠️') and
            ' # ' in line):  # Has explanatory comment
            commands.append(line)
    
    return commands


def clean_motd_text(motd_text: str) -> str:
    """Clean MOTD text by removing box drawing characters and normalizing formatting"""
    if not motd_text:
        return ""
    
    # Box drawing characters to remove
    box_chars = ['╔', '╚', '╗', '╝', '║', '═', '─', '┌', '┐', '└', '┘', '│', '├', '┤', '┼']
    
    cleaned = motd_text
    for char in box_chars:
        cleaned = cleaned.replace(char, '')
    
    # Remove lines that are only spaces or have only dashes
    lines = []
    for line in cleaned.split('\n'):
        # Remove lines with only drawing characters
        if line.strip() and not all(c in '─═ ' for c in line):
            lines.append(line.rstrip())
        elif line.strip():  # Keep non-empty lines
            lines.append(line.rstrip())
    
    # Remove multiple consecutive empty lines
    result = []
    prev_empty = False
    for line in lines:
        if not line.strip():
            if not prev_empty:
                result.append('')
            prev_empty = True
        else:
            result.append(line)
            prev_empty = False
    
    return '\n'.join(result).strip()


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