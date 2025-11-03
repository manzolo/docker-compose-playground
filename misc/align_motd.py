#!/usr/bin/env python3
import re
from pathlib import Path

# Caratteri box-drawing
BOX = {
    'tl': '╔', 'tr': '╗',
    'bl': '╚', 'br': '╝',
    'h': '═', 'v': '║'
}

def align_motd_block(motd_block: str) -> str:
    """Riceve il blocco multilinea del motd (dopo |) e lo restituisce allineato"""
    lines = motd_block.splitlines()
    if len(lines) < 3:
        return motd_block

    # Trova header: ╔...╗ e ╚...╝
    header_start = header_end = -1
    for i, line in enumerate(lines):
        if BOX['tl'] in line and BOX['tr'] in line:
            header_start = i
        if BOX['bl'] in line and BOX['br'] in line:
            header_end = i
            break

    if header_start == -1 or header_end == -1 or header_end <= header_start + 1:
        return motd_block

    # Calcola larghezza interna del box
    top_line = lines[header_start]
    match = re.match(fr'\{BOX["tl"]}(.+)\{BOX["tr"]}', top_line)
    if not match:
        return motd_block
    box_inner_width = len(match.group(1))
    if box_inner_width <= 0:
        return motd_block

    # Centra solo la riga del titolo (header_start + 1)
    title_idx = header_start + 1
    if title_idx >= len(lines):
        return motd_block

    title_line = lines[title_idx]
    if BOX['v'] not in title_line:
        return motd_block

    parts = title_line.split(BOX['v'], 2)
    if len(parts) < 3:
        return motd_block

    text = parts[1].strip()
    text_len = len(text)
    if text_len >= box_inner_width:
        return motd_block  # Troppo lungo, non centrare

    padding = box_inner_width - text_len
    left_pad = padding // 2
    right_pad = padding - left_pad

    new_title_line = f"{BOX['v']}{' ' * left_pad}{text}{' ' * right_pad}{BOX['v']}"
    lines[title_idx] = new_title_line

    return '\n'.join(lines)


def process_file_safely(file_path: Path) -> bool:
    content = file_path.read_text(encoding='utf-8')
    changed = False

    # Regex: trova motd: | seguito da blocco indentato
    motd_pattern = re.compile(
        r'^(\s*motd:\s*\|\s*\n)'           # motd: |\n
        r'((?:^\s{2,}.*\n)*)',             # tutte le righe indentate (almeno 2 spazi)
        re.MULTILINE
    )

    def replace_motd(match):
        nonlocal changed
        header = match.group(1)  # motd: |\n
        body = match.group(2)   # blocco indentato

        # Rimuovi indentazione comune del blocco
        indent = len(body) - len(body.lstrip())
        common_indent = min(
            (len(line) - len(line.lstrip(' ')) for line in body.splitlines() if line.strip()),
            default=indent
        )

        # De-indenta
        dedented_lines = [
            line[common_indent:] if len(line) >= common_indent else line
            for line in body.splitlines()
        ]
        dedented_block = '\n'.join(dedented_lines)

        aligned_block = align_motd_block(dedented_block)

        if aligned_block != dedented_block:
            changed = True

        # Ri-indenta con indentazione originale
        reindented_lines = [' ' * common_indent + line for line in aligned_block.splitlines()]
        return header + '\n'.join(reindented_lines) + '\n'

    new_content = motd_pattern.sub(replace_motd, content)

    if changed:
        file_path.write_text(new_content, encoding='utf-8')
        print(f"Allineato motd in: {file_path}")
    else:
        print(f"Nessun cambiamento: {file_path}")

    return changed


if __name__ == "__main__":
    config_d = Path('/home/manzolo/Workspaces/python/docker-compose-playground/config.d')
    if not config_d.is_dir():
        print(f"Errore: {config_d} non è una directory")
        exit(1)

    updated = 0
    for yml_file in config_d.glob('*.yml'):
        if process_file_safely(yml_file):
            updated += 1

    print(f"\nFatto! {updated} file aggiornati. Il resto del file è intatto.")