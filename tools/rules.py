"""The rule catalogue, `rules.json`: derived from the specification and the schema, never written by hand.

`rules.json` holds:

- ``rules``: one entry per rule of the specification, in document order, extracted from its codes table with a Markdown
  parser (markdown-it-py), which reads the specification as CommonMark with GFM tables. The codes table is a format
  this extractor parses, and it is strict:

  - **The table.** The specification has one ``## Rules`` heading, and the codes table is the one table, in the section
    from that heading to the next ``#`` or ``##`` heading, whose header's first cell is ``Code``. No table elsewhere has
    that first cell. Its columns are Code, Level and Rule, in that order. Other tables, such as the recommendations,
    are not read.
  - **Layer rows.** A row whose Code cell is text in strong emphasis (``**parse**``, ``***validator, in each universe
    the driving analysis reaches***``), and whose Level and Rule cells are empty, sets the layer of the rows below it,
    up to the next layer row: its first word, ``parse``, ``schema``, ``validator``, ``check`` or ``runner``. The table
    starts with one.
  - **Rule rows.** Every other row is a case of a rule, with one cell per column (counted on its source line,
    blockquote markers aside) and none empty. Its Code is one code span holding a capital letter, then capitals, digits
    and underscores (``[A-Z][A-Z0-9_]*``), and its Level ``MUST`` or ``SHOULD``. The rows of one code are one rule: they
    are consecutive, under one layer row, with one level, and no other row of the document has their code. The rule's
    statement is their Rule cells, in order, joined with ``; ``.
  - **Status.** A check row's Rule cell has one ``→``, in its text, outside emphasis and links: the text before it is
    the row's part of the statement, and the text after it the status a broken rule gives, the same in each row of the
    rule. No other row's text has a ``→``.
  - **Rule cells.** Each is one sentence: as the cell reads once rendered, outside its code spans, no ``.``, ``?`` or
    ``!`` is followed by white space, even after a closing bracket or quote. It uses no RFC 2119 keyword in capitals of
    another level than its row's, in its text, in a code span, or as the cell reads once rendered (``MU*ST*`` reads as
    ``MUST``).
  - **Cells** are inline Markdown, and the published page shows each cell as the same text. They hold only text, code
    spans, emphasis, links and inline HTML. ``rules.json`` records a statement and a status as Markdown rebuilt from
    what they parse to, with each link reduced to its text, so the rebuilt Markdown must parse the same way: an escape
    whose loss would change the cell, such as ``\\*`` before text that would then become emphasis, is not allowed.

  A specification that breaks any of this is an error, and no ``rules.json`` is made from it.
- ``errors``: for each keyword of the generated JSON Schemas whose error can make the instance fail, its absolute
  keyword location (the schema's ``$id``, ``#``, and the JSON Pointer to the keyword) and the code of the rule it
  enforces. The code comes from the LinkML sources, where each constraint names it in a ``rule`` annotation (on the type
  or slot that defines a pattern, on a class rule, on each branch of an ``exactly_one_of``), or, for the keywords whose
  code never varies, from a default. A map's keys take their key's code for their ``pattern``. A class's checks (its
  exactly-one-of and its class rules) are guarded members of ``allOf``: each member's ``if`` and the keywords of its
  ``then`` take the check's code, and nothing inside an ``if`` or a ``not`` does, since no error there makes the
  instance fail. Every such keyword has exactly one code, every code is a schema-layer rule of the specification, as
  is every default code, and every ``rule`` annotation gives some keyword its code.
"""

import argparse
import dataclasses
import itertools
import json
import sys
import unicodedata
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from linkml_runtime import SchemaView
from markdown_it import MarkdownIt
from markdown_it.rules_block.table import escapedSplit
from markdown_it.token import Token

RULES = "Rules"
"""The `##` heading whose section holds the codes table."""

COLUMNS = ["Code", "Level", "Rule"]
"""The columns of the codes table, in order."""

LAYERS = ["parse", "schema", "validator", "check", "runner"]
"""The layers a layer row of the codes table names, in order."""

