# Glove80 layer view

Live Linux layout display using Glorious Engrammer v52.

**Bluetooth/USB implementation and run instructions: [receiver/README.md](receiver/README.md).**

## Native learning overlay

Press **Super + F8** to toggle the keyboard-only overlay. Run `./glove80-overlay`
from this directory to do the same. Size, opacity, and placement are configurable;
see [overlay/README.md](overlay/README.md). No additional firmware change is required.

## Current status

- Original JSON, keymap, and combined UF2 are preserved in the project root.
- All 32 exported layers contain 80 keys. The saved UF2 has valid UF2 block
  framing and contains the left and right Glove80 family IDs. This is a format
  check, not proof that the firmware matches the exports or works on hardware.
- `preview/index.html` supports manual exploration when opened as a file and
  live updates when served by the receiver.
- Baseline firmware compiled successfully for both halves. The combined image is
  `firmware/output/glove80-baseline.uf2`. Its UF2 block numbering, counts, and
  board family IDs passed validation. Nothing has been flashed by this tool.
  Hardware behavior still needs testing.
- Bluetooth and USB telemetry firmware compiled successfully. The Linux receiver
  and live viewer pass automated checks; keyboard testing is still pending.

## Preview

Open `preview/index.html` in Brave or another browser for offline exploration,
or open the receiver URL for live layers. Hover a layer pill to preview it, click
to pin it, and use **Follow keyboard** to return to the keyboard's actual layers.
Transparent keys inherit from the active lower layers and layer 0. Hover or click
a key for its binding and description.

The last-input display captures browser-delivered keys while the page is focused.
Use the test field for composed text. No input is stored or sent to the server.
Custom behavior labels come from the export; the viewer does not emulate macros.

Regenerate after replacing the JSON export:

```sh
python scripts/make_preview.py 'Glorious Engrammer v52.json'
```

Geometry comes from MoErgo's `app/boards/arm/glove80/glove80-layouts.dtsi`
at commit `11454d23596afbdb06380a1125371b19ab65675c` (v25.11).

## Baseline firmware

The source version is pinned to MoErgo v25.11, matching the version in the
original UF2 filename. `firmware/config/glove80.keymap` is a byte-for-byte copy
of the export. The editor's `HID_POINTING=y` setting is represented by
`CONFIG_ZMK_POINTING=y`. Both halves compiled successfully; reproducing
an editor build does not guarantee byte-for-byte identical firmware.

The original file checksums are recorded in `firmware/original-checksums.json`.
Keep the saved UF2 as the restore image.

### Local build

The local build succeeded using Docker. The script now saves new baseline builds under `firmware/output/baseline/`.
It saves the image, build log,
and each half's generated Kconfig and devicetree for inspection:

```sh
bash scripts/build-firmware.sh
```

If Docker is stopped, start it in your own terminal:

```sh
sudo systemctl start docker.service
```

The pinned source is already checked out under `firmware/src`. For a fresh
checkout, clone MoErgo's v25.11 source there:

```sh
git clone --depth 1 --branch v25.11 https://github.com/moergo-sc/zmk.git firmware/src
git -C firmware/src rev-parse HEAD
```

Verify the commit matches the one above, then build from this directory:

```sh
docker run --rm --network host \
  -v "$PWD:/work" -w /work \
  nixos/nix:2.24.11 \
  sh -c 'nix-build firmware/config -o firmware/result && mkdir -p firmware/output && cp -L firmware/result/glove80.uf2 firmware/output/glove80-baseline.uf2'
```

The output must be copied out of the container's Nix store before the container
exits; `firmware/result` alone points inside that temporary store. The first
build downloads the toolchain and dependencies. Docker may require `sudo` on
your system. No build command flashes the keyboard.

### GitHub Actions alternative

`.github/workflows/build.yml` checks out the pinned source and builds both
halves as a combined UF2. The local project is based on `Huuums/glove80-zmk-config`, on branch
`glove80-layer-viewer`. `origin` points to that fork; `upstream` points to
`moergo-sc/glove80-zmk-config`. Local changes have not been pushed.
The baseline workflow uses `firmware/config`; the root `config` directory and
legacy build scripts are retained from the upstream template.

## Implementation status

The user confirmed the baseline works on hardware. Bluetooth/USB telemetry is
implemented as a build-time addition in `firmware/telemetry`, with the Linux
receiver in `receiver`. The telemetry build passed compilation and UF2 validation.
See [live setup and hardware checks](receiver/README.md) for the remaining test.

## References

- [MoErgo build template](https://github.com/moergo-sc/glove80-zmk-config)
- [Pinned firmware source](https://github.com/moergo-sc/zmk/tree/11454d23596afbdb06380a1125371b19ab65675c)
- [Layout export documentation](https://docs.moergo.com/layout-editor-guide/advanced-usage-export-import/)
