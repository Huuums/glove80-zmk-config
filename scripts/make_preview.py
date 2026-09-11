"""Generate a self-contained, offline preview from a MoErgo JSON export."""
import argparse
import html
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def generate(source, output):
    layout = json.loads(source.read_text())
    if layout.get('keyboard') != 'glove80':
        raise ValueError('Expected a Glove80 export')
    layers = layout['layers']
    if not 1 <= len(layers) <= 32 or any(len(layer) != 80 for layer in layers):
        raise ValueError('Expected 1–32 layers of 80 keys')
    if len(layout['layer_names']) != len(layers):
        raise ValueError('Layer names and bindings do not match')
    data = {key: layout[key] for key in ('title', 'layers', 'layer_names')}
    helper_path = ROOT / 'preview/helper-bindings.json'
    if helper_path.exists():
        helpers = json.loads(helper_path.read_text())
        if helpers['layout_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest():
            for position, resolved in helpers['bindings'].items():
                layer, key = map(int, position.split(':'))
                data['layers'][layer][key]['resolved'] = resolved
        else:
            print('Helper data is for a different export; skipping it. Run resolve_helpers.py with the matching DTS.')
    data['locale'] = layout.get('locale', 'en-US')
    data['geometry'] = json.loads((ROOT / 'preview/geometry.json').read_text())
    # Prevent export labels from closing the JSON script element.
    payload = json.dumps(data, ensure_ascii=True).replace('<', '\\u003c')
    template = (ROOT / 'preview/template.html').read_text()
    template = template.replace('__KEY_LABELS__', (ROOT / 'preview/key-labels.js').read_text())
    license_text = (ROOT / 'preview/vendor/keymap-editor-LICENSE.txt').read_text()
    output.write_text(template.replace('__LAYOUT_DATA__', payload).replace('__EDITOR_LICENSE__', html.escape(license_text)))
    print(f'Generated {output}: {len(layers)} layers, 80 keys each')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'preview/index.html')
    args = parser.parse_args()
    generate(args.source, args.output)
