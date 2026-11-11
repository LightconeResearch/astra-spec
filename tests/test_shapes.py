"""The shapes tools give each other: the validation report, the resolved analysis, the plan and the check report.

Each has a generated JSON Schema, and an example in `tests/shapes/`: the shape of the specification's worked example,
with `output2` also reading `stage.output3#v1`, so that one output has results in universes of two analyses.
"""

import copy
import json

import pytest
from jsonschema import Draft201909Validator

from .conftest import GENERATED, REPO_ROOT

EXAMPLES = REPO_ROOT / "tests" / "shapes"

SHAPES = {
    "validation-report": "astra-validation-report/1",
    "resolved-analysis": "astra-resolved-analysis/1",
    "plan": "astra-plan/1",
    "check-report": "astra-check-report/1",
}
"""Each shape's file name, with the name and version its documents state."""

SHARED = ("Identity", "Element", "Place", "Read", "Selected")
"""The classes of a planned result, which the resolved analysis, the plan and the check report define alike."""


def schema(name: str) -> dict:
    return json.loads((GENERATED / f"{name}.schema.json").read_text(encoding="utf-8"))


def example(name: str) -> dict:
    return json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))


def errors(name: str, document: dict) -> list[str]:
    return [error.message for error in Draft201909Validator(schema(name)).iter_errors(document)]


@pytest.mark.parametrize("name", SHAPES)
def test_schema_is_a_json_schema_with_its_own_id(name):
    Draft201909Validator.check_schema(schema(name))
    assert schema(name)["$id"].endswith(f"/{name}.schema.json")
    assert schema(name)["properties"]["shape"]["const"] == SHAPES[name]


@pytest.mark.parametrize("name", SHAPES)
def test_example_is_valid(name):
    assert errors(name, example(name)) == []


@pytest.mark.parametrize("name", SHAPES)
def test_unknown_field_is_refused(name):
    document = {**example(name), "extra": 1}
    assert len(errors(name, document)) == 1


@pytest.mark.parametrize("name", SHAPES)
def test_another_shape_is_refused(name):
    document = {**example(name), "shape": "astra-other/1"}
    assert len(errors(name, document)) == 1


@pytest.mark.parametrize("name", ["resolved-analysis", "plan", "check-report"])
def test_absent_value_is_left_out_never_null(name):
    document = copy.deepcopy(example(name))
    document["results"][0]["universe"] = None
    assert len(errors(name, document)) == 1


@pytest.mark.parametrize("name", ["plan", "check-report"])
@pytest.mark.parametrize("shared", SHARED)
def test_planned_result_is_defined_alike(name, shared):
    if (name, shared) == ("check-report", "Place"):  # a checked place is a place with its statuses
        place, checked = schema("resolved-analysis")["$defs"]["Place"], schema(name)["$defs"]["CheckedPlace"]
        assert set(place["required"]) <= set(checked["required"])
        assert place["properties"].items() <= checked["properties"].items()
    else:
        assert schema(name)["$defs"][shared] == schema("resolved-analysis")["$defs"][shared]


@pytest.mark.parametrize("name", ["plan", "check-report"])
def test_planned_result_has_the_resolved_analysis_s_fields(name):
    result = "PlannedResult" if name == "plan" else "CheckedResult"
    head = schema("resolved-analysis")["$defs"]["Result"]
    assert set(head["required"]) <= set(schema(name)["$defs"][result]["required"])
    for field, definition in head["properties"].items():
        if field != "places" or name == "plan":
            assert schema(name)["$defs"][result]["properties"][field] == definition


def test_resolved_analysis_holds_each_analysis_as_its_document():
    resolved, analysis = schema("resolved-analysis"), schema("analysis")
    fields = resolved["$defs"]["Analysis"]
    assert fields["properties"].keys() == analysis["properties"].keys()
    assert fields["required"] == analysis["required"]


def test_examples_agree_on_the_planned_results():
    head = ("names", "owner", "output", "universe", "inputs", "decisions")
    keep = ("name", "address", "record", "bytes")
    results = {}
    for name in ("resolved-analysis", "plan", "check-report"):
        results[name] = [
            {
                **{field: result[field] for field in head if field in result},
                "places": [{field: place[field] for field in keep} for place in result["places"]],
            }
            for result in example(name)["results"]
        ]
    assert results["resolved-analysis"] == results["plan"] == results["check-report"]
    assert len({result["output"]["id"] for result in results["resolved-analysis"]}) < len(results["resolved-analysis"])
