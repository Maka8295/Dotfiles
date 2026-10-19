"""Turn a schematic symbol into LCSC search criteria, then find the cheapest part that meets them."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

import lcsc_api
from lcsc_api import Category, Part, SearchPlan

MAX_PAGES = 5  # LCSC returns 100 parts per page, cheapest first

PREFIX = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "U": 1e-6, "m": 1e-3, "": 1.0, "R": 1.0,
          "k": 1e3, "K": 1e3, "M": 1e6, "G": 1e9}

PASSIVES = ("resistor", "capacitor", "inductor", "ferrite")
MAIN_PARAM = {"resistor": "Resistance", "capacitor": "Capacitance",
              "inductor": "Inductance", "crystal": "Frequency"}
DIELECTRICS = {"X5R", "X7R", "X7S", "X6S", "X8R", "X7T", "X5S", "X8L", "C0G", "NP0",
               "Y5V", "Z5U"}
DIELECTRIC_ALIASES = {"COG": "C0G", "NPO": "NP0"}
CHIP_SIZES = ("01005", "0201", "0402", "0603", "0805", "1206", "1210", "1812", "2010",
              "2512", "2220", "1808", "0612", "0508")
_CHIP_RE = re.compile(r"(?:^|_)(" + "|".join(CHIP_SIZES) + r")(?:_|$)")
_IC_PACKAGE_RE = re.compile(
    r"^(?:T?SOT|SOD|SOIC|SOP|V?SSOP|TSSOP|HTSSOP|MSOP|ESOP|HSOP|TSOP|[VWUTXH]?QFN|[UTX]?DFN|"
    r"LQFP|TQFP|QFP|TO|DO|SM[ABC]F?|MiniMELF|MELF|LGA|BGA|WLCSP|P?DIP|SIP|DPAK|D2PAK|SC|"
    r"[UWX]?SON|LFCSP|PowerPAK)(?:-[0-9A-Z]+)*$", re.I)

# Schematic field names that carry each criterion (matched case-insensitively).
FIELD_ALIASES = {
    "tolerance": ("Tolerance", "Tol"),
    "voltage": ("Voltage", "Voltage Rating", "Voltage Rated", "Rated Voltage", "Max Voltage",
                "Voltage (DC)"),
    "power": ("Power", "Power Rating", "Wattage", "Power (W)", "Power(Watts)"),
    "current": ("Current", "Current Rating", "Rated Current", "Max Current"),
    "dielectric": ("Dielectric", "Temperature Coefficient", "Temp Coefficient", "TC"),
    "package": ("Package", "Case", "Case/Package"),
}
# Fields that hold a manufacturer part number ("Manufacturer Part" comes from EasyEDA/LCSC imports).
MPN_FIELDS = ("MPN", "Manufacturer Part", "Part", "Manufacturer Part Number",
              "Manufacturer_Part_Number", "Mfr. Part #", "MP", "PartNumber", "Part Number")

# Kinds whose Value is a specification (10k, 100nF) rather than a part number.
VALUE_KINDS = PASSIVES + ("crystal",)
# Kinds whose MPN field, when filled in, says exactly which part is wanted.
PART_NUMBER_KINDS = ("generic", "diode", "connector")

# LCSC parameter names that carry each rating: (names in priority order, words to skip, unit)
VOLTAGE_SPEC = (["voltage rating", "rated voltage", "voltage rated", "voltage - rated",
                 "voltage - max", "voltage - dc reverse", "reverse voltage",
                 "drain to source voltage", "drain source voltage", "breakdown", "voltage"],
                ["forward", "esd", "input", "output", "clamp", "threshold", "gate"], "V")
POWER_SPEC = (["power(watts)", "power rating", "power - max", "power dissipation", "power"],
              [], "W")
CURRENT_SPEC = (["current rating", "rated current", "current - rectified", "average rectified",
                 "continuous drain", "current - saturation", "hold current", "current - max",
                 "forward current", "current"],
                ["leakage", "surge", "reverse", "quiescent", "trip", "peak", "pulse"], "A")

KIND_CATEGORY_WORDS = {
    "resistor": (["resistor"], ["network", "array", "thermistor", "potentiometer", "varistor"]),
    "capacitor": (["capacitor"], ["network", "array"]),
    "inductor": (["inductor"], []),
    "ferrite": (["ferrite"], []),
    "led": (["led"], []),
    "crystal": (["crystal", "resonator"], ["oscillator"]),
    "fuse": (["fuse"], []),
    "diode": (["diode", "rectifier", "tvs", "zener", "schottky"], []),
    "connector": (["connector", "header", "socket", "jack", "terminal", "plug", "receptacle"],
                  ["housing", "adapter", "cable", "crimp", "contact", "accessor"]),
}


def _num(x: float) -> str:
    return f"{x:.6f}".rstrip("0").rstrip(".") or "0"


def guess_kind(reference: str, lib_id: str, footprint: str = "") -> str:
    prefix = re.match(r"[A-Za-z]*", reference or "").group(0).upper()
    library, _, name = (lib_id or "").rpartition(":")
    name = name.upper()
    if prefix == "R" or re.match(r"R(_|$)", name):
        return "resistor"
    if prefix == "C" or re.match(r"C(P)?(_|$)", name):
        return "capacitor"
    if prefix == "FB" or "FERRITE" in name:
        return "ferrite"
    if prefix == "L" or re.match(r"L(_|$)", name):
        return "inductor"
    if (library.lower().startswith("connector") or re.match(r"(CONN_|USB_|BARREL_JACK)", name)
            or (footprint or "").startswith("Connector")
            or prefix in ("J", "P", "CN", "CON", "CONN", "USB")):
        return "connector"
    if prefix in ("Y", "X") or "CRYSTAL" in name:
        return "crystal"
    if "LED" in prefix or name.startswith("LED"):
        return "led"
    if prefix == "F" or name.startswith("FUSE"):
        return "fuse"
    if prefix == "D":
        return "diode"
    return "generic"


def parse_amount(text: str, unit: str) -> float | None:
    """'16', '16V', '6.3 V', '100mW', '1/4W', '±1%' -> number in base units (None if invalid)."""
    if text is None or not str(text).strip():
        return None
    s = str(text).strip().replace("µ", "u").replace("μ", "u").replace(",", ".")
    m = re.fullmatch(r"[±+]?\s*(\d+(?:\.\d+)?|\.\d+)\s*(?:/\s*(\d+(?:\.\d+)?))?\s*"
                     r"([pnumkKMG]?)\s*([A-Za-z%]*)", s)
    if not m:
        return None
    number = float(m.group(1))
    if m.group(2):
        number /= float(m.group(2))
    prefix, suffix = m.group(3), m.group(4)
    if suffix and suffix.lower() != unit.lower():
        if not prefix and suffix[:1] in PREFIX and suffix[1:].lower() == unit.lower():
            prefix, suffix = suffix[:1], suffix[1:]
        else:
            return None
    return number * PREFIX.get(prefix, 1.0)


_UNIT_SUFFIX = {"resistor": r"(?:Ω|Ω|ohms?)", "capacitor": r"F", "inductor": r"H",
                "crystal": r"Hz"}
_VALUE_PREFIXES = {"resistor": "RkKmMG", "capacitor": "pnuUm", "inductor": "pnuUm",
                   "crystal": "kKmM"}


def parse_component_value(text: str, kind: str) -> float | None:
    """'4k7' -> 4700, '100n' (capacitor) -> 1e-7, '2R2' -> 2.2, '12M' (crystal) -> 12e6."""
    if kind not in _UNIT_SUFFIX or not text:
        return None
    s = text.strip().replace("µ", "u").replace("μ", "u").replace(",", ".").replace(" ", "")
    s, had_unit = re.subn(_UNIT_SUFFIX[kind] + "$", "", s, flags=re.I)
    m = re.fullmatch(r"(\d*\.?\d+|\d+\.)?([" + _VALUE_PREFIXES[kind] + r"])?(\d+)?", s)
    if not m or not (m.group(1) or m.group(3)):
        return None
    number, prefix, fraction = m.group(1), m.group(2), m.group(3)
    if fraction and number and "." in number:
        return None
    if not prefix and not had_unit and kind != "resistor":
        return None  # a bare number is ambiguous for anything but a resistor
    mantissa = float(f"{number or '0'}.{fraction}") if fraction else float(number)
    multiplier = PREFIX.get(prefix or "", 1.0)
    if kind == "crystal" and prefix == "m":
        multiplier = 1e6
    return mantissa * multiplier


def format_component_value(value: float, kind: str) -> str:
    """Format a value the way LCSC's search parses it best."""
    scales = {
        # Milliohms are written as decimals: LCSC's search is case-insensitive, so
        # "10mΩ" would match 10MΩ parts.
        "resistor": [(1e9, "G"), (1e6, "M"), (1e3, "k"), (1, "")],
        "capacitor": [(1, ""), (1e-6, "u"), (1e-9, "n"), (1e-12, "p")],
        "inductor": [(1, ""), (1e-3, "m"), (1e-6, "u"), (1e-9, "n")],
        "crystal": [(1e6, "M"), (1e3, "k"), (1, "")],
    }[kind]
    unit = {"resistor": "Ω", "capacitor": "F", "inductor": "H", "crystal": "Hz"}[kind]
    for scale, prefix in scales:
        if value >= scale * (1 - 1e-9):
            return f"{_num(value / scale)}{prefix}{unit}"
    scale, prefix = scales[-1]
    return f"{_num(value / scale)}{prefix}{unit}"


