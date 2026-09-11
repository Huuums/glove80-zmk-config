"""Install the overlay binding directly in the user's Hyprland binds.lua."""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
config = Path.home()/'.config/hypr/hyprland.lua'
binds = config.parent/'config/binds.lua'
if not config.is_file() or not binds.is_file():
    raise SystemExit('Expected ~/.config/hypr/hyprland.lua and config/binds.lua.')
binding = next(line for line in (ROOT/'overlay/hyprland.lua').read_text().splitlines()
               if line.startswith('hl.bind('))
text = binds.read_text()
if binding not in text:
    backup = binds.with_name('binds.lua.glove80-backup')
    if not backup.exists():
        shutil.copy2(binds, backup)
    binds.write_text(text.rstrip()+'\n\n-- Glove80 learning overlay\n'+binding+'\n')
    print(f'Added shortcut to {binds}')
legacy = 'dofile(' + json.dumps(str(ROOT/'overlay/hyprland.lua')) + ')'
text = config.read_text()
if legacy in text.splitlines():
    lines = text.splitlines()
    index = lines.index(legacy)
    del lines[index]
    if index and lines[index-1] == '-- Glove80 keyboard overlay':
        del lines[index-1]
    config.write_text('\n'.join(lines).rstrip()+'\n')
    print(f'Removed legacy overlay dofile from {config}')
