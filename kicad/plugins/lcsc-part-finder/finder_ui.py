"""The LCSC Part Finder window."""

from __future__ import annotations

import json
import os
import re
import threading
import traceback

import wx
import wx.adv

import part_query
from kicad_bridge import read_clipboard_text
from schematic_io import (PlacedSymbol, SchematicProject, symbols_from_clipboard,
                          unsaved_differences, write_fields)

# Existing fields with any of these names are updated instead of adding a new one.
LCSC_FIELDS = ("LCSC", "LCSC Part", "LCSC Part #", "LCSC#", "LCSC Part Number", "LCSC_PART",
               "JLCPCB Part #", "JLCPCB", "JLC")
MPN_FIELDS = part_query.MPN_FIELDS
MANUFACTURER_FIELDS = ("Manufacturer", "MFR", "Mfr", "MF", "Manufacturer Name")
# Symbols imported from EasyEDA/LCSC keep the LCSC number in "Supplier Part" (next to
# "Supplier": "LCSC").
SUPPLIER_PART_FIELDS = ("Supplier Part", "Supplier Part Number")
MANAGED_FIELDS = set(LCSC_FIELDS + MPN_FIELDS + MANUFACTURER_FIELDS + SUPPLIER_PART_FIELDS
                     + ("Datasheet",))

COLUMNS = [("LCSC #", 105), ("MPN", 170), ("Manufacturer", 130), ("Package", 110),
           ("Stock", 90), ("Unit price", 85), ("Order", 110), ("Description", 330)]


def _settings_path() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "kicad-lcsc-part-finder", "settings.json")


def load_settings() -> dict:
    settings = {"min_stock": 100, "quantity": 1, "write_mpn": False, "explained_revert": False}
    try:
        with open(_settings_path(), encoding="utf-8") as fh:
            settings.update(json.load(fh))
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_settings_path()), exist_ok=True)
        with open(_settings_path(), "w", encoding="utf-8") as fh:
            json.dump(settings, fh, indent=2)
    except OSError:
        pass


def _fmt_amount(value: float | None) -> str:
    return "" if value is None else part_query._num(value)


def _field_name(sym: PlacedSymbol, aliases: tuple[str, ...]) -> str:
    found = sym.get(*aliases)
    return found[0] if found else aliases[0]


def _lcsc_field(sym: PlacedSymbol) -> tuple[str, str] | None:
    """The field holding the symbol's LCSC number, if it has one."""
    found = sym.get(*LCSC_FIELDS)
    if found:
        return found
    supplier, part = sym.get("Supplier"), sym.get(*SUPPLIER_PART_FIELDS)
    if part and (re.fullmatch(r"C\d+", part[1].strip())
                 or (supplier and supplier[1].strip().upper() in ("LCSC", "JLCPCB"))):
        return part
    return None