def package_from_footprint(footprint: str) -> str:
    """'Resistor_SMD:R_0603_1608Metric' -> '0603', 'Package_SO:SOIC-8_3.9x4.9mm' -> 'SOIC-8'."""
    name = (footprint or "").split(":", 1)[-1]
    if not name:
        return ""
    m = _CHIP_RE.search(name)
    if m:
        return m.group(1)
    m = re.search(r"Crystal_SMD_(\d{4})", name)
    if m:
        return m.group(1)
    m = re.match(r"CP_Elec_(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", name)
    if m:
        return f"D{m.group(1)}xL{m.group(2)}mm"  # how LCSC names SMD electrolytic sizes
    stripped = re.sub(r"^(?:R|C|CP|L|D|LED|F|Fuse|FB)_", "", name)
    token = stripped.split("_", 1)[0]
    token = re.sub(r"-\d*EP$", "", token, flags=re.I)  # QFN-32-1EP -> QFN-32
    return token if _IC_PACKAGE_RE.match(token) else ""


# ----------------------------------------------------------------------------------------
# Part numbers


def looks_like_part_number(text: str) -> bool:
    """'USBLC6-2SC6', 'TYPE-C-31-M-12' or 'B2B-PH-K', but not '10k', '16V', 'red' or 'C25804'."""
    s = (text or "").strip()
    return (len(s) >= 3 and not re.search(r"\s", s)
            and re.search(r"[A-Za-z]", s) is not None and re.search(r"\d", s) is not None
            and not re.fullmatch(r"C\d{2,}", s, re.I)
            and not re.fullmatch(r"[\d.,/]+[pnuµμmkKMG]?[A-Za-zΩ%]{0,3}", s))


