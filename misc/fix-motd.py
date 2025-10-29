#!/usr/bin/env python3
import re
from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

# Manteniamo i caratteri box-drawing (Unicode, non ANSI!)
# Sono perfettamente supportati in UTF-8
BOX_TOP_LEFT     = '╔'
BOX_TOP_RIGHT    = '╗'
BOX_BOTTOM_LEFT  = '╚'
BOX_BOTTOM_RIGHT = '╝'
BOX_HORIZONTAL   = '═'
BOX_VERTICAL     = '║'

# Sostituiamo solo gli escape errati \U0001F4E6
EMOJI_REPLACE = {
    r'\\U0001F4E6': '[Package]',   # package
    r'\\U0001F527': '[Tools]',     # wrench
    r'\\U0001F4A1': '[Tips]',      # lightbulb
    r'\\U0001F4DA': '[Docs]',      # books
}

def rebuild_header(title):
    """Ricostruisce header con box-drawing e titolo centrato"""
    title = title.strip()
    inner_width = len(title) + 2  # spazi laterali
    total_width = max(inner_width, 60)  # almeno 60 colonne
    padding = total_width - inner_width
    left_pad = padding // 2
    right_pad = padding - left_pad

    top    = BOX_TOP_LEFT + BOX_HORIZONTAL * (total_width) + BOX_TOP_RIGHT
    middle = BOX_VERTICAL + ' ' * left_pad + title + ' ' * right_pad + BOX_VERTICAL
    bottom = BOX_BOTTOM_LEFT + BOX_HORIZONTAL * (total_width) + BOX_BOTTOM_RIGHT

    return f"{top}\n{middle}\n{bottom}\n"

def fix_motd_text(raw_motd):
    if not raw_motd or not isinstance(raw_motd, str):
        return raw_motd

    # 1. Sostituisci \U0001F4E6 → [Package], ecc.
    text = raw_motd
    for pattern, repl in EMOJI_REPLACE.items():
        text = re.sub(pattern, repl, text)

    # 2. Estrai header (se c'è il box-drawing originale)
    lines = text.splitlines()
    header_lines = []
    body_lines = []
    in_header = False
    header_title = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('╔') and 'Quick Reference' in stripped:
            in_header = True
            # Estrai titolo tra ║
            match = re.search(r'║\s*(.+?)\s*║', line)
            if match:
                header_title = match.group(1)
            header_lines.append(line)
        elif in_header and stripped.startswith('╚'):
            header_lines.append(line)
            in_header = False
            if header_title:
                # Ricostruisci header bello e allineato
                new_header = rebuild_header(header_title)
                body_lines.append(new_header)
        elif in_header:
            header_lines.append(line)
        else:
            # Pulizia corpo: rimuovi indentazione eccessiva
            if stripped or line:  # mantieni righe vuote
                indent = len(line) - len(line.lstrip())
                indent = min(indent, 3)
                cleaned = ' ' * indent + line.lstrip()
                body_lines.append(cleaned)
            else:
                body_lines.append('')

    result = '\n'.join(body_lines).rstrip() + '\n'
    return result

def process_yaml_file(filepath):
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(mapping=2, sequence=4, offset=2)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.load(f)
    except Exception as e:
        print(f"Errore lettura {filepath}: {e}")
        return False

    if not isinstance(data, dict) or 'images' not in data:
        return False

    modified = False
    for img_key, img_data in data.get('images', {}).items():
        if not isinstance(img_data, dict) or 'motd' not in img_data:
            continue
        old_motd = img_data['motd']
        if not isinstance(old_motd, str):
            continue

        new_motd = fix_motd_text(old_motd)
        if new_motd != old_motd:
            img_data['motd'] = LiteralScalarString(new_motd)
            print(f"Header e MOTD corretti: {img_key}")
            modified = True

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f)
        print(f"Salvato: {filepath}\n")
    return modified

def main():
    folder = Path('.')
    yaml_files = list(folder.glob('*.yml')) + list(folder.glob('*.yaml'))
    if not yaml_files:
        print("Nessun file .yml trovato.")
        return

    print(f"Trovati {len(yaml_files)} file. Elaborazione...\n")
    total = sum(process_yaml_file(f) for f in yaml_files)
    print(f"Completato! {total} file corretti.")

if __name__ == '__main__':
    main()