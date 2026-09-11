# Glove80 learning overlay

A standalone Linux executable for the native GTK4/Wayland overlay. It uses the
same key-label JavaScript as the web viewer, evaluated through JavaScriptCore;
no browser process or browser window is needed. The PyInstaller package bundles
Python, libraries, the receiver, and the current layout into one executable.
You can copy `dist/glove80-overlay` elsewhere without the project or virtual environment.

## Use

**Super + F8** toggles the keyboard-only overlay in your Hyprland session.
It is click-through and never takes keyboard focus, so you keep typing in your
current application. It follows actual live layers; there are no preview controls
or input recorder in this window. A disconnected keyboard is visibly dimmed.

The installed executable is `~/.local/bin/glove80-overlay`. Run it from any directory:

```sh
~/.local/bin/glove80-overlay          # toggle (launches on first use)
~/.local/bin/glove80-overlay show
~/.local/bin/glove80-overlay hide
~/.local/bin/glove80-overlay quit
```

The app stays running while hidden. Super+F8 sends a small D-Bus action directly
to that running app, avoiding executable extraction and Python/GTK startup on
every press. If the app is stopped, the shortcut launches it; that first press
still includes startup time. It uses an
existing receiver on port 8765, or starts its bundled receiver with USB and Bluetooth auto-detection if the receiver is unavailable. An existing receiver
is never stopped by the overlay. Quitting the overlay stops a receiver it started.
Receiver startup errors are written to `~/.local/state/glove80-overlay/receiver.log`
(or under `$XDG_STATE_HOME`).

## Size, opacity, and placement

Defaults: **900 pixels wide, 85% opacity, bottom center, 35-pixel margin**.
Height follows the keyboard's aspect ratio.

Persist a different configuration (applies immediately if running):

```sh
~/.local/bin/glove80-overlay configure --width 1100 --opacity 0.7 --position bottom-right
```

Or temporarily show it with different settings:

```sh
~/.local/bin/glove80-overlay show --width 750 --opacity 0.9 --position top
```

Positions: `top`, `bottom`, `center`, `top-left`, `top-right`, `bottom-left`,
`bottom-right`. Use `--margin 20` to change edge spacing and `--monitor DP-1`
to choose an output. `--monitor ''` restores the compositor's default output.
Width is measured in Wayland logical pixels; display scaling applies normally.

Defaults are bundled from `overlay/settings.json`; saved preferences are in
`~/.config/glove80-overlay/settings.json` (or under `$XDG_CONFIG_HOME`). Advanced settings include `receiver_port` and
`start_receiver`. Edit these before starting the app. Opacity is between 0.15 and
1.0. Size and opacity are applied to the whole overlay, including the key legends.

## Shortcut setup

The shortcut is a direct `hl.bind(...)` entry in
`~/.config/hypr/config/binds.lua`. Edit it there and run `hyprctl reload`.
It invokes the running app's D-Bus toggle action, falling back to launching
`~/.local/bin/glove80-overlay` when needed.

To remove it, delete the Glove80 binding from `binds.lua`, reload Hyprland,
and run `~/.local/bin/glove80-overlay quit`.

For a new checkout, `overlay/hyprland.lua` is an example binding. Adjust its
executable path, then run `python scripts/install-overlay-shortcut.py` and
`hyprctl reload`. The installer adds the binding directly to `binds.lua`,
backs it up as `binds.lua.glove80-backup`, and removes the old overlay `dofile`
entry if present. The live configuration does not depend on this repository.

## Build and validation

Build the executable with:

```sh
bash scripts/build-executable.sh
install -Dm755 dist/glove80-overlay ~/.local/bin/glove80-overlay
~/.local/bin/glove80-overlay --self-test
```

The output is about 59 MB. Rebuild after changing the layout or application.
This is a packaged Python application, not Python translated into native machine
code. It was built and tested on this x86-64 CachyOS system; compatibility with
older Linux distributions is not guaranteed.

For development, `./glove80-overlay` remains the source launcher and stores
preferences in `overlay/settings.local.json`. Its required system packages are already present on this CachyOS machine:
GTK4, gtk4-layer-shell, python-gobject, python-cairo, and JavaScriptCoreGTK 4.1.
The source launcher uses the receiver virtual environment for Bluetooth/serial packages.
The standalone build includes those packages.
This version targets Wayland compositors with layer-shell; it does not implement
an X11 or GNOME fallback.

Checks:

```sh
python tests/check_overlay_model.py
GLOVE80_OVERLAY_EXECUTABLE="$HOME/.local/bin/glove80-overlay" python tests/check_overlay.py
```

The first validates labels and settings without opening a window. The second
exercises an already running overlay in Hyprland, checks size and focus, and
leaves it hidden. Native rendering is Cairo/Pango; effective bindings and helper
labels are shared with the web viewer. Original editor attribution remains in
`preview/vendor/keymap-editor-LICENSE.txt`.
