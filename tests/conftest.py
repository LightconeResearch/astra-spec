"""The fixture harness: YAML 1.2 loading, the generated validators, `rules.json` and the fixture headers (design §9)."""

import functools
import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft201909Validator, ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.constructor import ConstructorError, DuplicateKeyError, SafeConstructor
from ruamel.yaml.error import YAMLError
from ruamel.yaml.resolver import VersionedResolver
from ruamel.yaml.scanner import Scanner, ScannerError
from rules import json_pointer

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATED = REPO_ROOT / "src" / "astra" / "schema" / "generated"
DATA = REPO_ROOT / "tests" / "data"

_SCHEMA_NAMES = {"Analysis": "analysis", "ProvenanceRecord": "provenance"}
"""Each fixture root, with the name of its generated schema."""

_RULE_LINE = re.compile(r"# rule: ([A-Z][A-Z_]*)")
_FAILS_AT_LINE = re.compile(r"# fails at: (\(root\)|parse|(/[^/]*)+)")

PARSE_ERRORS: dict[str, type[Exception]] = {
    "INVALID_SYNTAX": YAMLError,
    "DUPLICATE_KEY": DuplicateKeyError,
}
"""Each parse-layer code, with the loader error a fixture breaking it raises (any loader error, for `INVALID_SYNTAX`)."""

COMBINATORS = {"oneOf", "anyOf"}
"""Keywords whose error at an ancestor of the place a fixture fails at is allowed: they report what fails inside them."""


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


class _CoreSchemaScanner(Scanner):
    """ruamel.yaml's scanner, refusing a `%YAML` directive for any version but 1.2."""

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


class _CoreSchemaConstructor(SafeConstructor):
    """Constructs the core schema's types only, each from its core form; any other tag is an error."""

    yaml_constructors: dict[Any, Any] = {}

    def flatten_mapping(self, node: Any) -> None:
        """No merge keys: `<<` is an ordinary key."""

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
    """ruamel.yaml's pure safe loader, YAML 1.2, restricted to the core schema."""
    yaml = YAML(typ="safe", pure=True)
    yaml.Scanner = _CoreSchemaScanner
    yaml.Resolver = _CoreSchemaResolver
    yaml.Constructor = _CoreSchemaConstructor
    return yaml


def load_yaml(path: Path) -> Any:
    """The document in `path`, read as YAML 1.2 under the core schema only; raises `DuplicateKeyError` on a repeated key.

    A plain scalar is a null, a bool, an int or a float only in its core-schema form, and a string otherwise (so
    timestamps and `1_000` are strings); `<<` is an ordinary key; a tag outside the core schema (`!!set`,
    `!!binary`, `!!omap`, `!!timestamp`, a local tag) and a `%YAML` directive other than 1.2 are errors.
    """
    return _core_schema_yaml().load(path)


def load_yaml_text(text: str) -> Any:
    """The document `text`, read as `load_yaml` reads a file."""
    return _core_schema_yaml().load(text)


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


def is_ancestor(pointer: str, of: str) -> bool:
    """Whether the JSON Pointer `pointer` names a strict ancestor of `of` (`(root)` is everything's)."""
    if pointer == "(root)":
        return of != "(root)"
    return of.startswith(pointer + "/")


def fixture_header(path: Path) -> tuple[str, str]:
    """`(rule, fails_at)` from an invalid fixture's first two lines."""
    lines = path.read_text(encoding="utf-8").splitlines()[:2]
    rule = _RULE_LINE.fullmatch(lines[0]) if lines else None
    fails_at = _FAILS_AT_LINE.fullmatch(lines[1]) if len(lines) > 1 else None
    if rule is None or fails_at is None:
        raise ValueError(
            f"{path.name}: lines 1-2 must be '# rule: <CODE>' and '# fails at: <location>'"
        )
    return rule[1], fails_at[1]


def fixtures(kind: str) -> list[Path]:
    """The fixtures of `kind` (`valid` or `invalid`), sorted."""
    return sorted((DATA / kind).glob("*.yaml"))
