# Build from the repository root with scripts/build-executable.sh.
from pathlib import Path
import json
import sys
from PyInstaller.utils.hooks import collect_submodules
root = Path(SPECPATH).parent
sys.path.insert(0, str(root/'overlay'))
from model import load_settings
assets = root/'build/bundle-assets'
assets.mkdir(parents=True, exist_ok=True)
(assets/'settings.json').write_text(json.dumps(load_settings()))
a = Analysis(
    [str(root/'packaging/entry.py')],
    pathex=[str(root/'overlay'), str(root/'receiver')],
    binaries=[('/usr/lib/libgtk4-layer-shell.so', '.')],
    datas=[(str(root/'preview/index.html'), 'preview'),
           (str(root/'preview/key-labels.js'), 'preview'),
           (str(root/'preview/vendor/keymap-editor-LICENSE.txt'), 'preview/vendor'),
           (str(assets/'settings.json'), 'overlay')],
    hiddenimports=collect_submodules('dbus_fast') + ['gi.repository.JavaScriptCore', 'gi.repository.Gtk4LayerShell', 'cairo'],
    hooksconfig={'gi': {'module-versions': {'Gtk': '4.0', 'Gdk': '4.0', 'JavaScriptCore':'4.1', 'Gtk4LayerShell':'1.0'},
                       'icons': [], 'themes': [], 'languages': ['en']}},
    excludes=['tkinter','pytest','IPython'],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='glove80-overlay',
          debug=False, strip=False, upx=False, console=True)
