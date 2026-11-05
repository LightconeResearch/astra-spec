"""The fixture harness: YAML 1.2 and strict JSON loading, the generated validators, `rules.json` and the fixture headers
(design §9)."""

import functools
import json
import math
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
    """An `astra.yaml` that breaks a parse rule (spec §3), as `load_document` reads it."""


class DuplicateKeyError(YAMLError):
    """A map of an `astra.yaml` with two equal string keys (spec §3)."""


class JSONError(ValueError):
    """A record's text that breaks a parse rule (spec §3), as `load_json` reads it."""


class DuplicateNameError(JSONError):
    """An object of a record with a name written twice (spec §3)."""


PARSE_ERRORS = (YAMLError, JSONError)
"""What the loaders raise for a file that breaks a parse rule: `load_document` a `YAMLError`, `load_json` a
`JSONError`."""


def parse_code(error: YAMLError | JSONError) -> str:
    """The parse-layer code of a loader error: `DUPLICATE_KEY` for a repeated key or name, `INVALID_SYNTAX` for any
    other."""
    return (
        "DUPLICATE_KEY"
        if isinstance(error, (DuplicateKeyError, DuplicateNameError))
        else "INVALID_SYNTAX"
    )


# --- An astra.yaml: a stock YAML 1.2 parser, with ASTRA's rules checked on the text, the events and the value ---

_FORBIDDEN = re.compile(
    "[\x00-\x09\x0b\x0c\x0e-\x1f\x7f-\x9f\u2028\u2029\ufeff\ufffe\uffff]"
)
"""What a file holds nowhere, quoted or not, once the byte order mark that may start it is dropped: a tab, a C0
control other than LF and CR, DEL, a C1 control (NEL included), LS, PS, U+FEFF, U+FFFE and U+FFFF (spec §3). An escape
in a double-quoted scalar still writes any of them."""

_YAML_1_2 = re.compile(r"%YAML +1\.2( +#.*)? *")
"""The one directive a file may hold: `%YAML 1.2`, with the version written so, and maybe a comment."""

_START = re.compile(r"---( |$)")
"""A line that is a document start marker, `---`, alone or before white space."""

_END = re.compile(r"\.\.\.( |$)")
"""A line that is a document end marker, `...`, alone or before white space."""

_END_LINE = re.compile(r"\.\.\.( +#.*)? *")
"""A document end marker's line with nothing on it but a comment."""

_SURROGATE = re.compile("[\ud800-\udfff]")
"""A surrogate, which a scalar's value holds only from a `\\u` or `\\U` escape: UTF-8 text can't hold one."""

_DOUBLE_DIGITS = 309
"""The most digits an integer within a double's range can have: the greatest double is about 1.8 × 10^308."""


_CORE_TABLE = (
    (re.compile(r"null|Null|NULL|~|"), lambda text: None),
    (re.compile(r"true|True|TRUE"), lambda text: True),
    (re.compile(r"false|False|FALSE"), lambda text: False),
    (re.compile(r"[-+]?[0-9]+"), int),
    (re.compile(r"0o[0-7]+"), lambda text: int(text[2:], 8)),
    (re.compile(r"0x[0-9a-fA-F]+"), lambda text: int(text[2:], 16)),
    (re.compile(r"[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?"), float),
    (re.compile(r"[-+]?(\.inf|\.Inf|\.INF)"), lambda text: math.inf),
    (re.compile(r"\.nan|\.NaN|\.NAN"), lambda text: math.nan),
)
"""YAML 1.2.2 §10.3.2's table: each row's pattern, and how a plain scalar it matches is read, in the table's order."""


def _text(data: bytes) -> str:
    """The text of an `astra.yaml`'s bytes, as the parser is given it, once the rules on the text hold (spec §3); raises
    `YAMLError` if one doesn't.

    The bytes are UTF-8, strictly, and may start with a byte order mark, which is dropped. The text holds none of
    `_FORBIDDEN`. LF, CR LF and a CR on its own each end a line: a lone CR is read as an LF, which changes nothing else,
    since YAML 1.2.2 §5.4 makes every CR a line break, and a missing final line break is read as present. Then
    `_documents` checks the directives and the document markers.
    """
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise YAMLError(
            f"found bytes that aren't UTF-8 at byte {error.start}: an astra.yaml is UTF-8"
        ) from None
    text = text.removeprefix("\ufeff")
    found = _FORBIDDEN.search(text)
    if found is not None:
        raise YAMLError(
            f"found U+{ord(found[0]):04X} at character {found.start()}: a file holds none, quoted or not"
        )
    text = re.sub("\r(?!\n)", "\n", text)
    if text and not text.endswith("\n"):
        text += "\n"
    _documents(text)
    return text


