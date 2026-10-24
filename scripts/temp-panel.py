#!/usr/bin/env python3
# Temperature panel for waybar's CPU / GPU temperatures (right-click): every CPU and GPU
# sensor, graded in the bar's colours, and a speed slider for each fan CoolerControl can
# drive (on the desktop just the GPU's; the board's fan chip has no Linux driver).
# Moving a slider fixes the fan at that speed; Auto hands it back to the hardware curve.
# Both are saved by CoolerControl, so they last across reboots like settings made there.
#
# The fans go through coolercontrold's API, never sysfs, so the two can't fight over them.
# It needs an access token with Write Access (CoolerControl > Access Protection > Create
# Token) in ~/.config/coolercontrol-token, kept out of this repo. Without one the panel
# still shows the temperatures and says what's missing.
#
# Opens next to the cursor on whichever side the bar is on; running it again, Escape,
# or clicking away closes it. dungeonOS colours, matching waybar/style.css.

import glob
import json
import os
import subprocess
import urllib.error
import urllib.request

from waybar_popup import Popup, open_or_empty, run_popup  # sets the GTK versions, so it comes first
from gi.repository import GLib, Gtk  # noqa: E402

DAEMON = "http://127.0.0.1:11987"
TOKEN_FILE = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")), "coolercontrol-token"
)

NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # it's on loopback

# the same sensors as scripts/cputemp.sh and gputemp.sh
CPU_SENSORS = ("k10temp", "zenpower", "coretemp", "cpu_thermal")
GPU_SENSORS = ("amdgpu",)
# friendlier names for the sensor labels the drivers give
LABELS = {"Tctl": "Die", "Tccd1": "CCD 1", "Tccd2": "CCD 2", "Tdie": "Die",
          "edge": "Edge", "junction": "Junction", "mem": "Memory"}

CSS = """
#title {
    font-family: "CloisterBlack";
    font-size: 21px;
    color: #A88A5B;
}
.section { color: #9D8E7C; font-size: 12px; }
.section.later { margin-top: 6px; }   /* space above GPU, after the CPU rows */
.sensor { color: #C8B8A0; }
#hint, #rpm { color: #6F675E; font-size: 12px; }

/* temperatures graded like the bar's (scripts/temp-json.sh, waybar/style.css) */
.temp {
    font-family: "CloisterBlack";
    font-size: 17px;
    padding: 1px 6px;
}
.temp.cool { color: #6E7F5A; }
.temp.warm { color: #A88A5B; }
.temp.hot { color: #C8B8A0; background: #7A5E47; }
.temp.critical { color: #C8B8A0; background: #7B4A3E; }

#fan-icon {
    font-family: "FantasqueSansM Nerd Font Propo";
    font-size: 22px;
    color: #9D8E7C;
}
#duty { color: #6F675E; font-size: 12px; }
/* on the label itself: the popups' "label" colour would win over the button's */
button.on label { color: #A88A5B; }

scale { padding: 0; margin: 0; }
scale trough {
    background: #24201C;
    border: 1px solid #463D34;
    border-radius: 0;
    min-height: 6px;
}
scale highlight {
    background: #879376;
    border: none;
    border-radius: 0;
}
scale slider {
    background: #A88A5B;
    border: 1px solid #141210;
    border-radius: 0;
    box-shadow: none;
    min-width: 10px;
    min-height: 14px;
    margin: -5px 0;
}
scale slider:hover { background: #C8B8A0; }
scale:disabled highlight { background: #463D34; }
scale:disabled slider { background: #6F675E; }
separator { background: #463D34; min-height: 1px; margin: 6px 0; }
"""


def heat(t):
    """The bar's heat class for a temperature (scripts/temp-json.sh)."""
    if t >= 85:
        return "critical"
    if t >= 75:
        return "hot"
    if t >= 50:
        return "warm"
    return "cool"


