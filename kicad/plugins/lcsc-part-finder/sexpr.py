"""Minimal S-expression reader for KiCad files.

Every node and atom remembers its character offsets in the source text, so an
edit can be spliced into the original file without re-serialising (and
reformatting) anything else.
"""

from __future__ import annotations

import re

_TOKEN_RE = re.compile(r'\s+|(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+)', re.S)
_UNESCAPES = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}


class SexprError(ValueError):
    pass


class Atom:
    __slots__ = ("value", "quoted", "start", "end")

    def __init__(self, value: str, quoted: bool, start: int, end: int):
        self.value = value
        self.quoted = quoted
        self.start = start
        self.end = end

    def __repr__(self) -> str:
        return f"Atom({self.value!r})"


class Node:
    __slots__ = ("items", "start", "end")

    def __init__(self, start: int):
        self.items: list[Node | Atom] = []
        self.start = start
        self.end = -1

    @property
    def head(self) -> str | None:
        first = self.items[0] if self.items else None
        if isinstance(first, Atom) and not first.quoted:
            return first.value
        return None

    def nodes(self, head: str | None = None) -> list[Node]:
        return [c for c in self.items if isinstance(c, Node) and (head is None or c.head == head)]

    def first(self, head: str) -> Node | None:
        for c in self.items:
            if isinstance(c, Node) and c.head == head:
                return c
        return None

    def atom(self, index: int, default: str | None = None) -> str | None:
        if index < len(self.items) and isinstance(self.items[index], Atom):
            return self.items[index].value
        return default

    def __repr__(self) -> str:
        return f"Node({self.head!r}, {len(self.items)} items)"


def unescape(raw: str) -> str:
    if "\\" not in raw:
        return raw
    return re.sub(r"\\(.)", lambda m: _UNESCAPES.get(m.group(1), m.group(1)), raw, flags=re.S)


def quote(value: str) -> str:
    """Quote a string the way KiCad's OUTPUTFORMATTER does."""
    escaped = (value.replace("\\", "\\\\").replace('"', '\\"')
               .replace("\n", "\\n").replace("\r", "\\r"))
    return f'"{escaped}"'


def parse(text: str) -> list[Node]:
    """Parse every top-level list in ``text``. Stray top-level atoms are ignored."""
    roots: list[Node] = []
    stack: list[Node] = []
    pos = 0
    for m in _TOKEN_RE.finditer(text):
        if m.start() != pos:
            raise SexprError(f"Unexpected character at offset {pos}: {text[pos:pos + 20]!r}")
        pos = m.end()
        if m.group(1):
            node = Node(m.start())
            (stack[-1].items if stack else roots).append(node)
            stack.append(node)
        elif m.group(2):
            if not stack:
                raise SexprError(f"Unbalanced ')' at offset {m.start()}")
            stack.pop().end = m.end()
        elif m.group(3) is not None:
            if stack:
                stack[-1].items.append(Atom(unescape(m.group(3)), True, m.start(), m.end()))
        elif m.group(4):
            if stack:
                stack[-1].items.append(Atom(m.group(4), False, m.start(), m.end()))
    if pos != len(text):
        raise SexprError(f"Unexpected character at offset {pos}: {text[pos:pos + 20]!r}")
    if stack:
        raise SexprError("Unbalanced '(' — the text ends inside a list")
    return roots
