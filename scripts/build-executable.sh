#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"
if [[ ! -x .build-venv/bin/pyinstaller ]]; then
    /usr/bin/python -m venv --system-site-packages .build-venv
    .build-venv/bin/pip install pyinstaller -r receiver/requirements.txt
fi
mkdir -p build
PYINSTALLER_CONFIG_DIR="$project_dir/build/pyinstaller-cache" \
    .build-venv/bin/python -m PyInstaller --noconfirm packaging/glove80-overlay.spec 2>&1 | tee build/executable.log
./dist/glove80-overlay --self-test
