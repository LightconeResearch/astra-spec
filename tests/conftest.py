"""The fixture harness: YAML 1.2 loading, the generated validators, `rules.json` and the fixture headers (design §9)."""

import functools
import json
import math
import re
from collections.abc import Hashable
from pathlib import Path
from typing import Any

from jsonschema import Draft201909Validator, ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.composer import Composer
from ruamel.yaml.constructor import ConstructorError, DuplicateKeyError, SafeConstructor
from ruamel.yaml.error import YAMLError
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


def parse_code(error: YAMLError) -> str:
    """The parse-layer code of a loader error: `DUPLICATE_KEY` for a repeated key, `INVALID_SYNTAX` for any other."""
    return "DUPLICATE_KEY" if isinstance(error, DuplicateKeyError) else "INVALID_SYNTAX"


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
    """ruamel.yaml's composer, giving a scalar tagged `!` the tag `!!str`, as YAML 1.2.2 does (§6.9.1).

    ruamel.yaml resolves such a scalar as if it were plain, so that `! 12` would be 12.
    """

    def compose_scalar_node(self, anchor: Any) -> Any:
        event = self.parser.peek_event()
        if event.tag == "!":
            event.tag = _TAG + "str"
        return super().compose_scalar_node(anchor)


class _CoreSchemaConstructor(SafeConstructor):
    """Constructs the core schema's types only, each from its core form; any other tag is an error."""

    yaml_constructors: dict[Any, Any] = {}

    def construct_mapping(self, node: Any, deep: bool = False) -> Any:
        """The map of `node`, whose keys must be distinct YAML nodes (YAML 1.2.2 §3.2.1.3); `<<` is an ordinary key.

        Two keys with the same tag and canonical form raise `DuplicateKeyError`, whatever their spelling: `a` and
        `"\\x61"`, `.nan` and `.nan`. Keys that are distinct nodes but one Python value, such as `1`, `1.0` and `true`,
        raise `ConstructorError`, since a Python dict can't hold them apart.
        """
        if not isinstance(node, MappingNode):
            raise ConstructorError(
                None,
                None,
                f"expected a mapping node, but found {node.id}",
                node.start_mark,
            )
        canonical_keys = set()
        mapping: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            canonical = self._canonical(key_node, ())
            if canonical in canonical_keys:
                raise DuplicateKeyError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found a key equal to an earlier one: the same tag and canonical form",
                    key_node.start_mark,
                )
            canonical_keys.add(canonical)
            key = self.construct_object(key_node, deep=True)
            if isinstance(key, list):
                key = tuple(key)
            if not isinstance(key, Hashable):
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found a key Python can't hash",
                    key_node.start_mark,
                )
            if key in mapping:
                raise ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    "found a key that is a distinct YAML node but equal in Python to an earlier one",
                    key_node.start_mark,
                )
            mapping[key] = self.construct_object(value_node, deep=deep)
        return mapping

    def _canonical(self, node: Any, path: tuple) -> Any:
        """`node` as YAML compares nodes: its tag, and its canonical form (a scalar's value, a collection's nodes)."""
        if any(node is ancestor for ancestor in path):
            raise ConstructorError(
                None, None, "found a key that holds itself", node.start_mark
            )
        if isinstance(node, ScalarNode):
            value = self.construct_object(node, deep=True)
            if isinstance(value, float) and math.isnan(value):
                value = ".nan"
            return node.tag, value
        path = (*path, node)
        if isinstance(node, SequenceNode):
            return node.tag, tuple(self._canonical(item, path) for item in node.value)
        return node.tag, frozenset(
            (self._canonical(key, path), self._canonical(value, path))
            for key, value in node.value
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
        value = self._core_scalar(node, "int")
        if value.startswith(("0o", "0x")):
            return int(value[2:], 8 if value[1] == "o" else 16)
        return int(value)

    def construct_core_float(self, node: Any) -> float:
        value = self._core_scalar(node, "float").lower()
        return float(value.replace(".inf", "inf").replace(".nan", "nan"))


for _name in _CORE_SCALARS:
    _CoreSchemaConstructor.add_constructor(
        _TAG + _name, getattr(_CoreSchemaConstructor, f"construct_core_{_name}")
    )
for _name in ("str", "seq", "map"):
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


def _load(source: Path | str) -> Any:
    """The document in `source`, a file or a text, with an error Python raises for its text raised as a YAML error.

    ruamel.yaml turns a `\\U` escape into a character without checking its range, so an escape beyond U+10FFFF
    raises `ValueError` or `OverflowError`: it is raised as a `ScannerError`, from the original.
    """
    try:
        return _core_schema_yaml().load(source)
    except (ValueError, OverflowError) as error:
        raise ScannerError(
            None, None, f"found text YAML can't read as a value: {error}"
        ) from error


def load_yaml(path: Path) -> Any:
    """The document in `path`, read as YAML 1.2.2 under the core schema only; raises a `YAMLError` if it isn't one.

    A plain scalar is a null, a bool, an int or a float only in its core-schema form, and a string otherwise (so
    timestamps and `1_000` are strings); a scalar tagged `!` is a string; `<<` is an ordinary key; a tag outside the
    core schema (`!!set`, `!!binary`, `!!omap`, `!!timestamp`, a local tag) and a `%YAML` directive other than 1.2
    are errors. Two keys of a map that are equal YAML nodes, with the same tag and canonical form, raise
    `DuplicateKeyError` (keys that are distinct nodes but one Python value, such as `1` and `true`, raise
    `ConstructorError`). Text YAML 1.2.2 makes ill-formed raises a `YAMLError` even where ruamel.yaml would read it:
    a comment glued to a token, an under-indented line of a flow collection or a quoted scalar, `[-]`, `!<!>`, and
    a `\\U` escape beyond U+10FFFF. A `RecursionError` (a document nested too deep) is left as it is.
    """
    return _load(path)


def load_yaml_text(text: str) -> Any:
    """The document `text`, read as `load_yaml` reads a file."""
    return _load(text)


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


def fixture_header(path: Path) -> tuple[str, str, tuple[str, str] | None]:
    """`(rule, fails_at, also)` from an invalid fixture's header.

    The header is two comment lines, `# rule: <CODE>` and `# fails at: <location>`, then optionally a third,
    `# also: <CODE> at <pointer>`: a second error the fixture's one break brings. `also` is that line's
    `(code, pointer)`, or None. A third line that is a comment must be an `# also:` line.
    """
    lines = path.read_text(encoding="utf-8").splitlines()[:3]
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
    """The fixtures of `kind` (`valid` or `invalid`), sorted."""
    return sorted((DATA / kind).glob("*.yaml"))