class FinderFrame(wx.Frame):
    def __init__(self, project: SchematicProject, located_by: str):
        super().__init__(None, title="LCSC Part Finder", size=wx.Size(1180, 760))
        self.SetSize(self.FromDIP(wx.Size(1180, 760)))
        self.project = project
        self.located_by = located_by
        self.settings = load_settings()
        self.clip_symbols: dict[str, PlacedSymbol] = {}
        self.choices: list[PlacedSymbol] = []
        self.current: PlacedSymbol | None = None
        self.criteria: part_query.Criteria | None = None
        self.result: part_query.SearchResult | None = None
        self.candidates: list[part_query.Candidate] = []
        self.search_token = 0
        self.applied: list[str] = []
        self._build()
        self.Bind(wx.EVT_CLOSE, self._on_close)
        # Read the clipboard once the window is up: on Wayland only a focused
        # window is allowed to read it.
        wx.CallLater(200, self._load_symbols, True)

    # ---------------------------------------------------------------- layout

    def _build(self):
        panel = self.panel = wx.Panel(self)
        outer = wx.BoxSizer(wx.VERTICAL)
        gap = self.FromDIP(6)

        top = wx.BoxSizer(wx.HORIZONTAL)
        top.Add(wx.StaticText(panel, label="Symbol:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, gap)
        self.symbol_choice = wx.Choice(panel)
        self.symbol_choice.Bind(wx.EVT_CHOICE, self._on_symbol_chosen)
        top.Add(self.symbol_choice, 1, wx.EXPAND | wx.RIGHT, gap)
        refresh = wx.Button(panel, label="Use copied symbol")
        refresh.SetToolTip("Re-read the clipboard (select a symbol in the schematic and press "
                           "Ctrl+C first) and reload the saved schematic.")
        refresh.Bind(wx.EVT_BUTTON, lambda _e: self._load_symbols(True))
        top.Add(refresh, 0, wx.RIGHT, gap)
        choose = wx.Button(panel, label="Schematic…")
        choose.SetToolTip("Work on a different schematic file")
        choose.Bind(wx.EVT_BUTTON, self._on_choose_schematic)
        top.Add(choose, 0)
        outer.Add(top, 0, wx.EXPAND | wx.ALL, gap * 2)

        self.symbol_info = wx.StaticText(panel, label="")
        outer.Add(self.symbol_info, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, gap * 2)
        self.warning = wx.StaticText(panel, label="")
        self.warning.SetForegroundColour(wx.Colour(200, 40, 40))
        self.warning.Hide()
        outer.Add(self.warning, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, gap * 2)

        box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Criteria")
        sb = box.GetStaticBox()
        grid = wx.FlexGridSizer(cols=4, vgap=gap, hgap=gap * 2)
        grid.AddGrowableCol(1, 1)
        grid.AddGrowableCol(3, 1)

        def text(tip: str) -> wx.TextCtrl:
            ctrl = wx.TextCtrl(sb, style=wx.TE_PROCESS_ENTER)
            ctrl.SetToolTip(tip)
            ctrl.Bind(wx.EVT_TEXT_ENTER, lambda _e: self._search())
            return ctrl

        def add(label: str, ctrl: wx.Window):
            grid.Add(wx.StaticText(sb, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            grid.Add(ctrl, 1, wx.EXPAND)

        self.value_ctrl = text("Value (e.g. 10kΩ, 100nF), part number, or an LCSC code like C25804")
        self.package_ctrl = text("Package, e.g. 0603 or SOT-23-5 (taken from the footprint)")
        self.extra_ctrl = text("Extra words that must match, e.g. X7R, red, PTC")
        self.category_choice = wx.Choice(sb, choices=["Automatic"])
        self.category_choice.SetSelection(0)
        self.category_choice.Bind(wx.EVT_CHOICE, lambda _e: self._search(keep_category=True))
        self.tolerance_ctrl = text("Widest acceptable tolerance in %, e.g. 1")
        self.voltage_ctrl = text("Lowest acceptable voltage rating in volts, e.g. 50")
        self.power_ctrl = text("Lowest acceptable power rating in watts, e.g. 0.1 or 1/8")
        self.current_ctrl = text("Lowest acceptable current rating in amps, e.g. 0.5 or 500mA")
        self.stock_ctrl = wx.SpinCtrl(sb, min=0, max=100_000_000,
                                      initial=int(self.settings["min_stock"]))
        self.stock_ctrl.SetToolTip("Only show parts LCSC has at least this many of in stock")
        self.qty_ctrl = wx.SpinCtrl(sb, min=1, max=10_000_000,
                                    initial=int(self.settings["quantity"]))
        self.qty_ctrl.SetToolTip("How many you need. Prices include LCSC's minimum order and "
                                 "order multiples, so the cheapest order is ranked first.")

        add("Value / part number", self.value_ctrl)
        add("Package", self.package_ctrl)
        add("Extra keywords", self.extra_ctrl)
        add("Category", self.category_choice)
        add("Tolerance at most (%)", self.tolerance_ctrl)
        add("Voltage rating at least (V)", self.voltage_ctrl)
        add("Power rating at least (W)", self.power_ctrl)
        add("Current rating at least (A)", self.current_ctrl)
        add("Minimum stock", self.stock_ctrl)
        add("Quantity needed", self.qty_ctrl)
        box.Add(grid, 0, wx.EXPAND | wx.ALL, gap)
        params_row = wx.BoxSizer(wx.HORIZONTAL)
        params_row.Add(wx.StaticText(sb, label="Parameters"), 0,
                       wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, gap * 2)
        self.params_ctrl = text(
            "Parameters a part must have, as LCSC names them on a part's page, separated by “;”:\n"
            "  Gender=Female\n  Pitch=2mm|2.5mm   (any of these)\n"
            "  Number of Contacts=12P..16P   (a range)\n"
            "  Description~pin header   (the description must contain this)\n"
            "Filled in for connectors from the symbol and footprint.")
        params_row.Add(self.params_ctrl, 1, wx.EXPAND)
        box.Add(params_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, gap)
        self.search_btn = wx.Button(sb, label="Search LCSC")
        self.search_btn.Bind(wx.EVT_BUTTON, lambda _e: self._search())
        box.Add(self.search_btn, 0, wx.ALIGN_RIGHT | wx.ALL, gap)
        outer.Add(box, 0, wx.EXPAND | wx.ALL, gap * 2)

        self.results = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        for i, (title, width) in enumerate(COLUMNS):
            fmt = wx.LIST_FORMAT_RIGHT if title in ("Stock", "Unit price", "Order") else wx.LIST_FORMAT_LEFT
            self.results.InsertColumn(i, title, fmt, self.FromDIP(width))
        self.results.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_result_selected)
        self.results.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self._open_selected("url"))
        self.results.Bind(wx.EVT_LIST_COL_CLICK, self._on_sort)
        outer.Add(self.results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, gap * 2)

        self.status = wx.StaticText(panel, label="")
        outer.Add(self.status, 0, wx.EXPAND | wx.ALL, gap * 2)

        self.selected_info = wx.StaticText(panel, label="")
        outer.Add(self.selected_info, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, gap * 2)
        self.datasheet_link = wx.adv.HyperlinkCtrl(panel, label=" ", url="")
        outer.Add(self.datasheet_link, 0, wx.LEFT | wx.RIGHT, gap * 2)

        self.mpn_check = wx.CheckBox(panel, label="Also set the MPN and Manufacturer fields")
        self.mpn_check.SetValue(bool(self.settings["write_mpn"]))
        outer.Add(self.mpn_check, 0, wx.ALL, gap * 2)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.datasheet_btn = wx.Button(panel, label="Open datasheet")
        self.datasheet_btn.Bind(wx.EVT_BUTTON, lambda _e: self._open_selected("datasheet"))
        self.page_btn = wx.Button(panel, label="Open on LCSC")
        self.page_btn.Bind(wx.EVT_BUTTON, lambda _e: self._open_selected("url"))
        buttons.Add(self.datasheet_btn, 0, wx.RIGHT, gap)
        buttons.Add(self.page_btn, 0)
        buttons.AddStretchSpacer()
        hint = wx.StaticText(panel, label="Save the schematic first. Afterwards use "
                                          "File → Revert in the Schematic Editor to load the change.")
        hint.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))
        buttons.Add(hint, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, gap * 2)
        close = wx.Button(panel, wx.ID_CLOSE)
        close.Bind(wx.EVT_BUTTON, lambda _e: self.Close())
        buttons.Add(close, 0, wx.RIGHT, gap)
        self.apply_btn = wx.Button(panel, label="Apply")
        self.apply_btn.Bind(wx.EVT_BUTTON, self._on_apply)
        buttons.Add(self.apply_btn, 0)
        outer.Add(buttons, 0, wx.EXPAND | wx.ALL, gap * 2)

        panel.SetSizer(outer)
        self._update_buttons()

    # ---------------------------------------------------------------- symbols

    def _on_choose_schematic(self, _event):
        with wx.FileDialog(self, "Choose the root schematic", defaultDir=self.project.dir,
                           wildcard="KiCad schematic (*.kicad_sch)|*.kicad_sch",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return
            self.project = SchematicProject(dialog.GetPath())
        self.located_by = "file chooser"
        self.current = None
        self._load_symbols(True)

    def _load_symbols(self, read_clipboard: bool):
        keep = self.current.uuid if self.current else None
        self.SetTitle(f"LCSC Part Finder — {os.path.basename(self.project.root)}")
        try:
            self.project.load()
        except Exception as exc:
            wx.MessageBox(f"Could not read the schematic:\n{exc}", "LCSC Part Finder",
                          wx.ICON_ERROR, self)
            return
        if read_clipboard:
            self.clip_symbols = {s.uuid: s for s in symbols_from_clipboard(read_clipboard_text())}

        seen, self.choices = set(), []
        for sym in self.project.symbols:
            key = (tuple(sym.references), sym.lib_id)
            if key not in seen:
                seen.add(key)
                self.choices.append(sym)
        unsaved = [s for s in self.clip_symbols.values()
                   if self.project.find(s.uuid) is None]
        self.choices.extend(unsaved)

        labels = [s.label() + ("  (not saved yet)" if s.file is None else "")
                  for s in self.choices]
        self.symbol_choice.Set(labels)

        target = None
        if read_clipboard and self.clip_symbols:
            first = next(iter(self.clip_symbols.values()))
            target = self._choice_for(first)
        if target is None and keep:
            target = next((i for i, s in enumerate(self.choices) if s.uuid == keep), None)
        if target is not None:
            self.symbol_choice.SetSelection(target)
            self._select_symbol(self.choices[target])
        elif not self.current:
            self._set_status(f"Schematic: {self.project.root} (found via {self.located_by}). "
                             "Pick a symbol above, or select one in the schematic, press "
                             "Ctrl+C and click “Use copied symbol”.")

    def _choice_for(self, clip: PlacedSymbol) -> int | None:
        disk = self.project.find(clip.uuid)
        for i, sym in enumerate(self.choices):
            if sym.uuid == clip.uuid or (disk and sym.lib_id == disk.lib_id
                                         and set(sym.references) & set(disk.references)):
                return i
        return None

    def _on_symbol_chosen(self, _event):
        index = self.symbol_choice.GetSelection()
        if index != wx.NOT_FOUND:
            self._select_symbol(self.choices[index])

    def _describe_symbol(self, sym: PlacedSymbol):
        current_lcsc = _lcsc_field(sym)
        info = [f"Footprint: {sym.footprint or '(none)'}"]
        info.append(f"{current_lcsc[0]}: {current_lcsc[1]}" if current_lcsc and current_lcsc[1]
                    else "No LCSC part assigned yet")
        if sym.file:
            info.append(f"Sheet file: {os.path.relpath(sym.file, self.project.dir)}")
        self.symbol_info.SetLabel("    ".join(info))

        clip = self.clip_symbols.get(sym.uuid)
        warnings = []
        if sym.file is None:
            warnings.append(f"This symbol isn't in the saved {os.path.basename(self.project.root)} "
                            "yet. Save the schematic (Ctrl+S) and click “Use copied symbol”, or "
                            "pick the right project with “Schematic…”.")
        elif clip is not None:
            diffs = unsaved_differences(clip, self.project.find(sym.uuid), MANAGED_FIELDS)
            if diffs:
                warnings.append("The schematic has unsaved changes to this symbol ("
                                + "; ".join(diffs[:3]) + "). Save it (Ctrl+S), then click "
                                "“Use copied symbol”.")
        self.warning.SetLabel("\n".join(warnings))
        self.warning.Show(bool(warnings))
        self.panel.Layout()

    def _select_symbol(self, sym: PlacedSymbol):
        self.current = sym
        self._describe_symbol(sym)
        has_mpn = sym.get(*MPN_FIELDS) or sym.get(*MANUFACTURER_FIELDS)
        self.mpn_check.SetValue(bool(has_mpn) or bool(self.settings["write_mpn"]))

        crit = part_query.criteria_from_symbol(sym, self.stock_ctrl.GetValue(),
                                               self.qty_ctrl.GetValue())
        self.criteria = crit
        self.value_ctrl.SetValue(crit.value)
        self.value_ctrl.SetHint(crit.describe)  # what's searched for if the box is left empty
        self.package_ctrl.SetValue(crit.package)
        self.extra_ctrl.SetValue(crit.extra)
        self.params_ctrl.SetValue(part_query.format_rules(crit.params))
        self.tolerance_ctrl.SetValue(_fmt_amount(crit.max_tolerance))
        self.voltage_ctrl.SetValue(_fmt_amount(crit.min_voltage))
        self.power_ctrl.SetValue(_fmt_amount(crit.min_power))
        self.current_ctrl.SetValue(_fmt_amount(crit.min_current))
        self.category_choice.Set(["Automatic"])
        self.category_choice.SetSelection(0)
        self.apply_btn.SetLabel(f"Apply to {', '.join(sym.references)}")
        self.panel.Layout()
        self._show_results([])
        if crit.keyword():
            self._search()
        else:
            self._set_status("Enter a value or part number and click “Search LCSC”.")

    # ---------------------------------------------------------------- searching

    def _read_criteria(self) -> part_query.Criteria | None:
        base = self.criteria or part_query.Criteria()
        crit = part_query.Criteria(kind=base.kind, prefer_categories=list(base.prefer_categories),
                                   describe=base.describe)
        crit.value = self.value_ctrl.GetValue().strip()
        if base.exact_part and crit.value == base.value:
            # Still the symbol's own part number; once edited it matches as typed.
            crit.exact_part, crit.part_source = True, base.part_source
        crit.package = self.package_ctrl.GetValue().strip()
        crit.extra = self.extra_ctrl.GetValue().strip()
        crit.min_stock = self.stock_ctrl.GetValue()
        crit.quantity = self.qty_ctrl.GetValue()
        try:
            crit.params = part_query.parse_rules(self.params_ctrl.GetValue())
        except ValueError as exc:
            wx.MessageBox(f"“{exc}” isn't a parameter rule. Write Name=value, Name=a|b, "
                          "Name=12P..16P or Description~words, separated by “;”.",
                          "LCSC Part Finder", wx.ICON_WARNING, self)
            self.params_ctrl.SetFocus()
            return None
        for ctrl, unit, attr, label in (
                (self.tolerance_ctrl, "%", "max_tolerance", "tolerance"),
                (self.voltage_ctrl, "V", "min_voltage", "voltage rating"),
                (self.power_ctrl, "W", "min_power", "power rating"),
                (self.current_ctrl, "A", "min_current", "current rating")):
            text = ctrl.GetValue().strip()
            if not text:
                continue
            amount = part_query.parse_amount(text, unit)
            if amount is None:
                wx.MessageBox(f"“{text}” isn't a valid {label}. Use a number such as 0.25 "
                              f"(in {unit}).", "LCSC Part Finder", wx.ICON_WARNING, self)
                ctrl.SetFocus()
                return None
            setattr(crit, attr, amount)
        return crit

    def _search(self, keep_category: bool = False):
        crit = self._read_criteria()
        if crit is None:
            return
        category_id = None
        if keep_category and self.result and self.result.plan:
            index = self.category_choice.GetSelection()
            if index > 0:
                category_id = self.result.plan.categories[index - 1].id
        self.search_token += 1
        token = self.search_token
        self.search_btn.Disable()
        self.apply_btn.Disable()
        self._set_status(f"Searching LCSC for “{crit.keyword()}”…")

        def progress(message: str):
            wx.CallAfter(self._on_progress, token, message)

        def work():
            try:
                result = part_query.search(crit, category_id, progress)
                error = None
            except Exception as exc:
                traceback.print_exc()
                result, error = None, exc
            wx.CallAfter(self._on_search_done, token, result, error, keep_category)

        threading.Thread(target=work, daemon=True).start()

    def _on_progress(self, token: int, message: str):
        if token == self.search_token:
            self._set_status(message)

    def _on_search_done(self, token, result, error, keep_category):
        if token != self.search_token or not self:
            return
        self.search_btn.Enable()
        if error is not None:
            self._show_results([])
            self._set_status(f"Search failed: {error}")
            return
        self.result = result
        if result.plan and result.plan.categories:
            categories = result.plan.categories
            selection = self.category_choice.GetSelection() if keep_category else 0
            self.category_choice.Set(["Automatic"] + [c.label() for c in categories])
            self.category_choice.SetSelection(selection if 0 <= selection <= len(categories) else 0)
        self._show_results(result.candidates)
        self._set_status(result.summary())

    def _show_results(self, candidates):
        self.candidates = list(candidates)
        self.results.DeleteAllItems()
        for i, cand in enumerate(self.candidates):
            part = cand.part
            row = [part.code, part.mpn, part.manufacturer, part.package, f"{part.stock:,}",
                   f"${cand.unit_price:.4f}", f"{cand.buy_qty:,} = ${cand.total:,.2f}",
                   part.description]
            self.results.InsertItem(i, row[0])
            for col, text in enumerate(row[1:], start=1):
                self.results.SetItem(i, col, text)
        if self.candidates:
            self.results.Select(0)
            self.results.Focus(0)
        else:
            self.selected_info.SetLabel("")
            self.datasheet_link.SetLabel(" ")
            self.datasheet_link.SetURL("")
        self._update_buttons()

    def _on_sort(self, event):
        keys = {0: lambda c: c.part.code, 1: lambda c: c.part.mpn.lower(),
                2: lambda c: c.part.manufacturer.lower(), 3: lambda c: c.part.package,
                4: lambda c: -c.part.stock, 5: lambda c: c.unit_price, 6: lambda c: c.total,
                7: lambda c: c.part.description.lower()}
        key = keys.get(event.GetColumn())
        if key and self.candidates:
            self._show_results(sorted(self.candidates, key=key))

    def _selected(self) -> part_query.Candidate | None:
        index = self.results.GetFirstSelected()
        return self.candidates[index] if 0 <= index < len(self.candidates) else None

    def _on_result_selected(self, _event):
        cand = self._selected()
        if cand:
            part = cand.part
            self.selected_info.SetLabel(
                f"{part.code}: {part.manufacturer} {part.mpn} — {part.description}\n"
                f"Minimum order {part.min_order:,}, multiples of {part.order_multiple:,}. "
                f"Price breaks: " + ", ".join(f"{q:,}+ ${p:.4f}" for q, p in part.price_breaks[:6]))
            self.datasheet_link.SetLabel(part.datasheet or "(no datasheet listed)")
            self.datasheet_link.SetURL(part.datasheet or "")
            self.panel.Layout()
        self._update_buttons()

    def _open_selected(self, what: str):
        cand = self._selected()
        url = getattr(cand.part, what, "") if cand else ""
        if url:
            wx.LaunchDefaultBrowser(url)

    def _update_buttons(self):
        cand = self._selected() if hasattr(self, "results") else None
        has_symbol = self.current is not None and self.current.file is not None
        self.apply_btn.Enable(bool(cand) and has_symbol)
        self.datasheet_btn.Enable(bool(cand and cand.part.datasheet))
        self.page_btn.Enable(bool(cand))

    def _set_status(self, message: str):
        self.status.SetLabel(message)
        self.status.Wrap(self.GetClientSize().width - self.FromDIP(30))
        self.panel.Layout()

    # ---------------------------------------------------------------- applying

    def _on_apply(self, _event):
        cand, sym = self._selected(), self.current
        if not cand or not sym or not sym.file:
            return
        part = cand.part
        lcsc_field = _lcsc_field(sym)
        updates = {lcsc_field[0] if lcsc_field else LCSC_FIELDS[0]: part.code,
                   "Datasheet": part.datasheet}
        if self.mpn_check.GetValue():
            updates[_field_name(sym, MPN_FIELDS)] = part.mpn
            updates[_field_name(sym, MANUFACTURER_FIELDS)] = part.manufacturer
        if not part.datasheet:
            updates.pop("Datasheet")

        if self.warning.GetLabel():
            answer = wx.MessageBox(
                self.warning.GetLabel() + "\n\nWrite to the saved file anyway?",
                "LCSC Part Finder", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, self)
            if answer != wx.YES:
                return

        try:
            self.project.load()
            disk = self.project.find(sym.uuid)
            if disk is None:
                raise RuntimeError("the symbol is no longer in the saved schematic")
            by_file: dict[str, dict[str, dict[str, str]]] = {}
            for unit in self.project.units_of(disk):
                by_file.setdefault(unit.file, {})[unit.uuid] = updates
            for path, edits in by_file.items():
                write_fields(path, edits)
        except Exception as exc:
            traceback.print_exc()
            wx.MessageBox(f"Nothing was changed: {exc}", "LCSC Part Finder", wx.ICON_ERROR, self)
            return

        refs = ", ".join(disk.references)
        files = ", ".join(sorted(os.path.relpath(p, self.project.dir) for p in by_file))
        self.applied.append(refs)
        self.settings["write_mpn"] = self.mpn_check.GetValue()
        self._remember()
        if not self.settings.get("explained_revert"):
            wx.MessageBox(
                f"Saved {part.code} to {refs} in {files}.\n\n"
                "The Schematic Editor still shows the old version. Choose File → Revert there "
                "to load the change from disk.\n\nDon't save in the Schematic Editor before "
                "reverting, or these fields will be overwritten. You can apply several parts "
                "first and revert once at the end.",
                "LCSC Part Finder", wx.ICON_INFORMATION, self)
            self.settings["explained_revert"] = True
            self._remember()
        try:
            self.project.load()
        except Exception:
            traceback.print_exc()
        fresh = self.project.find(sym.uuid)
        if fresh is not None:
            self.current = fresh
            index = self.symbol_choice.GetSelection()
            if 0 <= index < len(self.choices):
                self.choices[index] = fresh
            self._describe_symbol(fresh)
        self._set_status(f"Saved {part.code} to {refs} ({', '.join(updates)}). Updated so far: "
                         f"{'; '.join(self.applied)}. Use File → Revert in the Schematic Editor "
                         "to see the changes.")

    def _remember(self):
        self.settings["min_stock"] = self.stock_ctrl.GetValue()
        self.settings["quantity"] = self.qty_ctrl.GetValue()
        save_settings(self.settings)

    def _on_close(self, event):
        self.search_token += 1
        self._remember()
        event.Skip()
