# LCSC Part Finder (KiCad 10 schematic plugin)

Finds the cheapest in-stock LCSC part that meets a symbol's criteria, then writes its
LCSC number and datasheet URL into the schematic.

## Setup (once)

1. KiCad → **Preferences → Plugins**: tick **Enable KiCad API** (the Python interpreter
   should be `/usr/bin/python3`). Restart KiCad.
2. KiCad builds a private Python environment for the plugin and installs
   `kicad-python` the first time (needs internet; takes a minute). The button then appears in
   the Schematic Editor's top toolbar. If it doesn't, use **Preferences → Plugins → Reload**.

**No button?** KiCad 10 sometimes fails to finish setting up a new plugin's environment on the
first run, without showing an error, and doesn't retry until it restarts. Quit KiCad completely
(every window) and start it again. To see why it failed, start it from a terminal with
`WXTRACE=KICAD_API kicad` and look for lines starting with `Manager:`.

## Use

1. **Save** the schematic (Ctrl+S).
2. Click the symbol, press **Ctrl+C**, then click the **LCSC Part Finder** toolbar button.
3. The window fills the criteria from the symbol (Value, MPN, Footprint → package or connector
   type, and fields such as Tolerance, Voltage, Power, Current, Temperature Coefficient) and
   searches immediately.
   Edit anything, set **Minimum stock** and **Quantity needed**, and press Enter to search again.
4. The cheapest match is selected. Click **Apply to R5** to confirm.
5. In the Schematic Editor choose **File → Revert** to load the change. You can apply several
   parts first (pick them in the Symbol list, or Ctrl+C another symbol and click
   **Use copied symbol**) and revert once at the end.

Why Ctrl+C and Revert: KiCad 10's plugin API can't read the schematic selection or edit symbols
(that arrives in KiCad 11). So the plugin reads the copied symbol from the clipboard and edits the
saved `.kicad_sch` file directly, changing only the fields it sets. Don't save from the editor
between Apply and Revert, or the editor's older copy overwrites the change. The window warns you
when the copied symbol differs from the saved file (i.e. there are unsaved edits).

## Part numbers and connectors

When the symbol says exactly which part it is, only that part is accepted (from any maker that
sells it under the same number, e.g. `TPUSBLC6-2SC6`):

* a filled-in MPN field (`MPN`, `Manufacturer Part`, …) on ICs, diodes and connectors, even if
  the Value is a label such as `USBC`;
* a connector footprint named after a part, as KiCad's are:
  `USB_C_Receptacle_HRO_TYPE-C-31-M-12`, `USB_C_Receptacle_GCT_USB4105-xx-A_…` (the `xx` matches
  any variant), `JST_PH_B2B-PH-K_1x02_…`, `BarrelJack_CUI_PJ-102AH_…`.

Part numbers you type are checked too, so LCSC's search can't swap in a similar-looking one.
Edit or clear **Value / part number** to compare other parts.

Otherwise connectors are matched by their **Parameters**, filled in from the symbol and footprint
and filtered by LCSC itself: a USB 2.0 Type-C symbol needs a Type-C receptacle with 12–16
contacts (not a 6-pin charge-only one), and `PinHeader_1x04_P2.54mm_Vertical` needs a 1x4, 2.54 mm,
through-hole pin header. Parts with the same parameters can still have different footprints, so
check the drawing before applying. You can add rules for any part, using the parameter names on
LCSC's part pages: `Pitch=2mm|2.5mm`, `Number of Contacts=12P..16P`, `Description~pin header`.

## What gets written

* `LCSC`: the LCSC part number. An existing field such as `LCSC Part` or `JLCPCB Part #` is
  reused, and so is `Supplier Part` on symbols imported from EasyEDA/LCSC.
* `Datasheet`: the LCSC datasheet PDF.
* Optional (checkbox): MPN and Manufacturer. Existing `Part`/`MP`/`MPN` and
  `Manufacturer`/`MF` fields are reused, so it is ticked automatically when the symbol has them.

All units of a multi-unit part are updated together. Before each write, the original file is copied
to `~/.cache/kicad-lcsc-part-finder/backups/`.

## How "cheapest" is decided

Parts are ranked by the cost of the order you'd actually place for the quantity you need,
including LCSC's minimum order, order multiples, and price breaks. Parts are excluded when they
have less stock than the minimum (or than the order), the wrong value, package or part number,
a wider tolerance, a lower voltage/power/current rating than required, or a parameter that
doesn't match. Click a column header to
re-sort; double-click a row to open it on LCSC.

## Notes

* The search uses the JSON endpoints behind www.lcsc.com. LCSC doesn't publish or document them,
  so a site change can break the search. All LCSC-specific code is in `lcsc_api.py`.
* Running outside KiCad: `python3 lcsc_finder.py path/to/project.kicad_sch`.
* Settings (minimum stock, quantity) persist in `~/.config/kicad-lcsc-part-finder/settings.json`.