def _is_wildcard(ch: str, text: str, upper_too: bool) -> bool:
    # KiCad footprint names write variable characters as x ('USB4105-xx-A'), and sometimes X.
    return (ch == "x" and text != text.lower()) or (ch == "X" and upper_too)


def part_number_regex(text: str, upper_wildcards: bool = False) -> re.Pattern:
    """Finds the part number in an upper-case MPN, ignoring separators: '12401548E4-2A' finds
    '12401548E4#2A', and 'USB4105-xx-A' finds 'USB4105-GF-A'."""
    pieces = ["[0-9A-Z]" if _is_wildcard(ch, text, upper_wildcards) else re.escape(ch.upper())
              for ch in text if ch.isalnum()]
    return re.compile(r"[^0-9A-Z]*".join(pieces))


def part_number_matches(pattern: re.Pattern, mpn: str, whole: bool) -> bool:
    """Whether an MPN carries the part number. A maker's prefix of up to three letters
    ('TPUSBLC6-2SC6') or one ending in a separator ('SH-U262-161N') is allowed, and so is a
    suffix after a separator ('USB4105-GF-A-060'). A whole part number can't run on into more
    letters or digits: 'TYPE-C-31-M-12' doesn't match 'TYPE-C-31-M-12A'."""
    mpn = (mpn or "").upper()
    for m in pattern.finditer(mpn):
        before = mpn[:m.start()]
        if before and before[-1].isalnum() and not re.fullmatch(r"[A-Z]{1,3}", before):
            continue
        if whole and m.end() < len(mpn) and mpn[m.end()].isalnum():
            continue
        return True
    return False


def part_number_search_text(text: str, upper_wildcards: bool = False) -> str:
    """What to give LCSC's search for a part number with wildcards: 'USB4105-xx-A' -> 'USB4105'."""
    for i, ch in enumerate(text):
        if _is_wildcard(ch, text, upper_wildcards):
            prefix = text[:i].rstrip("-_./ ")
            return prefix if sum(c.isalnum() for c in prefix) >= 4 else text
    return text


# Words in connector footprint names that describe the layout, not the part.
_LAYOUT_WORD = re.compile(r"USB\d|\d+(?:[.,]\d+)?mm|P\d+(?:[.,]\d+)?(?:mm)?|\d+x\d+|\d+P|"
                          r"\d+pins?|Pin\d\w*|\d{1,4}", re.I)


def part_number_from_footprint(footprint: str) -> str:
    """The part a connector footprint was drawn for. KiCad names them
    <type>_<maker>_<part>_<layout>: 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12' ->
    'TYPE-C-31-M-12', 'Connector_JST:JST_PH_B2B-PH-K_1x02_P2.00mm_Vertical' -> 'B2B-PH-K'."""
    name = (footprint or "").split(":")[-1]
    if re.match(r"(PinHeader|PinSocket)_", name):
        return ""
    for word in name.split("_")[1:]:
        word = re.sub(r"(?i)^(Molex|JST|Hirose|TE|Wuerth|Amphenol)-(?=\d)", "", word)
        if not re.search(r"\d", word) or _LAYOUT_WORD.fullmatch(word):
            continue
        if re.search(r"[A-Za-z-]", word) or len(word) >= 5:
            return word
    return ""


# ----------------------------------------------------------------------------------------
# Parameters a part must have


