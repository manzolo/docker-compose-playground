#!/usr/bin/env python3
"""
Simple script to add basic MOTDs to container config files
"""

import os
import yaml
from pathlib import Path

CONFIG_DIR = Path("config.d")

def add_simple_motd(filepath):
    """Add a simple MOTD to a YAML config file if it doesn't have one"""

    with open(filepath, 'r') as f:
        content = f.read()

    # Skip if already has MOTD
    if 'motd:' in content:
        return False

    # Parse to get info
    try:
        data = yaml.safe_load(content)
        if not data or 'images' not in data:
            return False

        for img_name, img_config in data['images'].items():
            description = img_config.get('description', img_name)
            category = img_config.get('category', 'general')

            # Create simple MOTD
            motd = f"""    motd: |
      ╔══════════════════════════════════════════════════════════════╗
      ║              {description:^44}              ║
      ╚══════════════════════════════════════════════════════════════╝

      📁 Useful Directories:
         /shared                                   # Shared with host

      💡 Tips:
         • Use /shared directory for persistent data
         • Check container logs for startup information
         • Refer to official documentation for detailed usage

      📚 Category: {category}
"""

            # Append MOTD at the end of file
            with open(filepath, 'a') as f:
                f.write(motd)

            print(f"✅ Added MOTD to {filepath.name}")
            return True

    except Exception as e:
        print(f"❌ Error processing {filepath.name}: {e}")
        return False

def main():
    print("🔍 Adding MOTDs to config files...\n")

    count = 0
    skipped = 0

    for filepath in sorted(CONFIG_DIR.glob("*.yml")):
        if add_simple_motd(filepath):
            count += 1
        else:
            skipped += 1

    print(f"\n{'='*70}")
    print(f"✨ Complete!")
    print(f"   Added: {count} files")
    print(f"   Skipped: {skipped} files (already have MOTD)")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
