"""GL snapshots: v1 layer mask (8 bytes), v2 adds HID modifiers (9 bytes)."""
import struct

SERVICE_UUID = '64d90001-7e6b-4f7e-9c80-2f7d773a4b10'
STATE_UUID = '64d90002-7e6b-4f7e-9c80-2f7d773a4b10'
PACKET = struct.Struct('<2sBBI')


def decode(data):
    if len(data) < PACKET.size:
        raise ValueError('Incomplete layer snapshot')
    magic, version, count, mask = PACKET.unpack(data[:PACKET.size])
    if magic != b'GL' or version not in (1, 2):
        raise ValueError('Unsupported layer protocol')
    if len(data) != (9 if version == 2 else 8):
        raise ValueError('Invalid snapshot length')
    if not 1 <= count <= 32 or mask == 0 or mask >> count:
        raise ValueError('Invalid layer count or mask')
    return {'layer_count': count, 'mask': mask,
            'modifiers': data[8] if version == 2 else None,
            'layers': [i for i in range(count) if mask & (1 << i)]}


class Decoder:
    """Recover complete frames from arbitrary USB read boundaries and noise."""
    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data):
        self.buffer.extend(data)
        frames = []
        while len(self.buffer) >= PACKET.size:
            size = 9 if self.buffer[:3] == b'GL\x02' else 8
            if len(self.buffer) < size:
                break
            try:
                frame = decode(self.buffer[:size])
            except ValueError:
                del self.buffer[0]
            else:
                frames.append(frame)
                del self.buffer[:size]
        return frames
