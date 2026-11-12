"""The three documents tools exchange about an analysis (`documents.yaml`): the validation report, the resolved
analysis and the check report.

Each has a generated JSON Schema, and an example in `tests/documents/`, all three of one analysis: the specification's
worked example, with a switch, an output that reads a universe of a declared analysis, and that analysis's own
universe. The examples are checked against the schemas, and the resolved analysis against what a producer guarantees
of one beyond its schema.
"""

import json

import pytest

from .conftest import JSONSCHEMA, REPO_ROOT, validator

EXAMPLES = REPO_ROOT / "tests" / "documents"

SHAPES = {
    "ValidationReport": ("validation-report", "astra-validation-report/1"),
    "ResolvedAnalysis": ("resolved-analysis", "astra-resolved-analysis/1"),
    "CheckReport": ("check-report", "astra-check-report/1"),
}
"""Each document's root class, with its file name and the shape its documents state."""


def schema(name: str) -> dict:
    return json.loads((JSONSCHEMA / f"{name}.schema.json").read_text(encoding="utf-8"))


def example(root: str) -> dict:
    path = EXAMPLES / f"{SHAPES[root][0]}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def broken(root: str, document: dict) -> int:
    """How many schema errors `document` has."""
    return len(list(validator(root).iter_errors(document)))


def key(identity: dict) -> tuple[str, str | None]:
    return identity["folder"], identity.get("commit")


@pytest.fixture
def resolved() -> dict:
    return example("ResolvedAnalysis")


# --- Each document against its schema ---


@pytest.mark.parametrize("root", SHAPES)
def test_schema_has_its_own_id_and_shape(root):
    name, shape = SHAPES[root]
    assert schema(name)["$id"].endswith(f"/{name}.schema.json")
    assert schema(name)["properties"]["shape"]["const"] == shape


@pytest.mark.parametrize("root", SHAPES)
def test_example_is_valid(root):
    assert broken(root, example(root)) == 0


@pytest.mark.parametrize("root", SHAPES)
def test_unknown_field_is_refused(root):
    assert broken(root, {**example(root), "extra": 1}) == 1


@pytest.mark.parametrize("root", SHAPES)
def test_another_shape_is_refused(root):
    assert broken(root, {**example(root), "shape": "astra-other/1"}) == 1


@pytest.mark.parametrize("root", ["ResolvedAnalysis", "CheckReport"])
def test_absent_value_is_left_out_never_null(root):
    document = example(root)
    document["results"][1]["universe"] = None
    assert broken(root, document) == 1


@pytest.mark.parametrize("change", ["neither", "both"])
def test_read_names_an_input_or_a_result_never_both(resolved, change):
    read = resolved["results"][0]["inputs"][0]
    if change == "neither":
        del read["input"]
    else:
        read["result"] = 0
    assert broken("ResolvedAnalysis", resolved) == 1


def test_resolved_analysis_holds_each_file_as_the_analysis_schema_defines_it(resolved):
    ours, analysis = schema("resolved-analysis")["$defs"], schema("analysis")
    for name, definition in analysis["$defs"].items():
        assert ours[name] == definition
    for keyword in ("properties", "required", "additionalProperties"):
        assert ours["Analysis"][keyword] == analysis[keyword]
    for entry in resolved["analyses"]:
        assert not list(validator("Analysis").iter_errors(entry["fields"]))


def test_check_report_holds_a_record_as_the_open_record_schema_defines_it():
    ours, record = schema("check-report")["$defs"], schema("provenance.open")
    for name, definition in record["$defs"].items():
        assert ours[name] == definition
    for keyword in ("properties", "required", "additionalProperties"):
        assert ours["ProvenanceRecord"][keyword] == record[keyword]
    report = example("CheckReport")
    place = report["results"][0]["places"][0]
    place["provenance"]["generated_by"]["later"] = 1
    assert broken("CheckReport", report) == 0
    place["later"] = 1
    assert broken("CheckReport", report) == 1


# --- What a producer guarantees of a resolved analysis, beyond its schema ---


def test_analyses_are_the_driving_analysis_then_each_identity_once(resolved):
    identities = [key(entry) for entry in resolved["analyses"]]
    assert identities[0] == ("", None)
    assert len(set(identities)) == len(identities)


def test_every_identity_is_an_entry_of_analyses(resolved):
    entries = {key(entry) for entry in resolved["analyses"]}

    def identities(node):
        if isinstance(node, dict):
            if "folder" in node:
                yield key(node)
            for name, value in node.items():
                if name != "fields":
                    yield from identities(value)
        elif isinstance(node, list):
            for value in node:
                yield from identities(value)

    assert set(identities(resolved)) == entries


def test_declares_has_each_declaration_of_the_file(resolved):
    for entry in resolved["analyses"]:
        assert entry["declares"].keys() == entry["fields"].get("analyses", {}).keys()


def test_results_are_in_an_order_they_can_be_built_in(resolved):
    for at, result in enumerate(resolved["results"]):
        for read in result["inputs"]:
            assert read.get("result", -1) < at


def test_each_result_is_built_in_a_universe_of_its_owner(resolved):
    universes = {
        (key(entry["analysis"]), entry["id"]) for entry in resolved["universes"]
    }
    built_in = {
        (key(result["owner"]), result["universe"])
        for result in resolved["results"]
        if "universe" in result
    }
    assert built_in <= universes


def test_each_result_has_the_inputs_and_decisions_of_its_output(resolved):
    fields = {key(entry): entry["fields"] for entry in resolved["analyses"]}
    for result in resolved["results"]:
        output = result["output"]
        written = fields[key(output["analysis"])]["outputs"][output["id"]]
        assert [read["entry"] for read in result["inputs"]] == written.get("inputs", [])
        assert list(result["decisions"]) == written.get("decisions", [])


def test_each_result_is_named_by_its_owner_and_first_address(resolved):
    names = [
        (key(result["owner"]), result["places"][0]["address"])
        for result in resolved["results"]
    ]
    assert len(set(names)) == len(names)


def test_evidence_points_at_an_item_that_cites_an_output(resolved):
    fields = {key(entry): entry["fields"] for entry in resolved["analyses"]}
    for item in resolved["evidence"]:
        node = fields[key(item["analysis"])]
        for token in item["pointer"].split("/")[1:]:
            node = node[int(token)] if isinstance(node, list) else node[token]
        assert "artifact" in node
        for citation in item["cites"]:
            assert citation["result"] < len(resolved["results"])


# --- The check report beside the resolved analysis ---


def test_check_report_joins_the_resolved_analysis(resolved):
    report = example("CheckReport")
    head = ("owner", "output", "universe")
    place = ("name", "address", "record", "bytes")
    assert [
        (
            {name: result[name] for name in head if name in result},
            [{name: at[name] for name in place} for at in result["places"]],
        )
        for result in report["results"]
    ] == [
        ({name: result[name] for name in head if name in result}, result["places"])
        for result in resolved["results"]
    ]
    assert [(item["analysis"], item["pointer"]) for item in report["evidence"]] == [
        (item["analysis"], item["pointer"]) for item in resolved["evidence"]
    ]


def test_check_report_gives_a_record_where_it_is_the_result_s():
    for result in example("CheckReport")["results"]:
        for place in result["places"]:
            assert ("provenance" in place) == (place["record_status"] != "missing")
            if "provenance" in place:
                assert place["provenance"]["address"] == place["address"]
