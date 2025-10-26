"""MOTD (Message of the Day) processing utilities"""
import re
from markupsafe import Markup


def parse_urls(text: str) -> Markup:
    """Converte gli URL in link HTML"""
    if not text:
        return Markup("")
    
    # Pattern per riconoscere URL (http, https, ftp)
    url_pattern = r'(https?|ftp)://[^\s<>"{}|\\^`\[\]]+'
    
    def make_link(match):
        url = match.group(0)
        # Estrai il dominio per il testo del link
        domain = url.split('//')[1].split('/')[0]
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="motd-link" title="{url}">{domain}</a>'
    
    html = re.sub(url_pattern, make_link, text)
    return Markup(html)


def motd_to_html(motd_text: str) -> Markup:
    """Converte MOTD text in HTML preservando la formattazione"""
    if not motd_text:
        return Markup("")
    
    html = []
    lines = motd_text.split('\n')
    
    for line in lines:
        if not line.strip():
            html.append('')
            continue
        
        # Sostituisci i caratteri box drawing con HTML equivalenti
        html_line = escape_html(line)
        
        # Colora le righe di separazione
        if any(c in line for c in ['═', '║', '╔', '╚', '╗', '╝']):
            html_line = f'<span class="motd-separator">{html_line}</span>'
        
        # Colora le emoji e testo speciale
        elif line.strip().startswith(('🔐', '📊', '📁', '🚀')):
            html_line = f'<span class="motd-highlight">{html_line}</span>'
        elif line.strip().startswith(('💡', '⚠️', '❌')):
            html_line = f'<span class="motd-warning">{html_line}</span>'
        elif ' # ' in line:  # Commenti
            html_line = highlight_command_with_comment(html_line)
        
        # Applica il parsing degli URL
        html_line = parse_urls(html_line)
        
        html.append(str(html_line))
    
    # Crea paragrafi
    result = '<br>\n'.join(html)
    return Markup(result)


def escape_html(text: str) -> str:
    """Escapa i caratteri HTML speciali"""
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }
    for char, escaped in replacements.items():
        text = text.replace(char, escaped)
    return text


def highlight_command_with_comment(line: str) -> str:
    """Evidenzia il comando e il commento separatamente"""
    if ' # ' in line:
        parts = line.split(' # ', 1)
        command = parts[0]
        comment = parts[1]
        return f'<span class="motd-command">{command}</span> <span class="motd-comment"># {comment}</span>'
    return line


def parse_motd_commands(motd_text: str) -> list[dict]:
    """Parse MOTD text and extract command lines with descriptions"""
    if not motd_text:
        return []
    
    commands = []
    for line in motd_text.split('\n'):
        line = line.strip()
        # Extract lines that look like commands or URLs
        # Exclude: empty lines, box drawing chars, section headers
        if (line and
            not any(c in line for c in ['║', '═', '╔', '╚', '╗', '╝', '─', '┌', '┐', '└', '┘']) and
            not line.startswith('Note:') and
            not line.startswith('⚠️') and
            not line.startswith('💡') and
            not line.startswith('Section:') and
            len(line) > 3):  # Almeno 3 caratteri
            
            # Controlla se è un comando o una URL
            is_command = any(cmd in line for cmd in ['apk ', 'apt ', 'apt-get ', 'npm ', 'pip ', 'docker ', 
                                                      'curl ', 'wget ', 'chmod ', 'chown ', 'mkdir ', 'cd ',
                                                      './']) or ' # ' in line
            is_url = any(protocol in line for protocol in ['http://', 'https://', 'ftp://'])
            
            if is_command or is_url:
                # Separa comando/URL e descrizione
                if ' # ' in line:
                    command, description = line.split(' # ', 1)
                    commands.append({
                        'command': command.strip(),
                        'description': description.strip()
                    })
                else:
                    commands.append({
                        'command': line,
                        'description': ''
                    })
    
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