def _same_param_value(a: str, b: str) -> bool:
    """'2mm' == '2.00mm', 'Surface Mount, Right Angle' == 'Surface Mount,Right Angle'."""
    a, b = (re.sub(r"\s+", "", s.lower()) for s in (a, b))
    ma, mb = (re.fullmatch(r"(\d+(?:\.\d+)?)([a-z%]*)", s) for s in (a, b))
    if ma and mb:
        return ma.group(2) == mb.group(2) and abs(float(ma.group(1)) - float(mb.group(1))) < 1e-9
    return re.sub(r"[^0-9a-z]", "", a) == re.sub(r"[^0-9a-z]", "", b)


@dataclass
class ParamRule:
    """A parameter an LCSC part must have, written as LCSC names it on a part's page:
    "Gender=Female", "Pitch=2mm|2.5mm" (any of these), "Number of Contacts=12P..16P" (a range)
    or "Description~pin header" (must contain)."""
    name: str
    values: tuple[str, ...] = ()
    low: float | None = None
    high: float | None = None
    unit: str = ""
    contains: str = ""

    def __str__(self) -> str:
        if self.contains:
            return f"{self.name}~{self.contains}"
        if self.low is not None or self.high is not None:
            low = "" if self.low is None else _num(self.low) + self.unit
            high = "" if self.high is None else _num(self.high) + self.unit
            return f"{self.name}={low}..{high}"
        return f"{self.name}={'|'.join(self.values)}"

    def accepts(self, text: str) -> bool:
        text = (text or "").strip()
        if self.contains:
            return self.contains.lower() in text.lower()
        if self.low is not None or self.high is not None:
            m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*[A-Za-z]*", text)
            if not m:
                return False
            number = float(m.group(1))
            return ((self.low is None or number >= self.low - 1e-9)
                    and (self.high is None or number <= self.high + 1e-9))
        return any(_same_param_value(v, text) for v in self.values)


def parse_rules(text: str) -> list[ParamRule]:
    """Read the Parameters box ("Name=value; Name~words"). Raises ValueError(entry)."""
    rules = []
    for entry in re.split(r"[;\n]", text or ""):
        entry = entry.strip()
        if not entry:
            continue
        m = re.fullmatch(r"([^=~]+?)\s*([=~])\s*(.+)", entry)
        if not m:
            raise ValueError(entry)
        name, op, rest = m.group(1).strip(), m.group(2), m.group(3).strip()
        if op == "~":
            rules.append(ParamRule(name, contains=rest))
            continue
        r = re.fullmatch(r"(?:(\d+(?:\.\d+)?)\s*([A-Za-z%]*))?\s*\.\.\s*"
                         r"(?:(\d+(?:\.\d+)?)\s*([A-Za-z%]*))?", rest)
        if r and (r.group(1) or r.group(3)):
            rules.append(ParamRule(name, low=float(r.group(1)) if r.group(1) else None,
                                   high=float(r.group(3)) if r.group(3) else None,
                                   unit=r.group(2) or r.group(4) or ""))
        else:
            values = tuple(v.strip() for v in rest.split("|") if v.strip())
            if not values:
                raise ValueError(entry)
            rules.append(ParamRule(name, values))
    return rules


def format_rules(rules: list[ParamRule]) -> str:
    return "; ".join(str(r) for r in rules)


def param_mismatch(part: Part, rule: ParamRule) -> str | None:
    if rule.name.lower() == "description":
        return None if rule.accepts(part.description) else f"without “{rule.contains}” in the description"
    text = next((v for k, v in part.params.items() if k.lower() == rule.name.lower()), None)
    if text is None or text.strip() in ("", "-"):
        return None  # not listed, so it can't be checked
    return None if rule.accepts(text) else f"different {rule.name.lower()}"


def lcsc_filters(rules: list[ParamRule], values: dict[str, list[str]]):
    """Turn rules into the site's parameter filter, using the values param_values() listed.
    Returns (filter, rule): rule is the first one no listed value satisfies, so nothing can
    match. Rules for parameters LCSC can't filter on are checked on each part instead."""
    filters: dict[str, list[str]] = {}
    for rule in rules:
        name = next((n for n in values if n.lower() == rule.name.lower()), None)
        if name is None:
            continue
        allowed = [v for v in values[name] if v.strip() not in ("", "-") and rule.accepts(v)]
        if not allowed:
            return filters, rule
        filters[name] = allowed
    return filters, None


@dataclass
class ConnectorSpec:
    describe: str = ""  # words to search for when the symbol names no part
    rules: list[ParamRule] = field(default_factory=list)
    prefer: list[str] = field(default_factory=list)  # category name words


