"""The rule catalogue, `rules.json`: derived from the specification and the schema, never written by hand (design D13).

`rules.json` holds:

- ``rules``: one entry per rule of the specification's ``## 9. Conformance``, in order, extracted from its four rule
  tables with a Markdown parser (markdown-it-py). Extraction is strict: a malformed row, a repeated code, a missing
  or unknown column, an unknown layer or level, or a rule whose RFC 2119 keyword contradicts its level is an error.
- ``errors``: for each keyword of the generated JSON Schemas that can report an error, its absolute keyword location
  (the schema's ``$id``, ``#``, and the JSON Pointer to the keyword) and the code of the rule it enforces. The code
  comes from the LinkML sources, where each constraint names it in a ``rule`` annotation (on the type or slot that
  defines a pattern, on a class rule, on each branch of an ``exactly_one_of``), or, for the keywords whose code never
  varies, from a default. A map's keys take their key's code for both their ``type`` and their ``pattern``. A class's
  checks (its exactly-one-of and its class rules) are guarded members of ``allOf``: each member's ``if`` and the
  keywords of its ``then`` take the check's code, and nothing inside an ``if`` or a ``not`` does. Every such keyword
  has exactly one code, every code is a schema-layer rule of §9, and every ``rule`` annotation gives some keyword its
  code.
"""

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from linkml_runtime import SchemaView
from markdown_it import MarkdownIt
from markdown_it.rules_block.table import escapedSplit
from markdown_it.token import Token

SECTION = "9. Conformance"
"""The `##` heading whose tables are the catalogue."""

COLUMNS = {
    "parse and schema": ["Code", "Layer", "Level", "Rule", "Source"],
    "validator": ["Code", "Level", "Rule", "Source"],
    "check": ["Code", "Level", "Rule", "Status when broken", "Source"],
    "runner": ["Code", "Level", "Rule", "Source"],
}
"""Each `###` subsection of §9, in order, with the columns of its rule table (the one table there with a `Code` column)."""

FIELDS = {"Rule": "statement", "Source": "source", "Status when broken": "status"}
"""The columns copied into a rule's entry as inline Markdown, with the entry field each becomes."""

LAYERS = {"parse and schema": {"parse", "schema"}}
"""The layers a subsection's Layer column may name; a subsection without one is its own layer."""

LEVELS = {"MUST", "SHOULD", "MAY"}

KEYWORDS = {
    "MUST": "MUST",
    "REQUIRED": "MUST",
    "SHALL": "MUST",
    "SHOULD": "SHOULD",
    "RECOMMENDED": "SHOULD",
    "MAY": "MAY",
    "OPTIONAL": "MAY",
}
"""The RFC 2119 keywords, in capitals, with the level each states (`NOT` changes none)."""

ANNOTATION = "rule"
"""The LinkML annotation that names the code of the constraint it is on."""

DEFAULTS = {
    "type": "WRONG_TYPE",
    "minProperties": "EMPTY_COLLECTION",
    "minItems": "EMPTY_COLLECTION",
    "uniqueItems": "DUPLICATE_ENTRY",
    "enum": "INVALID_VALUE",
    "minimum": "INVALID_VALUE",
}
"""The keywords whose code never varies, with that code. Also `required` outside a rule (`MISSING_FIELD`) and
`additionalProperties: false` (`UNKNOWN_FIELD`).

Two take their default only where it is what they check. A map key's `type` takes the key's code, as its `pattern`
does. `minProperties` and `minItems` take `EMPTY_COLLECTION` ("at least one entry") only with a value of 1 (see
`ONE_ENTRY`): any other minimum has no code, as `maxItems` has none."""

ONE_ENTRY = {"minProperties", "minItems"}
"""The keywords whose default, `EMPTY_COLLECTION`, holds only when their value is 1."""

METADATA = {"$comment", "$id", "$schema", "description", "title"}
"""Keywords that never report an error."""

ENTRY_SUFFIX = "__identifier_optional"
"""The suffix of the `$defs` entry LinkML makes for a class written as a map entry, its key left out."""


def json_pointer(tokens: Iterable[Any]) -> str:
    """The JSON Pointer (RFC 6901) made of `tokens`, each escaped (`~` as `~0`, `/` as `~1`); `""` for none."""
    return "".join(
        "/" + str(token).replace("~", "~0").replace("/", "~1") for token in tokens
    )


# --- The rules, from §9 ---


