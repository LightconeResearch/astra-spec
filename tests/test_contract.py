"""The shape of the generated contract, so that a LinkML upgrade or a schema edit can't quietly loosen it.

Design §3 and §9, D3 and D12; the patterns, Rulings R5 and R7.
"""

import functools
import json
import re
from collections.abc import Iterator
from typing import Any

import pytest
from jsonschema import Draft201909Validator
from jsonschema_specifications import REGISTRY

from .conftest import GENERATED, REPO_ROOT, load_yaml

SOURCES = REPO_ROOT / "src" / "astra" / "schema"

ROOTS = {
    "analysis.schema.json": "Analysis",
    "provenance.schema.json": "ProvenanceRecord",
    "provenance.open.schema.json": "ProvenanceRecord",
}
"""Each generated JSON Schema, with the class it is rooted at."""

CLOSED = ["analysis.schema.json", "provenance.schema.json"]

NAMESPACE = "https://w3id.org/astra/"
"""Where every artefact is published, under its own file name (design §3)."""

ANNOTATIONS = {"description", "title"}
"""Keywords that annotate a subschema without constraining it."""

ENTRY_SUFFIX = "__identifier_optional"
"""The suffix of the `$defs` entry LinkML makes for a class written as a map entry, its key left out."""

ONE_CLASS = re.compile(r"\[\^?(?:\\.|[^\\\]])+\]", re.DOTALL)
"""A pattern that is a single bracketed character class, such as `[^\\x00-\\x20\\x7f]`."""

DIALECT_ESCAPES = set("dDwWsSbBAZz")
"""Escapes that Python's `re` and ECMA-262 define differently, or that only one of them has."""

STANDARD_KEYWORDS = {
    keyword
    for vocabulary in ("core", "applicator", "validation", "meta-data")
    for keyword in REGISTRY.contents(
        f"https://json-schema.org/draft/2019-09/meta/{vocabulary}"
    )["properties"]
}
"""The keywords of JSON Schema 2019-09's core, applicator, validation and meta-data vocabularies."""

DEF_PREFIX = "#/$defs/"


def load(name: str) -> dict[str, Any]:
    """The committed generated JSON Schema `name`."""
    return json.loads((GENERATED / name).read_text(encoding="utf-8"))


def nodes(node: Any, pointer: str = "") -> Iterator[tuple[str, dict]]:
    """Every object in the parsed JSON `node`, with its JSON Pointer, depth first."""
    if isinstance(node, dict):
        yield pointer, node
        children = node.items()
    elif isinstance(node, list):
        children = enumerate(node)
    else:
        return
    for key, child in children:
        yield from nodes(
            child, f"{pointer}/{str(key).replace('~', '~0').replace('/', '~1')}"
        )


def is_map(subschema: dict) -> bool:
    """Whether `subschema` checks its entries with an `additionalProperties` schema, as a map does."""
    return isinstance(subschema.get("additionalProperties"), dict)


def key_pattern(subschema: dict) -> Any:
    """The `pattern` that `subschema`'s `propertyNames` gives its keys, or None."""
    names = subschema.get("propertyNames")
    return names.get("pattern") if isinstance(names, dict) else None


def maps(schema: dict) -> list[tuple[str, dict]]:
    """Every map anywhere in `schema`, with its JSON Pointer."""
    return [(pointer, node) for pointer, node in nodes(schema) if is_map(node)]


def fields(schema: dict) -> Iterator[tuple[str, str, dict]]:
    """`(owner, field, subschema)` for each property of the root (owner `(root)`) and of each `$defs` entry."""
    yield from (
        ("(root)", field, sub) for field, sub in schema.get("properties", {}).items()
    )
    for owner, definition in schema["$defs"].items():
        yield from (
            (owner, field, sub)
            for field, sub in definition.get("properties", {}).items()
        )


@functools.cache
def source_classes() -> dict[str, dict]:
    """Every class of the LinkML sources, by name, as written (each class declares its own slots)."""
    classes = {}
    for module in ("types", "analysis", "insight", "provenance"):
        classes.update(load_yaml(SOURCES / f"{module}.yaml").get("classes") or {})
    return classes