def hwmon_temps(names):
    """[(label, °C)] for every sensor of the first hwmon chip with one of these names."""
    for name in names:
        for hwmon in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
            if open_or_empty(f"{hwmon}/name").strip() != name:
                continue
            temps = []
            for path in sorted(glob.glob(f"{hwmon}/temp*_input")):
                raw = open_or_empty(path).strip()
                if not raw:
                    continue
                label = open_or_empty(path.replace("_input", "_label")).strip()
                label = label or os.path.basename(path).split("_")[0]
                temps.append((LABELS.get(label, label), int(raw) // 1000))
            if temps:
                return temps
    return []


def nvidia_temps():
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=1).stdout.split()
        return [("GPU", int(out[0]))] if out else []
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return []


def read_temps():
    """[("CPU", [(label, °C)]), ("GPU", [...])], leaving out a chip with no sensor."""
    chips = (("CPU", hwmon_temps(CPU_SENSORS)),
             ("GPU", hwmon_temps(GPU_SENSORS) or nvidia_temps()))
    return [(chip, temps) for chip, temps in chips if temps]


class CoolerControl:
    """Just enough of coolercontrold's REST API for fixed speeds (see its /openapi spec)."""

    def __init__(self):
        self.token = open_or_empty(TOKEN_FILE).strip()

    def call(self, method, path, body=None):
        """The decoded JSON reply; raises RuntimeError with something to show the user."""
        if not self.token:
            raise RuntimeError("fan control needs a CoolerControl token in "
                               "~/.config/coolercontrol-token")
        request = urllib.request.Request(
            DAEMON + path, method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {self.token}",
                     "Content-Type": "application/json"})
        try:
            with NO_PROXY.open(request, timeout=1) as reply:
                data = reply.read()
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise RuntimeError("CoolerControl refused the token") from e
            if e.code == 403:
                raise RuntimeError("the token needs Write Access") from e
            raise RuntimeError(f"CoolerControl said {e.code}") from e
        except (OSError, ValueError) as e:
            raise RuntimeError("coolercontrold isn't running") from e
        return json.loads(data) if data else None

    def fans(self):
        """[(device uid, channel, name)] for every fan that takes a fixed speed."""
        fans = []
        for device in self.call("GET", "/devices")["devices"]:
            for channel, info in sorted(device["info"]["channels"].items()):
                options = info.get("speed_options")
                if not (options and options.get("fixed_enabled")):
                    continue
                # "type", not the "d_type" the 5.1.1 spec says
                owner = "GPU" if device.get("type") == "GPU" else device["name"]
                label = info.get("label") or ("fan" if channel == "fan1" else channel)
                fans.append((device["uid"], channel, f"{owner} {label}"))
        return fans

    def status(self, uid, channel):
        """(duty %, rpm) as the daemon last read them."""
        history = self.call("GET", f"/status/{uid}")["status_history"]
        for ch in history[-1]["channels"] if history else []:
            if ch["name"] == channel:
                return ch.get("duty"), ch.get("rpm")
        return None, None

    def fixed_speed(self, uid, channel):
        """The % the fan is held at, or None when it follows the hardware / a profile."""
        for setting in self.call("GET", f"/devices/{uid}/settings")["settings"]:
            if setting["channel_name"] == channel:
                return setting.get("speed_fixed")
        return None

    def set_fixed(self, uid, channel, duty):
        self.call("PUT", f"/devices/{uid}/settings/{channel}/manual", {"speed_fixed": duty})

    def reset(self, uid, channel):
        self.call("PUT", f"/devices/{uid}/settings/{channel}/reset")


class FanRow:
    """Slider, duty and RPM for one fan, plus Auto to give it back to the hardware."""

    def __init__(self, panel, uid, channel, name):
        self.panel, self.uid, self.channel = panel, uid, channel
        self.dragging = False   # held by the user, so refresh leaves the slider alone
        self.pending = None     # timer for applying the speed once the slider settles
        self.updating = False   # set while refresh moves the slider itself
        self.fixed = None       # the % the fan is held at; None on Auto

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        top = Gtk.Box(spacing=6)
        icon = Gtk.Label(label="\U000f0210")   # nf-md-fan
        icon.set_name("fan-icon")
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.scale.set_draw_value(False)
        self.scale.connect("value-changed", self.changed)
        self.scale.connect("button-press-event", lambda *_: setattr(self, "dragging", True))
        self.scale.connect("button-release-event", lambda *_: setattr(self, "dragging", False))
        self.duty = Gtk.Label()
        self.duty.set_name("duty")
        self.duty.set_width_chars(4)
        top.pack_start(icon, False, False, 0)
        top.pack_start(self.scale, True, True, 0)
        top.pack_start(self.duty, False, False, 0)

        bottom = Gtk.Box(spacing=6)
        label = Gtk.Label(label=name, xalign=0)
        label.get_style_context().add_class("section")
        self.rpm = Gtk.Label(xalign=0)
        self.rpm.set_name("rpm")
        self.auto = Gtk.Button(label="Auto")
        self.auto.set_relief(Gtk.ReliefStyle.NONE)
        self.auto.set_can_focus(False)
        self.auto.connect("clicked", lambda _b: self.apply(self.panel.cc.reset, self.uid, self.channel))
        bottom.pack_start(label, False, False, 0)
        bottom.pack_start(self.rpm, False, False, 0)
        bottom.pack_end(self.auto, False, False, 0)

        self.box.pack_start(top, False, False, 0)
        self.box.pack_start(bottom, False, False, 0)
        self.refresh_mode()

    def changed(self, scale):
        self.duty.set_text(f"{int(scale.get_value())}%")
        if self.updating:
            return
        # wait for the slider to settle, so a drag sends one change instead of dozens
        if self.pending:
            GLib.source_remove(self.pending)
        self.pending = GLib.timeout_add(250, self.settled)

    def settled(self):
        if self.dragging:
            return True   # still held: check again shortly
        self.pending = None
        self.apply(self.panel.cc.set_fixed, self.uid, self.channel, int(self.scale.get_value()))
        return False

    def apply(self, action, *args):
        try:
            action(*args)
        except RuntimeError as e:
            self.panel.show_hint(str(e))
        self.refresh_mode()

    def refresh_mode(self):
        """Light up Auto while the fan isn't held at a fixed speed."""
        try:
            self.fixed = self.panel.cc.fixed_speed(self.uid, self.channel)
        except RuntimeError:
            return
        ctx = self.auto.get_style_context()
        (ctx.remove_class if self.fixed is not None else ctx.add_class)("on")

    def refresh(self):
        duty, rpm = self.panel.cc.status(self.uid, self.channel)
        self.rpm.set_text(f"{rpm} RPM" if rpm is not None else "")
        # a fixed speed shows as set: the fan reads back a point low (15% is 36/255 = 14%)
        shown = self.fixed if self.fixed is not None else duty
        if shown is not None and not self.dragging and not self.pending:
            self.updating = True
            self.scale.set_value(round(shown))
            self.updating = False