class _Row:
    """A row of a rule table, for error messages that name it."""

    def __init__(self, line: int, heading: str, label: str):
        self.line, self.heading, self.label = line, heading, label

    def error(self, problem: str) -> ValueError:
        return ValueError(
            f"line {self.line}, ### {self.heading}, row {self.label}: {problem}"
        )


def _markdown() -> MarkdownIt:
    return MarkdownIt("commonmark").enable("table")


def _text(tokens: list[Token]) -> str:
    """The plain text of inline tokens: their text and code spans, without markup, each set apart by a space.

    So a keyword written against a code span or a link (``see`SHOULD` ``, `[the](#a)SHOULD`) is still a word.
    """
    return " ".join(t.content for t in tokens if t.type in ("text", "code_inline"))


def _shape(tokens: list[Token]) -> list[tuple[str, str, str]]:
    """Inline tokens as `(type, content, markup)`, adjacent text merged, for comparing two parses."""
    shape: list[tuple[str, str, str]] = []
    for t in tokens:
        if t.type == "text" and shape and shape[-1][0] == "text":
            shape[-1] = ("text", shape[-1][1] + t.content, "")
        else:
            shape.append((t.type, t.content, t.markup))
    return shape


def _inline_markdown(inline: Token, row: _Row, column: str) -> str:
    """A cell's inline Markdown, with each link reduced to its text."""
    kept = [
        t for t in inline.children or [] if t.type not in ("link_open", "link_close")
    ]
    parts = []
    for t in kept:
        if t.type == "text":
            parts.append(t.content)
        elif t.type == "code_inline":
            pad = (
                " "
                if t.content[:1] in ("`", " ") or t.content[-1:] in ("`", " ")
                else ""
            )
            parts.append(t.markup + pad + t.content + pad + t.markup)
        elif t.type in ("em_open", "em_close", "strong_open", "strong_close"):
            parts.append(t.markup)
        elif t.type == "html_inline":
            parts.append(t.content)
        else:
            raise row.error(
                f"its {column} cell holds a {t.type}, which a rule's cell can't"
            )
    markdown = "".join(parts)
    if _shape(_markdown().parseInline(markdown)[0].children or []) != _shape(kept):
        raise row.error(
            f"its {column} cell can't be written back as Markdown without its links"
        )
    return markdown


def _code(inline: Token, row: _Row) -> str:
    """The code of a row: its Code cell, one code span of capitals, digits and underscores, starting with a capital."""
    children = inline.children or []
    code = (
        children[0].content
        if len(children) == 1 and children[0].type == "code_inline"
        else ""
    )
    if not (
        code[:1].isascii()
        and code[:1].isupper()
        and all(c.isascii() and (c.isupper() or c.isdigit() or c == "_") for c in code)
    ):
        raise row.error(
            "the Code cell must be one code span holding a code, such as `INVALID_ID`"
        )
    return code


def _keywords(text: str) -> list[str]:
    """The RFC 2119 keywords in `text`, as whole words (a word is letters, digits and underscores)."""
    words = "".join(c if c.isalnum() or c == "_" else " " for c in text).split()
    return [word for word in words if word in KEYWORDS]


def _sections(tokens: list[Token]) -> list[tuple[str, int, list[list[Token]]]]:
    """`(heading, line, tables)` for each `###` subsection of §9, each table as its tokens."""
    starts = [
        i
        for i, t in enumerate(tokens)
        if t.type == "heading_open"
        and t.tag == "h2"
        and tokens[i + 1].content == SECTION
    ]
    if len(starts) != 1:
        raise ValueError(
            f"the specification must have one '## {SECTION}' heading, not {len(starts)}"
        )
    sections: list[tuple[str, int, list[list[Token]]]] = []
    table: list[Token] | None = None
    for i in range(starts[0] + 3, len(tokens)):
        t = tokens[i]
        if t.type == "heading_open" and t.tag in ("h1", "h2"):
            break
        if t.type == "heading_open" and t.tag == "h3":
            assert t.map is not None
            sections.append((tokens[i + 1].content, t.map[0] + 1, []))
        elif t.type == "table_open":
            table = []
        if table is not None:
            table.append(t)
            if t.type == "table_close":
                if sections:
                    sections[-1][2].append(table)
                elif "Code" in _rows(table)[0]:
                    raise ValueError(
                        f"line {(table[0].map or [0])[0] + 1}: a rule table (a table with a Code column)"
                        " must be under one of §9's ### subsections"
                    )
                table = None
    return sections


