#!/usr/bin/env python3
# Music panel for waybar's cava module (right-click): cmus volume slider and cmus
# controls (track, seek, previous / play-pause / next / stop, shuffle, repeat).
# Opens next to the cursor on whichever side the bar is on; running it again, Escape,
# or clicking away closes it. dungeonOS colours, matching waybar/style.css.

import os

from waybar_popup import Popup, run, run_popup  # sets the GTK versions, so it comes first
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

CSS = """
#title {
    font-family: "CloisterBlack";
    font-size: 21px;
    color: #A88A5B;
}
#artist { color: #9D8E7C; }
#time, #vol-value { color: #6F675E; font-size: 12px; }

button { font-size: 18px; }
#play { color: #879376; font-size: 22px; }
button.on { color: #A88A5B; }
#mute.on { color: #7B4A3E; }

scale { padding: 0; margin: 0; }
scale trough {
    background: #24201C;
    border: 1px solid #463D34;
    border-radius: 0;
    min-height: 6px;
}
scale highlight {
    background: #6E7F5A;
    border: none;
    border-radius: 0;
}
#volume highlight { background: #879376; }
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
separator { background: #463D34; min-height: 1px; margin: 6px 0; }
"""


def cmus(*args):
    run("cmus-remote", *args)


def cmus_status():
    """cmus-remote -Q as a dict, or None when cmus isn't running."""
    out = run("cmus-remote", "-Q")
    if not out:
        return None
    info = {"tag": {}, "set": {}}
    for line in out.splitlines():
        key, _, rest = line.partition(" ")
        if key in ("tag", "set"):
            name, _, value = rest.partition(" ")
            info[key][name] = value
        else:
            info[key] = rest
    return info


def cmus_volume(info):
    """cmus's volume in percent (the louder of left / right)."""
    try:
        return max(int(info["set"]["vol_left"]), int(info["set"]["vol_right"]))
    except (KeyError, ValueError):
        return 0


