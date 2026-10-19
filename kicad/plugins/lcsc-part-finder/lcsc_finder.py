#!/usr/bin/env python3
"""LCSC Part Finder: find the cheapest in-stock LCSC part for a schematic symbol.

Runs from the Schematic Editor toolbar as a KiCad 10 IPC-API plugin, or directly:

    python3 lcsc_finder.py path/to/project.kicad_sch
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import wx  # noqa: E402

from finder_ui import FinderFrame  # noqa: E402
from kicad_bridge import locate_schematic  # noqa: E402
from schematic_io import SchematicProject  # noqa: E402


def main(argv: list[str]) -> int:
    app = wx.App(False)
    app.SetAppName("kicad-lcsc-part-finder")
    path, how = locate_schematic(argv)
    if path is None:
        with wx.FileDialog(None, f"Choose the schematic to work on ({how})",
                           wildcard="KiCad schematic (*.kicad_sch)|*.kicad_sch",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dialog:
            if dialog.ShowModal() != wx.ID_OK:
                return 0
            path, how = dialog.GetPath(), "file chooser"
    frame = FinderFrame(SchematicProject(path), how)
    frame.Show()
    frame.Raise()
    app.MainLoop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
