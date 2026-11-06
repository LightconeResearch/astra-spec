"""The fixture harness: YAML 1.2 and JSON loading, the generated validators, `rules.json` and the fixture headers
(design §9)."""

import functools
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from jsonschema import Draft201909Validator, ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.events import (
    AliasEvent,
    CollectionEndEvent,
    DocumentStartEvent,
    MappingStartEvent,
    ScalarEvent,
)
from rules import json_pointer

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATED = REPO_ROOT / "src" / "astra" / "schema" / "generated"
DATA = REPO_ROOT / "tests" / "data"

_SCHEMA_NAMES = {"Analysis": "analysis", "ProvenanceRecord": "provenance"}
"""Each fixture root, with the name of its generated schema."""

_RULE_LINE = re.compile(r"# rule: ([A-Z][A-Z0-9_]*)")
_FAILS_AT_LINE = re.compile(r"# fails at: (\(root\)|parse|(/[^/]*)+)")
_ALSO_LINE = re.compile(r"# also: ([A-Z][A-Z0-9_]*) at (\(root\)|(/[^/]*)+)")

PARSE_CODES = {"INVALID_SYNTAX", "DUPLICATE_KEY"}
"""The parse-layer codes `parse_code` gives."""


class YAMLError(ValueError):
    """An `astra.yaml` that breaks a parse rule (spec §3), as `load_yaml` reads it."""


class DuplicateKeyError(YAMLError):
    """A map of an `astra.yaml` with two equal keys (spec §3)."""


class JSONError(ValueError):
    """A record's text that breaks a parse rule (spec §3), as `load_json` reads it."""


class DuplicateNameError(JSONError):
    """An object of a record with a name written twice (spec §3)."""


PARSE_ERRORS = (YAMLError, JSONError)
"""What the loaders raise for a file that breaks a parse rule: `load_yaml` a `YAMLError`, `load_json` a `JSONError`."""


def parse_code(error: YAMLError | JSONError) -> str:
    """The parse-layer code of a loader error: `DUPLICATE_KEY` for a repeated key or name, `INVALID_SYNTAX` for any
    other."""
    return (
        "DUPLICATE_KEY"
        if isinstance(error, (DuplicateKeyError, DuplicateNameError))
        else "INVALID_SYNTAX"
    )


# --- An astra.yaml: a stock YAML 1.2 parser, read under the core schema, whose content is a JSON value ---

_CORE = "tag:yaml.org,2002:"
"""The prefix of the core schema's tags."""

_CORE_TABLE = (
    ("null", re.compile(r"null|Null|NULL|~|"), lambda text: None),
    ("bool", re.compile(r"true|True|TRUE"), lambda text: True),
    ("bool", re.compile(r"false|False|FALSE"), lambda text: False),
    ("int", re.compile(r"[-+]?[0-9]+"), int),
    ("int", re.compile(r"0o[0-7]+"), lambda text: int(text[2:], 8)),
    ("int", re.compile(r"0x[0-9a-fA-F]+"), lambda text: int(text[2:], 16)),
    (
        "float",
        re.compile(r"[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?"),
        float,
    ),
    ("float", re.compile(r"[-+]?(\.inf|\.Inf|\.INF)"), None),
    ("float", re.compile(r"\.nan|\.NaN|\.NAN"), None),
)
"""YAML 1.2.2 §10.3.2's table: each row's type, its pattern, and how a scalar it matches is read, in the table's order.
The rows of `.inf` and `.nan` read nothing, since a number that isn't finite has no JSON form. Numbers are held as
Python holds them, so a float beyond a double's range, such as `1e400`, is read as an infinity."""


def _at(mark: Any) -> str:
    """Where a parser's mark is, in words."""
    return f"at line {mark.line + 1}, column {mark.column + 1}"


def _tag_error(tag: str, mark: Any) -> YAMLError:
    """The error for a tag that isn't one of the core schema's, or isn't one for its node's kind."""
    return YAMLError(
        f"found the tag {tag} {_at(mark)}: a node's tag is one of the core schema's, for its kind"
    )


