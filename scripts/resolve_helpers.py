"""Resolve Engrammer Tap helpers from a matching compiled, symbolic Zephyr DTS.

Only the verified release-all-modifiers / tap-prefix / tap-parameter pattern
is recognized. Other macros remain opaque rather than guessing their output.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path


def resolve(layout, dts):
    nodes = {name: body for name, body in re.findall(r'(\w+):\s*\w+\s*\{([^{}]*)\}', dts)}
    result = {}
    for layer, name in enumerate(layout['layer_names']):
        node = re.search(r'\blayer_' + re.escape(name) + r'\s*\{([^{}]*)\}', dts)
        if not node:
            raise ValueError(f'Missing compiled layer: {name}')
        bindings = re.search(r'\bbindings\s*=\s*(.*?);', node[1], re.S)
        entries = re.findall(r'&(\w+)([^&<>]*)', bindings[1])
        if len(entries) != len(layout['layers'][layer]):
            raise ValueError(f'Compiled layer size mismatch: {name}')
        for index, (behavior, parameters) in enumerate(entries):
            key = layout['layers'][layer][index]
            if key.get('decoration', {}).get('label') != 'Tap':
                continue
            params = [int(value, 0) for value in parameters.split()]
            if behavior == 'kp' and len(params) == 1:
                result[f'{layer}:{index}'] = {'codes': params, 'clearsModifiers': False}
                continue
            body = nodes.get(behavior, '')
            binding = re.search(r'\bbindings\s*=\s*(.*?);', body, re.S)
            if not binding or len(params) != 1:
                continue
            groups = re.findall(r'<\s*(.*?)\s*>', binding[1])
            if len(groups) != 4:
                continue
            release = re.fullmatch(r'&macro_release((?:\s+&kp\s+0x[0-9a-f]+)+)', groups[0])
            prefix = re.fullmatch(r'&macro_tap\s+&kp\s+(0x[0-9a-f]+)', groups[1])
            if not release or not prefix or groups[2] != '&macro_param_1to1' or groups[3] != '&macro_tap &kp 0x0':
                continue
            released = {int(v, 16) for v in re.findall(r'0x[0-9a-f]+', release[1])}
            if released != set(range(0x700e0, 0x700e8)):
                continue
            result[f'{layer}:{index}'] = {'codes': [int(prefix[1], 16), *params], 'clearsModifiers': True}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('layout', type=Path)
    parser.add_argument('dts', type=Path)
    parser.add_argument('--output', type=Path, default=Path('preview/helper-bindings.json'))
    args = parser.parse_args()
    raw = args.layout.read_bytes()
    helpers = resolve(json.loads(raw), args.dts.read_text())
    args.output.write_text(json.dumps({'layout_sha256': hashlib.sha256(raw).hexdigest(),
                                      'dts_sha256': hashlib.sha256(args.dts.read_bytes()).hexdigest(),
                                      'bindings': helpers}, indent=2) + '\n')
    print(f'Resolved {len(helpers)} helper labels from compiled bindings')
