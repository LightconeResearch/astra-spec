"""The provenance record: its open variant, and its mapping onto PROV-O (design §3, §6, D10)."""

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from linkml_runtime import SchemaView

from .conftest import DATA, GENERATED, REPO_ROOT, error_pointers, load_yaml, validator

SCHEMA = REPO_ROOT / "src" / "astra" / "schema" / "provenance.yaml"
PROV = "http://www.w3.org/ns/prov#"


def invalid_fixture(number: str) -> Any:
    """The document of the one invalid fixture `ProvenanceRecord-<number>-….yaml`."""
    (path,) = (DATA / "invalid").glob(f"ProvenanceRecord-{number}-*.yaml")
    return load_yaml(path)


def context(path: Path) -> dict[str, Any]:
    """The `@context` of the JSON-LD context file at `path`."""
    return json.loads(path.read_text(encoding="utf-8"))["@context"]


def test_unknown_field_passes_the_open_variant():
    record = invalid_fixture("215")
    assert error_pointers(validator("ProvenanceRecord"), record) == {"(root)"}
    assert list(validator("ProvenanceRecord", closed=False).iter_errors(record)) == []


@pytest.mark.parametrize(
    "where", [("generated_by",), ("generated_by", "runner")], ids=".".join
)
def test_unknown_nested_field_passes_only_the_open_variant(where):
    record = copy.deepcopy(load_yaml(DATA / "valid" / "ProvenanceRecord-001-full.yaml"))
    target = record
    for field in where:
        target = target[field]
    target["added_by_a_newer_version"] = "x"
    assert error_pointers(validator("ProvenanceRecord"), record) == {
        "/" + "/".join(where)
    }
    assert list(validator("ProvenanceRecord", closed=False).iter_errors(record)) == []


def test_open_variant_still_checks_known_fields():
    open_ = validator("ProvenanceRecord", closed=False)
    assert error_pointers(open_, invalid_fixture("206")) == {"/content_hash"}
    assert error_pointers(open_, invalid_fixture("210")) == {"/generated_by/commit"}


def test_context_maps_the_record_onto_prov():
    terms = context(GENERATED / "provenance.context.jsonld")
    assert terms["prov"] == PROV
    assert terms["schema"] == "http://schema.org/"
    slots = [
        "generated_by",
        "inputs",
        "environment",
        "runner",
        "started",
        "finished",
        "version",
    ]
    assert {slot: terms[slot]["@id"] for slot in slots} == {
        "generated_by": "prov:wasGeneratedBy",
        "inputs": "prov:used",
        "environment": "prov:used",
        "runner": "prov:wasAssociatedWith",
        "started": "prov:startedAtTime",
        "finished": "prov:endedAtTime",
        "version": "schema:softwareVersion",
    }
    times = ["started", "finished"]
    assert {time: terms[time].get("@type") for time in times} == dict.fromkeys(
        times, "xsd:dateTime"
    )
    assert terms["iri"] == "@id"


def test_classes_map_onto_prov():
    sv = SchemaView(str(SCHEMA))
    classes = [
        "ProvenanceRecord",
        "Generation",
        "RecordedInput",
        "Environment",
        "Runner",
    ]
    assert {c: sv.get_uri(c, expand=True) for c in classes} == {
        "ProvenanceRecord": PROV + "Entity",
        "Generation": PROV + "Activity",
        "RecordedInput": PROV + "Entity",
        "Environment": PROV + "Entity",
        "Runner": PROV + "SoftwareAgent",
    }
