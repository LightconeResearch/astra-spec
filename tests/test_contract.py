"""The shape of the generated contract, so that a LinkML upgrade or a schema edit can't quietly loosen it.

Design §3 and §9, D3 and D12; the patterns, Rulings R5 and R7.
"""

import copy
import functools
import json
import re
from collections.abc import Iterator
from typing import Any

import pytest
from jsonschema import Draft201909Validator
from jsonschema_generator import generate
from jsonschema_specifications import REGISTRY
from referencing import Registry
from referencing.jsonschema import DRAFT201909

from .conftest import (
    DATA,
    GENERATED,
    REPO_ROOT,
    ecma_262,
    load_fixture,
    load_yaml,
    rules_catalogue,
)
from .test_types import HARNESS

SOURCES = REPO_ROOT / "src" / "astra" / "schema"

ROOTS = {
    "analysis.schema.json": "Analysis",
    "provenance.schema.json": "ProvenanceRecord",
    "provenance.open.schema.json": "ProvenanceRecord",
}
"""Each generated JSON Schema, with the class it is rooted at."""

CLOSED = ["analysis.schema.json", "provenance.schema.json"]

NAMESPACE = "https://w3id.org/astra/"
"""Where every artefact is published, under the series of its version and its own file name (design §3)."""

VERSION = r"[0-9]+\.[0-9]+\.[0-9]+(?:(?:a|b|rc)[0-9]+)?|dev"
"""A version a generated file is stamped with: a release `X.Y.Z`, a pre-release (`0.1.0rc1`), or `dev`."""

STAMP = re.compile(rf".* version ({VERSION})")
"""A `$comment` stamped with a version, which it ends with."""

MINIMAL = {
    "Analysis": DATA / "valid" / "Analysis-001-minimal.yaml",
    "ProvenanceRecord": DATA / "valid" / "ProvenanceRecord-003-minimal.json",
}
"""A minimal valid document of each root."""

ANNOTATIONS = {"description", "title"}
"""Keywords that annotate a subschema without constraining it."""

ENTRY_SUFFIX = "__identifier_optional"
"""The suffix of the `$defs` entry LinkML makes for a class written as a map entry, its key left out."""

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


TYPED = {
    ("Analysis", "spec_version"): "spec_version",
    ("Output", "inputs"): "reference",
    ("Output", "decisions"): "address",
    ("Output", "when"): "condition",
    ("Decision", "when"): "condition",
    ("Option", "insights"): "id",
    ("Option", "requires"): "option_reference",
    ("Option", "incompatible_with"): "option_reference",
    ("Universe", "derived_from"): "id",
    ("Universe", "analysis"): "address",
    ("Universe", "universe"): "id",
    ("DecisionSelection", "option"): "id",
    ("AnalysisDeclaration", "commit"): "commit_id",
    ("Evidence", "artifact"): "reference",
    ("FragmentSelector", "conforms_to"): "iri",
    ("ProvenanceRecord", "spec_version"): "spec_version",
    ("ProvenanceRecord", "address"): "reference",
    ("ProvenanceRecord", "content_hash"): "content_hash",
    ("Generation", "commit"): "commit_id",
    ("Generation", "started"): "timestamp",
    ("Generation", "finished"): "timestamp",
    ("RecordedInput", "entry"): "reference",
    ("RecordedInput", "content_hash"): "content_hash",
    ("Environment", "iri"): "iri",
}
"""The named type of each slot that takes one, a map's key aside (spec §4, Named types), written by hand."""

KEY_TYPES = {("Universe", "decisions"): "address"}
"""The type of the keys of each map not keyed by an `id`: `Universe.decisions`, keyed by a decision's address."""


@functools.cache
def named_types() -> dict[str, dict]:
    """The named types of `types.yaml`, by name, as written."""
    return load_yaml(SOURCES / "types.yaml")["types"]


@functools.cache
def type_patterns() -> dict[str, str]:
    """The pattern of each named type, as the generator writes it on a field of that type (the types harness)."""
    return {
        name: sub["pattern"] for name, sub in generate(HARNESS)["properties"].items()
    }


def located_fields(name: str) -> Iterator[tuple[tuple[str, str], str, dict]]:
    """`((class, slot), pointer, subschema)` for each property of the root and of each `$defs` entry of the generated
    schema `name`."""
    schema = load(name)
    for owner, field, sub in fields(schema):
        if owner == "(root)":
            yield (ROOTS[name], field), f"/properties/{field}", sub
        else:
            pointer = f"/$defs/{owner}/properties/{field}"
            yield (owner.removesuffix(ENTRY_SUFFIX), field), pointer, sub


