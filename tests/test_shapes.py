"""The shapes tools give each other: the validation report, the resolved analysis, the plan and the check report.

Each has a generated JSON Schema and Pydantic model, and an example in `tests/shapes/`: the shape of an analysis like
the specification's worked example, in which one output has results in universes of two analyses, and an output reads
a switch that takes a case in one universe only.
"""

import copy
import json
import warnings

import pytest
from jsonschema import Draft201909Validator

from astra.schema.generated import check, plan, resolved, validation

from .conftest import GENERATED, REPO_ROOT

EXAMPLES = REPO_ROOT / "tests" / "shapes"

SHAPES = {
    "validation-report": "astra-validation-report/1",
    "resolved-analysis": "astra-resolved-analysis/1",
    "plan": "astra-plan/1",
    "check-report": "astra-check-report/1",
}
"""Each shape's file name, with the name and version its documents state."""

MODELS = {
    "validation-report": validation.ValidationReport,
    "resolved-analysis": resolved.ResolvedAnalysis,
    "plan": plan.Plan,
    "check-report": check.CheckReport,
}
"""Each shape's Pydantic model, in the module generated from its LinkML module."""

SHARED = ("Identity", "Element", "Place", "Read", "Selected")
"""The classes of a planned result, which the resolved analysis, the plan and the check report define alike."""


def schema(name: str) -> dict:
    return json.loads((GENERATED / f"{name}.schema.json").read_text(encoding="utf-8"))


def example(name: str) -> dict:
    return json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))


def errors(name: str, document: dict) -> list[str]:
    return [
        error.message
        for error in Draft201909Validator(schema(name)).iter_errors(document)
    ]


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
    if (name, shared) == (
        "check-report",
        "Place",
    ):  # a checked place is a place with its statuses
        place, checked = (
            schema("resolved-analysis")["$defs"]["Place"],
            schema(name)["$defs"]["CheckedPlace"],
        )
        assert set(place["required"]) <= set(checked["required"])
        assert place["properties"].items() <= checked["properties"].items()
    else:
        assert (
            schema(name)["$defs"][shared]
            == schema("resolved-analysis")["$defs"][shared]
        )


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
                "places": [
                    {field: place[field] for field in keep}
                    for place in result["places"]
                ],
            }
            for result in example(name)["results"]
        ]
    assert results["resolved-analysis"] == results["plan"] == results["check-report"]
    assert len(
        {result["output"]["id"] for result in results["resolved-analysis"]}
    ) < len(results["resolved-analysis"])


@pytest.mark.parametrize("name", SHAPES)
def test_model_compiles_without_warnings(name):
    path = GENERATED / f"{MODELS[name].__module__.rsplit('.', 1)[1]}.py"
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


@pytest.mark.parametrize("name", SHAPES)
def test_model_reads_the_example(name):
    document = example(name)
    model = MODELS[name].model_validate(document)
    assert model.shape == SHAPES[name]
    if name != "validation-report":
        assert [result.names for result in model.results] == [
            result["names"] for result in document["results"]
        ]


def test_model_reads_each_analysis_as_its_document():
    model = resolved.ResolvedAnalysis.model_validate(example("resolved-analysis"))
    fields = model.analyses[0].fields
    assert fields.outputs["switch1"].id == "switch1"
    assert fields.outputs["switch1"].cases["b"] == "stage.output3"