def connector_spec(lib_name: str, footprint: str) -> ConnectorSpec:
    """What a connector symbol and footprint require, in LCSC's parameter names."""
    name = (footprint or "").split(":")[-1]
    m = re.match(r"(PinHeader|PinSocket)_(\d+)x(\d+)_P(\d+(?:\.\d+)?)mm_(Vertical|Horizontal)"
                 r"(_SMD)?", name)
    if m:
        layout = f"{int(m.group(2))}x{int(m.group(3))}P"
        pitch = f"{_num(float(m.group(4)))}mm"
        smd = bool(m.group(6))
        if m.group(5) == "Vertical":
            mounting = "Surface Mount,Vertical" if smd else "Through Hole"
        else:
            mounting = "Surface Mount, Right Angle" if smd else "Right Angle"
        if m.group(1) == "PinHeader":
            # "Pin Header" keeps out shrouded (JST XH style) headers, which LCSC files with them.
            return ConnectorSpec(f"{pitch} {layout} pin header",
                                 [ParamRule("Pin Structure", (layout,)), ParamRule("Pitch", (pitch,)),
                                  ParamRule("Connector Type", (mounting,)),
                                  ParamRule("Description", contains="Pin Header")],
                                 ["male pins"])
        return ConnectorSpec(f"{pitch} {layout} female header",
                             [ParamRule("Holes Structure", (layout,)), ParamRule("Pitch", (pitch,)),
                              ParamRule("Mounting Type", (mounting,))],
                             ["female"])

    m = re.fullmatch(r"USB_C_(Receptacle|Plug)(?:_(USB2\.0|PowerOnly))?(?:_(\d+)P)?", lib_name)
    if m:
        gender = "Female" if m.group(1) == "Receptacle" else "Male"
        if m.group(2) == "USB2.0":
            # LCSC counts a USB 2.0 Type-C connector's contacts as 12, 14 or 16
            contacts = ParamRule("Number of Contacts", low=12, high=16, unit="P")
        elif m.group(2) == "PowerOnly" and m.group(3) == "6":
            contacts = ParamRule("Number of Contacts", ("6P",))
        else:
            contacts = ParamRule("Number of Contacts", ("24P",))
        return ConnectorSpec(f"Type-C {m.group(1).lower()}",
                             [ParamRule("Connector Type", ("Type-C",)),
                              ParamRule("Gender", (gender,)), contacts],
                             ["usb"])
    m = re.fullmatch(r"USB_(A|B_Micro)(_.*)?", lib_name)
    if m:
        usb = "Type-A" if m.group(1) == "A" else "Micro-B"
        gender = "Male" if "Plug" in lib_name else "Female"
        return ConnectorSpec(f"USB {usb} {'plug' if gender == 'Male' else 'receptacle'}",
                             [ParamRule("Connector Type", (usb,)), ParamRule("Gender", (gender,))],
                             ["usb"])
    if lib_name.startswith("Barrel_Jack"):
        return ConnectorSpec("DC power jack", [ParamRule("Connector Type", ("DC Power Jack",))],
                             ["power connectors"])

    m = re.search(r"_(\d+)x(\d+)_(?:.*_)?P(\d+(?:\.\d+)?)mm", name)
    if m:
        layout = f"{int(m.group(1))}x{int(m.group(2))}P"
        pitch = f"{_num(float(m.group(3)))}mm"
        family = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name.split("_")[0])
        return ConnectorSpec(f"{family} {pitch} {layout}",
                             [ParamRule("Pitch", (pitch,)), ParamRule("Pin Structure", (layout,))])
    return ConnectorSpec()


@dataclass
class Criteria:
    kind: str = "generic"
    value: str = ""
    package: str = ""
    extra: str = ""
    max_tolerance: float | None = None  # percent
    min_voltage: float | None = None    # volts
    min_power: float | None = None      # watts
    min_current: float | None = None    # amps
    min_stock: int = 0
    quantity: int = 1
    prefer_categories: list[str] = field(default_factory=list)
    params: list[ParamRule] = field(default_factory=list)
    describe: str = ""         # searched for when no value is given
    exact_part: bool = False   # value is a complete part number from the symbol
    part_source: str = ""      # where it came from: "the footprint" or "the MPN field"

    def part_number(self) -> re.Pattern | None:
        """The part number results must carry, if the value is one."""
        value = self.value.strip()
        if not value or re.fullmatch(r"C\d{2,}", value, re.I):
            return None
        if self.exact_part or (self.kind not in VALUE_KINDS and looks_like_part_number(value)):
            return part_number_regex(value, self.part_source == "the footprint")
        return None

    def search_value(self) -> str:
        value = self.value.strip()
        if self.part_number() is not None:
            return part_number_search_text(value, self.part_source == "the footprint")
        return value or self.describe

    def keyword(self, with_package: bool = True) -> str:
        words = [self.search_value(), self.package if with_package else "", self.extra]
        return " ".join(w.strip() for w in words if w and w.strip())


