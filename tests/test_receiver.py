import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'receiver'))
from protocol import PACKET, Decoder, decode
from main import State, bluetooth_loop, select_bluetooth_device
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from protocol import STATE_UUID, SERVICE_UUID


class ProtocolTests(unittest.TestCase):
    def test_layer_31_and_base(self):
        self.assertEqual(decode(PACKET.pack(b'GL', 1, 32, 0x80000001))['layers'], [0, 31])

    def test_all_packet_boundaries_and_noise(self):
        frames = [PACKET.pack(b'GL', 1, 32, mask) for mask in (1, 0x80000001, 0x10001, 1)]
        stream = b'bad prefix' + b''.join(frames)
        for size in range(1, len(stream) + 1):
            decoder = Decoder()
            decoded = []
            for start in range(0, len(stream), size):
                decoded.extend(decoder.feed(stream[start:start + size]))
            self.assertEqual([f['mask'] for f in decoded], [1, 0x80000001, 0x10001, 1])

    def test_reject_incompatible_or_corrupt_frames(self):
        for packet in [b'', PACKET.pack(b'GL', 2, 32, 1), PACKET.pack(b'GL', 1, 0, 1),
                       PACKET.pack(b'GL', 1, 33, 1), PACKET.pack(b'GL', 1, 2, 4),
                       PACKET.pack(b'GL', 1, 32, 0)]:
            with self.assertRaises(ValueError):
                decode(packet)

    def test_invalid_frame_does_not_poison_following_frame(self):
        decoder = Decoder()
        frames = decoder.feed(PACKET.pack(b'GL', 99, 32, 1) + PACKET.pack(b'GL', 1, 32, 17))
        self.assertEqual([f['mask'] for f in frames], [17])
        self.assertLess(len(decoder.buffer), 8)

    def test_v2_modifiers_and_mixed_frame_boundaries(self):
        old = PACKET.pack(b'GL', 1, 32, 1)
        new = PACKET.pack(b'GL', 2, 32, 0x201) + bytes([0x22])
        released = PACKET.pack(b'GL', 2, 32, 1) + bytes([0])
        stream = old + new + released + old
        self.assertIsNone(decode(old)['modifiers'])
        self.assertEqual(decode(new)['modifiers'], 0x22)
        for size in range(1, len(stream) + 1):
            decoder = Decoder()
            frames = []
            for offset in range(0, len(stream), size):
                frames.extend(decoder.feed(stream[offset:offset + size]))
            self.assertEqual([f['modifiers'] for f in frames], [None, 0x22, 0, None])


class StateTests(unittest.TestCase):
    def test_staleness_and_usb_fallback(self):
        state = State()
        with patch('main.time.monotonic', return_value=0):
            state.update('usb', decode(PACKET.pack(b'GL', 1, 32, 1)))
        with patch('main.time.monotonic', return_value=2):
            state.update('bluetooth', decode(PACKET.pack(b'GL', 1, 32, 17)))
            self.assertEqual(state.snapshot()['transport'], 'usb')
        with patch('main.time.monotonic', return_value=4.1):
            self.assertEqual(state.snapshot()['transport'], 'bluetooth')
        with patch('main.time.monotonic', return_value=6.1):
            self.assertFalse(state.snapshot()['connected'])

    def test_error_clears_stale_layer_and_reconnect_clears_error(self):
        state = State()
        frame = decode(PACKET.pack(b'GL', 1, 32, 17))
        state.update('usb', frame)
        state.failed('usb', 'Disconnected')
        self.assertFalse(state.snapshot()['connected'])
        self.assertEqual(state.snapshot()['layers'], [])
        state.update('usb', frame)
        self.assertTrue(state.snapshot()['connected'])
        self.assertEqual(state.errors, {})


class DiscoveryTests(unittest.TestCase):
    def device(self, name='Glove80', paired=True, uuids=(), address='AA:BB'):
        return {'org.bluez.Device1': {key: SimpleNamespace(value=value) for key, value in
                dict(Name=name, Paired=paired, UUIDs=uuids, Address=address).items()}}

    def test_unique_paired_glove80(self):
        objects = {'/keyboard': self.device(), '/mouse': self.device('Mouse')}
        self.assertEqual(select_bluetooth_device(objects, 'auto')[0], '/keyboard')

    def test_renamed_keyboard_by_service(self):
        objects = {'/keyboard': self.device('My keyboard', uuids=[SERVICE_UUID])}
        self.assertEqual(select_bluetooth_device(objects, 'auto')[0], '/keyboard')

    def test_unpaired_and_ambiguous_rejected(self):
        for objects in [{'/keyboard': self.device(paired=False)},
                        {'/one': self.device(), '/two': self.device(address='CC:DD')}]:
            with self.assertRaises(RuntimeError):
                select_bluetooth_device(objects, 'auto')

    def test_explicit_address_overrides_name(self):
        objects = {'/keyboard': self.device('Renamed'), '/other': self.device(address='CC:DD')}
        self.assertEqual(select_bluetooth_device(objects, 'aa:bb')[0], '/keyboard')


class BluetoothTests(unittest.IsolatedAsyncioTestCase):
    async def test_read_race_and_cleanup_preserve_hid_connection(self):
        address = 'AA:BB:CC:DD:EE:FF'
        device_path = '/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF'
        char_path = device_path + '/service001/char001'
        variant = lambda value: SimpleNamespace(value=value)
        objects = {
            device_path: {'org.bluez.Device1': {
                'Address': variant(address), 'Paired': variant(True), 'Connected': variant(True)}},
            char_path: {'org.bluez.GattCharacteristic1': {'UUID': variant(STATE_UUID)}}}
        callback = None
        def register(fn):
            nonlocal callback
            callback = fn
        async def read(options):
            callback('org.bluez.GattCharacteristic1',
                     {'Value': variant(PACKET.pack(b'GL', 1, 32, 0x80000001))}, [])
            return PACKET.pack(b'GL', 1, 32, 1)
        characteristic = SimpleNamespace(call_start_notify=AsyncMock(),
                                         call_stop_notify=AsyncMock(), call_read_value=read)
        device = SimpleNamespace(call_connect=AsyncMock(), call_disconnect=AsyncMock())
        interfaces = {
            'org.freedesktop.DBus.ObjectManager': SimpleNamespace(call_get_managed_objects=AsyncMock(return_value=objects)),
            'org.freedesktop.DBus.Properties': SimpleNamespace(on_properties_changed=register),
            'org.bluez.GattCharacteristic1': characteristic,
            'org.bluez.Device1': device}
        disconnected = []
        bus = SimpleNamespace(introspect=AsyncMock(return_value=None),
                              get_proxy_object=lambda *args: SimpleNamespace(get_interface=interfaces.__getitem__),
                              disconnect=lambda: disconnected.append(True))
        factory = SimpleNamespace(connect=AsyncMock(return_value=bus))
        state = State()
        with patch('dbus_fast.aio.MessageBus', return_value=factory), \
             patch('main.asyncio.sleep', new=AsyncMock(side_effect=asyncio.CancelledError)):
            with self.assertRaises(asyncio.CancelledError):
                await bluetooth_loop(address, state)
        self.assertEqual(state.snapshot()['layers'], [0, 31])
        device.call_connect.assert_not_awaited()
        device.call_disconnect.assert_not_awaited()
        characteristic.call_start_notify.assert_awaited_once()
        characteristic.call_stop_notify.assert_awaited_once()
        self.assertEqual(disconnected, [True])


if __name__ == '__main__':
    unittest.main()