def _cells(tokens: list[Token], start: int) -> list[Token]:
    """The inline tokens of the cells of the row that opens at `tokens[start]`."""
    cells = []
    for t in tokens[start + 1 :]:
        if t.type == "tr_close":
            return cells
        if t.type == "inline":
            cells.append(t)
    raise ValueError("a table row without its end")


def _rows(table: list[Token]) -> tuple[list[str], list[tuple[int, list[Token]]]]:
    """A table's header names, and `(line, cells)` for each of its body rows."""
    header: list[str] = []
    rows = []
    in_body = False
    for i, t in enumerate(table):
        if t.type == "tbody_open":
            in_body = True
        elif t.type == "tr_open":
            assert t.map is not None
            cells = _cells(table, i)
            if in_body:
                rows.append((t.map[0] + 1, cells))
            else:
                header = [cell.content for cell in cells]
    return header, rows


def _source_cell_count(lines: list[str], line: int) -> int:
    """How many cells the table row at `line` (1-based) writes, split as markdown-it splits it."""
    cells = escapedSplit(lines[line - 1].strip())
    if cells and cells[0] == "":
        cells.pop(0)
    if cells and cells[-1] == "":
        cells.pop()
    return len(cells)


def extract_rules(markdown: str) -> list[dict]:
    """The rules of `markdown`'s `## 9. Conformance`, one entry per row of its four rule tables, in order.

    Each entry has the row's `code`, `layer`, `level`, `statement` (its Rule cell) and `source`, and, in the check
    table, `status` (its *Status when broken* cell); the last three are the cells' inline Markdown, with each link
    reduced to its text. Raises `ValueError`, naming the row or table, on anything malformed.
    """
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    sections = _sections(_markdown().parse(markdown))
    headings = [heading for heading, _, _ in sections]
    for heading, line, _ in sections:
        if heading not in COLUMNS:
            raise ValueError(
                f"line {line}: ### {heading} is not a subsection of §9: they are {', '.join(COLUMNS)}"
            )
    if headings != list(COLUMNS):
        missing = [heading for heading in COLUMNS if heading not in headings]
        raise ValueError(
            f"§9 has no ### {missing[0]}"
            if missing
            else f"§9's subsections must be {', '.join(COLUMNS)}, in order"
        )
    rules: list[dict] = []
    seen: dict[str, int] = {}
    for heading, line, tables in sections:
        rule_tables = [table for table in tables if "Code" in _rows(table)[0]]
        if len(rule_tables) != 1:
            raise ValueError(
                f"line {line}, ### {heading}: has no rule table (a table with a Code column)"
                if not rule_tables
                else f"line {line}, ### {heading}: has {len(rule_tables)} rule tables, not one"
            )
        header, rows = _rows(rule_tables[0])
        table_line = (rule_tables[0][0].map or [0])[0] + 1
        for column in COLUMNS[heading]:
            if column not in header:
                raise ValueError(
                    f"line {table_line}, ### {heading}: the rule table has no {column} column"
                )
        for column in header:
            if column not in COLUMNS[heading] or header.count(column) > 1:
                raise ValueError(
                    f"line {table_line}, ### {heading}: the rule table's column {column!r} is unknown or repeated"
                )
        for row_line, cells in rows:
            row = _Row(
                row_line, heading, cells[header.index("Code")].content or "(no code)"
            )
            written = _source_cell_count(lines, row_line)
            if written != len(header):
                raise row.error(
                    f"it has {written} cells, but the table has {len(header)} columns"
                )
            cell = dict(zip(header, cells))
            for column, inline in cell.items():
                if not inline.content:
                    raise row.error(f"its {column} cell is empty")
            code = _code(cell["Code"], row)
            layer = cell["Layer"].content if "Layer" in cell else heading
            if layer not in LAYERS.get(heading, {heading}):
                raise row.error(
                    f"unknown layer {layer!r}: ### {heading} holds {' and '.join(sorted(LAYERS.get(heading, {heading})))}"
                )
            level = cell["Level"].content
            if level not in LEVELS:
                raise row.error(
                    f"unknown level {level!r}: a level is MUST, SHOULD or MAY"
                )
            statement = cell["Rule"].children or []
            for keyword in _keywords(_text(statement)):
                if KEYWORDS[keyword] != level:
                    raise row.error(
                        f"its rule says {keyword}, which contradicts its level, {level}"
                    )
            if code in seen:
                raise row.error(
                    f"the code {code} is already the code of the row at line {seen[code]}"
                )
            seen[code] = row_line
            entry = {"code": code, "layer": layer, "level": level}
            for column, name in FIELDS.items():
                if column in cell:
                    entry[name] = _inline_markdown(cell[column], row, column)
            rules.append(entry)
    return rules


