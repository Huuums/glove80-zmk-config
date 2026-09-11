# Glove80 custom firmware

Glorious Engrammer v52 layout with optional Bluetooth/USB layer telemetry.

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

## References

- [MoErgo build template](https://github.com/moergo-sc/glove80-zmk-config)
- [Pinned firmware source](https://github.com/moergo-sc/zmk/tree/11454d23596afbdb06380a1125371b19ab65675c)
- [Layout export documentation](https://docs.moergo.com/layout-editor-guide/advanced-usage-export-import/)
