"""The fixture harness: YAML 1.2 and strict JSON loading, the generated validators, `rules.json` and the fixture headers
(design §9)."""

import functools
import json
import math
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft201909Validator, ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.composer import Composer, ComposerError
from ruamel.yaml.constructor import ConstructorError, DuplicateKeyError, SafeConstructor
from ruamel.yaml.error import YAMLError
from ruamel.yaml.events import AliasEvent
from ruamel.yaml.nodes import MappingNode, ScalarNode, SequenceNode
from ruamel.yaml.reader import Reader
from ruamel.yaml.resolver import VersionedResolver
from ruamel.yaml.scanner import Scanner, ScannerError
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


_TAG = "tag:yaml.org,2002:"

_CORE_SCALARS = {
    "null": re.compile(r"null|Null|NULL|~|"),
    "bool": re.compile(r"true|True|TRUE|false|False|FALSE"),
    "int": re.compile(r"[-+]?[0-9]+|0o[0-7]+|0x[0-9a-fA-F]+"),
    "float": re.compile(
        r"[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?|[-+]?\.(inf|Inf|INF)|\.(nan|NaN|NAN)"
    ),
}
"""The YAML 1.2 core schema's plain scalars other than strings (YAML 1.2.2 §10.3.2), in resolution order."""


_BREAKS = "\r\n\x85\u2028\u2029"
"""The characters ruamel.yaml's scanner reads as line breaks."""

_BEFORE_A_COMMENT = ("", " ", "\t", "\ufeff", *_BREAKS)
"""What a comment may follow: the start of the stream (`""`), white space, a byte order mark or a line break."""


class _CoreSchemaReader(Reader):
    """ruamel.yaml's reader, which also keeps the last character it read, for the scanner to look one back."""

    last = ""
    """The last character read, or `""` at the start of the stream."""

    def forward(self, length: int = 1) -> None:
        super().forward(length)
        if length:
            self.last = self.buffer[self.pointer - 1]


class _CoreSchemaScanner(Scanner):
    """ruamel.yaml's scanner, refusing a `%YAML` directive for any version but 1.2, and the text YAML 1.2.2 makes
    ill-formed that ruamel.yaml would read.

    The directive is ASTRA's rule, not YAML's (spec §3): YAML 1.2.2 §6.8.1 has a 1.2 processor accept `%YAML 1.1`,
    and process a later 1.x with a warning.

    That text is: a comment with no white space before it (YAML 1.2.2 §6.6); a line of a flow collection or of a
    quoted scalar, its closing bracket or quote included, with no more indentation in spaces than the block
    collection it is in (§6.3, §8.2.3: under a block collection indented `n` spaces, a flow node is at `n+1`); `-`,
    `?` or `:` starting a plain scalar in a flow collection with a flow indicator after it (§7.3.3, as in `[-]`);
    and the verbatim tag `!<!>` (§6.9.1).
    """

    _quoted = False
    """True while a quoted scalar is scanned."""

    def scan_to_next_token(self) -> Any:
        if self.reader.peek() == "#" and self.reader.last not in _BEFORE_A_COMMENT:
            raise ScannerError(
                None,
                None,
                "found '#' right after a token: a comment needs white space before it",
                self.reader.get_mark(),
            )
        return super().scan_to_next_token()

    def scan_line_break(self) -> Any:
        line_break = super().scan_line_break()
        if line_break and (self.flow_level or self._quoted):
            self._check_continuation()
        return line_break

    def _check_continuation(self) -> None:
        """Refuse the line just begun, in a flow collection or a quoted scalar, if it isn't indented past the block.

        A line of white space only, and in a flow collection a comment line, may have any indentation.
        """
        peek = self.reader.peek
        spaces = 0
        while peek(spaces) == " ":
            spaces += 1
        end = spaces
        while peek(end) in " \t":
            end += 1
        if peek(end) in ("\0", *_BREAKS) or (peek(end) == "#" and not self._quoted):
            return
        if spaces <= self.indent:
            raise ScannerError(
                "while scanning a quoted scalar"
                if self._quoted
                else "while scanning a flow collection",
                None,
                f"found a line indented {spaces} spaces: it must be indented more than the block it is in "
                f"({self.indent} spaces)",
                self.reader.get_mark(),
            )

    def scan_flow_scalar(self, style: Any) -> Any:
        self._quoted = True
        try:
            return super().scan_flow_scalar(style)
        finally:
            self._quoted = False

    def check_plain(self) -> Any:
        peek = self.reader.peek
        if self.flow_level and peek() in "-?:" and peek(1) in ",[]{}":
            return False
        return super().check_plain()

    def scan_tag(self) -> Any:
        verbatim = self.reader.prefix(2) == "!<"
        token = super().scan_tag()
        if verbatim and token.value == (None, "!"):
            raise ScannerError(
                "while scanning a tag",
                token.start_mark,
                "found the verbatim tag !<!>, which YAML doesn't allow",
                token.end_mark,
            )
        return token

    def scan_directive(self) -> Any:
        token = super().scan_directive()
        if token.name == "YAML" and token.value != (1, 2):
            major, minor = token.value
            raise ScannerError(
                None,
                None,
                f"found %YAML {major}.{minor}: only 1.2 is read",
                token.start_mark,
            )
        return token