def criteria_from_symbol(sym, min_stock: int = 0, quantity: int = 1) -> Criteria:
    kind = guess_kind(sym.reference, sym.lib_id, sym.footprint)
    crit = Criteria(kind=kind, min_stock=min_stock, quantity=quantity)
    value = (sym.value or "").strip().replace("µ", "u").replace("μ", "u")
    lib_name = sym.lib_id.split(":")[-1]
    if (value in ("~", "") or (kind in PASSIVES and value.upper() in
                               {lib_name.upper(), "R", "C", "L", "CP", "FB", "FERRITEBEAD"})
            or (kind == "connector" and value.upper() == lib_name.upper())):
        value = ""

    extras = []
    if kind in PASSIVES:
        m = re.search(r"(?<![\d.])(\d+)\s*/\s*(\d+)\s*W\b", value, re.I)
        if m:
            crit.min_power = int(m.group(1)) / int(m.group(2))
            value = (value[:m.start()] + " " + value[m.end():]).strip()
        rest = []
        for tok in re.split(r"[\s,;/]+", value):
            if not tok:
                continue
            upper = tok.upper()
            if re.fullmatch(r"\d+(\.\d+)?[kKmM]?V(DC|AC)?", tok, re.I):
                crit.min_voltage = parse_amount(re.sub(r"(?i)(dc|ac)$", "", tok), "V")
            elif re.fullmatch(r"±?\d+(\.\d+)?%", tok):
                crit.max_tolerance = parse_amount(tok, "%")
            elif re.fullmatch(r"\d+(\.\d+)?[mk]?W", tok, re.I):
                crit.min_power = parse_amount(tok, "W")
            elif kind in ("inductor", "ferrite") and re.fullmatch(r"\d+(\.\d+)?[mu]?A", tok, re.I):
                crit.min_current = parse_amount(tok, "A")
            elif DIELECTRIC_ALIASES.get(upper, upper) in DIELECTRICS:
                extras.append(DIELECTRIC_ALIASES.get(upper, upper))
            elif tok in CHIP_SIZES:
                crit.package = tok
            else:
                rest.append(tok)
        value = " ".join(rest)

    if kind in MAIN_PARAM:
        parsed = parse_component_value(value, kind)
        if parsed is not None:
            value = format_component_value(parsed, kind)
    elif kind == "generic" and value == lib_name:
        value = value.replace("_", " ")  # a library default such as "Barrel_Jack"

    # Words that steer LCSC's search engine to the right kind of part.
    if kind == "led" and "led" not in value.lower():
        extras.insert(0, "LED")
    elif kind == "ferrite" and "ferrite" not in value.lower():
        extras.insert(0, "ferrite bead")
    elif kind == "fuse":
        value = re.sub(r"(?i)\b(poly\s*fuse|pptc|resettable(\s+fuse)?)\b", "PTC", value)
        if not re.search(r"(?i)\b(fuse|ptc)\b", value):
            extras.insert(0, "fuse")

    # A part number in the MPN field (or, for a connector, the footprint's name) says exactly
    # which part is wanted, whatever the Value says ("USBC", "SS_ESD_Port1").
    if kind in PART_NUMBER_KINDS:
        found = sym.get(*MPN_FIELDS)
        number = found[1].strip() if found and found[1].strip() not in ("", "~") else ""
        source = "the MPN field"
        if not number and kind == "connector":
            number, source = part_number_from_footprint(sym.footprint), "the footprint"
        if number:
            value, crit.exact_part, crit.part_source = number, True, source
    crit.value = value

    footprint_name = sym.footprint.split(":")[-1]
    if footprint_name.startswith("CP_Elec"):
        crit.prefer_categories = ["aluminum electrolytic"]
    elif "tantalum" in footprint_name.lower():
        crit.prefer_categories = ["tantalum"]
    if kind == "connector":
        spec = connector_spec(lib_name, sym.footprint)
        crit.params, crit.prefer_categories = spec.rules, spec.prefer
        crit.describe = spec.describe or lib_name.replace("_", " ")

    # Connector "packages" on LCSC are things like "SMD"; the footprint is checked by part
    # number or parameters instead.
    footprint_package = "" if kind == "connector" else package_from_footprint(sym.footprint)
    if footprint_package:
        crit.package = footprint_package
    elif not crit.package and kind != "connector":
        found = sym.get(*FIELD_ALIASES["package"])
        if found and found[1].strip():
            crit.package = found[1].strip()

    for key, unit, attr in (("tolerance", "%", "max_tolerance"), ("voltage", "V", "min_voltage"),
                            ("power", "W", "min_power"), ("current", "A", "min_current")):
        found = sym.get(*FIELD_ALIASES[key])
        if found:
            amount = parse_amount(found[1].replace("DC", "").replace("dc", ""), unit)
            if amount is not None:
                setattr(crit, attr, amount)
    if kind == "capacitor":
        found = sym.get(*FIELD_ALIASES["dielectric"])
        if found:
            code = DIELECTRIC_ALIASES.get(found[1].strip().upper(), found[1].strip().upper())
            if code in DIELECTRICS and code not in extras:
                extras.append(code)
    crit.extra = " ".join(extras)
    return crit