def source_slots(class_name: str) -> dict[str, dict]:
    """The slots of the class `class_name` in the LinkML sources, by name."""
    return {
        name: slot or {}
        for name, slot in (source_classes()[class_name].get("attributes") or {}).items()
    }


def source_maps() -> set[tuple[str, str]]:
    """`(class, slot)` for each map the sources declare: `multivalued` and `inlined`, not `inlined_as_list`."""
    return {
        (class_name, name)
        for class_name in source_classes()
        for name, slot in source_slots(class_name).items()
        if slot.get("multivalued")
        and slot.get("inlined")
        and not slot.get("inlined_as_list")
    }


def references(node: Any) -> set[str]:
    """The name of every `$defs` entry that a `$ref` anywhere in `node` points to."""
    return {
        child["$ref"].removeprefix(DEF_PREFIX)
        for _, child in nodes(node)
        if isinstance(child.get("$ref"), str) and child["$ref"].startswith(DEF_PREFIX)
    }


def reachable(schema: dict) -> set[str]:
    """The `$defs` entries that a `$ref` reaches from the root, directly or through other entries."""
    found: set[str] = set()
    todo = references({key: value for key, value in schema.items() if key != "$defs"})
    while todo:
        name = todo.pop()
        found.add(name)
        todo |= references(schema["$defs"][name]) - found
    return found


def item_type(items: dict, defs: dict) -> Any:
    """The JSON type of a list's items, through their `$ref` if they have one."""
    if "$ref" in items:
        items = defs[items["$ref"].removeprefix(DEF_PREFIX)]
    return items.get("type")


def accepts_null(subschema: dict, defs: dict) -> bool:
    """Whether a value that `subschema` checks may be `null`, its references resolved in `defs`."""
    return Draft201909Validator({**subschema, "$defs": defs}).is_valid(None)


def pattern_problems(pattern: str) -> list[str]:
    """What in `pattern` Python's `re` and ECMA-262 could read differently; empty if nothing."""
    problems = []
    if pattern.startswith("^"):
        if not pattern.endswith((r"$(?!\n)", r"$(?!\n))$")):
            problems.append(r"anchored, but doesn't end in $(?!\n)")
    elif not ONE_CLASS.fullmatch(pattern):
        problems.append("unanchored, but not a single bracketed class")
    in_class = False
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "\\":
            if pattern[i + 1 : i + 2] in DIALECT_ESCAPES:
                problems.append(pattern[i : i + 2])
            i += 2
            continue
        if in_class:
            in_class = char != "]"
        elif char == "[":
            in_class = True
        elif char == ".":
            problems.append("unescaped . outside a class")
        elif pattern.startswith(("(?<", "(?P"), i):
            problems.append(pattern[i : i + 3])
        i += 1
    return problems


@pytest.mark.parametrize("name", ROOTS)
def test_every_map_constrains_its_keys(name):
    assert [
        pointer
        for pointer, node in maps(load(name))
        if not isinstance(key_pattern(node), str)
    ] == []


@pytest.mark.parametrize("name", ROOTS)
def test_every_source_map_is_a_map(name):
    """A map exactly where the sources declare one, so no map can slip past the map tests unseen."""
    schema = load(name)
    declared = source_maps()
    found = {(owner, field) for owner, field, sub in fields(schema) if is_map(sub)}
    expected = {
        (owner, field)
        for owner, field, _ in fields(schema)
        if (
            ROOTS[name] if owner == "(root)" else owner.removesuffix(ENTRY_SUFFIX),
            field,
        )
        in declared
    }
    assert found == expected