def fmt_time(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def icon_button(icon, name, callback):
    button = Gtk.Button(label=icon)
    button.set_name(name)
    button.set_relief(Gtk.ReliefStyle.NONE)
    button.set_can_focus(False)
    button.connect("clicked", lambda _b: (callback(), GLib.timeout_add(80, panel.refresh)))
    return button


class Panel(Popup):
    def __init__(self):
        super().__init__("music-panel")
        self.dragging = set()   # sliders the user is holding, so refresh leaves them alone
        self.updating = False   # set while refresh moves the sliders itself
        self.unmuted = 50       # volume the mute button goes back to (cmus has no mute)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        body.set_name("body")
        body.set_size_request(300, -1)
        self.add(body)

        self.title = Gtk.Label(xalign=0)
        self.title.set_name("title")
        self.title.set_ellipsize(3)   # Pango.EllipsizeMode.END
        self.title.set_max_width_chars(26)
        self.artist = Gtk.Label(xalign=0)
        self.artist.set_name("artist")
        self.artist.set_ellipsize(3)
        self.artist.set_max_width_chars(34)
        body.pack_start(self.title, False, False, 0)
        body.pack_start(self.artist, False, False, 0)

        # seek bar with elapsed / total time
        self.seek = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1)
        self.seek.set_draw_value(False)
        self.seek.set_name("seek")
        self.hold(self.seek, lambda v: cmus("-k", str(int(v))))
        self.elapsed = Gtk.Label(xalign=0)
        self.elapsed.set_name("time")
        self.total = Gtk.Label(xalign=1)
        self.total.set_name("time")
        times = Gtk.Box()
        times.pack_start(self.elapsed, True, True, 0)
        times.pack_end(self.total, True, True, 0)
        body.pack_start(self.seek, False, False, 0)
        body.pack_start(times, False, False, 0)

        # transport: shuffle | previous, play/pause, next, stop | repeat
        controls = Gtk.Box(spacing=2)
        self.shuffle = icon_button("\U000f049d", "shuffle", lambda: cmus("-S"))   # nf-md-shuffle_variant
        self.play = icon_button("", "play", self.toggle_play)
        self.repeat = icon_button("\U000f0456", "repeat", lambda: cmus("-R"))     # nf-md-repeat
        controls.pack_start(self.shuffle, False, False, 0)
        controls.set_center_widget(self.centre_controls())
        controls.pack_end(self.repeat, False, False, 0)
        body.pack_start(controls, False, False, 2)

        body.pack_start(Gtk.Separator(), False, False, 0)

        # cmus volume (with softvol off it's cmus's own stream volume, not the whole system)
        volume_row = Gtk.Box(spacing=6)
        self.mute = icon_button("\U000f057e", "mute", self.toggle_mute)
        self.volume = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.volume.set_draw_value(False)
        self.volume.set_name("volume")
        self.volume.connect("value-changed", self.volume_changed)
        self.hold(self.volume, None)
        self.vol_value = Gtk.Label()
        self.vol_value.set_name("vol-value")
        self.vol_value.set_width_chars(4)
        volume_row.pack_start(self.mute, False, False, 0)
        volume_row.pack_start(self.volume, True, True, 0)
        volume_row.pack_start(self.vol_value, False, False, 0)
        body.pack_start(volume_row, False, False, 0)

        self.refresh()
        GLib.timeout_add(500, self.refresh)

    def centre_controls(self):
        box = Gtk.Box(spacing=2)
        box.pack_start(icon_button("", "prev", lambda: cmus("-r")), False, False, 0)
        box.pack_start(self.play, False, False, 0)
        box.pack_start(icon_button("", "next", lambda: cmus("-n")), False, False, 0)
        box.pack_start(icon_button("", "stop", lambda: cmus("-s")), False, False, 0)
        return box

    def hold(self, scale, on_release):
        """Track dragging; on_release(value) runs when the user lets go."""
        def press(*_):
            self.dragging.add(scale)

        def release(*_):
            self.dragging.discard(scale)
            if on_release:
                on_release(scale.get_value())
            GLib.timeout_add(80, self.refresh)

        scale.connect("button-press-event", press)
        scale.connect("button-release-event", release)

    def volume_changed(self, scale):
        value = int(scale.get_value())
        self.vol_value.set_text(f"{value}%")
        if not self.updating:
            cmus("-v", f"{value}%")

    def toggle_mute(self):
        info = cmus_status()
        if info is None:
            return
        level = cmus_volume(info)
        if level > 0:
            self.unmuted = level
            cmus("-v", "0%")
        else:
            cmus("-v", f"{self.unmuted}%")

    def toggle_play(self):
        info = cmus_status()
        if info and info.get("status") == "stopped":
            cmus("-p")
        else:
            cmus("-u")

    def refresh(self):
        self.updating = True
        info = cmus_status()
        if info is None:
            self.title.set_text("cmus is not running")
            self.artist.set_text("")
            self.elapsed.set_text("")
            self.total.set_text("")
        else:
            tag = info["tag"]
            title = tag.get("title") or os.path.basename(info.get("file", "")) or "nothing playing"
            artist = " — ".join(p for p in (tag.get("artist"), tag.get("album")) if p)
            self.title.set_text(title)
            self.artist.set_text(artist)
            duration = max(1, int(info.get("duration", "0") or 0))
            position = int(info.get("position", "0") or 0)
            if self.seek not in self.dragging:
                self.seek.set_range(0, duration)
                self.seek.set_value(position)
            self.elapsed.set_text(fmt_time(self.seek.get_value()))
            self.total.set_text(fmt_time(duration) if info.get("duration") else "")
            self.play.set_label("" if info.get("status") == "playing" else "")
            for button, key in ((self.shuffle, "shuffle"), (self.repeat, "repeat")):
                ctx = button.get_style_context()
                (ctx.add_class if info["set"].get(key) == "true" else ctx.remove_class)("on")

        level = cmus_volume(info) if info else 0
        muted = info is not None and level == 0
        if self.volume not in self.dragging:
            self.volume.set_value(min(level, 100))
            self.vol_value.set_text(f"{level}%")
        self.mute.set_label("\U000f075f" if muted else "\U000f057e")   # volume off / high
        ctx = self.mute.get_style_context()
        (ctx.add_class if muted else ctx.remove_class)("on")
        self.updating = False
        return True

    def on_key(self, w, event):
        super().on_key(w, event)
        if event.keyval == Gdk.KEY_space:
            self.toggle_play()
            GLib.timeout_add(80, self.refresh)


def make_panel():
    global panel
    panel = Panel()
    return panel


panel = None   # the open panel; the buttons refresh it after they act

if __name__ == "__main__":
    run_popup("music-panel", make_panel, CSS)
