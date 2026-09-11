"""Measure live Hyprland visibility latency; leave the overlay hidden."""
import json
import os
import statistics
import subprocess
import time

executable = os.environ.get('GLOVE80_OVERLAY_EXECUTABLE', os.path.expanduser('~/.local/bin/glove80-overlay'))
action = ['gapplication', 'action', 'com.glove80.LayerOverlay', 'toggle']

def visible():
    data = json.loads(subprocess.check_output(['hyprctl', '-j', 'layers']))
    return any(s['namespace'] == 'glove80-overlay' for m in data.values()
               for level in m['levels'].values() for s in level)

def focus():
    return json.loads(subprocess.check_output(['hyprctl', '-j', 'activewindow'])).get('address')

subprocess.run([executable, 'hide'], check=True)
before = focus()
results = {}
try:
    for name, command in [('executable', [executable, 'toggle']), ('direct_action', action)]:
        samples = []
        for i in range(6):
            expected = i % 2 == 0
            start = time.perf_counter()
            subprocess.run(command, check=True)
            while visible() != expected:
                assert time.perf_counter() - start < 3, 'Visibility did not change'
                time.sleep(.005)
            samples.append((time.perf_counter() - start) * 1000)
        results[name] = round(statistics.median(samples), 1)
    assert focus() == before, 'Overlay stole keyboard focus'
    print(json.dumps({'median_visibility_ms': results, 'focus_preserved': True}))
finally:
    subprocess.run([executable, 'hide'], check=True)