# --- The error map, from the schema ---


def _annotation(element: Any) -> str | None:
    """The `rule` annotation of a LinkML element, or None."""
    annotations = getattr(element, "annotations", None) or {}
    annotation = (
        annotations.get(ANNOTATION)
        if isinstance(annotations, dict)
        else getattr(annotations, ANNOTATION, None)
    )
    if annotation is None:
        return None
    value = getattr(annotation, "value", annotation)
    if not isinstance(value, str):
        raise TypeError(f"a {ANNOTATION!r} annotation must be a code, not {value!r}")
    return value


class _ErrorMap:
    """The walk of one generated JSON Schema, keyword by keyword, with the LinkML element each subschema comes from."""

    def __init__(self, schema: dict, view: SchemaView):
        self.view = view
        self.base = schema["$id"] + "#"
        self.codes: dict[str, str] = {}
        self.used: set[tuple[str, ...]] = set()
        """The LinkML elements whose `rule` annotation gave a code, keyed as `_rule_annotations` keys them."""

    def location(self, pointer: list[Any]) -> str:
        return self.base + json_pointer(pointer)

    def add(self, pointer: list[Any], code: str) -> None:
        location = self.location(pointer)
        if location in self.codes:
            raise ValueError(f"{location}: two codes")
        self.codes[location] = code

    def unknown(self, pointer: list[Any], keyword: str) -> ValueError:
        return ValueError(
            f"{self.location([*pointer, keyword])}: no code for this keyword (tools/rules.py)"
        )

    # A class's subschema: the root, or a `$defs` entry.

    def klass(self, node: dict, pointer: list[Any], name: str) -> None:
        for keyword, value in node.items():
            here = [*pointer, keyword]
            if keyword in METADATA or (keyword == "$defs" and not pointer):
                continue
            if keyword == "type":
                self.add(here, DEFAULTS[keyword])
            elif keyword == "required":
                self.add(here, "MISSING_FIELD")
            elif keyword == "additionalProperties" and isinstance(value, bool):
                if value is False:
                    self.add(here, "UNKNOWN_FIELD")
            elif keyword == "properties":
                for field, sub in value.items():
                    self.value(sub, [*here, field], name, self.slot(name, field, here))
            elif keyword == "allOf":
                self.checks(value, here, name)
            else:
                raise self.unknown(pointer, keyword)

    def checks(self, members: list[dict], pointer: list[Any], cls: str) -> None:
        """A class's checks, each a guarded member of `allOf` (the generator's step 5): its exactly-one-of first, if it
        has one, then its class rules, in order.

        Each member is `{if, then}`. Its `if` takes the check's code, since Ajv reports it when the `then` fails, but
        nothing inside it does: it only guards the check. The keywords of its `then` that can fail take the code too.
        """
        codes = (
            [self.exactly_one_of_code(cls, pointer)]
            if self.view.get_class(cls).exactly_one_of
            else []
        ) + self.class_rules(cls, pointer)
        if len(members) != len(codes):
            raise ValueError(
                f"{self.location(pointer)}: {len(members)} checks, but {cls} has {len(codes)}"
            )
        for index, (member, code) in enumerate(zip(members, codes)):
            here = [*pointer, index]
            if set(member) - METADATA != {"if", "then"}:
                raise ValueError(
                    f"{self.location(here)}: a check is a member with an `if` and a `then` only"
                )
            self.add([*here, "if"], code)
            then = member["then"]
            if index == 0 and self.view.get_class(cls).exactly_one_of:
                if set(then) - METADATA != {"oneOf"}:
                    raise ValueError(
                        f"{self.location([*here, 'then'])}: {cls}'s exactly_one_of is a `then` with a `oneOf` only"
                    )
                self.exactly_one_of(then["oneOf"], [*here, "then", "oneOf"], cls)
            else:
                self.condition(then, [*here, "then"], code)

    def enum(self, node: dict, pointer: list[Any]) -> None:
        for keyword in node:
            if keyword in METADATA:
                continue
            if keyword not in ("type", "enum"):
                raise self.unknown(pointer, keyword)
            self.add([*pointer, keyword], DEFAULTS[keyword])

    # A slot's subschema: a property, a list's items, a map's keys or entries.

    def value(self, node: dict, pointer: list[Any], cls: str, slot: Any) -> None:
        for keyword, value in node.items():
            here = [*pointer, keyword]
            if keyword in METADATA or keyword == "$ref":
                continue  # A `$ref`'s target is walked as its own `$defs` entry.
            if keyword in ONE_ENTRY and value != 1:
                raise self.unknown(pointer, keyword)
            if keyword in DEFAULTS:
                self.add(here, DEFAULTS[keyword])
            elif keyword == "pattern":
                self.add(here, self.pattern_code(cls, slot, here))
            elif keyword == "items":
                self.value(value, here, cls, slot)
            elif keyword == "propertyNames":
                key = self.view.get_identifier_slot(slot.range, use_key=True)
                key_slot = self.view.induced_slot(key.name, slot.range)
                code = self.pattern_code(slot.range, key_slot, here)
                self.add(here, code)
                self.key(value, here, code)
            elif keyword == "additionalProperties" and isinstance(value, dict):
                # A map's entries: the object form refers to the entry's class; the compact form is its other slot.
                if "$ref" in value:
                    self.value(value, here, cls, slot)
                else:
                    self.value(value, here, slot.range, self.compact_slot(slot, here))
            else:
                raise self.unknown(pointer, keyword)

    def key(self, node: dict, pointer: list[Any], code: str) -> None:
        """A map's keys: their `type` and `pattern` both take the key's code, since either fails on a key that isn't one."""
        for keyword in node:
            if keyword in METADATA:
                continue
            if keyword not in ("type", "pattern"):
                raise self.unknown(pointer, keyword)
            self.add([*pointer, keyword], code)

    # Inside a class rule or an exactly-one-of branch, every keyword that can report an error takes the rule's code.

    def condition(self, node: dict, pointer: list[Any], code: str) -> None:
        for keyword, value in node.items():
            here = [*pointer, keyword]
            if keyword in METADATA:
                continue
            if keyword == "properties":
                for field, sub in value.items():
                    self.condition(sub, [*here, field], code)
            elif keyword == "not":
                # Nothing inside a `not` is reported, only the `not`.
                self.add(here, code)
            elif keyword in DEFAULTS or keyword in ("required", "pattern"):
                self.add(here, code)
            else:
                raise self.unknown(pointer, keyword)

    def exactly_one_of(
        self, branches: list[dict], pointer: list[Any], cls: str
    ) -> None:
        if len(self.view.get_class(cls).exactly_one_of) != len(branches):
            raise ValueError(f"{self.location(pointer)}: not {cls}'s exactly_one_of")
        code = self.exactly_one_of_code(cls, pointer)
        self.add(pointer, code)
        for index, branch in enumerate(branches):
            self.condition(branch, [*pointer, index], code)

    # From the schema to LinkML.

    def slot(self, cls: str, field: str, pointer: list[Any]) -> Any:
        for slot in self.view.class_induced_slots(cls):
            if (slot.alias or slot.name) == field:
                return slot
        raise ValueError(f"{self.location(pointer)}: {cls} has no slot {field}")

    def compact_slot(self, slot: Any, pointer: list[Any]) -> Any:
        """The one slot besides its key of the class a compact-form map's entries are."""
        key = self.view.get_identifier_slot(slot.range, use_key=True)
        others = [
            s for s in self.view.class_induced_slots(slot.range) if s.name != key.name
        ]
        if len(others) != 1:
            raise ValueError(
                f"{self.location(pointer)}: {slot.range} has no one slot besides its key"
            )
        return others[0]

    def exactly_one_of_code(self, cls: str, pointer: list[Any]) -> str:
        """The code of `cls`'s exactly_one_of, which each of its branches names, the same one."""
        expressions = self.view.get_class(cls).exactly_one_of
        codes = [_annotation(expression) for expression in expressions]
        if None in codes or len(set(codes)) != 1:
            raise ValueError(
                f"{self.location(pointer)}: each branch of {cls}'s exactly_one_of must name the same code"
                f" in a {ANNOTATION!r} annotation, not {codes}"
            )
        self.used.update(
            ("exactly_one_of", cls, str(index)) for index in range(len(expressions))
        )
        return codes[0]

    def class_rules(self, cls: str, pointer: list[Any]) -> list[str]:
        """The code of each class rule of `cls` and its ancestors, in the order LinkML writes them; none bidirectional."""
        codes = []
        for ancestor in self.view.class_ancestors(cls):
            for index, rule in enumerate(self.view.get_class(ancestor).rules or []):
                if rule.bidirectional:
                    raise ValueError(
                        f"{self.location(pointer)}: {cls}'s class rules can't be bidirectional"
                    )
                code = _annotation(rule)
                if code is None:
                    raise ValueError(
                        f"{self.location(pointer)}: {cls}'s class rule has no {ANNOTATION!r} annotation"
                    )
                self.used.add(("rule", ancestor, str(index)))
                codes.append(code)
        return codes

    def pattern_code(self, cls: str, slot: Any, pointer: list[Any]) -> str:
        """The code of a slot's pattern: the slot's annotation, or else that of the type the pattern comes from.

        A slot that writes its own pattern must name its code. A slot whose pattern is its type's may name one too,
        which then wins over the type's: so a map's key slot can say that a bad key is `INVALID_ID`, whatever its type.
        """
        code = _annotation(slot)
        if code is not None:
            self.used.update(self.slot_origins(cls, slot.name))
            return code
        if (
            not (slot.pattern or slot.structured_pattern)
            and slot.range in self.view.all_types()
        ):
            for name in self.view.type_ancestors(slot.range):
                definition = self.view.get_type(name)
                if definition.pattern or definition.structured_pattern:
                    code = _annotation(definition)
                    if code is None:
                        raise ValueError(
                            f"{self.location(pointer)}: the type {name} has no {ANNOTATION!r} annotation for its pattern"
                        )
                    self.used.add(("type", name))
                    return code
        raise ValueError(
            f"{self.location(pointer)}: {cls}.{slot.name} has no {ANNOTATION!r} annotation for its pattern"
        )

    def slot_origins(self, cls: str, name: str) -> set[tuple[str, ...]]:
        """Where the slot `name` of `cls` is written with a `rule` annotation: an attribute, a slot_usage, a slot."""
        found = set()
        for ancestor in self.view.class_ancestors(cls):
            definition = self.view.get_class(ancestor)
            for kind, slots in (
                ("attribute", definition.attributes),
                ("slot_usage", definition.slot_usage),
            ):
                if name in (slots or {}) and _annotation(slots[name]) is not None:
                    found.add((kind, ancestor, name))
        top = self.view.all_slots(attributes=False).get(name)
        if top is not None and _annotation(top) is not None:
            found.add(("slot", name))
        return found