def _documents(text: str) -> None:
    """Raise `YAMLError` unless `text`'s only directive is `%YAML 1.2`, a `---` line comes, if at all, once and before
    the content, and a `...` line comes, if at all, once and after the document, with nothing but comments after it.

    Read line by line, leaving out blank lines and comments: a directive is a line starting with `%` before the
    content. A line scan reads the markers exactly, since YAML 1.2.2 lets no scalar hold a line that starts with `---`
    or `...` followed by white space or the line's end (§9.1.2).
    """
    lines: list[str] = []
    """The lines that are neither blank, a comment nor a directive."""
    for line in re.split("\r?\n", text):
        bare = line.lstrip(" ")
        if bare == "" or bare.startswith("#"):
            continue
        if not lines and line.startswith("%"):
            if _YAML_1_2.fullmatch(line) is None:
                raise YAMLError(
                    f"found the directive {line!r}: the only directive is %YAML 1.2"
                )
            continue
        lines.append(line)
    starts = [i for i, line in enumerate(lines) if _START.match(line)]
    ends = [i for i, line in enumerate(lines) if _END.match(line)]
    if starts not in ([], [0]):
        raise YAMLError(
            "found a `---` after the content: a file holds one document, its `---` first"
        )
    if ends not in ([], [len(lines) - 1]) or ends == [0]:
        raise YAMLError(
            "found a `...` before the end, or with no document before it: a file holds one document, its `...` last"
        )
    if ends and _END_LINE.fullmatch(lines[-1]) is None:
        raise YAMLError("found content after `...` on its line")


class _Node:
    """A node of the document, built from the parser's events: a scalar's value, or a list's items or a map's keys and
    values, alternating, with where it starts and ends in the text."""

    __slots__ = ("start", "end", "value", "children", "is_map")

    def __init__(self, start: int, *, value: Any = None, is_map: bool = False):
        self.start = self.end = start
        self.value = value
        self.children: list[_Node] | None = None
        self.is_map = is_map


def _plain(text: str, mark: Any) -> Any:
    """The value of a plain scalar `text`: the type of the row of YAML 1.2.2 §10.3.2's table it matches, or a string if
    it matches none. A number that isn't finite or is beyond a double's range has no JSON form, and raises `YAMLError`.

    A decimal integer's digits are counted first, since Python refuses to convert one of more than 4300 digits.
    """
    for pattern, read in _CORE_TABLE:
        if pattern.fullmatch(text):
            break
    else:
        return text
    if read is int and len(text.lstrip("+-").lstrip("0")) > _DOUBLE_DIGITS:
        value = math.inf
    else:
        value = read(text)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise YAMLError(
                f"found {text[:20]!r}{'…' if len(text) > 20 else ''} {_at(mark)}: a number that isn't finite or is"
                " beyond a double's range has no JSON form"
            )
    return value


def _at(mark: Any) -> str:
    """Where a parser's mark is, in words."""
    return f"at line {mark.line + 1}, column {mark.column + 1}"


def _events(text: str) -> Iterator[Any]:
    """The events of stock ruamel.yaml's parser for `text`; an error it raises, whatever its class, is a `YAMLError`:
    the text isn't YAML 1.2 the parser reads (spec §3). A `RecursionError` (a document nested too deep) is left as it
    is."""
    events = YAML(typ="safe", pure=True).parse(text)
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


def _node(event: Any, events: Iterator[Any]) -> _Node:
    """The node that `event` starts, its children read from `events`; raises `YAMLError` for an alias, a tag, an escape
    of a surrogate, or a number with no JSON form (spec §3). An anchor alone is ignored."""
    if isinstance(event, AliasEvent):
        raise YAMLError(
            f"found the alias *{event.anchor} {_at(event.start_mark)}: a file uses no alias"
        )
    if event.tag is not None:
        raise YAMLError(
            f"found the tag {event.tag} {_at(event.start_mark)}: a file uses no tag"
        )
    if isinstance(event, ScalarEvent):
        found = _SURROGATE.search(event.value)
        if found is not None:
            raise YAMLError(
                f"found an escape of the surrogate U+{ord(found[0]):04X} {_at(event.start_mark)}: a file writes a"
                " character beyond U+FFFF as itself or with \\U"
            )
        node = _Node(
            event.start_mark.index,
            value=event.value if event.style else _plain(event.value, event.start_mark),
        )
        node.end = event.end_mark.index
        return node
    node = _Node(event.start_mark.index, is_map=isinstance(event, MappingStartEvent))
    node.children = []
    for child in events:
        if isinstance(child, CollectionEndEvent):
            node.end = child.end_mark.index
            return node
        node.children.append(_node(child, events))
    raise YAMLError("found the end of the events inside a collection")


