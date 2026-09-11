"""Shared labels evaluated in JavaScriptCore, no embedded browser required."""
import json
import os
import sys
from pathlib import Path
import re

FROZEN = getattr(sys, 'frozen', False)
ROOT = Path(sys._MEIPASS) if FROZEN else Path(__file__).resolve().parents[1]

def settings_path():
    if FROZEN:
        return Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'glove80-overlay/settings.json'
    return ROOT/'overlay/settings.local.json'

def receiver_log_path():
    if FROZEN:
        return Path(os.environ.get('XDG_STATE_HOME', Path.home()/'.local/state'))/'glove80-overlay/receiver.log'
    return ROOT/'overlay/receiver.log'


def load_settings(overrides=None):
    settings = json.loads((ROOT / 'overlay/settings.json').read_text())
    local = settings_path()
    if local.exists():
        settings.update(json.loads(local.read_text()))
    settings.update(overrides or {})
    for name, low, high in [('width', 320, 2400), ('opacity', 0.15, 1), ('margin', 0, 500), ('receiver_port', 1024, 65535)]:
        value = settings[name]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not low <= value <= high:
            raise ValueError(f'{name} must be between {low} and {high}')
    for name in ('width', 'margin', 'receiver_port'):
        if not isinstance(settings[name], int):
            raise ValueError(f'{name} must be an integer')
    if settings['position'] not in ('top', 'bottom', 'center', 'top-left', 'top-right', 'bottom-left', 'bottom-right'):
        raise ValueError('Unknown position')
    if not isinstance(settings['monitor'], str) or not isinstance(settings['start_receiver'], bool):
        raise ValueError('Invalid monitor or start_receiver setting')
    return settings


class KeyboardModel:
    def __init__(self):
        import gi
        gi.require_version('JavaScriptCore', '4.1')
        from gi.repository import JavaScriptCore
        html = (ROOT / 'preview/index.html').read_text()
        self.data = json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', html, re.S)[1])
        self.context = JavaScriptCore.Context()
        self.evaluate('const data=' + json.dumps(self.data) + '; let connected=false, liveModifiers=null;')
        self.evaluate((ROOT / 'preview/key-labels.js').read_text())
        self.evaluate('''function overlayKeys(state) {
            connected=Boolean(state.connected); liveModifiers=state.modifiers??null;
            const active=(state.layers?.length?state.layers:[0]).filter(i=>Number.isInteger(i)&&i>=0&&i<data.layers.length).sort((a,b)=>b-a);
            return data.geometry.map((geometry,position)=>{
                let key={value:'&none'};
                for(const layer of active){key=data.layers[layer][position];if(binding(key).trim()!=='&trans')break;}
                return {geometry, label:label(key), icon:icons[key.decoration?.icon]||'',
                        background:key.decoration?.background||'#f5f5f5', color:key.decoration?.color||'#253044',
                        empty:binding(key)==='&none'};
            });
        }''')

    def evaluate(self, script):
        value = self.context.evaluate(script, -1)
        error = self.context.get_exception()
        if error:
            self.context.clear_exception()
            raise RuntimeError(error.get_message())
        return value

    def keys(self, state):
        return json.loads(self.evaluate('JSON.stringify(overlayKeys('+json.dumps(state)+'))').to_string())