def _rule_annotations(view: SchemaView) -> set[tuple[str, ...]]:
    """Every element of `view` written with a `rule` annotation, keyed as the walk keys the ones it takes a code from."""
    found: set[tuple[str, ...]] = set()

    def note(key: tuple[str, ...], element: Any) -> None:
        if _annotation(element) is not None:
            found.add(key)

    note(("schema", view.schema.name), view.schema)
    for name, definition in view.all_types().items():
        note(("type", name), definition)
    for name, definition in view.all_slots(attributes=False).items():
        note(("slot", name), definition)
    for name, definition in view.all_enums().items():
        note(("enum", name), definition)
        for value, permissible in (definition.permissible_values or {}).items():
            note(("permissible_value", name, value), permissible)
    for name, definition in view.all_classes().items():
        note(("class", name), definition)
        for kind, slots in (
            ("attribute", definition.attributes),
            ("slot_usage", definition.slot_usage),
        ):
            for slot_name, slot in (slots or {}).items():
                note((kind, name, slot_name), slot)
        for kind, expressions in (
            ("rule", definition.rules),
            ("exactly_one_of", definition.exactly_one_of),
            ("any_of", definition.any_of),
            ("all_of", definition.all_of),
            ("none_of", definition.none_of),
        ):
            for index, expression in enumerate(expressions or []):
                note((kind, name, str(index)), expression)
    return found