def _root(events: Iterator[Any]) -> _Node | None:
    """The node of the one document in `events`, or None if there is none."""
    root = None
    for event in events:
        if isinstance(event, DocumentStartEvent):
            if root is not None:
                raise YAMLError("found a second document: a file holds one")
            root = _node(next(events), events)
    return root


def _json_form(
    node: _Node, path: list[Any], text: str, left_out: list[tuple[str, str]] | None
) -> Any:
    """The JSON form of `node`, at `path` in the document, recording in `left_out` the pointer of its map and the key
    as written for each entry left out since its key isn't a string; raises `DuplicateKeyError` for two equal string
    keys of one map.

    Keys that aren't strings take no part in that. An entry left out is still read, for a duplicate key in its key or
    its value, with `left_out` None: a key in it is left out with it, and not recorded.
    """
    if node.children is None:
        return node.value
    if not node.is_map:
        return [
            _json_form(item, [*path, i], text, left_out)
            for i, item in enumerate(node.children)
        ]
    mapping: dict[str, Any] = {}
    for key, value in zip(node.children[::2], node.children[1::2]):
        if key.children is None and isinstance(key.value, str):
            if key.value in mapping:
                raise DuplicateKeyError(
                    f"found the key {key.value!r} twice in the map at {_pointer(path)}: its string keys are distinct"
                )
            mapping[key.value] = _json_form(value, [*path, key.value], text, left_out)
            continue
        _json_form(key, path, text, None)
        _json_form(value, path, text, None)
        if left_out is not None:
            left_out.append((_pointer(path), text[key.start : key.end].rstrip()))
    return mapping


def load_document(source: Path | str) -> tuple[Any, list[tuple[str, str]]]:
    """`(document, left_out)`: the JSON form of the `astra.yaml` in `source`, a file or a text, and the keys left out of
    it; raises a `YAMLError` if it breaks a parse rule (spec §3).

    The rules are checked on the text, before parsing (`_text`): UTF-8, with one optional leading byte order mark; no
    raw tab, C0 control other than LF and CR, DEL, C1 control, LS, PS, U+FEFF, U+FFFE or U+FFFF; LF, CR LF and a lone
    CR each end a line, and a missing final line break is read as present; no directive but `%YAML 1.2`; at most one
    `---`, before the content, and one `...`, after it. Then on the events of ruamel.yaml's stock parser (`_node`): any
    error the parser raises; no alias, though an anchor alone is allowed; no tag at all; no escape of a surrogate,
    paired or not; each plain scalar typed by YAML 1.2.2 §10.3.2's table, and each number finite and within a double's
    range. Then on the tree, once the whole file has parsed (`_json_form`): no two equal string keys in one map
    (`DuplicateKeyError`), and every key a string. A file with no document (empty, or only comments) is None.

    A key that isn't a string (`true`, `1`, `~`, a list or a map) has no JSON form, but it is left out rather than
    raised: its entry isn't in the document, and `left_out` holds `(pointer of the map, key as written)` for it, in
    document order, as `errors` writes a pointer, so that the rest of the document can be validated. A key inside a
    left-out entry is left out with it, and not listed. A `RecursionError` (a document nested too deep) is left as it
    is.
    """
    data = source.read_bytes() if isinstance(source, Path) else source.encode("utf-8")
    text = _text(data)
    root = _root(_events(text))
    left_out: list[tuple[str, str]] = []
    document = None if root is None else _json_form(root, [], text, left_out)
    return document, left_out


def _without_left_out_keys(loaded: tuple[Any, list[tuple[str, str]]]) -> Any:
    """The document of `load_document`'s result, or a `ValueError` naming the keys left out of it, if any."""
    document, left_out = loaded
    if left_out:
        raise ValueError(
            "keys that aren't strings, left out of the document's JSON form: "
            + ", ".join(f"{key!r} at {pointer}" for pointer, key in left_out)
        )
    return document