_CORE_RESOLVERS: dict[Any, list] = {}
"""The core schema's resolvers, by the first character of the scalar (`""` for the empty one), as ruamel.yaml looks them up."""
for _name, _pattern in _CORE_SCALARS.items():
    _anchored = re.compile(rf"(?:{_pattern.pattern})\Z")
    for _first in ["", *"~nNtTfF-+0123456789."]:
        _CORE_RESOLVERS.setdefault(_first, []).append((_TAG + _name, _anchored))


class _CoreSchemaResolver(VersionedResolver):
    """Resolves a plain scalar by the core schema only: no timestamps, no merge key, no `_` in numbers."""

    @property
    def versioned_resolver(self) -> Any:
        return _CORE_RESOLVERS


class _CoreSchemaComposer(Composer):
    """ruamel.yaml's composer, refusing every anchor and alias (spec §3), and giving a scalar tagged `!` the tag
    `!!str`, as YAML 1.2.2 does (§6.9.1).

    An anchor or an alias raises `ComposerError`: a file uses neither, so an entry is written out in full. ruamel.yaml
    resolves a scalar tagged `!` as if it were plain, so that `! 12` would be 12.
    """

    def compose_node(self, parent: Any, index: Any) -> Any:
        event = self.parser.peek_event()
        if isinstance(event, AliasEvent):
            raise ComposerError(
                None,
                None,
                f"found the alias *{event.anchor}: a file uses no alias",
                event.start_mark,
            )
        if event.anchor is not None:
            raise ComposerError(
                None,
                None,
                f"found the anchor &{event.anchor}: a file uses no anchor",
                event.start_mark,
            )
        return super().compose_node(parent, index)

    def compose_scalar_node(self, anchor: Any) -> Any:
        event = self.parser.peek_event()
        if event.tag == "!":
            event.tag = _TAG + "str"
        return super().compose_scalar_node(anchor)


def _joined(value: str, mark: Any) -> str:
    """The string `value`, with each surrogate pair joined into the one character it encodes, as JSON joins `\\uD83D\\uDE00`
    into U+1F600; any other surrogate (U+D800-U+DFFF) raises `ConstructorError`, since a string holding one has no JSON
    form (spec §3).

    A surrogate can come only from an escape: YAML text can't hold one as a character.
    """
    try:
        return value.encode("utf-16-le", "surrogatepass").decode("utf-16-le")
    except UnicodeDecodeError as error:
        unit = int.from_bytes(error.object[error.start : error.start + 2], "little")
        raise ConstructorError(
            None,
            None,
            f"found the lone surrogate U+{unit:04X}: a string holding one has no JSON form",
            mark,
        ) from None


def _written(node: Any) -> str:
    """`node` as written in the text it was read from: from its first character (its tag's, if it has one) to its last."""
    start, end = node.start_mark, node.end_mark
    return start.buffer[start.pointer : start.pointer + end.index - start.index]