def _describe(key: tuple[str, ...]) -> str:
    """A LinkML element, from its key, for an error message."""
    kind, *parts = key
    if kind in ("attribute", "slot_usage"):
        return f"{parts[0]}.{parts[1]}" + (
            " (slot_usage)" if kind == "slot_usage" else ""
        )
    if kind == "permissible_value":
        return f"the value {parts[1]} of {parts[0]}"
    if len(parts) == 2:
        return f"{kind} {int(parts[1]) + 1} of {parts[0]}"
    return f"the {kind} {parts[0]}"


def _tree_root(view: SchemaView) -> str:
    (root,) = [name for name, cls in view.all_classes().items() if cls.tree_root]
    return root


def build_error_map(schema: dict, schema_view: SchemaView) -> dict[str, str]:
    """For the generated JSON Schema `schema` of the LinkML schema `schema_view`: absolute keyword location → code.

    It holds every keyword of `schema` that can report an error, and raises `ValueError` for any it can't give a code.
    """
    return dict(sorted(_walk(schema, schema_view).codes.items()))


def _walk(schema: dict, schema_view: SchemaView) -> _ErrorMap:
    """The walk of `schema`: its codes, and the LinkML elements whose `rule` annotation gave one."""
    walk = _ErrorMap(schema, schema_view)
    walk.klass(schema, [], _tree_root(schema_view))
    for name, definition in schema.get("$defs", {}).items():
        element = name.removesuffix(ENTRY_SUFFIX)
        if element in schema_view.all_classes():
            walk.klass(definition, ["$defs", name], element)
        elif element in schema_view.all_enums():
            walk.enum(definition, ["$defs", name])
        else:
            raise ValueError(
                f"{walk.location(['$defs', name])}: neither a class nor an enum of {schema_view.schema.name}"
            )
    return walk