@pytest.mark.parametrize("name", ROOTS)
def test_every_map_entry_has_one_form(name):
    schema = load(name)
    defs = schema["$defs"]
    wrong = []
    for pointer, node in maps(schema):
        entry = {
            k: v
            for k, v in node["additionalProperties"].items()
            if k not in ANNOTATIONS
        }
        if entry.keys() == {"$ref"}:
            # The object form: the entry's class without its key, so the id is written once, as the map key.
            target = entry["$ref"].removeprefix("#/$defs/")
            if not entry["$ref"].startswith("#/$defs/") or target not in defs:
                wrong.append(pointer)
                continue
            (key,) = [
                n
                for n, slot in source_slots(target.removesuffix(ENTRY_SUFFIX)).items()
                if slot.get("key")
            ]
            if key in defs[target].get("properties", {}) or key in defs[target].get(
                "required", []
            ):
                wrong.append(pointer)
        elif entry.keys() != {"type", "pattern"} or entry["type"] != "string":
            # Otherwise only the compact form: the value of the class's one slot besides its key.
            wrong.append(pointer)
    assert wrong == []


@pytest.mark.parametrize("name", ROOTS)
def test_no_field_accepts_null(name):
    schema = load(name)
    nullable = [
        pointer
        for pointer, node in nodes(schema)
        if node.get("type") == "null"
        or (isinstance(node.get("type"), list) and "null" in node["type"])
    ]
    assert nullable == []
    # And by behaviour, which a field with no type at all (`{}`) would also fail.
    values = [
        (f"{pointer}/*", node["additionalProperties"]) for pointer, node in maps(schema)
    ]
    for owner, field, sub in fields(schema):
        values.append((f"{owner}.{field}", sub))
        if isinstance(sub.get("items"), dict):
            values.append((f"{owner}.{field}[]", sub["items"]))
    assert [where for where, sub in values if accepts_null(sub, schema["$defs"])] == []


@pytest.mark.parametrize("name", CLOSED)
def test_closed_schemas_are_closed(name):
    schema = load(name)
    open_ = [
        owner
        for owner, definition in {"(root)": schema, **schema["$defs"]}.items()
        if "properties" in definition
        and definition.get("additionalProperties") is not False
    ]
    assert open_ == []


@pytest.mark.parametrize("name", ROOTS)
def test_every_pattern_means_the_same_in_python_and_ecma_262(name):
    patterns = set()
    for _, node in nodes(load(name)):
        if isinstance(node.get("pattern"), str):
            patterns.add(node["pattern"])
        if isinstance(node.get("patternProperties"), dict):
            patterns.update(node["patternProperties"])
    assert patterns
    problems = {pattern: pattern_problems(pattern) for pattern in sorted(patterns)}
    assert {pattern: found for pattern, found in problems.items() if found} == {}


def test_each_schema_is_identified_by_its_own_file_uri():
    """Each JSON Schema's `$id` is its published URI, so the closed and open record schemas are distinct."""
    assert {name: load(name).get("$id") for name in ROOTS} == {
        name: NAMESPACE + name for name in ROOTS
    }


@pytest.mark.parametrize("name", ROOTS)
def test_top_level_holds_only_standard_keywords(name):
    """No LinkML keyword at the top level, so strict validators (Ajv) compile the contract; the version is a comment."""
    schema = load(name)
    assert sorted(set(schema) - STANDARD_KEYWORDS) == []
    assert re.fullmatch(
        r".* version [0-9]+\.[0-9]+\.[0-9]+", schema.get("$comment", "")
    )


@pytest.mark.parametrize("name", ROOTS)
def test_every_def_is_reachable_from_the_root(name):
    schema = load(name)
    assert sorted(set(schema["$defs"]) - reachable(schema)) == []


@pytest.mark.parametrize("name", ROOTS)
def test_lists_of_strings_hold_no_entry_twice(name):
    """`uniqueItems` on every list of scalars, and on no list of objects (`DUPLICATE_ENTRY`)."""
    schema = load(name)
    lists = [
        (pointer, node)
        for pointer, node in nodes(schema)
        if node.get("type") == "array"
    ]
    assert lists
    found = {pointer: node.get("uniqueItems") is True for pointer, node in lists}
    expected = {
        pointer: item_type(node["items"], schema["$defs"]) != "object"
        for pointer, node in lists
    }
    assert found == expected
