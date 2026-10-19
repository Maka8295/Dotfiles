"""Everything that talks to KiCad itself: finding the open project and reading the clipboard."""

from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess


def _schematic_for(path: str) -> str | None:
    """Accept a .kicad_sch, a .kicad_pro or a project folder and return the root schematic."""
    path = os.path.abspath(os.path.expanduser(path))
    if os.path.isdir(path):
        projects = sorted(glob.glob(os.path.join(path, "*.kicad_pro")))
        if not projects:
            return None
        path = projects[0]
    if path.endswith(".kicad_pro"):
        path = path[:-len(".kicad_pro")] + ".kicad_sch"
    return path if path.endswith(".kicad_sch") and os.path.isfile(path) else None


def schematic_from_api() -> tuple[str | None, str]:
    """Ask the running KiCad (via its IPC API) which schematic is open."""
    if not os.environ.get("KICAD_API_SOCKET"):
        return None, "not launched from KiCad"
    try:
        from kipy import KiCad
        from kipy.proto.common.types import DocumentType
    except ImportError:
        return None, "the kicad-python package is not installed"
    try:
        kicad = KiCad(timeout_ms=4000)
        docs = kicad.get_open_documents(DocumentType.DOCTYPE_SCHEMATIC)
        if not docs:
            return None, "KiCad reports no open schematic"
        filename = docs[0].board_filename
        project_dir = kicad.get_project(docs[0]).expand_text_variables("${KIPRJMOD}")
    except Exception as exc:  # the API raises several unrelated exception types
        return None, f"KiCad API error: {exc}"
    path = filename if os.path.isabs(filename) else os.path.join(project_dir, filename)
    if os.path.isfile(path):
        return path, "KiCad API"
    return None, f"KiCad reported {path}, which does not exist"


def schematic_from_recent_projects() -> str | None:
    """Fall back to the projects KiCad lists as open in its settings."""
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    settings = sorted(glob.glob(os.path.join(base, "kicad", "*", "kicad.json")), reverse=True)
    for settings_file in settings:
        try:
            with open(settings_file, encoding="utf-8") as fh:
                system = json.load(fh).get("system", {})
        except (OSError, ValueError):
            continue
        for project in system.get("open_projects") or []:
            found = _schematic_for(project)
            if found:
                return found
    return None


def locate_schematic(argv: list[str]) -> tuple[str | None, str]:
    for arg in argv:
        found = _schematic_for(arg)
        if found:
            return found, "command line"
    found, how = schematic_from_api()
    if found:
        return found, how
    recent = schematic_from_recent_projects()
    if recent:
        return recent, f"KiCad's open-projects list ({how})"
    return None, how


def read_clipboard_text() -> str:
    """Text on the system clipboard (where KiCad puts copied symbols as S-expressions)."""
    text = ""
    try:
        import wx
        if wx.TheClipboard.Open():
            try:
                data = wx.TextDataObject()
                if wx.TheClipboard.GetData(data):
                    text = data.GetText()
            finally:
                wx.TheClipboard.Close()
    except Exception:
        text = ""
    if "(lib_id" in text:
        return text

    # wx can miss the clipboard on Wayland when the window isn't focused yet;
    # the command-line tools don't have that problem.
    commands = []
    if os.environ.get("WAYLAND_DISPLAY"):
        commands.append(["wl-paste", "--no-newline", "--type", "text"])
    if os.environ.get("DISPLAY"):
        commands += [["xclip", "-o", "-selection", "clipboard"], ["xsel", "--clipboard", "--output"]]
    for cmd in commands:
        if not shutil.which(cmd[0]):
            continue
        try:
            out = subprocess.run(cmd, capture_output=True, timeout=3).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        candidate = out.decode("utf-8", "replace")
        if "(lib_id" in candidate:
            return candidate
    return text