class _CoreSchemaConstructor(SafeConstructor):
    """Constructs the core schema's types only, each from its core form; any other tag is an error, and so is a value
    with no JSON form (spec §3): a float that isn't finite, an integer beyond a double's range, a string holding a lone
    surrogate.

    A map entry whose key isn't a string has no JSON form either, and is left out of its map. If the map is one of
    `map_pointers`, the maps of the document's JSON form, the key is recorded in `left_out`.
    """

    yaml_constructors: dict[Any, Any] = {}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.map_pointers: dict[MappingNode, str] = {}
        """The JSON Pointer of each map node of the document's JSON form, by node (`_map_pointers`)."""
        self.left_out: list[tuple[int, str, str]] = []
        """`(index, pointer of the map, key as written)` for each key left out of a map of `map_pointers`, `index`
        being where the key starts in the text (maps are constructed out of document order)."""

    def construct_mapping(self, node: Any, deep: bool = False) -> Any:
        """The map of `node`, whose keys must be distinct YAML nodes (YAML 1.2.2 §3.2.1.3); `<<` is an ordinary key.

        Two keys with the same tag and canonical form raise `DuplicateKeyError`, whatever their spelling and type: `a`
        and `"\\x61"`, `0x1f` and `31`, `true` and `True`. Keys of two tags are distinct, so `1`, `1.0`, `true` and
        `"1"` are four keys. An entry whose key isn't tagged `!!str` (a bool, a number, a null, a list or a map) isn't
        added: its key and value are still constructed, so that an error in them is raised, but it has no JSON form.
        If `node` is one of `map_pointers`, the key is recorded in `left_out`. A map inside a left-out entry isn't one
        of them, so a key left out of it is dropped with the entry.
        """
        if not isinstance(node, MappingNode):
            raise ConstructorError(
                None,
                None,
                f"expected a mapping node, but found {node.id}",
                node.start_mark,
            )
        canonical_keys = set()
        mapping: dict[str, Any] = {}
        for key_node, value_node in node.value:
            canonical = self._canonical(key_node)
            if canonical in canonical_keys:
                raise DuplicateKeyError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found a key equal to an earlier one: the same tag and canonical form",
                    key_node.start_mark,
                )
            canonical_keys.add(canonical)
            key = self.construct_object(key_node, deep=True)
            value = self.construct_object(value_node, deep=deep)
            if key_node.tag == _TAG + "str":
                mapping[key] = value
            elif node in self.map_pointers:
                self.left_out.append(
                    (
                        key_node.start_mark.index,
                        self.map_pointers[node],
                        _written(key_node),
                    )
                )
        return mapping

    def _canonical(self, node: Any) -> Any:
        """`node` as YAML compares nodes: its tag, and its canonical form (a scalar's value, a collection's nodes).

        With no alias, a node holds no node twice, so the recursion ends.
        """
        if isinstance(node, ScalarNode):
            return node.tag, self.construct_object(node, deep=True)
        if isinstance(node, SequenceNode):
            return node.tag, tuple(self._canonical(item) for item in node.value)
        return node.tag, frozenset(
            (self._canonical(key), self._canonical(value)) for key, value in node.value
        )

    def _core_scalar(self, node: Any, name: str) -> str:
        value = self.construct_scalar(node)
        if not _CORE_SCALARS[name].fullmatch(value):
            raise ConstructorError(
                None, None, f"{value!r} is not a core-schema {name}", node.start_mark
            )
        return value

    def construct_core_null(self, node: Any) -> None:
        self._core_scalar(node, "null")

    def construct_core_bool(self, node: Any) -> bool:
        return self._core_scalar(node, "bool").lower() == "true"

    def construct_core_int(self, node: Any) -> int:
        """An integer, read exactly; one beyond a double's range, which a double rounds to infinity, has no JSON form."""
        value = self._core_scalar(node, "int")
        if value.startswith(("0o", "0x")):
            number = int(value[2:], 8 if value[1] == "o" else 16)
        else:
            number = int(value)
        try:
            float(number)
        except OverflowError:
            raise ConstructorError(
                None,
                None,
                f"{value!r} is beyond a double's range: it has no JSON form",
                node.start_mark,
            ) from None
        return number

    def construct_core_float(self, node: Any) -> float:
        """A float; `.inf`, `-.inf`, `.nan` and a float beyond a double's range, which rounds to infinity, have no JSON
        form. One too small for a double rounds to 0."""
        value = self._core_scalar(node, "float")
        number = float(value.lower().replace(".inf", "inf").replace(".nan", "nan"))
        if not math.isfinite(number):
            raise ConstructorError(
                None,
                None,
                f"{value!r} isn't a finite number within a double's range: it has no JSON form",
                node.start_mark,
            )
        return number

    def construct_core_str(self, node: Any) -> str:
        """A string, a key's too, with each escaped surrogate pair joined into one character; a lone surrogate raises."""
        return _joined(self.construct_scalar(node), node.start_mark)


for _name in (*_CORE_SCALARS, "str"):
    _CoreSchemaConstructor.add_constructor(
        _TAG + _name, getattr(_CoreSchemaConstructor, f"construct_core_{_name}")
    )
for _name in ("seq", "map"):
    _CoreSchemaConstructor.add_constructor(
        _TAG + _name, getattr(SafeConstructor, f"construct_yaml_{_name}")
    )
_CoreSchemaConstructor.add_constructor(None, SafeConstructor.construct_undefined)


def _core_schema_yaml() -> YAML:
    """ruamel.yaml's pure safe loader, YAML 1.2, restricted to the core schema and held to YAML 1.2.2."""
    yaml = YAML(typ="safe", pure=True)
    yaml.Reader = _CoreSchemaReader
    yaml.Scanner = _CoreSchemaScanner
    yaml.Composer = _CoreSchemaComposer
    yaml.Resolver = _CoreSchemaResolver
    yaml.Constructor = _CoreSchemaConstructor
    return yaml


