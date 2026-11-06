"""The JSON Schema generator extension, on scratch schemas: id-keyed maps, and class-level checks (design §3, D2, D3, D12)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft201909Validator
from linkml.generators.jsonschemagen import JsonSchemaGenerator

from jsonschema_generator import generate, series

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA = REPO_ROOT / "tests" / "generator" / "maps.yaml"
CLI = REPO_ROOT / "tools" / "jsonschema_generator.py"
SCHEMA_ID = "https://example.org/maps.schema.json"
SERIES_ID = "https://example.org/{series}/maps.schema.json"
"""An `$id` with the placeholder for the series of the schema's version."""


@pytest.fixture(scope="module")
def closed():
    return Draft201909Validator(generate(SCHEMA))


@pytest.fixture(scope="module")
def open_():
    return Draft201909Validator(generate(SCHEMA, closed=False))


def document(**fields):
    """A valid document (its one required map has one entry), plus `fields`."""
    return {"required_things": {"r": {}}, **fields}


def failures(validator, instance):
    """The JSON Pointers at which `instance` fails; empty if it is valid."""
    return {
        "".join(
            "/" + str(part).replace("~", "~0").replace("/", "~1")
            for part in error.absolute_path
        )
        for error in validator.iter_errors(instance)
    }


def test_map_keys_follow_the_key_type(closed):
    assert failures(closed, document(things={"Bad-Key": {}})) == {"/things"}
    assert failures(closed, document(things={"ok": {}})) == set()
    assert failures(closed, document(picks={"a.b": "x"})) == set()
    assert failures(closed, document(picks={"A": "x"})) == {"/picks"}


def test_entries_take_only_the_object_form(closed):
    assert failures(closed, document(things={"a": "label"})) == {"/things/a"}
    assert failures(closed, document(things={"a": None})) == {"/things/a"}
    assert failures(closed, document(things={"a": {}})) == set()


def test_the_key_is_not_repeated_in_the_entry(closed):
    assert failures(closed, document(things={"a": {"id": "a"}})) == {"/things/a"}


def test_key_plus_one_slot_is_compact_only(closed):
    assert failures(closed, document(picks={"x.y": "foo"})) == set()
    assert failures(closed, document(picks={"x.y": {"choice": "foo"}})) == {
        "/picks/x.y"
    }
    assert failures(closed, document(picks={"x.y": "Foo"})) == {"/picks/x.y"}


def test_optional_fields_reject_null(closed):
    assert failures(closed, document(note=None)) == {"/note"}


def test_required_maps_keep_one_entry(closed):
    assert failures(closed, {"required_things": {}}) == {"/required_things"}


def test_lists_of_scalars_hold_no_entry_twice(closed):
    assert failures(closed, document(names=["a", "b"])) == set()
    assert failures(closed, document(names=["a", "a"])) == {"/names"}


def test_lists_of_objects_may_repeat_an_item(closed):
    assert failures(closed, document(listed_things=[{"id": "a"}, {"id": "a"}])) == set()


def test_open_variant_allows_unknown_fields(closed, open_):
    assert failures(closed, document(extra=1)) == {""}
    assert failures(open_, document(extra=1)) == set()


def test_schema_id_sets_the_id():
    assert generate(SCHEMA)["$id"] == "https://example.org/maps"
    assert generate(SCHEMA, schema_id=SCHEMA_ID)["$id"] == SCHEMA_ID


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("0.1.3", "0.1"),
        ("0.1.0", "0.1"),
        ("10.20.30", "10.20"),
        ("0.1.0rc1", "0.1.0rc1"),
        ("0.2.0a1", "0.2.0a1"),
        ("1.0.0b2", "1.0.0b2"),
        ("dev", "dev"),
    ],
)
def test_the_series_of_a_version(version, expected):
    """`X.Y` for a release `X.Y.Z` (spec §10), the whole version for a pre-release, and `dev` (CLAUDE.md)."""
    assert series(version) == expected


@pytest.mark.parametrize(
    "version",
    ["0.1", "0.0.0-x", "0.1.0-rc.1", "0.1.0.dev1", "v0.1.0", "0.1.0rc", "Dev", ""],
)
def test_a_version_with_no_series_fails(version):
    with pytest.raises(ValueError, match="has no series"):
        series(version)