def _scalar(event: ScalarEvent) -> Any:
    """The value of the scalar `event` under the core schema; raises `YAMLError` for a tag outside it, a scalar its tag
    doesn't read, or a number that isn't finite (spec §3).

    A plain scalar with no tag is typed by the core table: by the first row it matches, or as a string if it matches
    none. Any other scalar with no tag, and one with the non-specific tag `!` or with `!!str`, is a string. `!!null`,
    `!!bool`, `!!int` and `!!float` read it by their own rows of the table.
    """
    tag = event.tag
    if tag is None and not event.style:
        rows = _CORE_TABLE
    elif tag in (None, "!", _CORE + "str"):
        return event.value
    else:
        rows = tuple(row for row in _CORE_TABLE if _CORE + row[0] == tag)
        if not rows:
            raise _tag_error(tag, event.start_mark)
    for _, pattern, read in rows:
        if pattern.fullmatch(event.value):
            if read is None:
                raise YAMLError(
                    f"found {event.value!r} {_at(event.start_mark)}: a number that isn't finite has no JSON form"
                )
            return read(event.value)
    if tag is None:
        return event.value
    raise YAMLError(
        f"found {event.value!r} {_at(event.start_mark)}: the tag {tag} doesn't read it"
    )


class _Node:
    """A node of the document, built from the parser's events: a scalar's value, or a list's items or a map's keys and
    values, alternating, with the mark where it starts. A collection is `open` while its children are read."""

    __slots__ = ("mark", "value", "children", "is_map", "open")

    def __init__(self, mark: Any, *, value: Any = None, is_map: bool = False):
        self.mark = mark
        self.value = value
        self.children: list[_Node] | None = None
        self.is_map = is_map
        self.open = False


def _events(data: bytes | str) -> Iterator[Any]:
    """The events of stock ruamel.yaml's parser for `data`; an error it raises, whatever its class, is a `YAMLError`:
    the file isn't YAML 1.2 the parser reads (spec §3). A `RecursionError` (a document nested too deep) is left as it
    is."""
    events = YAML(typ="safe", pure=True).parse(data)
    while True:
        try:
            event = next(events)
        except StopIteration:
            return
        except RecursionError:
            raise
        except Exception as error:
            raise YAMLError(f"found text YAML doesn't read: {error}") from error
        yield event


def _node(event: Any, events: Iterator[Any], anchors: dict[str, _Node]) -> _Node:
    """The node that `event` starts, its children read from `events`, and an alias read as the node its anchor names
    in `anchors`; raises `YAMLError` for a node with no value under the core schema (`_scalar`), a collection with
    another tag than its kind's, and an alias that names no node before it or one it is inside of, which leaves the
    content no JSON value (spec §3)."""
    if isinstance(event, AliasEvent):
        node = anchors.get(event.anchor)
        if node is None:
            raise YAMLError(
                f"found the alias *{event.anchor} {_at(event.start_mark)}: no node before it has that anchor"
            )
        if node.open:
            raise YAMLError(
                f"found the alias *{event.anchor} {_at(event.start_mark)} inside the node it names: the content"
                " has no JSON value"
            )
        return node
    if isinstance(event, ScalarEvent):
        node = _Node(event.start_mark, value=_scalar(event))
    else:
        is_map = isinstance(event, MappingStartEvent)
        if event.tag not in (None, "!", _CORE + ("map" if is_map else "seq")):
            raise _tag_error(event.tag, event.start_mark)
        node = _Node(event.start_mark, is_map=is_map)
        node.children = []
        node.open = True
    if event.anchor is not None:
        anchors[event.anchor] = node
    if node.children is None:
        return node
    for child in events:
        if isinstance(child, CollectionEndEvent):
            node.open = False
            return node
        node.children.append(_node(child, events, anchors))
    raise YAMLError("found the end of the events inside a collection")


def _root(events: Iterator[Any]) -> _Node | None:
    """The node of the one document in `events`, or None if there is none."""
    root = None
    for event in events:
        if isinstance(event, DocumentStartEvent):
            if root is not None:
                raise YAMLError("found a second document: a file holds at most one")
            root = _node(next(events), events, {})
    return root


def _json_value(node: _Node, path: list[Any]) -> Any:
    """The JSON value of `node`, at `path` in the document; raises `YAMLError` for a key that isn't a string, and
    `DuplicateKeyError` for two equal keys of one map (spec §3)."""
    if node.children is None:
        return node.value
    if not node.is_map:
        return [_json_value(item, [*path, i]) for i, item in enumerate(node.children)]
    mapping: dict[str, Any] = {}
    for key, value in zip(node.children[::2], node.children[1::2]):
        if key.children is not None or not isinstance(key.value, str):
            raise YAMLError(
                f"found a key that isn't a string {_at(key.mark)}: every key of a JSON value is a string"
            )
        if key.value in mapping:
            raise DuplicateKeyError(
                f"found the key {key.value!r} twice in the map at {_pointer(path)}: its keys are distinct"
            )
        mapping[key.value] = _json_value(value, [*path, key.value])
    return mapping