def load_yaml(path: Path) -> Any:
    """The JSON form of the document in `path`, read as `load_document` reads it; raises a `YAMLError` if it breaks a
    parse rule, and a `ValueError` naming each key that isn't a string, if it has any.

    So a document that must be valid (a valid fixture, an example, a block of the specification) fails on such a key.
    """
    return _without_left_out_keys(load_document(path))


def load_yaml_text(text: str) -> Any:
    """The document `text`, read as `load_yaml` reads a file."""
    return _without_left_out_keys(load_document(text))


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
    """`NaN`, `Infinity` or `-Infinity`, which `json.loads` reads but RFC 8259 has no form for: always raises."""
    raise JSONError(f"found {text}: RFC 8259 JSON has no such number")


def _json_float(text: str) -> float:
    """A number with a fraction or an exponent; one beyond a double's range, which rounds to infinity, raises."""
    number = float(text)
    if not math.isfinite(number):
        raise JSONError(
            f"{text!r} is beyond a double's range: it has no JSON form a record takes"
        )
    return number


def _json_int(text: str) -> int:
    """An integer, read exactly; one beyond a double's range, which a double rounds to infinity, raises.

    Its digits are counted first, since Python refuses to convert an integer of more than 4300 digits.
    """
    if len(text.lstrip("-")) <= _DOUBLE_DIGITS:
        number = int(text)
        try:
            float(number)
        except OverflowError:
            pass
        else:
            return number
    raise JSONError(
        f"{text[:20]}… is beyond a double's range: it has no JSON form a record takes"
    )


def _refuse_lone_surrogates(value: Any) -> None:
    """Raise `JSONError` if a string of `value`, a name included, holds a surrogate (U+D800-U+DFFF).

    `json.loads` joins an escaped surrogate pair into one character, so any surrogate left is a lone one, which has no
    JSON form (spec §3). Strict UTF-8 can't encode one, so raw text can't hold it: it comes only from an escape.
    """
    todo = [value]
    while todo:
        node = todo.pop()
        if isinstance(node, dict):
            todo.extend(node)
            todo.extend(node.values())
        elif isinstance(node, list):
            todo.extend(node)
        elif isinstance(node, str):
            try:
                node.encode("utf-8")
            except UnicodeEncodeError as error:
                raise JSONError(
                    f"found the lone surrogate U+{ord(node[error.start]):04X}: a string holding one has no JSON form"
                ) from None


def load_json(source: Path | str) -> Any:
    """The record in `source`, a file or a text, read as spec §3 reads a record: RFC 8259 JSON text in UTF-8 with no
    byte order mark, and with distinct names; raises a `JSONError` if it isn't one.

    A file's bytes are decoded as UTF-8, strictly, and a byte order mark at the start is refused, though RFC 8259 §8.1
    lets a parser ignore one. The text is read by `json.loads`, which takes only JSON's forms (no comment, trailing
    comma, single quote or YAML block form), except for what the hooks refuse: `NaN`, `Infinity` and `-Infinity`
    (`parse_constant`); a name written twice in one object, of which `json.loads` keeps the last, raises
    `DuplicateNameError` (`object_pairs_hook`), names being compared once their escapes are read, so `"a"` and
    `"\\u0061"` are one name; and a number beyond a double's range (`1e400`, an integer of 400 digits), which
    `json.loads` reads as an infinity or an exact integer (`parse_float`, `parse_int`). An escaped surrogate pair is
    one character, as `json.loads` reads it, so `"\\uD83D\\uDE00"` is U+1F600; any other surrogate (`"\\uD800"`) is
    refused by a walk over the value read, names included. A `RecursionError` (a record nested too deep) is left as it
    is.
    """
    data = source.read_bytes() if isinstance(source, Path) else source.encode("utf-8")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise JSONError(f"found bytes that aren't UTF-8: {error}") from None
    if text.startswith("\ufeff"):
        raise JSONError("found a byte order mark: a record starts without one")
    try:
        value = json.loads(
            text,
            object_pairs_hook=_json_object,
            parse_constant=_json_constant,
            parse_float=_json_float,
            parse_int=_json_int,
        )
    except json.JSONDecodeError as error:
        raise JSONError(f"found text that isn't RFC 8259 JSON: {error}") from None
    _refuse_lone_surrogates(value)
    return value


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
