#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
variant="${1:-baseline}"
case "$variant" in baseline|telemetry) ;; *) echo "Usage: $0 [baseline|telemetry]" >&2; exit 2;; esac
output_dir="$project_dir/firmware/output/$variant"
mkdir -p "$output_dir"

docker_command=(docker)
if ! docker info >/dev/null 2>&1; then
    echo 'Docker requires administrator access. Authenticate in this terminal.'
    sudo -v
    docker_command=(sudo docker)
fi

# Copy artifacts out before the temporary container's Nix store disappears.
# Retain generated Kconfig and devicetree files for baseline validation too.
"${docker_command[@]}" run --rm --network host \
    -v "$project_dir:/work" -v glove80-nix-cache:/nix -e VARIANT="$variant" -w /work \
    nixos/nix:2.24.11 sh -c '
      set -eu
      destination="firmware/output/$VARIANT"
      if [ "$VARIANT" = telemetry ]; then
        nix-build firmware/telemetry -o firmware/result-telemetry
        cp --remove-destination -L firmware/result-telemetry/glove80.uf2 "$destination/glove80-telemetry.uf2"
      else
        nix-build firmware/config -o firmware/result
        cp --remove-destination -L firmware/result/glove80.uf2 "$destination/glove80-baseline.uf2"
      fi
      for side in lh rh; do
        if [ "$VARIANT" = telemetry ]; then
          nix-build firmware/telemetry --argstr side "$side" -o "firmware/result-telemetry-$side"
          result="firmware/result-telemetry-$side"
        else
          nix-build --expr "let firmware = import ./firmware/src {}; in firmware.zmk.override { board = \"glove80_$side\"; keymap = ./firmware/config/glove80.keymap; kconfig = ./firmware/config/glove80.conf; }" -o "firmware/result-$side"
          result="firmware/result-$side"
        fi
        cp --remove-destination -L "$result/zmk.kconfig" "$destination/$side.kconfig"
        cp --remove-destination -L "$result/zmk.dts" "$destination/$side.dts"
      done
    ' 2>&1 | tee "$output_dir/build.log"

echo "Firmware and build log saved in $output_dir"
