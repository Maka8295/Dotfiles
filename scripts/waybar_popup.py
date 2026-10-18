# Shared bits of the waybar popups (music-panel.py, calendar-panel.py): a dungeonOS panel
# window that opens next to the bar at the clicked module, on whichever side the bar is.
# Running the same popup again, Escape, or clicking away closes it.

import os
import signal
import subprocess

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell  # noqa: E402

LAYOUT_STATE = os.path.join(
    os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state")), "waybar-layout"
)

# the panel frame from waybar/style.css; each popup adds its own CSS after this
BASE_CSS = """
window {
    background: #1A1816;
    border: 1px solid #7E705D;
    box-shadow: inset 0 0 0 2px #141210, inset 0 0 0 3px #463D34;
    color: #C8B8A0;
}
#body { padding: 14px 16px; }
label { color: #C8B8A0; }
button {
    background: transparent;
    border: none;
    border-radius: 0;
    box-shadow: none;
    color: #9D8E7C;
    padding: 4px 10px;
    min-width: 0;
    min-height: 0;
}
button:hover {
    background: #463D34;
    color: #C8B8A0;
    box-shadow: inset 0 0 0 3px #1A1816;
}
"""


def run(*cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=1).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def open_or_empty(path):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return ""


class Popup(Gtk.Window):
    """Layer-shell panel placed next to the bar, lined up with the cursor."""

    def __init__(self, namespace):
        super().__init__()
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_namespace(self, namespace)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.ON_DEMAND)
        self.place()
        self.connect("key-press-event", self.on_key)
        self.connect("focus-out-event", lambda *_: self.close_soon())

    def place(self):
        try:
            x, y = (int(v) for v in run("hyprctl", "cursorpos").replace(",", " ").split())
        except ValueError:
            x, y = 0, 0
        vertical = open_or_empty(LAYOUT_STATE).strip() != "horizontal"
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        # margins count from the edge of the space the bar leaves free
        if vertical:
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, 4)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, max(10, y - 40))
        else:
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 4)
            GtkLayerShell.set_margin(self, GtkLayerShell.Edge.LEFT, max(10, x - 40))

    def on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()

    def close_soon(self):
        # clicking a slider can briefly move focus, so only close if it stays away
        GLib.timeout_add(150, lambda: (None if self.has_toplevel_focus() else Gtk.main_quit()))


def run_popup(name, make_window, css):
    """Open the popup, or close it if it's already open (so one click toggles it)."""
    pidfile = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), f"{name}.pid")
    try:
        pid = int(open_or_empty(pidfile))
        if name not in open_or_empty(f"/proc/{pid}/cmdline"):
            raise ProcessLookupError   # stale file, that pid is something else now
        os.kill(pid, signal.SIGTERM)
        os.remove(pidfile)
        return
    except (ValueError, ProcessLookupError, PermissionError, FileNotFoundError):
        pass
    with open(pidfile, "w") as f:
        f.write(str(os.getpid()))

    provider = Gtk.CssProvider()
    provider.load_from_data((BASE_CSS + css).encode())
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    window = make_window()
    window.connect("destroy", Gtk.main_quit)
    try:   # GLibUnix is newer; older PyGObject only has the GLib name
        from gi.repository import GLibUnix
        add_signal = GLibUnix.signal_add
    except ImportError:
        add_signal = GLib.unix_signal_add
    add_signal(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: Gtk.main_quit() or False)
    window.show_all()
    try:
        Gtk.main()
    finally:
        if open_or_empty(pidfile).strip() == str(os.getpid()):
            os.remove(pidfile)