def staged(tmp_path: Path, version: str) -> Path:
    """A copy of the scratch schema with `version` in place of its placeholder, as `just gen-schema` stages it."""
    text = SCHEMA.read_text(encoding="utf-8")
    assert "\nversion: 0.0.0\n" in text
    path = tmp_path / f"maps-{version or 'none'}.yaml"
    path.write_text(
        text.replace("\nversion: 0.0.0\n", f"\nversion: {version}\n"), encoding="utf-8"
    )
    return path


@pytest.mark.parametrize(
    ("version", "expected"),
    [("0.1.3", "0.1"), ("0.1.0rc1", "0.1.0rc1"), ("dev", "dev")],
)
def test_the_id_takes_the_series_of_the_schemas_version(tmp_path, version, expected):
    schema = generate(staged(tmp_path, version), schema_id=SERIES_ID)
    assert schema["$id"] == f"https://example.org/{expected}/maps.schema.json"
    assert schema["$comment"] == f"maps schema version {version}"


@pytest.mark.parametrize("version", ["0.1", "0.0.0-x"])
def test_an_id_with_a_series_fails_for_a_version_with_none(tmp_path, version):
    with pytest.raises(ValueError, match="has no series"):
        generate(staged(tmp_path, version), schema_id=SERIES_ID)
    assert generate(staged(tmp_path, version), schema_id=SCHEMA_ID)["$id"] == SCHEMA_ID


