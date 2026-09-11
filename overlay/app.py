#!/usr/bin/env python3
"""Hyprland/Wayland keyboard overlay. Run again to toggle; use 'quit' to stop."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import urllib.request

from model import ROOT, FROZEN, KeyboardModel, load_settings, settings_path, receiver_log_path

# Load layer-shell before GTK/libwayland (required by its Python bindings).
from ctypes import CDLL
CDLL(str(ROOT/"libgtk4-layer-shell.so") if FROZEN and (ROOT/"libgtk4-layer-shell.so").exists() else "libgtk4-layer-shell.so")
os.environ["GDK_BACKEND"] = "wayland"
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Gtk4LayerShell', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk4LayerShell as LayerShell
from gi.repository import Gtk, Gio, GLib, Gdk, Pango, PangoCairo


def arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', choices=['toggle', 'show', 'hide', 'quit', 'configure'], default='toggle')
    parser.add_argument('--width', type=int)
    parser.add_argument('--opacity', type=float)
    parser.add_argument('--position', choices=['top', 'bottom', 'center', 'top-left', 'top-right', 'bottom-left', 'bottom-right'])
    parser.add_argument('--margin', type=int)
    parser.add_argument('--monitor', help='Wayland output connector, e.g. DP-1; empty uses compositor default')
    return parser.parse_args(argv)


def rgba(value):
    color = Gdk.RGBA()
    if not color.parse(value):
        color.parse('#f5f5f5')
    return color.red, color.green, color.blue, color.alpha


def rounded(cr, x, y, width, height, radius):
    cr.new_sub_path()
    for cx, cy, start in [(x+width-radius, y+radius, -90), (x+width-radius, y+height-radius, 0),
                          (x+radius, y+height-radius, 90), (x+radius, y+radius, 180)]:
        cr.arc(cx, cy, radius, math.radians(start), math.radians(start+90))
    cr.close_path()


class Overlay(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='com.glove80.LayerOverlay', flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.window = None
        self.settings = load_settings()
        self.model = KeyboardModel()
        self.state = {'connected': False, 'layers': [0]}
        self.keys = self.model.keys(self.state)
        self.signature = None
        self.latest = None
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.receiver = None
        self.held = False

    def do_startup(self):
        Gtk.Application.do_startup(self)
        action = Gio.SimpleAction.new('toggle', None)
        action.connect('activate', self.toggle_action)
        self.add_action(action)

    def toggle_action(self, *_):
        self.settings = load_settings()
        if self.window is None:
            self.setup()
        self.apply_settings()
        self.window.set_visible(not self.window.get_visible())

    def do_command_line(self, command_line):
        try:
            args = arguments(command_line.get_arguments()[1:])
            if args.command == 'quit':
                self.quit()
                return 0
            overrides = {k: v for k, v in vars(args).items() if k != 'command' and v is not None}
            self.settings = load_settings(overrides)
            if args.command == 'configure':
                settings_path().parent.mkdir(parents=True, exist_ok=True)
                settings_path().write_text(json.dumps(self.settings, indent=2)+'\n')
            if self.window is None:
                self.setup()
            self.apply_settings()
            if args.command == 'show':
                self.window.set_visible(True)
            elif args.command == 'hide':
                self.window.set_visible(False)
            elif args.command == 'toggle':
                self.window.set_visible(not self.window.get_visible())
            return 0
        except (ValueError, RuntimeError, OSError) as error:
            command_line.printerr_literal(str(error)+'\n')
            if self.window is None:
                self.quit()
            return 1

    def setup(self):
        if not LayerShell.is_supported():
            raise RuntimeError('This overlay requires a Wayland compositor with layer-shell support (such as Hyprland).')
        self.hold()
        self.held = True
        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_title('Glove80 keyboard overlay')
        self.window.set_decorated(False)
        self.window.add_css_class('glove80-overlay')
        css = Gtk.CssProvider()
        css.load_from_data(b'window.glove80-overlay { background: transparent; box-shadow: none; }')
        Gtk.StyleContext.add_provider_for_display(self.window.get_display(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        LayerShell.init_for_window(self.window)
        LayerShell.set_namespace(self.window, 'glove80-overlay')
        LayerShell.set_layer(self.window, LayerShell.Layer.OVERLAY)
        LayerShell.set_keyboard_mode(self.window, LayerShell.KeyboardMode.NONE)
        LayerShell.set_exclusive_zone(self.window, 0)
        self.area = Gtk.DrawingArea()
        self.area.set_draw_func(self.draw)
        self.area.set_can_target(False)
        self.area.set_focusable(False)
        self.window.set_child(self.area)
        self.window.connect('realize', self.click_through)
        GLib.timeout_add(100, self.tick)
        threading.Thread(target=self.receive, daemon=True).start()

    def click_through(self, *_):
        import cairo
        self.window.get_surface().set_input_region(cairo.Region())

    def apply_settings(self):
        width = self.settings['width']
        self.window.set_default_size(width, round(width*890/1860))
        self.area.set_content_width(width)
        self.area.set_content_height(round(width*890/1860))
        self.window.set_opacity(self.settings['opacity'])
        position = self.settings['position']
        for name, edge in [('top', LayerShell.Edge.TOP), ('bottom', LayerShell.Edge.BOTTOM),
                           ('left', LayerShell.Edge.LEFT), ('right', LayerShell.Edge.RIGHT)]:
            LayerShell.set_anchor(self.window, edge, name in position)
            LayerShell.set_margin(self.window, edge, self.settings['margin'])
        monitor_name = self.settings['monitor']
        monitor = None
        monitors = self.window.get_display().get_monitors()
        if monitor_name:
            monitor = next((monitors.get_item(i) for i in range(monitors.get_n_items())
                            if monitors.get_item(i).get_connector() == monitor_name), None)
            if monitor is None:
                raise ValueError(f'Monitor not found: {monitor_name}')
        LayerShell.set_monitor(self.window, monitor)
        self.area.queue_draw()

    def receive(self):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        attempted = False
        while not self.stop.is_set():
            try:
                port = self.settings['receiver_port']
                with opener.open(f'http://127.0.0.1:{port}/state', timeout=0.7) as response:
                    state = json.load(response)
                if state.get('connected') and state.get('layer_count') != len(self.model.data['layers']):
                    state = {'connected': False, 'error': 'Layout mismatch'}
            except Exception:
                state = {'connected': False, 'error': 'Receiver unavailable'}
                if not attempted and self.settings['start_receiver']:
                    attempted = True
                    python = ROOT / '.venv/bin/python'
                    if FROZEN or python.exists():
                        log_path = receiver_log_path()
                        log_path.parent.mkdir(parents=True, exist_ok=True)
                        command = [sys.executable, '--receiver'] if FROZEN else [str(python), str(ROOT/'receiver/main.py')]
                        with log_path.open('a') as log:
                            self.receiver = subprocess.Popen(command + ['--usb', '--bluetooth', '--port', str(port)],
                                                             stdout=log, stderr=log, start_new_session=True)
            with self.lock:
                self.latest = state
            self.stop.wait(0.15)

    def tick(self):
        with self.lock:
            state = self.latest
        if state is not None:
            signature = json.dumps(state, sort_keys=True)
            if signature != self.signature:
                self.signature = signature
                if not state.get('connected'):
                    state = dict(state, layers=self.state.get('layers', [0]))
                self.state = state
                self.keys = self.model.keys(state)
                self.area.queue_draw()
        return True

    def text(self, cr, text, x, y, width, size, color):
        layout = PangoCairo.create_layout(cr)
        font = Pango.FontDescription('Sans')
        font.set_absolute_size(size*Pango.SCALE)
        layout.set_font_description(font)
        layout.set_width(int(width*Pango.SCALE))
        layout.set_ellipsize(Pango.EllipsizeMode.END)
        layout.set_alignment(Pango.Alignment.CENTER)
        layout.set_text(text, -1)
        _, height = layout.get_pixel_size()
        cr.set_source_rgba(*rgba(color))
        cr.move_to(x, y-height/2)
        PangoCairo.show_layout(cr, layout)

    def draw(self, area, cr, width, height):
        scale = min(width/1860, height/890)
        cr.translate((width-1860*scale)/2, (height-890*scale)/2)
        cr.scale(scale, scale)
        cr.translate(30, 30)
        cr.push_group()
        for key in self.keys:
            w,h,x,y,angle,rx,ry = key['geometry']
            cr.save()
            cr.translate(rx,ry); cr.rotate(math.radians(angle/100)); cr.translate(-rx,-ry)
            rounded(cr,x+4,y+3,w-8,h-9,6)
            cr.set_source_rgba(*rgba(key['background'])); cr.fill_preserve()
            cr.set_source_rgba(0.4,0.46,0.56,0.7); cr.set_line_width(1.5); cr.stroke()
            label = key['label']
            size = 29 if len(label)==1 else 13 if len(label)>10 else 16 if len(label)>6 else 20
            self.text(cr,label,x+8,y+h/2,w-16,size,key['color'])
            if key['icon']:
                self.text(cr,key['icon'],x+w-29,y+20,20,12,key['color'])
            cr.restore()
        cr.pop_group_to_source()
        cr.paint_with_alpha(1 if self.state.get('connected') else 0.4)
        if not self.state.get('connected'):
            self.text(cr,self.state.get('error','Keyboard disconnected'),500,25,800,23,'#e75e5e')

    def do_shutdown(self):
        self.stop.set()
        if self.receiver is not None and self.receiver.poll() is None:
            self.receiver.terminate()
        Gtk.Application.do_shutdown(self)


def main():
    # Let --help work without opening a display or starting the receiver.
    if '--help' in sys.argv or '-h' in sys.argv:
        arguments(sys.argv[1:])
    raise SystemExit(Overlay().run(sys.argv))


if __name__ == '__main__':
    main()