def typed_values(name: str) -> dict[tuple[str, str], tuple[str, dict]]:
    """For each `(class, slot)` of the generated schema `name`, the pointer and subschema of its value: of each item of
    a list, and for a map in the compact form, of the one slot of the entry's class besides its key."""
    values = {}
    for (class_name, field), pointer, sub in located_fields(name):
        if is_map(sub):
            if "$ref" not in sub["additionalProperties"]:
                entry = source_slots(class_name)[field]["range"]
                (slot,) = [
                    n for n, s in source_slots(entry).items() if not s.get("key")
                ]
                values[(entry, slot)] = (
                    pointer + "/additionalProperties",
                    sub["additionalProperties"],
                )
        elif sub.get("type") == "array":
            values[(class_name, field)] = (pointer + "/items", sub["items"])
        else:
            values[(class_name, field)] = (pointer, sub)
    return values


def test_typed_slots_are_those_of_the_sources():
    """`TYPED` lists exactly the slots whose range is a named type, keys aside, each with that type."""
    assert {
        (class_name, name): slot["range"]
        for class_name in source_classes()
        for name, slot in source_slots(class_name).items()
        if slot.get("range") in named_types() and not slot.get("key")
    } == TYPED


def test_every_typed_slot_is_in_the_contract():
    """Each slot of `TYPED` has a value in some generated schema, so that the next test checks it."""
    found = set().union(*(typed_values(name) for name in ROOTS))
    assert sorted(set(TYPED) - found) == []


@pytest.mark.parametrize("name", ROOTS)
def test_every_typed_slot_takes_its_types_pattern_and_code(name):
    """A slot of a named type checks its values with exactly the type's pattern, whose errors take the type's code:
    no pattern or `rule` of its own (spec §4)."""
    prefix = load(name)["$id"] + "#"
    error_map = rules_catalogue()["errors"]
    values = typed_values(name)
    found = {
        slot: (
            values[slot][1].get("pattern"),
            error_map.get(prefix + values[slot][0] + "/pattern"),
        )
        for slot in TYPED
        if slot in values
    }
    expected = {
        slot: (
            type_patterns()[TYPED[slot]],
            named_types()[TYPED[slot]]["annotations"]["rule"],
        )
        for slot in found
    }
    assert found
    assert found == expected


@pytest.mark.parametrize("name", ROOTS)
def test_every_map_key_takes_its_types_pattern_and_is_an_id(name):
    """Every map's keys take `id`'s pattern, but those of `Universe.decisions`, which take `address`'s, and nothing
    else, since a key is a string (spec §3); a bad key is `INVALID_ID` whatever its type (spec §4, §9)."""
    schema = load(name)
    prefix = schema["$id"] + "#"
    error_map = rules_catalogue()["errors"]
    keys = {
        pointer: (slot, sub)
        for slot, pointer, sub in located_fields(name)
        if is_map(sub)
    }
    assert sorted(pointer for pointer, _ in maps(schema)) == sorted(keys)
    found = {
        pointer: (
            sub["propertyNames"],
            {
                error_map.get(prefix + pointer + "/propertyNames" + keyword)
                for keyword in ("", "/pattern")
            },
        )
        for pointer, (_, sub) in keys.items()
    }
    expected = {
        pointer: (
            {"pattern": type_patterns()[KEY_TYPES.get(slot, "id")]},
            {"INVALID_ID"},
        )
        for pointer, (slot, _) in keys.items()
    }
    assert found == expected


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
def test_the_harness_reads_every_pattern_as_ecma_262(name):
    """Each pattern of the contract keeps to what `ecma_262` reads as ECMA-262 does, so the tests give a validator's
    verdicts."""
    patterns = {
        node["pattern"]
        for _, node in nodes(load(name))
        if isinstance(node.get("pattern"), str)
    }
    assert patterns
    for pattern in patterns:
        ecma_262(pattern)


@pytest.mark.parametrize(
    ("pattern", "value", "matches"),
    [
        # ECMA-262's `$` matches only at the end of the value; Python's also before a final newline.
        (r"^a$", "a", True),
        (r"^a$", "a\n", False),
        (r"^(?:a|b$)c?$", "b\n", False),
        (r"^[^/]", "\n", True),
        (r"^a(?!$)", "a\n", True),
        (r"^[$]$", "$", True),
        (r"^\$$", "$", True),
    ],
)
def test_the_harness_matches_as_ecma_262_does(pattern, value, matches):
    assert bool(ecma_262(pattern).search(value)) is matches


@pytest.mark.parametrize(
    "pattern",
    [
        r"^a.b$",
        r"^\d$",
        r"^[\s]$",
        r"^a\b",
        r"^a\Z",
        r"^(?<=a)b",
        r"^(?P<a>b)$",
        r"[]a]",
        r"[^]a]",
    ],
)
def test_the_harness_refuses_what_ecma_262_reads_otherwise(pattern):
    with pytest.raises(ValueError, match="ECMA-262 and Python's re read otherwise"):
        ecma_262(pattern)


def series(version: str) -> str:
    """The series of a stamped `version` (spec §10): `X.Y` for a release `X.Y.Z`, otherwise the whole version."""
    release = re.fullmatch(r"([0-9]+\.[0-9]+)\.[0-9]+", version)
    return release[1] if release else version