# ----------------------------------------------------------------------------------------
# Matching LCSC parts against the criteria


def _amounts(text: str, unit: str) -> list[float]:
    text = (text or "").replace("µ", "u").replace("μ", "u")
    return [float(n) * PREFIX.get(p, 1.0) for n, p in
            re.findall(r"(\d+(?:\.\d+)?)\s*([pnumkKM]?)" + re.escape(unit) + r"(?![a-z])", text)]


def part_rating(part: Part, spec) -> float | None:
    names, skip, unit = spec
    for wanted in names:
        for name, text in part.params.items():
            low = name.lower()
            if wanted in low and not any(s in low for s in skip):
                values = _amounts(text, unit)
                if values:
                    return max(values)
    return None


def part_value(part: Part, kind: str) -> float | None:
    text = part.params.get(MAIN_PARAM.get(kind, ""), "")
    if not text:
        return None
    if kind == "resistor":
        # LCSC writes milliohms as "mΩ" and megaohms as "MΩ"; keep the case.
        m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([mkMG]?)\s*(?:Ω|Ω|ohm)s?\s*", text)
        return float(m.group(1)) * PREFIX.get(m.group(2), 1.0) if m else None
    return parse_component_value(text, kind)


def part_tolerance(part: Part, value: float | None) -> float | None:
    text = part.params.get("Tolerance", "")
    percents = [abs(float(x)) for x in re.findall(r"(\d+(?:\.\d+)?)\s*%", text)]
    if percents:
        return max(percents)
    m = re.search(r"(\d+(?:\.\d+)?)\s*([pnu]?)F", text)
    if m and value:
        return float(m.group(1)) * PREFIX.get(m.group(2), 1.0) / value * 100
    return None


def _norm_package(text: str) -> str:
    return re.sub(r"[^0-9A-Z]", "", (text or "").upper()).replace("SOIC", "SOP")


def package_matches(wanted: str, have: str) -> bool:
    if wanted in CHIP_SIZES:
        return re.search(r"(?<!\d)" + wanted + r"(?!\d)", have or "") is not None
    a, b = _norm_package(wanted), _norm_package(have)
    return bool(a and b) and (a in b or b in a)


def rejection_reason(part: Part, crit: Criteria, target: float | None,
                     check_package: bool, number: re.Pattern | None = None) -> str | None:
    if number is not None and not part_number_matches(number, part.mpn, crit.exact_part):
        return "different part number"
    buy, unit, _ = part.order_for(max(crit.quantity, 1))
    if unit is None:
        return "no price listed"
    if part.stock < max(crit.min_stock, buy):
        return "not enough stock"
    if target is not None:
        actual = part_value(part, crit.kind)
        if actual is not None and abs(actual - target) > max(abs(target) * 1e-3, 1e-15):
            return "different value"
    if crit.package and (crit.package in CHIP_SIZES or check_package):
        if not package_matches(crit.package, part.package):
            return "different package"
    if crit.max_tolerance is not None:
        tol = part_tolerance(part, target if target is not None else part_value(part, crit.kind))
        if tol is None:
            return "tolerance not listed"
        if tol > crit.max_tolerance + 1e-9:
            return "tolerance too wide"
    for limit, spec, label in ((crit.min_voltage, VOLTAGE_SPEC, "voltage rating"),
                               (crit.min_power, POWER_SPEC, "power rating"),
                               (crit.min_current, CURRENT_SPEC, "current rating")):
        if limit is None:
            continue
        rating = part_rating(part, spec)
        if rating is None:
            return f"{label} not listed"
        if rating < limit * (1 - 1e-9):
            return f"{label} too low"
    for rule in crit.params:
        reason = param_mismatch(part, rule)
        if reason:
            return reason
    return None


@dataclass
class Candidate:
    part: Part
    buy_qty: int
    unit_price: float
    total: float


@dataclass
class SearchResult:
    keyword: str = ""
    candidates: list[Candidate] = field(default_factory=list)
    plan: SearchPlan | None = None
    category: Category | None = None
    examined: int = 0
    listed: int = 0
    rejected: Counter = field(default_factory=Counter)
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if not self.candidates:
            head = "No part meets every criterion."
        else:
            head = f"{len(self.candidates)} matching part(s); the cheapest is selected."
        if self.examined:
            head += f" Checked {self.examined} in-stock listing(s)"
            head += f" in {self.category.name}." if self.category else "."
        if self.rejected:
            hidden = ", ".join(f"{n} {why}" for why, n in self.rejected.most_common())
            head += f" Excluded: {hidden}."
        return " ".join([head] + self.notes)