# --- rules.json ---


def build_catalogue(
    markdown: str, schemas: list[tuple[dict, SchemaView]]
) -> dict[str, Any]:
    """`rules.json` without its `$comment`: the rules of `markdown`'s §9, and the error map of each `(schema, view)`.

    Every code in the error map is a schema-layer code of §9, and every `rule` annotation in the views gives a code
    to some keyword of the schemas: one that gives none (on a class, say) is an error.
    """
    rules = extract_rules(markdown)
    schema_codes = {rule["code"] for rule in rules if rule["layer"] == "schema"}
    errors: dict[str, str] = {}
    annotated: set[tuple[str, ...]] = set()
    used: set[tuple[str, ...]] = set()
    for schema, view in schemas:
        walk = _walk(schema, view)
        for location, code in walk.codes.items():
            if code not in schema_codes:
                raise ValueError(f"{location}: {code} is not a schema-layer code of §9")
            if location in errors:
                raise ValueError(f"{location}: in two schemas")
            errors[location] = code
        annotated |= _rule_annotations(view)
        used |= walk.used
    if annotated - used:
        raise ValueError(
            f"no keyword of the JSON Schemas takes its code from the {ANNOTATION!r} annotation of "
            + ", ".join(_describe(key) for key in sorted(annotated - used))
        )
    return {"rules": rules, "errors": dict(sorted(errors.items()))}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Write rules.json, from the specification and the schema, to stdout."
    )
    parser.add_argument(
        "specification",
        type=Path,
        help="the specification (Markdown), whose §9 is the catalogue",
    )
    parser.add_argument(
        "sources",
        type=Path,
        nargs="+",
        metavar="SCHEMA_YAML",
        help="the LinkML schemas, versioned",
    )
    parser.add_argument(
        "--schemas",
        type=Path,
        nargs="+",
        required=True,
        metavar="JSON",
        help="the generated JSON Schemas, each paired with the LinkML schema its title names",
    )
    args = parser.parse_args(argv)
    views = {}
    for source in args.sources:
        view = SchemaView(str(source))
        views[view.schema.name] = view
    versions = {view.schema.version for view in views.values()}
    if len(versions) != 1:
        raise SystemExit(
            f"the LinkML schemas have different versions: {sorted(map(str, versions))}"
        )
    schemas = []
    for path in args.schemas:
        schema = json.loads(path.read_text(encoding="utf-8"))
        if schema.get("title") not in views:
            raise SystemExit(
                f"{path}: its title, {schema.get('title')!r}, names none of the LinkML schemas"
            )
        schemas.append((schema, views[schema["title"]]))
    catalogue = build_catalogue(args.specification.read_text(encoding="utf-8"), schemas)
    (version,) = versions
    catalogue["$comment"] = f"ASTRA rule catalogue, schema version {version}"
    text = json.dumps(catalogue, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    sys.stdout.buffer.write(text.encode("utf-8"))


if __name__ == "__main__":
    main()
