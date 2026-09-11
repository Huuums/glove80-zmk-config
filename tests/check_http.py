"""Integration check: bind a temporary loopback server; no keyboard access."""
import http.client
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'receiver'))
from main import State, serve
from protocol import PACKET, decode

state = State()
server = serve(state, 0)
try:
    conn = http.client.HTTPConnection('127.0.0.1', server.server_port)
    conn.request('GET', '/state')
    response = conn.getresponse()
    assert response.status == 200 and not json.loads(response.read())['connected']
    state.update('usb', decode(PACKET.pack(b'GL', 1, 32, 0x80000001)))
    conn.request('GET', '/state')
    assert json.loads(conn.getresponse().read())['layers'] == [0, 31]
    conn.request('GET', '/')
    response = conn.getresponse()
    assert response.status == 200 and b'Follow keyboard' in response.read()
    conn.request('GET', '/state', headers={'Host': 'untrusted.example'})
    response = conn.getresponse()
    assert response.status == 403
    response.read()
    conn.request('GET', '/../README.md')
    response = conn.getresponse()
    assert response.status == 404
    response.read()
    conn.close()
    print('HTTP passed: offline state, live snapshot, viewer, host and path restrictions.')
finally:
    server.shutdown()
    server.server_close()