class Panel(Popup):
    def __init__(self):
        super().__init__("temp-panel")
        self.cc = CoolerControl()

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        body.set_name("body")
        body.set_size_request(300, -1)
        self.add(body)

        title = Gtk.Label(label="Temperatures", xalign=0)
        title.set_name("title")
        body.pack_start(title, False, False, 0)
        body.pack_start(Gtk.Separator(), False, False, 0)

        # a heading per chip, then a row per sensor; refresh only changes the values
        grid = Gtk.Grid(column_spacing=12, row_spacing=2)
        self.temps = {}   # (chip, sensor) -> value label
        row = 0
        for chip, temps in read_temps():
            head = Gtk.Label(label=chip, xalign=0)
            head.get_style_context().add_class("section")
            if row:
                head.get_style_context().add_class("later")
            grid.attach(head, 0, row, 2, 1)
            row += 1
            for sensor, _t in temps:
                name = Gtk.Label(label=sensor, xalign=0, hexpand=True)
                name.get_style_context().add_class("sensor")
                value = Gtk.Label(xalign=1)
                grid.attach(name, 0, row, 1, 1)
                grid.attach(value, 1, row, 1, 1)
                self.temps[chip, sensor] = value
                row += 1
        body.pack_start(grid, False, False, 0)
        body.pack_start(Gtk.Separator(), False, False, 0)

        # the fans, or why there aren't any
        self.hint = Gtk.Label(xalign=0)
        self.hint.set_name("hint")
        self.hint.set_line_wrap(True)
        self.hint.set_max_width_chars(36)
        self.hint.set_no_show_all(True)
        self.fans = []
        try:
            self.fans = [FanRow(self, *fan) for fan in self.cc.fans()]
            if not self.fans:
                self.show_hint("CoolerControl has no fans it can set")
        except RuntimeError as e:
            self.show_hint(str(e))
        for fan in self.fans:
            body.pack_start(fan.box, False, False, 0)
        body.pack_start(self.hint, False, False, 0)

        body.pack_start(Gtk.Separator(), False, False, 0)
        links = Gtk.Box(spacing=2)
        links.pack_start(self.link("CoolerControl", "coolercontrol"), False, False, 0)
        links.pack_end(self.link("btop", "kitty", "-e", "btop"), False, False, 0)
        body.pack_start(links, False, False, 0)

        self.refresh()
        GLib.timeout_add(1000, self.refresh)

    def link(self, text, *cmd):
        """A button that opens an app and closes the panel."""
        button = Gtk.Button(label=text)
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.set_can_focus(False)
        button.connect("clicked", lambda _b: (
            subprocess.Popen(cmd, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL),
            Gtk.main_quit()))
        return button

    def show_hint(self, text):
        self.hint.set_text(text)
        self.hint.show()

    def refresh(self):
        for chip, temps in read_temps():
            for sensor, t in temps:
                value = self.temps.get((chip, sensor))
                if value is None:
                    continue
                value.set_text(f"{t}°C")
                ctx = value.get_style_context()
                for level in ("cool", "warm", "hot", "critical"):
                    ctx.remove_class(level)
                ctx.add_class("temp")
                ctx.add_class(heat(t))
        for fan in self.fans:
            try:
                fan.refresh()
            except RuntimeError as e:
                self.show_hint(str(e))
        return True


if __name__ == "__main__":
    run_popup("temp-panel", Panel, CSS)
