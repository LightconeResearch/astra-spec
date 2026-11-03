"""The JSON Schema generator extension, on a scratch schema of id-keyed maps (design §3, D2, D3, D12)."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft201909Validator

from jsonschema_generator import generate

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA = REPO_ROOT / "tests" / "generator" / "maps.yaml"
CLI = REPO_ROOT / "tools" / "jsonschema_generator.py"
SCHEMA_ID = "https://example.org/maps.schema.json"


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


def test_cli_writes_the_same_schema():
    cases = [
        ([], {"closed": True}),
        (["--not-closed"], {"closed": False}),
        (["--id", SCHEMA_ID], {"closed": True, "schema_id": SCHEMA_ID}),
    ]
    for flags, options in cases:
        result = subprocess.run(
            [sys.executable, str(CLI), str(SCHEMA), *flags],
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout == json.dumps(generate(SCHEMA, **options), indent=2) + "\n"