def load_yaml(source: Path | str) -> Any:
    """The JSON value of the `astra.yaml` in `source`, a file or a text, as spec §3 reads it; raises a `YAMLError` if it
    breaks a parse rule.

    The file goes to ruamel.yaml's stock parser as it is, so that the parser reads its encoding. Then, on the parser's
    events (`_node`): any error the parser raises; at most one document; each scalar read under the core schema, a plain
    one by YAML 1.2.2 §10.3.2's table; only the core schema's tags, each on a node of its kind; every number finite;
    and each alias read as the node it names. Then on the tree, once the whole file has parsed (`_json_value`): every
    key a string, and no two equal keys in one map (`DuplicateKeyError`). A file with no document (empty, or only
    comments) is None. A `RecursionError` (a document nested too deep) is left as it is.
    """
    data = source.read_bytes() if isinstance(source, Path) else source
    root = _root(_events(data))
    return None if root is None else _json_value(root, [])


# --- A record: JSON, with distinct names ---


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """An object of a record, from its names and values in order; a name written twice raises `DuplicateNameError`."""
    found: dict[str, Any] = {}
    for name, value in pairs:
        if name in found:
            raise DuplicateNameError(
                f"found the name {name!r} twice in one object: a record's names are distinct"
            )
        found[name] = value
    return found


def _json_constant(text: str) -> Any:
    """`NaN`, `Infinity` or `-Infinity`, which `json.loads` reads but JSON has no form for: always raises."""
    raise JSONError(f"found {text}: JSON has no such number")


def load_json(source: Path | str) -> Any:
    """The record in `source`, a file or a text, as spec §3 reads a record: JSON text (RFC 8259) in UTF-8, with distinct
    names; raises a `JSONError` if it isn't one.

    A file's bytes are decoded as UTF-8, strictly. The text is read by `json.loads`, which takes only JSON's forms but
    for `NaN`, `Infinity` and `-Infinity`, which a hook refuses (`parse_constant`). A name written twice in one object,
    of which `json.loads` keeps the last, raises `DuplicateNameError` (`object_pairs_hook`), names being compared once
    their escapes are read, so `"a"` and `"\\u0061"` are one name. A `RecursionError` (a record nested too deep) is
    left as it is.
    """
    data = source.read_bytes() if isinstance(source, Path) else source.encode("utf-8")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise JSONError(f"found bytes that aren't UTF-8: {error}") from None
    try:
        return json.loads(
            text, object_pairs_hook=_json_object, parse_constant=_json_constant
        )
    except json.JSONDecodeError as error:
        raise JSONError(f"found text that isn't JSON: {error}") from None


def load_fixture(path: Path) -> Any:
    """The document of the fixture at `path`: a record (`.json`) by `load_json`, an `astra.yaml` by `load_yaml`."""
    return load_json(path) if path.suffix == ".json" else load_yaml(path)


@functools.cache
def validator(root: str, *, closed: bool = True) -> Draft201909Validator:
    """A validator for documents rooted at `root`, from the committed schema (its open variant if not `closed`).

    Made once for each schema, so that each schema is read, and indexed for `absolute_keyword_location`, once.
    """
    suffix = ".schema.json" if closed else ".open.schema.json"
    schema = json.loads(
        (GENERATED / f"{_SCHEMA_NAMES[root]}{suffix}").read_text(encoding="utf-8")
    )
    Draft201909Validator.check_schema(schema)
    return Draft201909Validator(schema)


@functools.cache
def rules_catalogue() -> dict[str, Any]:
    """The committed `rules.json`: the rules of the specification's §9, and the error map of the JSON Schemas."""
    return json.loads((GENERATED / "rules.json").read_text(encoding="utf-8"))


def _pointer(path) -> str:
    """The JSON Pointer for a path of keys and indices, or `(root)` for the document."""
    return json_pointer(path) if path else "(root)"


_SUBSCHEMAS: dict[int, tuple[dict, dict[int, str]]] = {}
"""For each schema indexed, by `id`: the schema itself (kept, so that no other object takes its `id`), and the JSON
Pointer of every object in it, by `id`."""


def _subschema_pointers(schema: dict) -> dict[int, str]:
    """The JSON Pointer of every object in `schema`, by identity (`id`), indexed once per schema."""
    if id(schema) not in _SUBSCHEMAS:
        pointers: dict[int, str] = {}
        todo: list[tuple[Any, list[Any]]] = [(schema, [])]
        while todo:
            node, tokens = todo.pop()
            if isinstance(node, dict):
                pointers[id(node)] = json_pointer(tokens)
                todo.extend((child, [*tokens, key]) for key, child in node.items())
            elif isinstance(node, list):
                todo.extend((child, [*tokens, i]) for i, child in enumerate(node))
        _SUBSCHEMAS[id(schema)] = (schema, pointers)
    return _SUBSCHEMAS[id(schema)][1]