STATUS = "→"
"""The mark in a check row's Rule cell between its part of the statement and its status."""

LEVELS = {"MUST", "SHOULD"}
"""The levels a rule can have. A permission (`MAY`) is no rule: the specification states it outside the codes table."""

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

SENTENCE_ENDS = {".", "?", "!"}
"""The marks that end a sentence: a Rule cell has none followed by white space, since a rule is one sentence."""

CLOSERS = {")", "]", '"', "'", "’", "”"}
"""The closing brackets and quotes that may stand between the end of a sentence and the white space after it."""

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

`minProperties` and `minItems` take their default, `EMPTY_COLLECTION` ("at least one entry"), only where it is what they
check, with a value of 1 (see `ONE_ENTRY`): any other minimum has no code, as `maxItems` has none."""

DEFAULT_CODES = {*DEFAULTS.values(), "MISSING_FIELD", "UNKNOWN_FIELD"}
"""Every code a keyword takes by default: each must be a schema-layer code of the specification."""

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


# --- The codes table ---


class _Row:
    """A row of the codes table, for error messages that name it."""

    def __init__(self, line: int, label: str):
        self.line, self.label = line, label

    def error(self, problem: str) -> ValueError:
        return ValueError(f"line {self.line}, row {self.label}: {problem}")


def _markdown() -> MarkdownIt:
    return MarkdownIt("commonmark").enable("table")


def _text(tokens: list[Token]) -> str:
    """The plain text of inline tokens: their text and code spans, without markup, each set apart by a space.

    So a keyword written against a code span or a link (``see`SHOULD` ``, `[the](#a)SHOULD`) is still a word.
    """
    return " ".join(t.content for t in tokens if t.type in ("text", "code_inline"))


def _rendered(tokens: list[Token]) -> str:
    """The text of inline tokens as they render: their text and code spans run together, inline HTML left out.

    So a keyword split by markup (`MU*ST*`, `[MU](#x)ST`, `` `MU`ST ``, `MU<span></span>ST`) is one word, as a reader
    sees it. markdown-it has already decoded entities (`&shy;` is U+00AD), and `_keywords` drops the format
    characters that don't show.
    """
    return "".join(t.content for t in tokens if t.type in ("text", "code_inline"))


def _shape(tokens: list[Token]) -> list[tuple[str, str, str]]:
    """Inline tokens as `(type, content, markup)`, adjacent text merged, for comparing two parses."""
    shape: list[tuple[str, str, str]] = []
    for t in tokens:
        if t.type == "text" and shape and shape[-1][0] == "text":
            shape[-1] = ("text", shape[-1][1] + t.content, "")
        else:
            shape.append((t.type, t.content, t.markup))
    return shape


def _inline_markdown(tokens: list[Token], row: _Row, what: str) -> str:
    """The inline Markdown of `tokens`, with each link reduced to its text; `what` names them in an error."""
    kept = [t for t in tokens if t.type not in ("link_open", "link_close")]
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
            raise row.error(f"its {what} holds a {t.type}, which a rule's cell can't")
    markdown = "".join(parts)
    if _shape(_markdown().parseInline(markdown)[0].children or []) != _shape(kept):
        raise row.error(
            f"its {what} can't be written back as Markdown without its links"
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
    """The RFC 2119 keywords in `text`, as whole words (a word is letters, digits and underscores).

    Format characters (Unicode category Cf, such as U+00AD SOFT HYPHEN and U+200B ZERO WIDTH SPACE) don't show, so
    they are dropped first: `MU`, U+200B, `ST` is `MUST`.
    """
    shown = "".join(c for c in text if unicodedata.category(c) != "Cf")
    words = "".join(c if c.isalnum() or c == "_" else " " for c in shown).split()
    return [word for word in words if word in KEYWORDS]


def _sentence_break(tokens: list[Token]) -> bool:
    """Whether inline tokens hold a sentence break: as they render, outside code spans, a `.`, `?` or `!`, with any
    closing brackets or quotes after it, followed by white space.

    Each code span stands as one letter, so a mark inside one (`` `{inputs.<entry>}` ``), or one written against one
    (``a.`b` ``), is no break. Inline HTML is left out and format characters are dropped, as `_rendered` and
    `_keywords` do.
    """
    text = "".join(
        t.content if t.type == "text" else "x"
        for t in tokens
        if t.type in ("text", "code_inline")
    )
    shown = "".join(c for c in text if unicodedata.category(c) != "Cf")
    for i, c in enumerate(shown):
        if c in SENTENCE_ENDS:
            after = i + 1
            while after < len(shown) and shown[after] in CLOSERS:
                after += 1
            if after < len(shown) and shown[after].isspace():
                return True
    return False


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
    """How many cells the table row at `line` (1-based) writes, split as markdown-it splits it.

    The row is split without its container prefix, as CommonMark reads it: each blockquote marker `>`, with the
    indentation before it and the space after it. The indentation is any run of spaces and tabs, not only up to 3, as
    a list item's content may sit 4 columns in (`1.  `). A row's own text never starts with `>`, which would open a
    blockquote and end the table. The count is made on the source line, not on markdown-it's cells: it pads a short
    row and truncates a long one, so an extra cell would go unseen.
    """
    text = lines[line - 1].lstrip(" \t")
    while text.startswith(">"):
        text = text[1:].lstrip(" \t")
    cells = escapedSplit(text.strip())
    if cells and cells[0] == "":
        cells.pop(0)
    if cells and cells[-1] == "":
        cells.pop()
    return len(cells)


def _line(token: Token) -> int:
    """The line a block token starts on, from 1."""
    return (token.map or [0])[0] + 1


def _codes_table(markdown: str) -> list[Token]:
    """The tokens of `markdown`'s codes table, the table whose header's first cell is `Code`.

    Raises `ValueError`, naming the line, unless there is exactly one `## Rules` heading and exactly one such table,
    in the section from that heading to the next `#` or `##` heading.
    """
    tokens = _markdown().parse(markdown)
    headings = [
        i
        for i, t in enumerate(tokens)
        if t.type == "heading_open"
        and t.tag == "h2"
        and t.level == 0
        and _rendered(tokens[i + 1].children or []) == RULES
    ]
    if not headings:
        raise ValueError(f"the specification must have one '## {RULES}' heading, not 0")
    if len(headings) > 1:
        raise ValueError(
            f"line {_line(tokens[headings[1]])}: a second '## {RULES}' heading, but the specification has one"
        )
    found: list[Token] | None = None
    inside = False
    for i, t in enumerate(tokens):
        if t.type == "heading_open" and t.level == 0 and t.tag in ("h1", "h2"):
            inside = i == headings[0]
        if t.type != "table_open":
            continue
        end = next(j for j in range(i, len(tokens)) if tokens[j].type == "table_close")
        table = tokens[i : end + 1]
        if _rows(table)[0][:1] != ["Code"]:
            continue
        if not inside:
            raise ValueError(
                f"line {_line(t)}: a codes table (a table whose first column is Code) must be in the"
                f" '## {RULES}' section"
            )
        if found is not None:
            raise ValueError(
                f"line {_line(t)}: a second codes table, but the specification has one, at line {_line(found[0])}"
            )
        found = table
    if found is None:
        raise ValueError(f"the '## {RULES}' section has no codes table")
    return found


def _layer_text(inline: Token) -> str | None:
    """The text of a Code cell that is text in strong emphasis, perhaps in emphasis too (`**parse**`); else None."""
    strong, texts = 0, []
    for t in inline.children or []:
        if t.type in ("strong_open", "strong_close"):
            strong += 1 if t.type == "strong_open" else -1
        elif t.type == "text" and strong > 0:
            texts.append(t.content)
        elif t.type == "text" and not t.content:
            continue
        elif t.type not in ("em_open", "em_close"):
            return None
    return "".join(texts) or None


def _split_status(
    tokens: list[Token], row: _Row, check: bool
) -> tuple[list[Token], list[Token]]:
    """A Rule cell's tokens as `(statement, status)`, split at its one `→` if its row is a check row, else `(tokens,
    [])`. The `→` is in a text token, outside emphasis and links, with something on each side."""
    marks = [
        i for i, t in enumerate(tokens) if t.type == "text" and STATUS in t.content
    ]
    if not check:
        if marks:
            raise row.error(
                f"its Rule cell has a {STATUS}, but only a check row gives a status after one"
            )
        return tokens, []
    if len(marks) != 1 or tokens[marks[0]].content.count(STATUS) != 1:
        raise row.error(
            f"its Rule cell must have one {STATUS}, followed by the status a broken check rule gives"
        )
    (i,) = marks
    if sum(t.nesting for t in tokens[:i]):
        raise row.error(f"its {STATUS} is inside emphasis or a link")
    before, _, after = tokens[i].content.partition(STATUS)
    statement = tokens[:i] + (
        [dataclasses.replace(tokens[i], content=before.rstrip())]
        if before.strip()
        else []
    )
    status = (
        [dataclasses.replace(tokens[i], content=after.lstrip())]
        if after.strip()
        else []
    ) + tokens[i + 1 :]
    if not _rendered(statement).strip():
        raise row.error(f"its Rule cell has nothing before its {STATUS}")
    if not _rendered(status).strip():
        raise row.error(f"its Rule cell has no status after its {STATUS}")
    return statement, status


class _Rule:
    """A rule being read: its first row, and each of its rows' part of its statement."""

    def __init__(self, row: _Row, code: str, layer: str, level: str):
        self.row, self.code, self.layer, self.level = row, code, layer, level
        self.parts: list[list[Token]] = []
        """The tokens of each row's part of the statement, in order."""
        self.status: str | None = None
        """The status, for a check rule."""

    def entry(self) -> dict:
        """The rule's entry in `rules.json`: its statement is its rows' parts, joined with `; `."""
        joined: list[Token] = []
        for part in self.parts:
            if joined:
                joined.append(Token("text", "", 0, content="; "))
            joined.extend(part)
        entry = {
            "code": self.code,
            "layer": self.layer,
            "level": self.level,
            "statement": _inline_markdown(
                joined, self.row, "statement, its rows joined"
            ),
        }
        if self.status is not None:
            entry["status"] = self.status
        return entry


def extract_rules(markdown: str) -> list[dict]:
    """The rules of `markdown`'s codes table, in document order.

    The codes table is in the `## Rules` section, with columns Code, Level and Rule. A layer row (`| **parse** | | |`)
    sets the layer of the rows below it, and the rows of one code are one rule. Each entry has the rule's `code`,
    `layer`, `level` and `statement` (its rows' Rule cells, joined with `; `), and, for a check rule, `status` (the text
    after `→` in its Rule cells, which the statement leaves out). The statement and the status are inline Markdown, with
    each link reduced to its text. Raises `ValueError`, naming the line, on anything malformed: the module docstring
    gives the format.
    """
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    table = _codes_table(markdown)
    header, rows = _rows(table)
    if header != COLUMNS:
        raise ValueError(
            f"line {_line(table[0])}: the codes table's columns are {', '.join(COLUMNS[:-1])} and {COLUMNS[-1]},"
            f" not {', '.join(header)}"
        )
    rules: list[_Rule] = []
    seen: dict[str, int] = {}
    layer: str | None = None
    current: _Rule | None = None
    for row_line, cells in rows:
        row = _Row(row_line, cells[0].content or "(no code)")
        written = _source_cell_count(lines, row_line)
        if written != len(header):
            raise row.error(
                f"it has {written} cells, but the table has {len(header)} columns"
            )
        cell = dict(zip(header, cells))
        heading = _layer_text(cell["Code"])
        if heading is not None:
            if cell["Level"].content or cell["Rule"].content:
                raise row.error("a layer row's Level and Rule cells must be empty")
            word = "".join(
                itertools.takewhile(lambda c: c.isalnum() or c == "_", heading)
            )
            if word not in LAYERS:
                raise row.error(
                    f"unknown layer {word!r}: a layer row's first word is {', '.join(LAYERS[:-1])} or {LAYERS[-1]}"
                )
            layer, current = word, None
            continue
        for column, inline in cell.items():
            if not inline.content:
                raise row.error(f"its {column} cell is empty")
        code = _code(cell["Code"], row)
        if layer is None:
            raise row.error("it comes before any layer row, such as | **parse** | | |")
        level = cell["Level"].content
        if level not in LEVELS:
            raise row.error(f"unknown level {level!r}: a level is MUST or SHOULD")
        tokens = cell["Rule"].children or []
        if _sentence_break(tokens):
            raise row.error(
                "its Rule cell has more than one sentence, but a rule is one sentence"
            )
        for keyword in _keywords(_text(tokens)) + _keywords(_rendered(tokens)):
            if KEYWORDS[keyword] != level:
                raise row.error(
                    f"its rule says {keyword}, which contradicts its level, {level}"
                )
        statement, status_tokens = _split_status(tokens, row, layer == "check")
        _inline_markdown(statement, row, "Rule cell")
        status = (
            _inline_markdown(status_tokens, row, "status") if layer == "check" else None
        )
        if current is not None and current.code == code:
            if level != current.level:
                raise row.error(
                    f"its level is {level}, but the row of {code} at line {current.row.line} is {current.level}:"
                    " the rows of a rule share its level"
                )
            if status != current.status:
                raise row.error(
                    f"its status is {status!r}, but the row of {code} at line {current.row.line} gives"
                    f" {current.status!r}: the rows of a check rule give one status"
                )
        else:
            if code in seen:
                raise row.error(
                    f"the code {code} is already the code of the rule at line {seen[code]}: the rows of a rule are"
                    " consecutive, under one layer row"
                )
            seen[code] = row_line
            current = _Rule(row, code, layer, level)
            current.status = status
            rules.append(current)
        current.parts.append(statement)
    return [rule.entry() for rule in rules]


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
        nothing inside it does: it only guards the check, and a tool drops any error inside an `if`, which can't make the
        instance fail. The keywords of its `then` that can fail take the code too.
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
        """A map's keys: their `pattern` takes the key's code."""
        for keyword in node:
            if keyword in METADATA:
                continue
            if keyword != "pattern":
                raise self.unknown(pointer, keyword)
            self.add([*pointer, keyword], code)

    # Inside a class rule or an exactly-one-of branch, every keyword whose error can make the instance fail takes the
    # rule's code.

    def condition(self, node: dict, pointer: list[Any], code: str) -> None:
        for keyword, value in node.items():
            here = [*pointer, keyword]
            if keyword in METADATA:
                continue
            if keyword == "properties":
                for field, sub in value.items():
                    self.condition(sub, [*here, field], code)
            elif keyword == "not":
                # Only the `not` is reported: a tool drops any error inside a `not`, which can't make the instance fail.
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

    It holds every keyword of `schema` whose error can make the instance fail, and raises `ValueError` for
    any it can't give a code.
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
    """`rules.json` without its `$comment`: the rules of `markdown`'s codes table, and the error map of each `(schema,
    view)`.

    Every code in the error map is a schema-layer code of the specification, as is every default code
    (`DEFAULT_CODES`), and every `rule` annotation in the views gives a code to some keyword of the schemas: one that
    gives none (on a class, say) is an error.
    """
    rules = extract_rules(markdown)
    schema_codes = {rule["code"] for rule in rules if rule["layer"] == "schema"}
    if DEFAULT_CODES - schema_codes:
        raise ValueError(
            "the default codes "
            + ", ".join(sorted(DEFAULT_CODES - schema_codes))
            + " are not schema-layer codes of the specification"
        )
    errors: dict[str, str] = {}
    annotated: set[tuple[str, ...]] = set()
    used: set[tuple[str, ...]] = set()
    for schema, view in schemas:
        walk = _walk(schema, view)
        for location, code in walk.codes.items():
            if code not in schema_codes:
                raise ValueError(
                    f"{location}: {code} is not a schema-layer code of the specification"
                )
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
        help="the specification (Markdown), whose codes table is the catalogue",
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
