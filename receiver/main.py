"""Local Glove80 layer receiver. Uses BlueZ's existing keyboard connection."""
import argparse
import asyncio
import json
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from protocol import Decoder, SERVICE_UUID, STATE_UUID, decode

ROOT = Path(__file__).resolve().parents[1]
STALE_SECONDS = 4


class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.frames = {}
        self.errors = {}

    def update(self, source, frame):
        with self.lock:
            self.frames[source] = (time.monotonic(), frame)
            self.errors.pop(source, None)

    def failed(self, source, error):
        with self.lock:
            self.frames.pop(source, None)
            self.errors[source] = str(error)

    def snapshot(self):
        with self.lock:
            now = time.monotonic()
            # A fresh USB snapshot wins when both transports are enabled.
            for source in ('usb', 'bluetooth'):
                if source in self.frames:
                    timestamp, frame = self.frames[source]
                    if now - timestamp < STALE_SECONDS:
                        return dict(frame, connected=True, transport=source)
            return {'connected': False, 'layers': [], 'errors': dict(self.errors)}


def serve(state, port):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            # No directory listing, arbitrary file reads, or cross-origin API.
            actual_port = self.server.server_port
            if self.headers.get('Host') not in (f'127.0.0.1:{actual_port}', f'localhost:{actual_port}'):
                self.send_error(403)
                return
            if self.path == '/state':
                content = json.dumps(state.snapshot()).encode()
                kind = 'application/json'
            elif self.path in ('/', '/index.html'):
                content = (ROOT / 'preview/index.html').read_bytes()
                kind = 'text/html; charset=utf-8'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


async def usb_loop(port, state):
    import serial
    from serial.tools import list_ports
    while True:
        stream = None
        try:
            selected = port
            if port == 'auto':
                matches = [p.device for p in list_ports.comports()
                           if p.vid == 0x16c0 and p.pid == 0x27db]
                if len(matches) != 1:
                    raise RuntimeError('Expected one Glove80 USB serial port; use --usb /dev/ttyACM…')
                selected = matches[0]
            stream = serial.Serial(selected, 115200, timeout=0.25, exclusive=True)
            stream.dtr = True
            decoder = Decoder()
            while True:
                chunk = await asyncio.to_thread(stream.read, 256)
                for frame in decoder.feed(chunk):
                    state.update('usb', frame)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            state.failed('usb', exc)
            await asyncio.sleep(2)
        finally:
            if stream is not None:
                stream.close()


async def bluez_objects(bus):
    intro = await bus.introspect('org.bluez', '/')
    proxy = bus.get_proxy_object('org.bluez', '/', intro)
    return await proxy.get_interface('org.freedesktop.DBus.ObjectManager').call_get_managed_objects()


async def list_devices():
    from dbus_fast.aio import MessageBus
    from dbus_fast.constants import BusType
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    try:
        objects = await bluez_objects(bus)
        for interfaces in objects.values():
            props = interfaces.get('org.bluez.Device1')
            if props:
                print(props['Address'].value, props.get('Name', props['Address']).value,
                      'paired' if props.get('Paired') and props['Paired'].value else 'unpaired')
    finally:
        bus.disconnect()


def select_bluetooth_device(objects, address):
    devices = [(path, interfaces['org.bluez.Device1']) for path, interfaces in objects.items()
               if 'org.bluez.Device1' in interfaces]
    if address != 'auto':
        matches = [(path, props) for path, props in devices
                   if props['Address'].value.lower() == address.lower()]
    else:
        matches = []
        for path, props in devices:
            paired = props.get('Paired') and props['Paired'].value
            names = [props[key].value.lower() for key in ('Name', 'Alias') if key in props]
            uuids = [uuid.lower() for uuid in props['UUIDs'].value] if 'UUIDs' in props else []
            if paired and (any('glove80' in name for name in names) or SERVICE_UUID in uuids):
                matches.append((path, props))
    if not matches:
        raise RuntimeError('No matching paired Glove80 found. Pair it in Bluetooth settings or specify --bluetooth ADDRESS.')
    if len(matches) > 1:
        addresses = ', '.join(props['Address'].value for _, props in matches)
        raise RuntimeError(f'Multiple matching keyboards found ({addresses}). Specify --bluetooth ADDRESS.')
    return matches[0]