def absolute_keyword_location(v: Draft201909Validator, error: ValidationError) -> str:
    """The absolute keyword location of `error`: the URI of the schema resource, `#`, and the JSON Pointer to the keyword.

    That is the keyword's place once every `$ref` is resolved, as JSON Schema 2019-09 defines it and as `rules.json`
    keys its error map. `jsonschema`'s `absolute_schema_path` runs through `$ref`s without naming them, so it isn't
    that place (spec §10). But `error.schema` is the subschema that holds the failing keyword, and `error.validator`
    the keyword: the location is that subschema's JSON Pointer, found in the schema by identity, then the keyword. It
    is an error if the subschema isn't in the schema or doesn't hold the keyword.
    """
    pointer = _subschema_pointers(v.schema).get(id(error.schema))
    if (
        pointer is None
        or error.validator not in error.schema
        or error.absolute_schema_path[-1] != error.validator
    ):
        raise ValueError(
            f"{list(error.absolute_schema_path)}: the subschema that failed isn't found in the schema"
        )
    return v.schema["$id"] + "#" + pointer + json_pointer([error.validator])


def errors(v: Draft201909Validator, doc: Any) -> set[tuple[str, str, bool]]:
    """`(pointer, location, explains)` for every error `v` reports for `doc`, and for every error in each one's context.

    `location` is the error's absolute keyword location. `explains` is true for an error in the context of an error
    at the same pointer: it says why a branch of that combinator failed, rather than failing on its own.
    """
    found = set()
    for error in v.iter_errors(doc):
        outer = _pointer(error.absolute_path)
        found.add((outer, absolute_keyword_location(v, error), False))
        for e in error.context:
            pointer = _pointer(e.absolute_path)
            found.add((pointer, absolute_keyword_location(v, e), pointer == outer))
    return found


def error_pointers(v: Draft201909Validator, doc: Any) -> set[str]:
    """The JSON Pointer of every error `v` reports for `doc`, and of every error in each one's context."""
    return {pointer for pointer, _, _ in errors(v, doc)}


def header_file(path: Path) -> Path:
    """The file holding the header of the fixture at `path`: the fixture itself, or for a record (`.json`), which can't
    hold a comment, its sidecar `<stem>.header`."""
    return path.with_suffix(".header") if path.suffix == ".json" else path


def fixture_header(path: Path) -> tuple[str, str, tuple[str, str] | None]:
    """`(rule, fails_at, also)` from an invalid fixture's header, at the start of `header_file(path)`.

    The header is two comment lines, `# rule: <CODE>` and `# fails at: <location>`, then optionally a third,
    `# also: <CODE> at <pointer>`: a second error the fixture's one break brings. `also` is that line's
    `(code, pointer)`, or None. A third line that is a comment must be an `# also:` line.

    The lines are the first three that end in LF, read from the bytes as ASCII, so that a fixture that isn't UTF-8,
    or holds a CR on its own, has a header (a CR LF's CR is dropped).
    """
    header = header_file(path)
    if not header.is_file():
        raise ValueError(f"{path.name}: its header file {header.name} is missing")
    lines = [
        line.removesuffix(b"\r").decode("ascii", "replace")
        for line in header.read_bytes().split(b"\n")[:3]
    ]
    rule = _RULE_LINE.fullmatch(lines[0]) if lines else None
    fails_at = _FAILS_AT_LINE.fullmatch(lines[1]) if len(lines) > 1 else None
    if rule is None or fails_at is None:
        raise ValueError(
            f"{path.name}: lines 1-2 must be '# rule: <CODE>' and '# fails at: <location>'"
        )
    also = None
    if len(lines) > 2 and lines[2].startswith("#"):
        match = _ALSO_LINE.fullmatch(lines[2])
        if match is None:
            raise ValueError(
                f"{path.name}: a third comment line must be '# also: <CODE> at <pointer>'"
            )
        also = (match[1], match[2])
    return rule[1], fails_at[1], also


def fixtures(kind: str) -> list[Path]:
    """The fixtures of `kind` (`valid` or `invalid`), sorted: each `astra.yaml` (`.yaml`) and record (`.json`)."""
    return sorted([*(DATA / kind).glob("*.yaml"), *(DATA / kind).glob("*.json")])