def choose_category(categories: list[Category], kind: str,
                    prefer: list[str] | None = None) -> Category:
    want, avoid = KIND_CATEGORY_WORDS.get(kind, ([], []))
    if prefer:
        hinted = [c for c in categories if any(w in c.name.lower() for w in prefer)
                  and not any(a in c.name.lower() for a in avoid)]
        if hinted:
            return max(hinted, key=lambda c: c.count)
    preferred = [c for c in categories
                 if any(w in c.name.lower() for w in want)
                 and not any(a in c.name.lower() for a in avoid)]
    return max(preferred or categories, key=lambda c: c.count)


def rank(parts: list[Part], crit: Criteria, check_package: bool):
    target = parse_component_value(crit.value, crit.kind) if crit.kind in MAIN_PARAM else None
    number = crit.part_number()
    candidates, rejected = [], Counter()
    seen = set()
    for part in parts:
        if part.code in seen:
            continue
        seen.add(part.code)
        reason = rejection_reason(part, crit, target, check_package, number)
        if reason:
            rejected[reason] += 1
            continue
        buy, unit, total = part.order_for(max(crit.quantity, 1))
        candidates.append(Candidate(part, buy, unit, total))
    candidates.sort(key=lambda c: (round(c.total, 6), c.unit_price, -c.part.stock))
    return candidates, rejected


def search(crit: Criteria, category_id: int | None = None,
           progress: Callable[[str], None] | None = None) -> SearchResult:
    progress = progress or (lambda _msg: None)
    result = SearchResult(keyword=crit.keyword())

    code = crit.value.strip().upper()
    if re.fullmatch(r"C\d{2,}", code) and not crit.package and not crit.extra:
        progress(f"Looking up {code}…")
        part = lcsc_api.get_part(code)
        if part is None:
            result.notes.append(f"LCSC has no part {code}.")
            return result
        result.examined = result.listed = 1
        candidates, rejected = rank([part], crit, check_package=False)
        if not candidates:
            buy, unit, total = part.order_for(max(crit.quantity, 1))
            candidates = [Candidate(part, buy, unit or 0.0, total or 0.0)]
            result.notes.append(f"Note: {code} does not meet: {', '.join(rejected)}.")
        result.candidates = candidates
        return result

    if not result.keyword:
        result.notes.append("Enter a value or part number to search for.")
        return result

    progress(f"Searching LCSC for “{result.keyword}”…")
    plan = lcsc_api.plan_search(result.keyword)
    check_package = False
    if crit.package and (plan.scene == "NO_RESULT" or not plan.categories):
        fallback = crit.keyword(with_package=False)
        if fallback:
            progress(f"Searching LCSC for “{fallback}”…")
            alt = lcsc_api.plan_search(fallback)
            if alt.categories:
                plan, check_package = alt, True
                result.keyword = fallback
                result.notes.append(f"LCSC didn't accept “{crit.package}” in the search, "
                                    "so the package was checked here instead.")
    elif crit.package and not plan.understood_package:
        check_package = True
    result.plan = plan
    if not plan.categories:
        result.notes.append(f"LCSC found nothing for “{result.keyword}”.")
        return result

    number = crit.part_number()
    chosen = next((c for c in plan.categories if c.id == category_id), None)
    if chosen is None and number is not None:
        # A part number can be filed in any of the categories LCSC found it in.
        category_ids = [c.id for c in plan.categories]
        where = f" in {len(category_ids)} categories" if len(category_ids) > 1 else ""
    else:
        result.category = chosen or choose_category(plan.categories, crit.kind,
                                                    crit.prefer_categories)
        category_ids = [result.category.id]
        where = f" in {result.category.name}"

    filters: dict[str, list[str]] = {}
    if crit.params and number is None:
        # Let LCSC filter by the parameters too, so the cheapest listings it returns are
        # ones that can match, rather than the cheapest of everything in the category.
        progress("Checking LCSC's parameter filters…")
        filters, impossible = lcsc_filters(crit.params, lcsc_api.param_values(plan, category_ids))
        if impossible is not None:
            result.notes.append(f"LCSC has no in-stock parts{where} with {impossible}.")
            return result

    parts: list[Part] = []
    for page in range(1, MAX_PAGES + 1):
        batch, listed, pages = lcsc_api.list_parts(plan, category_ids, page, params=filters)
        parts.extend(batch)
        result.listed = listed
        progress(f"Fetched {len(parts)} of {listed} listing(s){where}…")
        if not batch or page >= pages:
            break
    result.examined = len(parts)
    if result.listed > len(parts):
        result.notes.append(f"Only the {len(parts)} lowest-priced of {result.listed} listings "
                            "were checked; add keywords to narrow the search.")
    result.candidates, result.rejected = rank(parts, crit, check_package)
    if crit.exact_part and number is not None:
        result.notes.append(f"Only parts numbered “{crit.value}” (from {crit.part_source}) are "
                            "accepted. To compare other parts, edit or clear Value / part number.")
    elif crit.kind == "connector" and number is None and result.candidates:
        result.notes.append("Connectors with the same parameters can still have different "
                            "footprints: check the part's drawing against yours before applying.")
    return result
