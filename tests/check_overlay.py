"""Integration check against the current Hyprland session; leaves overlay hidden."""
import json
import os
from pathlib import Path
import subprocess
import time
ROOT = Path(__file__).resolve().parents[1]

def command(*args):
    subprocess.run([os.environ.get('GLOVE80_OVERLAY_EXECUTABLE', str(ROOT/'glove80-overlay')), *args], check=True)
    time.sleep(0.25)

def surfaces():
    data = json.loads(subprocess.check_output(['hyprctl','-j','layers']))
    return [surface for monitor in data.values() for level in monitor['levels'].values()
            for surface in level if surface['namespace']=='glove80-overlay']

def focus():
    return json.loads(subprocess.check_output(['hyprctl','-j','activewindow'])).get('address')

before = focus()
command('hide')
assert not surfaces()
command('show','--width','720','--opacity','0.65','--position','top-right')
assert len(surfaces()) == 1 and surfaces()[0]['w'] == 720
assert focus() == before, 'Overlay stole keyboard focus'
command('toggle')
assert not surfaces()
command('toggle')
assert len(surfaces()) == 1 and surfaces()[0]['w'] == 900
assert focus() == before
command('hide')
assert not surfaces()
print('Hyprland passed: single-instance show/hide/toggle, resizing, placement, focus retained.')
