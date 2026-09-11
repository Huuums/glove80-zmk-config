"""Single-file entry point for both native overlay and background receiver."""
import sys

if '--receiver' in sys.argv:
    sys.argv.remove('--receiver')
    from main import main
elif '--self-test' in sys.argv:
    from model import KeyboardModel, load_settings
    from protocol import decode
    import json
    model = KeyboardModel()
    keys = model.keys({'connected': True, 'layers': [0, 9], 'modifiers': 2})
    assert len(keys) == 80
    assert keys[39]['label'] == 'E → -'
    assert decode(b'GL\x02\x20\x01\x00\x00\x00\x02')['modifiers'] == 2
    import dbus_fast, serial
    print(json.dumps({'status':'ok','keys':len(keys),'settings':load_settings()}, ensure_ascii=False))
    raise SystemExit(0)
else:
    from app import main

main()
