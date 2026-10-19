"""Read placed symbols from KiCad schematics (files or the clipboard) and write fields back.

KiCad 10's IPC API cannot read or modify schematic symbols, so fields are written
straight into the .kicad_sch file with a minimal text splice: only the edited
property values (or the newly inserted properties) change, every other byte of
the file is left exactly as KiCad wrote it.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass, field

from sexpr import Atom, Node, parse, quote

# First schematic format that writes (hide yes) directly inside a property rather
# than inside its (effects ...). Only used when there is no hidden field to clone.
_PROPERTY_LEVEL_HIDE_VERSION = 20250000


class SchematicError(Exception):
    pass


@dataclass
class PlacedSymbol:
    uuid: str
    lib_id: str
    references: list[str]
    fields: dict[str, str]
    file: str | None = None
    unit: int = 1

    @property
    def reference(self) -> str:
        return self.references[0] if self.references else self.fields.get("Reference", "?")

    @property
    def value(self) -> str:
        return self.fields.get("Value", "")

    @property
    def footprint(self) -> str:
        return self.fields.get("Footprint", "")

    def get(self, *names: str) -> tuple[str, str] | None:
        """Case-insensitive lookup of the first field present among ``names``."""
        lowered = {k.lower(): k for k in self.fields}
        for name in names:
            key = lowered.get(name.lower())
            if key is not None:
                return key, self.fields[key]
        return None

    def label(self) -> str:
        refs = ", ".join(self.references) if self.references else self.reference
        value = self.value or "?"
        where = f" — {os.path.basename(self.file)}" if self.file else ""
        return f"{refs}  {value}  [{self.lib_id}]{where}"


def _natural_key(text: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", text)]


def _symbol_nodes(roots: list[Node]):
    """Yield placed-symbol nodes (they have a lib_id; library definitions don't)."""
    for root in roots:
        candidates = root.nodes("symbol") if root.head == "kicad_sch" else [root]
        for node in candidates:
            if node.head == "symbol" and node.first("lib_id") is not None:
                yield node


def _to_symbol(node: Node, file: str | None, project: str | None) -> PlacedSymbol | None:
    uuid_node = node.first("uuid")
    if uuid_node is None:
        return None
    fields = {}
    for prop in node.nodes("property"):
        name = prop.atom(1)
        if name is not None:
            fields[name] = prop.atom(2, "") or ""

    refs: list[str] = []
    all_refs: list[str] = []
    instances = node.first("instances")
    if instances is not None:
        for proj in instances.nodes("project"):
            for path in proj.nodes("path"):
                ref = path.first("reference")
                if ref is None or ref.atom(1) is None:
                    continue
                all_refs.append(ref.atom(1))
                if project is None or proj.atom(1) == project:
                    refs.append(ref.atom(1))
    refs = refs or all_refs or [fields.get("Reference", "?")]
    refs = sorted(dict.fromkeys(refs), key=_natural_key)

    unit_node = node.first("unit")
    try:
        unit = int(unit_node.atom(1)) if unit_node is not None else 1
    except (TypeError, ValueError):
        unit = 1

    return PlacedSymbol(uuid=uuid_node.atom(1) or "", lib_id=node.first("lib_id").atom(1) or "",
                        references=refs, fields=fields, file=file, unit=unit)


def symbols_from_text(text: str, file: str | None = None,
                      project: str | None = None) -> list[PlacedSymbol]:
    symbols = []
    for node in _symbol_nodes(parse(text)):
        sym = _to_symbol(node, file, project)
        if sym is not None:
            symbols.append(sym)
    return symbols


def looks_like_kicad_clipboard(text: str) -> bool:
    return bool(text) and "(lib_id" in text and "(symbol" in text


def symbols_from_clipboard(text: str) -> list[PlacedSymbol]:
    if not looks_like_kicad_clipboard(text):
        return []
    try:
        return [s for s in symbols_from_text(text) if not s.reference.startswith("#")]
    except Exception:
        return []


class SchematicProject:
    """All sheets reachable from a root schematic, and the symbols placed on them."""

    def __init__(self, root_schematic: str):
        self.root = os.path.abspath(root_schematic)
        self.dir = os.path.dirname(self.root)
        self.name = os.path.splitext(os.path.basename(self.root))[0]
        self.files: list[str] = []
        self.symbols: list[PlacedSymbol] = []
        self.missing: list[str] = []

    def load(self) -> "SchematicProject":
        self.files, self.symbols, self.missing = [], [], []
        queue = [self.root]
        while queue:
            path = queue.pop(0)
            if path in self.files:
                continue
            if not os.path.isfile(path):
                self.missing.append(path)
                continue
            self.files.append(path)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            try:
                roots = parse(text)
            except Exception as exc:
                raise SchematicError(f"Could not read {path}: {exc}") from exc
            for root in roots:
                if root.head != "kicad_sch":
                    continue
                for sheet in root.nodes("sheet"):
                    for prop in sheet.nodes("property"):
                        if prop.atom(1) in ("Sheetfile", "Sheet file") and prop.atom(2):
                            queue.append(os.path.normpath(
                                os.path.join(os.path.dirname(path), prop.atom(2))))
            for node in _symbol_nodes(roots):
                sym = _to_symbol(node, path, self.name)
                if sym is not None and not sym.reference.startswith("#"):
                    self.symbols.append(sym)
        self.symbols.sort(key=lambda s: _natural_key(s.reference))
        return self

    def find(self, uuid: str) -> PlacedSymbol | None:
        return next((s for s in self.symbols if s.uuid == uuid), None)

    def find_by_reference(self, reference: str) -> PlacedSymbol | None:
        return next((s for s in self.symbols if reference in s.references), None)

    def units_of(self, sym: PlacedSymbol) -> list[PlacedSymbol]:
        """Every placed unit of the same part (multi-unit symbols share a reference)."""
        refs = set(sym.references)
        units = [s for s in self.symbols
                 if s.lib_id == sym.lib_id and refs.intersection(s.references)]
        return units or [sym]


def unsaved_differences(clip: PlacedSymbol, disk: PlacedSymbol | None,
                        ignore: set[str]) -> list[str]:
    """Differences between the editor's copy of a symbol and the saved file.

    Any difference means the schematic has unsaved edits, and writing to the
    file would be undone (or would undo them) when KiCad saves or reverts.
    """
    if disk is None:
        return ["the symbol is not in the saved file yet"]
    ignore_lower = {n.lower() for n in ignore} | {"reference"}
    diffs = []
    if clip.lib_id != disk.lib_id:
        diffs.append(f"symbol {disk.lib_id!r} → {clip.lib_id!r}")
    disk_lower = {k.lower(): v for k, v in disk.fields.items()}
    for name, value in clip.fields.items():
        if name.lower() in ignore_lower:
            continue
        saved = disk_lower.get(name.lower())
        if saved != value:
            diffs.append(f"{name}: saved {saved!r}, editor {value!r}" if saved is not None
                         else f"{name}: not saved yet")
    return diffs


# ----------------------------------------------------------------------------------------
# Writing


def _is_hidden(prop: Node) -> bool:
    hide = prop.first("hide")
    if hide is not None and hide.atom(1, "yes") == "yes":
        return True
    effects = prop.first("effects")
    if effects is not None:
        if any(isinstance(i, Atom) and i.value == "hide" for i in effects.items):
            return True
        hide = effects.first("hide")
        if hide is not None and hide.atom(1, "yes") == "yes":
            return True
    return False


def _line_indent(text: str, offset: int) -> str | None:
    line_start = text.rfind("\n", 0, offset) + 1
    indent = text[line_start:offset]
    return indent if indent.strip() == "" else None


def _file_version(roots: list[Node]) -> int:
    for root in roots:
        if root.head == "kicad_sch":
            version = root.first("version")
            try:
                return int(version.atom(1)) if version is not None else 0
            except (TypeError, ValueError):
                return 0
    return 0


def _generated_property(name: str, value: str, at: tuple[str, str], indent: str,
                        nl: str, version: int) -> str:
    x, y = at
    font = ["(effects", "\t(font", "\t\t(size 1.27 1.27)", "\t)"]
    if version >= _PROPERTY_LEVEL_HIDE_VERSION:
        lines = [f"(property {quote(name)} {quote(value)}", f"\t(at {x} {y} 0)", "\t(hide yes)",
                 "\t(show_name no)", "\t(do_not_autoplace no)"]
        lines += ["\t" + ln for ln in font] + ["\t)", ")"]
    else:
        lines = [f"(property {quote(name)} {quote(value)}", f"\t(at {x} {y} 0)"]
        lines += ["\t" + ln for ln in font] + ["\t\t(hide yes)", "\t)", ")"]
    return (nl + indent).join(lines)


def _cloned_property(text: str, template: Node, name: str, value: str, new_id: int | None) -> str:
    base = template.start
    clone = text[template.start:template.end]
    replacements = []
    name_atom, value_atom = template.items[1], template.items[2]
    replacements.append((name_atom.start - base, name_atom.end - base, quote(name)))
    replacements.append((value_atom.start - base, value_atom.end - base, quote(value)))
    id_node = template.first("id")
    if id_node is not None and new_id is not None and len(id_node.items) > 1:
        atom = id_node.items[1]
        replacements.append((atom.start - base, atom.end - base, str(new_id)))
    for start, end, repl in sorted(replacements, reverse=True):
        clone = clone[:start] + repl + clone[end:]
    return clone


def _plan_edits(text: str, node: Node, updates: dict[str, str], version: int):
    nl = "\r\n" if "\r\n" in text else "\n"
    props = node.nodes("property")
    if not props:
        raise SchematicError("symbol has no properties to anchor new fields to")
    by_name = {}
    for prop in props:
        if prop.atom(1) is not None:
            by_name.setdefault(prop.atom(1).lower(), prop)

    def usable(p: Node) -> bool:
        return len(p.items) >= 3 and all(isinstance(i, Atom) and i.quoted for i in p.items[1:3])

    template = None
    for preferred in ("datasheet", "description", "footprint"):
        p = by_name.get(preferred)
        if p is not None and usable(p) and _is_hidden(p):
            template = p
            break
    if template is None:
        template = next((p for p in props if usable(p) and _is_hidden(p)
                         and p.atom(1) not in ("Reference", "Value")), None)

    ids = []
    for prop in props:
        id_node = prop.first("id")
        if id_node is not None and id_node.atom(1, "").lstrip("-").isdigit():
            ids.append(int(id_node.atom(1)))
    next_id = (max(ids) + 1) if ids else None

    at_node = node.first("at")
    at = (at_node.atom(1, "0"), at_node.atom(2, "0")) if at_node is not None else ("0", "0")

    last = props[-1]
    indent = _line_indent(text, last.start)
    edits, inserts = [], []
    for name, value in updates.items():
        prop = by_name.get(name.lower())
        if prop is not None:
            if len(prop.items) >= 3 and isinstance(prop.items[2], Atom):
                edits.append((prop.items[2].start, prop.items[2].end, quote(value)))
            else:
                edits.append((prop.items[1].end, prop.items[1].end, " " + quote(value)))
            continue
        if template is not None:
            new_prop = _cloned_property(text, template, name, value, next_id)
        else:
            new_prop = _generated_property(name, value, at, indent or "", nl, version)
        if next_id is not None:
            next_id += 1
        inserts.append((nl + indent if indent is not None else " ") + new_prop)
    if inserts:
        edits.append((last.end, last.end, "".join(inserts)))
    return edits


def _find_symbol_node(roots: list[Node], uuid: str) -> Node | None:
    for node in _symbol_nodes(roots):
        uuid_node = node.first("uuid")
        if uuid_node is not None and uuid_node.atom(1) == uuid:
            return node
    return None


def updated_text(text: str, uuid: str, updates: dict[str, str]) -> str:
    """Return ``text`` with the given fields set on the symbol ``uuid``."""
    roots = parse(text)
    node = _find_symbol_node(roots, uuid)
    if node is None:
        raise SchematicError(f"symbol {uuid} was not found in the file")
    new_text = text
    for start, end, repl in sorted(_plan_edits(text, node, updates, _file_version(roots)),
                                   key=lambda e: e[0], reverse=True):
        new_text = new_text[:start] + repl + new_text[end:]

    # Verify the result before anyone writes it to disk.
    check = _find_symbol_node(parse(new_text), uuid)
    if check is None:
        raise SchematicError("internal error: symbol vanished while editing")
    fields = {p.atom(1).lower(): p.atom(2, "") for p in check.nodes("property") if p.atom(1)}
    for name, value in updates.items():
        if fields.get(name.lower()) != value:
            raise SchematicError(f"internal error: field {name!r} did not take the new value")
    return new_text


def _backup_dir() -> str:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "kicad-lcsc-part-finder", "backups")


def write_fields(path: str, edits_by_uuid: dict[str, dict[str, str]],
                 backup_dir: str | None = None) -> str:
    """Apply field edits to one schematic file. Returns the backup file path."""
    with open(path, encoding="utf-8", newline="") as fh:
        original = fh.read()
    text = original
    for uuid, updates in edits_by_uuid.items():
        text = updated_text(text, uuid, updates)
    if text == original:
        return ""

    backup_dir = backup_dir or _backup_dir()
    os.makedirs(backup_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = os.path.join(backup_dir, f"{stamp}-{os.path.basename(path)}")
    shutil.copy2(path, backup)
    backups = sorted(os.listdir(backup_dir))
    for old in backups[:-200]:
        try:
            os.remove(os.path.join(backup_dir, old))
        except OSError:
            pass

    fd, tmp = tempfile.mkstemp(prefix=".lcsc-", suffix=".tmp", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        shutil.copymode(path, tmp)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return backup