def test_cli_writes_the_same_schema():
    cases = [
        ([], {"closed": True}),
        (["--not-closed"], {"closed": False}),
        (["--id", SCHEMA_ID], {"closed": True, "schema_id": SCHEMA_ID}),
        (["--id", SERIES_ID], {"closed": True, "schema_id": SERIES_ID}),
    ]
    for flags, options in cases:
        result = subprocess.run(
            [sys.executable, str(CLI), str(SCHEMA), *flags],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout == json.dumps(generate(SCHEMA, **options), indent=2) + "\n"


# --- Class-level checks (step 5), on a scratch schema with an exactly_one_of and two class rules ---

CHECKS = REPO_ROOT / "tests" / "generator" / "checks.yaml"

SOURCE_FIELDS = {
    "path": ("a", 5),
    "url": ("https://example.org/a", 5),
    "commit": ("c", 5),
    "doi": ("10.1/a", 5),
    "version": (2, "2"),
}
"""Each field of the scratch `Source`, with a value of its type and one of another type."""


@pytest.fixture(scope="module")
def checks_schema():
    return generate(CHECKS)


@pytest.fixture(scope="module")
def checks(checks_schema):
    return Draft201909Validator(checks_schema)


def source_errors(validator, source):
    """`(pointer, keyword)` for every error of the document holding `source`, and every error in each one's context."""
    found = set()
    for error in validator.iter_errors({"sources": [source]}):
        for e in [error, *error.context]:
            pointer = "".join(f"/{part}" for part in e.absolute_path)
            found.add((pointer, e.validator))
    return found


def sources() -> list:
    """Every combination of each `Source` field absent, of its type, of another type or null; and non-objects."""
    combinations = [{}]
    for field, (good, bad) in SOURCE_FIELDS.items():
        combinations = [
            {**combination, field: value}
            for combination in combinations
            for value in (good, bad, None)
        ] + combinations
    return [*combinations, "a", 5, None, ["a"]]


def test_each_check_is_a_guarded_member_of_all_of(checks_schema):
    """No check is left at the class level: the exactly_one_of, then each rule, guarded by the types of what it reads."""
    source = checks_schema["$defs"]["Source"]
    assert not {"oneOf", "if", "then", "else", "anyOf", "not"} & source.keys()
    assert [member["if"] for member in source["allOf"]] == [
        {
            "type": "object",
            "properties": {"path": {"type": "string"}, "url": {"type": "string"}},
        },
        {
            "type": "object",
            "properties": {"commit": {"type": "string"}, "url": {"type": "string"}},
            "required": ["url"],
        },
        {
            "type": "object",
            "properties": {"doi": {"type": "string"}, "version": {"type": "integer"}},
            "not": {"properties": {"doi": {}}, "required": ["doi"]},
        },
    ]
    assert [member["then"] for member in source["allOf"]] == [
        {
            "oneOf": [
                {"properties": {"path": {}}, "required": ["path"]},
                {"properties": {"url": {}}, "required": ["url"]},
            ]
        },
        {"properties": {"commit": {}}, "required": ["commit"]},
        {"not": {"properties": {"version": {}}, "required": ["version"]}},
    ]


@pytest.mark.parametrize(
    ("source", "pointer"),
    [
        ("a", "/sources/0"),
        (None, "/sources/0"),
        (["a"], "/sources/0"),
        ({"path": "a", "url": None}, "/sources/0/url"),
        ({"path": None, "url": "u", "commit": "c"}, "/sources/0/path"),
        ({"url": "u", "commit": 5}, "/sources/0/commit"),
        ({"path": "a", "version": None}, "/sources/0/version"),
        ({"path": "a", "doi": 5, "version": 2}, "/sources/0/doi"),
    ],
)
def test_a_value_of_the_wrong_type_fails_by_its_type_alone(checks, source, pointer):
    assert source_errors(checks, source) == {(pointer, "type")}


@pytest.mark.parametrize(
    ("source", "keywords"),
    [
        ({}, {"oneOf", "required"}),
        ({"path": "a", "url": "u", "commit": "c"}, {"oneOf"}),
        ({"url": "u"}, {"required"}),
        ({"path": "a", "version": 2}, {"not"}),
    ],
)
def test_the_checks_hold_for_values_of_their_type(checks, source, keywords):
    assert source_errors(checks, source) == {
        ("/sources/0", keyword) for keyword in keywords
    }


def test_no_verdict_changes(checks):
    """Stock LinkML's checks and the guarded ones accept and reject the same documents."""
    stock = Draft201909Validator(
        json.loads(JsonSchemaGenerator(str(CHECKS), include_null=False).serialize())
    )
    verdicts = {
        repr(source): checks.is_valid({"sources": [source]}) for source in sources()
    }
    assert set(verdicts.values()) == {True, False}
    differ = [
        source
        for source in sources()
        if stock.is_valid({"sources": [source]}) != verdicts[repr(source)]
    ]
    assert differ == []


def required_without_properties(node, pointer=""):
    """The JSON Pointer of each object in `node` with a field in `required` that isn't in its own `properties`."""
    if isinstance(node, list):
        for index, child in enumerate(node):
            yield from required_without_properties(child, f"{pointer}/{index}")
    elif isinstance(node, dict):
        if set(node.get("required", [])) - set(node.get("properties", {})):
            yield pointer
        for key, child in node.items():
            yield from required_without_properties(child, f"{pointer}/{key}")


def test_each_required_has_its_fields_beside_it(checks_schema):
    """What Ajv's `strictRequired` (on under `strict: true`) checks, inside a `not` too."""
    assert list(required_without_properties(checks_schema)) == []


UNGUARDABLE = {
    "an else": (
        "        postconditions:\n          slot_conditions:\n            commit:\n",
        (
            "        elseconditions:\n          slot_conditions:\n            path:\n"
            "              value_presence: PRESENT\n"
            "        postconditions:\n          slot_conditions:\n            commit:\n"
        ),
        r"Source: a class rule's 'else'",
    ),
    "an any_of": (
        "    exactly_one_of:\n",
        (
            "    any_of:\n      - slot_conditions:\n          doi:\n            required: true\n"
            "    exactly_one_of:\n"
        ),
        r"Source: a class-level 'anyOf'",
    ),
}


@pytest.mark.parametrize("old, new, message", UNGUARDABLE.values(), ids=UNGUARDABLE)
def test_a_check_the_generator_cannot_guard_fails(tmp_path, old, new, message):
    text = CHECKS.read_text(encoding="utf-8")
    assert old in text
    source = tmp_path / "checks.yaml"
    source.write_text(text.replace(old, new, 1), encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        generate(source)
