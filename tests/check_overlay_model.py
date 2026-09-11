"""Run with system Python, which supplies JavaScriptCore and GTK bindings."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'overlay'))
from model import KeyboardModel, load_settings
m=KeyboardModel()
keys=m.keys({'connected':True,'layers':[0,9],'modifiers':2})
assert len(keys)==80
assert keys[39]['label']=='E → -'
keys=m.keys({'connected':True,'layers':[0,19],'modifiers':0})
assert all(k['label']!='Tap' for k in keys)
for bad in [{'width':100},{'opacity':2},{'opacity':float('nan')},{'position':'invalid'}]:
    try: load_settings(bad)
    except ValueError: pass
    else: raise AssertionError(bad)
print('Overlay model passed: shared helper labels, 80-key geometry, settings validation.')