def _map_pointers(root: Any) -> dict[MappingNode, str]:
    """The JSON Pointer of each map node of the document's JSON form, by node, as `errors` writes it (`(root)` for the
    document): each map reached from `root` through list items and keys tagged `!!str`, and no other."""
    pointers: dict[MappingNode, str] = {}
    todo: list[tuple[Any, list[Any]]] = [(root, [])]
    while todo:
        node, path = todo.pop()
        if isinstance(node, MappingNode):
            pointers[node] = _pointer(path)
            todo.extend(
                (value, [*path, _joined(key.value, key.start_mark)])
                for key, value in node.value
                if key.tag == _TAG + "str" and isinstance(key, ScalarNode)
            )
        elif isinstance(node, SequenceNode):
            todo.extend((item, [*path, i]) for i, item in enumerate(node.value))
    return pointers


def load_document(source: Path | str) -> tuple[Any, list[tuple[str, str]]]:
    """`(document, left_out)`: the JSON form of the document in `source`, a file or a text, read as YAML 1.2.2 under
    the core schema only, and the keys left out of it; raises a `YAMLError` if it isn't such a document.

    A plain scalar is a null, a bool, an int or a float only in its core-schema form, and a string otherwise (so
    timestamps and `1_000` are strings); a scalar tagged `!` is a string; `<<` is an ordinary key; a tag outside the
    core schema (`!!set`, `!!binary`, `!!omap`, `!!timestamp`, a local tag), a core tag on a node of another kind or
    a scalar of another form (`!!seq x`, `!!bool yes`) and a `%YAML` directive other than 1.2 are errors. An anchor,
    an alias and a second document raise `ComposerError`; a file with no document (empty, or only comments) is
    None. Two keys of a map that are equal YAML nodes, with the same tag and canonical form, raise
    `DuplicateKeyError`, whatever their type. Text YAML 1.2.2 makes ill-formed raises a `YAMLError` even where
    ruamel.yaml would read it: a comment glued to a token, an under-indented line of a flow collection or a quoted
    scalar, `[-]`, `!<!>`, and a `\\U` escape beyond U+10FFFF. A `RecursionError` (a document nested too deep) is
    left as it is.

    A value with no JSON form raises a `ConstructorError` (spec §3): `.inf`, `-.inf`, `.nan`, a number beyond a
    double's range (`1e400`, an integer of 400 digits), and a string holding a surrogate that isn't half of an
    escaped pair (`"\\uD800"`); an escaped pair is one character, so `"\\uD83D\\uDE00"` is U+1F600. A key that
    isn't a string (`true`, `1`, `~`, a list or a map) has no JSON form either, but it is left out rather than
    raised: its entry isn't in the document, and `left_out` holds `(pointer of the map, key as written)` for it, in
    document order, as `errors` writes a pointer, so that the rest of the document can be validated. A key inside a
    left-out entry is left out with it, and not listed. The document is composed first, so that each map's pointer
    is known, then constructed.
    """
    text = source.read_bytes() if isinstance(source, Path) else source
    yaml = _core_schema_yaml()
    try:
        node = yaml.compose(text)
        if node is None:
            return None, []
        constructor = yaml.constructor
        constructor.map_pointers = _map_pointers(node)
        document = constructor.construct_document(node)
        return document, [(at, key) for _, at, key in sorted(constructor.left_out)]
    except (ValueError, OverflowError) as error:
        # ruamel.yaml turns a `\U` escape into a character without checking its range, so an escape beyond
        # U+10FFFF raises `ValueError` or `OverflowError`: it is raised as a `ScannerError`, from the original.
        raise ScannerError(
            None, None, f"found text YAML can't read as a value: {error}"
        ) from error


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
    """The JSON form of the document in `path`, as `load_document` reads it; raises a `YAMLError` if it isn't one, and
    a `ValueError` naming each key that isn't a string, if it has any.

    So a document that must be valid (a valid fixture, an example, a block of the specification) fails on such a key.
    """
    return _without_left_out_keys(load_document(path))


def load_yaml_text(text: str) -> Any:
    """The document `text`, read as `load_yaml` reads a file."""
    return _without_left_out_keys(load_document(text))


_DOUBLE_DIGITS = 309
"""The most digits an integer within a double's range can have: the greatest double is about 1.8 × 10^308."""


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
    keys its error map. `jsonschema`'s `absolute_schema_path` runs through `$ref`s without naming them (and leaves out
    an `if` before its `then`), so it isn't that place. But `error.schema` is the subschema that holds the failing
    keyword, and `error.validator` the keyword: the location is that subschema's JSON Pointer, found in the schema by
    identity, then the keyword. It is an error if the subschema isn't in the schema or doesn't hold the keyword.
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
    """
    header = header_file(path)
    if not header.is_file():
        raise ValueError(f"{path.name}: its header file {header.name} is missing")
    lines = header.read_text(encoding="utf-8").splitlines()[:3]
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
