# Live layer display on Linux

The firmware extension and receiver support Bluetooth and USB serial. The
telemetry firmware compiled successfully on MoErgo v25.11. Protocol, receiver,
and viewer checks pass; end-to-end behavior on the keyboard is not yet verified.

## Build and flash

From the project root:

```sh
bash scripts/build-firmware.sh telemetry
```

Output: `firmware/output/telemetry/glove80-telemetry.uf2`.
The existing baseline image is preserved. New baseline builds use
`bash scripts/build-firmware.sh baseline` and write to `firmware/output/baseline/`.
The Docker volume `glove80-nix-cache` retains build dependencies between runs.

Flash the combined telemetry UF2 to both halves (right, then left) using
[MoErgo's procedure](https://docs.moergo.com/glove80-user-guide/customizing-key-layout/#loading-new-zmk-firmware-onto-your-glove80).
The left half gains telemetry; the right half uses the baseline configuration.

## Run

Dependencies are already installed in this project's `.venv`. On a fresh checkout:

```sh
python -m venv .venv
.venv/bin/pip install -r receiver/requirements.txt
```

For USB, connect the **left half** with a data cable:

```sh
.venv/bin/python receiver/main.py --usb
```

For Bluetooth, keep the keyboard paired and select this computer's profile.
Auto-detect the paired Glove80 (no address needed):

```sh
.venv/bin/python receiver/main.py --bluetooth
```

If you have multiple paired Glove80 keyboards, choose one explicitly:

```sh
.venv/bin/python receiver/main.py --list-bluetooth
.venv/bin/python receiver/main.py --bluetooth AA:BB:CC:DD:EE:FF
```

Replace the example address with your Glove80 address. To support switching
between USB and Bluetooth, enable both:

```sh
.venv/bin/python receiver/main.py --usb --bluetooth
```

Open **http://127.0.0.1:8765**. The viewer follows actual active layers by default.
Hover a layer pill for a temporary preview; click it to pin that layer.
Click **Follow keyboard** to return to live layers. Green dots show the keyboard's
actual active layers even while previewing. Stop the receiver with Ctrl+C.

A preview places the chosen layer above the currently active lower layers and
layer 0. Higher layers are excluded. Transparent bindings fall through those
lower layers; it does not activate every layer with a lower number. Previews
never change the firmware's state.

**Last input** shows browser-delivered keys and shortcuts while the page is
focused. The test field also accepts composed text. Layer messages do not change
this display. Input stays in the tab and is never sent to the receiver or saved.
Browser/desktop shortcuts intercepted before reaching the page cannot be shown;
the page cannot distinguish the Glove80 from another keyboard.

A fresh USB snapshot takes precedence; Bluetooth takes over if USB disconnects
or stops delivering updates. The keyboard's selected typing output is independent
of this choice. Packets expire after four seconds and the display dims when stale.
The receiver retries failed connections every two seconds.

Bluetooth uses BlueZ directly over D-Bus, including already-connected devices.
It subscribes to the custom characteristic without taking ownership of the HID
connection. Shutdown stops our subscription without disconnecting the keyboard.
Only the keyboard's active Bluetooth profile receives notifications.

## Troubleshooting

- **USB permission denied:** use your desktop/session's normal serial-device
  access setup. On Arch/CachyOS this commonly involves the `uucp` group and a new
  login session. Run the viewer as your ordinary user once access is configured.
- **USB not found:** confirm telemetry firmware is installed on the left half and
  that the cable carries data. Use `--usb /dev/ttyACM0` (or the actual path) if
  automatic discovery finds multiple serial ports. A `/dev/serial/by-id/…` path
  is more stable across reconnects.
- **Layer service missing:** confirm the left half has telemetry firmware.
  Disconnect/reconnect the keyboard in Bluetooth settings so BlueZ rediscovers
  services. If the old GATT database remains cached, removing and re-pairing the
  keyboard may be necessary. The tool does not clear pairings automatically.
- **Layout mismatch:** regenerate the viewer from the JSON that corresponds to
  the compiled keymap. Matching layer counts alone cannot detect two different
  layouts with the same number of layers.

## Protocol and implementation

Both transports now send a version-2, 9-byte snapshot. The receiver also accepts
the original version-1, 8-byte packets (modifier state unavailable).

| Offset | Contents |
| --- | --- |
| 0–1 | ASCII `GL` |
| 2 | Version `2` |
| 3 | Number of layers (1–32) |
| 4–7 | Unsigned little-endian active-layer mask |
| 8 | Effective HID modifier byte: Ctrl=0x11, Shift=0x22, Alt=0x44, Super=0x88 (left/right bit pairs) |

Modifier changes trigger snapshots immediately through a hook in ZMK’s HID
report update; this includes implicit and masked modifiers. The pinned ZMK
version does not actually emit its declared modifier-change event.

The default layer is included. Bit 31 is supported. Firmware snapshots are sent
on changes and once per second while a host is subscribed or the serial port has
DTR asserted. Rapid changes may coalesce to the latest state: this is a display
protocol, not a key-event recorder. Failed sends recover at the next heartbeat.
USB frames have a bounded queue and are streamed without console logging.

Bluetooth service: `64d90001-7e6b-4f7e-9c80-2f7d773a4b10`.
Read/notify characteristic: `64d90002-7e6b-4f7e-9c80-2f7d773a4b10`.
Reading and subscribing require an encrypted connection. No host-to-keyboard
configuration commands are exposed. USB requires no application request: opening
the data port with DTR asserted starts snapshots.

`firmware/telemetry/default.nix` adds the C file during the build. The upstream
source checkout stays unchanged, so this extension is reviewable in the config
fork without maintaining another fork of ZMK. The baseline build is unaffected.

The viewer resolves explicit transparent bindings through active lower layers.
It displays the exported custom labels; it does not interpret every macro or
modifier-dependent behavior, and no individual keypresses are reported.

## Validation

```sh
.venv/bin/python -m unittest discover -s tests -v
node tests/test_viewer.cjs
.venv/bin/python tests/check_http.py
```

The last check uses a temporary loopback HTTP server. Tests cover USB stream
boundaries, malformed packets, layer 31, stale data and transport fallback,
Bluetooth read/notification ordering and cleanup, and live viewer updates.

Previously validated version-1 telemetry image: left 354552 bytes flash / 106808 bytes RAM;
right 181620 bytes flash / 35972 bytes RAM. Valid UF2 sequences for left family
`0x9807b007` (1385 blocks) and right family `0x9808b007` (710 blocks).
The inherited Engrammer/upstream build warnings remain; compilation succeeds.

On hardware, check held layers on press **and release**, toggles, combined layers,
layer 31, unplug/replug, Bluetooth reconnect, and USB-to-Bluetooth fallback. Verify
typing continues normally, including after stopping the receiver.


## Engrammer helper labels and held modifiers

All 282 exported "Tap" labels were resolved from the matching compiled
`lh.dts`. Direct `&kp` helpers show their key. Recognized Engrammer helpers
that release all modifiers and tap two keys show a sequence such as `C → B`.
The key details preserve the original macro binding. Unknown macro shapes are
left unresolved, rather than substituting a guessed base-layer character.

The compiled resolution is stored in `preview/helper-bindings.json`, bound to
the JSON export by SHA-256. After changing and building a layout, regenerate it:

```sh
python scripts/resolve_helpers.py 'Glorious Engrammer v52.json' firmware/output/telemetry/lh.dts
python scripts/make_preview.py 'Glorious Engrammer v52.json'
```

Version-2 firmware adds live modifiers. Rebuild with `bash scripts/build-firmware.sh telemetry`,
verify the build, flash the resulting image, and restart the receiver before
refreshing the page. Until then, helper labels work but the page reports that
modifier state is unavailable. Version-2 compilation/hardware validation is pending.

Held Shift updates ordinary key legends, but is not applied to helpers that
release modifiers. Symbol rendering follows the export’s US keycodes; Caps Lock,
OS input-method transformations, and arbitrary custom macros are not emulated.
