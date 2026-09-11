# Glove80 learning overlay

A small executable launcher for the native GTK4/Wayland overlay. It uses the
same key-label JavaScript as the web viewer, evaluated through JavaScriptCore;
no browser process or browser window is needed. Keep the project folder in place.

## Use

**Super + F8** toggles the keyboard-only overlay in your Hyprland session.
It is click-through and never takes keyboard focus, so you keep typing in your
current application. It follows actual live layers; there are no preview controls
or input recorder in this window. A disconnected keyboard is visibly dimmed.

You can also run the executable from the project directory:

```sh
./glove80-overlay          # toggle (launches on first use)
./glove80-overlay show
./glove80-overlay hide
./glove80-overlay quit
```

The app stays running while hidden to make subsequent toggles quick. It uses an
existing receiver on port 8765, or starts `.venv/bin/python receiver/main.py --usb
--bluetooth` automatically if the receiver is unavailable. An existing receiver
is never stopped by the overlay. Quitting the overlay stops a receiver it started.
Receiver startup errors are written to `overlay/receiver.log`.

## Size, opacity, and placement

Defaults: **900 pixels wide, 85% opacity, bottom center, 35-pixel margin**.
Height follows the keyboard's aspect ratio.

Persist a different configuration (applies immediately if running):

```sh
./glove80-overlay configure --width 1100 --opacity 0.7 --position bottom-right
```

Or temporarily show it with different settings:

```sh
./glove80-overlay show --width 750 --opacity 0.9 --position top
```

Positions: `top`, `bottom`, `center`, `top-left`, `top-right`, `bottom-left`,
`bottom-right`. Use `--margin 20` to change edge spacing and `--monitor DP-1`
to choose an output. `--monitor ''` restores the compositor's default output.
Width is measured in Wayland logical pixels; display scaling applies normally.

Defaults are in `overlay/settings.json`; saved preferences are in the ignored
`overlay/settings.local.json`. Advanced settings include `receiver_port` and
`start_receiver`. Edit these before starting the app. Opacity is between 0.15 and
1.0. Size and opacity are applied to the whole overlay, including the key legends.

## Shortcut setup

The shortcut is a direct `hl.bind(...)` entry in
`~/.config/hypr/config/binds.lua`. Edit it there and run `hyprctl reload`.
It invokes the running app's D-Bus toggle action, falling back to launching
`./glove80-overlay` when needed.

To remove it, delete the Glove80 binding from `binds.lua`, reload Hyprland,
and run `./glove80-overlay quit`.

For a new checkout, `overlay/hyprland.lua` is an example binding. Adjust its
executable path, then run `python scripts/install-overlay-shortcut.py` and
`hyprctl reload`. The installer adds the binding directly to `binds.lua`,
backs it up as `binds.lua.glove80-backup`, and removes the old overlay `dofile`
entry if present. The live configuration does not depend on this repository.

## Dependencies and validation

The required system packages are already present on this CachyOS machine:
GTK4, gtk4-layer-shell, python-gobject, python-cairo, and JavaScriptCoreGTK 4.1.
The existing receiver virtual environment supplies its Bluetooth/serial packages.
This version targets Wayland compositors with layer-shell; it does not implement
an X11 or GNOME fallback.

Checks:

```sh
python tests/check_overlay_model.py
python tests/check_overlay.py
```

The first validates labels and settings without opening a window. The second
exercises an already running overlay in Hyprland, checks size and focus, and
leaves it hidden. Native rendering is Cairo/Pango; effective bindings and helper
labels are shared with the web viewer. Original editor attribution remains in
`preview/vendor/keymap-editor-LICENSE.txt`.