def test_each_schema_is_identified_by_its_own_file_uri():
    """Each JSON Schema's `$id` is its published URI: the namespace, the series of the version in its `$comment`, `/`
    and its file name. So the closed and open record schemas are distinct, and so are two minor versions."""
    ids, expected = {}, {}
    for name in ROOTS:
        schema = load(name)
        stamp = STAMP.fullmatch(schema.get("$comment", ""))
        assert stamp, f"{name}: no version in its $comment"
        ids[name] = schema.get("$id")
        expected[name] = NAMESPACE + series(stamp[1]) + "/" + name
    assert ids == expected


@pytest.mark.parametrize("name", ROOTS)
def test_top_level_holds_only_standard_keywords(name):
    """No LinkML keyword at the top level, so strict validators (Ajv) compile the contract; the version is a comment,
    which ends in a release `X.Y.Z`, a pre-release or `dev`."""
    schema = load(name)
    assert sorted(set(schema) - STANDARD_KEYWORDS) == []
    assert STAMP.fullmatch(schema.get("$comment", ""))


@pytest.mark.parametrize("name", ROOTS)
def test_two_minor_versions_are_held_side_by_side(name):
    """Copies of a schema stamped `0.1` and `0.2` go into one `referencing` registry, and each URI resolves to its own
    copy: the `0.2` copy requires one more field, and only a `$ref` to it reports that field missing (spec §10)."""
    schema = load(name)
    copies = {}
    for minor, extra in (("0.1", []), ("0.2", ["added_in_0_2"])):
        stamped = copy.deepcopy(schema)
        stamped["$id"] = f"{NAMESPACE}{minor}/{name}"
        stamped["$comment"] = re.sub(
            f"(?:{VERSION})$", f"{minor}.0", schema["$comment"]
        )
        stamped["required"] = [*schema.get("required", []), *extra]
        copies[minor] = stamped
    registry = Registry().with_resources(
        (stamped["$id"], DRAFT201909.create_resource(stamped))
        for stamped in copies.values()
    )
    assert {minor: registry.contents(c["$id"]) for minor, c in copies.items()} == copies
    document = load_fixture(MINIMAL[ROOTS[name]])
    messages = {
        minor: [
            error.message
            for error in Draft201909Validator(
                {"$ref": stamped["$id"]}, registry=registry
            ).iter_errors(document)
        ]
        for minor, stamped in copies.items()
    }
    assert messages == {"0.1": [], "0.2": ["'added_in_0_2' is a required property"]}


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


def test_no_list_of_strings_in_an_analysis_is_empty():
    """`minItems: 1` on every list of scalars of `astra.yaml` (`EMPTY_COLLECTION`): a field with nothing to list is
    left out (spec §4)."""
    schema = load("analysis.schema.json")
    minimum = {
        pointer: node.get("minItems")
        for pointer, node in nodes(schema)
        if node.get("type") == "array"
        and item_type(node["items"], schema["$defs"]) != "object"
    }
    assert minimum
    assert minimum == dict.fromkeys(minimum, 1)


CHECK_KEYWORDS = {"oneOf", "anyOf", "not", "if", "then", "else"}
"""Keywords that would hold a class-level check outside the `allOf` that guards each one."""


def fields_read(node: Any) -> set[str]:
    """The fields of the object that a check's subschema `node` reads: those it names in `properties` or `required`."""
    if not isinstance(node, dict):
        return set()
    found = set(node.get("properties", {})) | set(node.get("required", []))
    for keyword in ("not", "if", "then", "else"):
        found |= fields_read(node.get(keyword))
    for keyword in ("oneOf", "anyOf", "allOf"):
        for sub in node.get(keyword, []):
            found |= fields_read(sub)
    return found


@pytest.mark.parametrize("name", ROOTS)
def test_every_class_check_is_guarded_by_the_types_it_reads(name):
    """Each class-level check is an `allOf` member whose `if` requires an object and the type of each field it reads.

    So a value of the wrong type is reported by its `type` alone, and no check adds a second code for it (F079, F119).
    """
    schema = load(name)
    classes = {"(root)": schema, **schema["$defs"]}
    unguarded = [
        f"{owner}/{keyword}"
        for owner, definition in classes.items()
        for keyword in CHECK_KEYWORDS & definition.keys()
    ]
    assert unguarded == []
    wrong = []
    for owner, definition in classes.items():
        for index, member in enumerate(definition.get("allOf", [])):
            guard = member.get("if", {})
            expected = {
                field: {"type": definition["properties"][field]["type"]}
                for field in fields_read(member)
            }
            typed = {
                field: {"type": sub.get("type")}
                for field, sub in guard.get("properties", {}).items()
            }
            if (
                set(member) != {"if", "then"}
                or guard.get("type") != "object"
                or typed != expected
            ):
                wrong.append(f"{owner}/allOf/{index}")
    assert wrong == []


@pytest.mark.parametrize("name", ROOTS)
def test_each_required_has_its_fields_beside_it(name):
    """Every `required` names only fields in a `properties` beside it, as Ajv's `strictRequired` (`strict: true`) wants."""
    assert [
        pointer
        for pointer, node in nodes(load(name))
        if set(node.get("required", [])) - set(node.get("properties", {}))
    ] == []