async def bluetooth_loop(address, state):
    from dbus_fast.aio import MessageBus
    from dbus_fast.constants import BusType
    while True:
        bus = None
        characteristic = None
        subscribed = False
        try:
            bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
            objects = await bluez_objects(bus)
            device_path, props = select_bluetooth_device(objects, address)
            # Keep the selected keyboard on retries; do not switch devices silently.
            address = props['Address'].value
            if not props['Paired'].value:
                raise RuntimeError('Pair the keyboard in desktop Bluetooth settings first.')
            intro = await bus.introspect('org.bluez', device_path)
            device = bus.get_proxy_object('org.bluez', device_path, intro).get_interface('org.bluez.Device1')
            if not props['Connected'].value:
                await asyncio.wait_for(device.call_connect(), 20)
            char_path = None
            for _ in range(40):
                objects = await bluez_objects(bus)
                char_path = next((path for path, interfaces in objects.items()
                                  if path.startswith(device_path + '/') and
                                  'org.bluez.GattCharacteristic1' in interfaces and
                                  interfaces['org.bluez.GattCharacteristic1']['UUID'].value == STATE_UUID), None)
                if char_path:
                    break
                await asyncio.sleep(0.25)
            if not char_path:
                raise RuntimeError('Layer service missing. Check telemetry firmware and BlueZ service cache.')
            intro = await bus.introspect('org.bluez', char_path)
            proxy = bus.get_proxy_object('org.bluez', char_path, intro)
            characteristic = proxy.get_interface('org.bluez.GattCharacteristic1')
            properties = proxy.get_interface('org.freedesktop.DBus.Properties')
            notifications = 0

            def received(interface, changed, invalidated):
                nonlocal notifications
                if interface == 'org.bluez.GattCharacteristic1' and 'Value' in changed:
                    try:
                        state.update('bluetooth', decode(bytes(changed['Value'].value)))
                        notifications += 1
                    except ValueError as exc:
                        state.failed('bluetooth', exc)

            properties.on_properties_changed(received)
            await characteristic.call_start_notify()
            subscribed = True
            before = notifications
            initial = await characteristic.call_read_value({})
            # Do not overwrite a newer notification with an older read response.
            if notifications == before:
                state.update('bluetooth', decode(bytes(initial)))
            while True:
                await asyncio.sleep(2)
                objects = await bluez_objects(bus)
                props = objects.get(device_path, {}).get('org.bluez.Device1', {})
                if not props.get('Connected') or not props['Connected'].value:
                    raise RuntimeError('Keyboard disconnected')
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            state.failed('bluetooth', exc)
            await asyncio.sleep(2)
        finally:
            if subscribed:
                try:
                    await asyncio.wait_for(characteristic.call_stop_notify(), 2)
                except Exception:
                    pass
            # Release our D-Bus subscription, not the shared HID connection.
            if bus is not None:
                bus.disconnect()


async def run(args):
    if args.list_bluetooth:
        await list_devices()
        return
    state = State()
    server = serve(state, args.port)
    print(f'Open http://127.0.0.1:{args.port} — waiting for layer telemetry', flush=True)
    tasks = []
    if args.usb:
        tasks.append(usb_loop(args.usb, state))
    if args.bluetooth:
        tasks.append(bluetooth_loop(args.bluetooth, state))
    try:
        await asyncio.gather(*tasks)
    finally:
        server.shutdown()
        server.server_close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--usb', nargs='?', const='auto', help='USB device path, or auto-detect if omitted')
    parser.add_argument('--bluetooth', nargs='?', const='auto', metavar='ADDRESS',
                        help='Auto-detect a paired Glove80, or specify its Bluetooth address')
    parser.add_argument('--list-bluetooth', action='store_true')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not args.usb and not args.bluetooth and not args.list_bluetooth:
        parser.error('Specify --usb, --bluetooth [ADDRESS], or --list-bluetooth')
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
