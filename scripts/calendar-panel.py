#!/usr/bin/env python3
# Calendar for waybar's clock (right-click), in dungeonOS colours like the bar: month title
# in brass, today marked with the moss square of the active workspace. The arrows or the
# scroll wheel change month, clicking the title goes back to this month. Weeks start on
# Monday, with ISO week numbers down the side.

import calendar
import datetime

from waybar_popup import Popup, run_popup  # sets the GTK versions, so it comes first
from gi.repository import Gdk, Gtk  # noqa: E402

CSS = """
#title {
    font-family: "CloisterBlack";
    font-size: 22px;
    color: #A88A5B;
    padding: 2px 8px;
}
#title:hover { color: #C8B8A0; }
#arrow { font-size: 16px; padding: 2px 10px; }

.weekday { color: #9D8E7C; font-size: 12px; }
.weekend { color: #7A5E47; }
.weeknum { color: #6F675E; font-size: 11px; }

.day {
    font-family: "CloisterBlack";
    font-size: 17px;
    min-width: 34px;
    min-height: 30px;
}
.other-month { color: #463D34; }
.day.weekend { color: #A88A5B; }
.day.other-month.weekend { color: #463D34; }
/* today: the active workspace's moss square, with a ring of the panel colour inside */
.today {
    background: #6E7F5A;
    color: #1A1816;
    box-shadow: inset 0 0 0 3px #1A1816;
}
.day.today.weekend { color: #1A1816; }

#date { color: #9D8E7C; padding-top: 4px; }
separator { background: #463D34; min-height: 1px; margin: 4px 0; }
"""


class CalendarPanel(Popup):
    def __init__(self):
        super().__init__("calendar-panel")
        self.today = datetime.date.today()
        self.year, self.month = self.today.year, self.today.month

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        body.set_name("body")
        self.add(body)

        header = Gtk.Box()
        self.title = Gtk.Button()
        self.title.set_name("title")
        self.title.set_relief(Gtk.ReliefStyle.NONE)
        self.title.set_can_focus(False)
        self.title.connect("clicked", lambda _b: self.show_month(self.today.year, self.today.month))
        header.pack_start(self.arrow("", -1), False, False, 0)   # nf-fa-chevron_left
        header.set_center_widget(self.title)
        header.pack_end(self.arrow("", 1), False, False, 0)      # nf-fa-chevron_right
        body.pack_start(header, False, False, 0)
        body.pack_start(Gtk.Separator(), False, False, 0)

        self.grid = Gtk.Grid(column_spacing=2, row_spacing=2)
        self.grid.set_halign(Gtk.Align.CENTER)
        body.pack_start(self.grid, False, False, 0)

        body.pack_start(Gtk.Separator(), False, False, 0)
        date = Gtk.Label(label=self.today.strftime("%A %-d %B %Y"))
        date.set_name("date")
        body.pack_start(date, False, False, 0)

        self.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.connect("scroll-event", self.on_scroll)
        self.show_month(self.year, self.month)

    def arrow(self, icon, step):
        button = Gtk.Button(label=icon)
        button.set_name("arrow")
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.set_can_focus(False)
        button.connect("clicked", lambda _b: self.step(step))
        return button

    def step(self, months):
        index = self.year * 12 + self.month - 1 + months
        self.show_month(index // 12, index % 12 + 1)

    def on_scroll(self, _w, event):
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            dy = event.get_scroll_deltas()[2]
            if dy:
                self.step(1 if dy > 0 else -1)
        elif event.direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.DOWN):
            self.step(1 if event.direction == Gdk.ScrollDirection.DOWN else -1)

    def on_key(self, w, event):
        super().on_key(w, event)
        if event.keyval in (Gdk.KEY_Left, Gdk.KEY_h):
            self.step(-1)
        elif event.keyval in (Gdk.KEY_Right, Gdk.KEY_l):
            self.step(1)

    def show_month(self, year, month):
        self.year, self.month = year, month
        self.title.set_label(datetime.date(year, month, 1).strftime("%B %Y"))
        for child in self.grid.get_children():
            self.grid.remove(child)

        for col, name in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"), start=1):
            self.grid.attach(label(name, "weekday", "weekend" if col > 5 else None), col, 0, 1, 1)

        # always six weeks, so the panel doesn't change height between months
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
        while len(weeks) < 6:
            weeks.append([d + datetime.timedelta(days=7) for d in weeks[-1]])
        for row, week in enumerate(weeks, start=1):
            self.grid.attach(label(str(week[0].isocalendar()[1]), "weeknum"), 0, row, 1, 1)
            for col, day in enumerate(week, start=1):
                classes = ["day"]
                if col > 5:
                    classes.append("weekend")
                if day.month != month:
                    classes.append("other-month")
                if day == self.today:
                    classes.append("today")
                self.grid.attach(label(str(day.day), *classes), col, row, 1, 1)
        self.grid.show_all()


def label(text, *classes):
    widget = Gtk.Label(label=text)
    for name in classes:
        if name:
            widget.get_style_context().add_class(name)
    return widget


if __name__ == "__main__":
    run_popup("calendar-panel", CalendarPanel, CSS)
