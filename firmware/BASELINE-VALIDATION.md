# Baseline validation

The user-run Docker build completed successfully for MoErgo v25.11 and the
unchanged Glorious Engrammer v52 keymap export.

Checks performed:

- Original JSON, keymap, and UF2 SHA-256 values still match the saved checksums.
- Build keymap is byte-for-byte identical to the original keymap export.
- USB and Bluetooth enabled on the left half; left is the split central.
- Bluetooth enabled on the right half; right is the split peripheral.
- Pointing enabled on both halves; maximum RGB brightness remains 80.
- Combined UF2 has complete block sequences for both board families:
  left `0x9807b007` (1370 blocks), right `0x9808b007` (710 blocks).
- Left build: 350656 bytes flash, 100560 bytes RAM.
- Right build: 181620 bytes flash, 35972 bytes RAM.

The build emitted warnings, including modifier masks narrowed to 8 bits in
Engrammer mod-morph behaviors, pointing macro redefinitions, an upstream
deprecated configuration symbol, and linker RWX segment warnings. Compilation
succeeded, but this is not a warning-free build or a hardware validation.

The baseline has no layer telemetry extension. Test typing on both halves,
layer switching, hold-taps, mouse keys, and Bluetooth/USB operation before
using it as the reference for the telemetry build.

Flash the same combined image to both halves, right first then left, following
[MoErgo's instructions](https://docs.moergo.com/glove80-user-guide/customizing-key-layout/#loading-new-zmk-firmware-onto-your-glove80).
Use the documented power-up bootloader method if custom bindings differ from
the default layout. The original UF2 in the project root remains available
for restoration.
