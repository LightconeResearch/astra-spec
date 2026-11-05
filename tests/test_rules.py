"""`rules.json`: the rules extracted from the specification's §9, and the error map derived from the schema (design D13).

The extractor is strict, so it is tested on small specifications, one per way a §9 can be malformed. The committed
`rules.json` holds every rule of §9 in order, and a code for every keyword of the three JSON Schemas whose error can
make an instance fail (spec §10), each a schema-layer code. `absolute_keyword_location` is checked where `jsonschema`'s
paths need resolving.
"""

import copy as copy_module
import functools
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from jschon import JSON, JSONSchema, create_catalog
from jsonschema import Draft201909Validator
from jsonschema_generator import generate
from linkml_runtime import SchemaView
from rules import build_catalogue, build_error_map, extract_rules, json_pointer

from .conftest import (
    GENERATED,
    REPO_ROOT,
    absolute_keyword_location,
    errors,
    fixture_header,
    fixtures,
    load_document,
    load_json,
    rules_catalogue,
    validator,
)

SPECIFICATION = REPO_ROOT / "docs" / "specification.md"
SOURCES = REPO_ROOT / "src" / "astra" / "schema"
SCHEMAS = {
    "analysis.schema.json": "analysis",
    "provenance.schema.json": "provenance",
    "provenance.open.schema.json": "provenance",
}
"""Each generated JSON Schema, with the LinkML module it is generated from."""


def load(name: str) -> dict[str, Any]:
    return json.loads((GENERATED / name).read_text(encoding="utf-8"))


ANALYSIS = load("analysis.schema.json")["$id"] + "#"
RECORD = load("provenance.schema.json")["$id"] + "#"
OPEN = load("provenance.open.schema.json")["$id"] + "#"
"""Where the error map's keys start for each schema: its committed `$id`, which names its series, and `#`."""

VERSION = r"[0-9]+\.[0-9]+\.[0-9]+(?:(?:a|b|rc)[0-9]+)?|dev"
"""A version a generated file is stamped with: a release `X.Y.Z`, a pre-release (`0.1.0rc1`), or `dev`."""


def specification() -> str:
    return SPECIFICATION.read_text(encoding="utf-8")


# --- The extractor, on small specifications ---

CHECK = """\
### check

| Status | Means |
|---|---|
| `missing` | The result has no record (`MAY`) |

| Code | Level | Rule | Status when broken | Source |
|---|---|---|---|---|
| `NO_RECORD` | MUST | Every planned result has a record | `missing` | 0005 §1 |

"""

RUNNER_TABLE = """\
| Code | Level | Rule | Source |
|---|---|---|---|
| `NO_SANDBOX` | MAY | A runner runs each recipe in a sandbox | main |
"""

RUNNER = "### runner\n\n" + RUNNER_TABLE + "\n"


def quoted(table: str, prefix: str = "> ") -> str:
    """`table` in a blockquote: each of its lines after `prefix`."""
    return "".join(prefix + line for line in table.splitlines(keepends=True))


VALID = (
    """\
# A specification

## 8. Before

| Code | Level | Rule | Source |
|---|---|---|---|
| `NOT_A_RULE` | MUST | Nothing outside section 9 is extracted | §8 |

## 9. Conformance

| Layer | When a rule is broken |
|---|---|
| parse | The file fails |

### parse and schema

| Code | Layer | Level | Rule | Source |
|---|---|---|---|---|
| `BAD_SYNTAX` | parse | MUST | Every file is well-formed [YAML 1.2](https://yaml.org/spec/1.2.2/) | §3 |
| `BAD_ID` | schema | MUST | Every `id` matches the *id* grammar | §4, 0003 |

### validator

| Code | Level | Rule | Source |
|---|---|---|---|
| `LOOSE_PIN` | SHOULD | No reference to an output built once has a pin | 0003 |

"""
    + CHECK
    + RUNNER
    + """\
## 10. After

| Code | Level | Rule | Source |
|---|---|---|---|
| `ALSO_NOT_A_RULE` | MUST | Nothing outside section 9 is extracted | §10 |
"""
)


def test_extracts_the_rule_tables_of_section_9():
    """Every row of the four rule tables, in order; links reduced to their text; other tables and sections skipped."""
    assert extract_rules(VALID) == [
        {
            "code": "BAD_SYNTAX",
            "layer": "parse",
            "level": "MUST",
            "statement": "Every file is well-formed YAML 1.2",
            "source": "§3",
        },
        {
            "code": "BAD_ID",
            "layer": "schema",
            "level": "MUST",
            "statement": "Every `id` matches the *id* grammar",
            "source": "§4, 0003",
        },
        {
            "code": "LOOSE_PIN",
            "layer": "validator",
            "level": "SHOULD",
            "statement": "No reference to an output built once has a pin",
            "source": "0003",
        },
        {
            "code": "NO_RECORD",
            "layer": "check",
            "level": "MUST",
            "statement": "Every planned result has a record",
            "status": "`missing`",
            "source": "0005 §1",
        },
        {
            "code": "NO_SANDBOX",
            "layer": "runner",
            "level": "MAY",
            "statement": "A runner runs each recipe in a sandbox",
            "source": "main",
        },
    ]


MALFORMED = {
    "code not a code span": (
        "| `LOOSE_PIN` |",
        "| LOOSE_PIN |",
        r"LOOSE_PIN.*Code cell",
    ),
    "code not upper case": ("`LOOSE_PIN`", "`Loose_pin`", r"Loose_pin.*Code cell"),
    "empty cell": (
        "| SHOULD | No reference to an output built once has a pin |",
        "| SHOULD |  |",
        r"LOOSE_PIN.*Rule cell is empty",
    ),
    "extra cell": (
        "| 0003 |\n\n### check",
        "| 0003 | x |\n\n### check",
        r"LOOSE_PIN.*5 cells",
    ),
    "missing cell": (
        "| No reference to an output built once has a pin | 0003 |",
        "| No reference to an output built once has a pin |",
        r"LOOSE_PIN.*3 cells",
    ),
    "quoted row with an extra cell": (
        RUNNER,
        "### runner\n\n"
        + quoted(RUNNER_TABLE.replace("| main |", "| main | x |"))
        + "\n",
        r"NO_SANDBOX.*it has 5 cells",
    ),
    "duplicate code": ("`NO_SANDBOX`", "`NO_RECORD`", r"NO_RECORD.*already"),
    "missing column": (
        "| Code | Level | Rule | Source |\n|---|---|---|---|\n| `LOOSE_PIN` | SHOULD | No reference to an output built once has a pin | 0003 |",
        "| Code | Level | Rule |\n|---|---|---|\n| `LOOSE_PIN` | SHOULD | No reference to an output built once has a pin |",
        r"### validator.*no Source column",
    ),
    "unknown column": (
        RUNNER,
        RUNNER.replace(
            "| Source |\n|---|---|---|---|", "| Source | Notes |\n|---|---|---|---|---|"
        ).replace("| main |", "| main | none |"),
        r"### runner.*Notes",
    ),
    "repeated column": (
        RUNNER,
        RUNNER.replace(
            "| Source |\n|---|---|---|---|",
            "| Source | Source |\n|---|---|---|---|---|",
        ).replace("| main |", "| main | 0005 |"),
        r"### runner.*'Source' is unknown or repeated",
    ),
    "no rule table": (
        RUNNER,
        RUNNER.replace("| Code |", "| Name |"),
        r"### runner.*no rule table",
    ),
    "two rule tables in one subsection": (
        RUNNER,
        RUNNER + RUNNER_TABLE.replace("NO_SANDBOX", "EXTRA_RULE") + "\n",
        r"### runner: has 2 rule tables, not one",
    ),
    "unknown layer": (
        "| `BAD_ID` | schema |",
        "| `BAD_ID` | semantic |",
        r"BAD_ID.*semantic",
    ),
    "unknown layer heading": ("### runner", "### executor", r"executor"),
    "missing layer heading": (RUNNER, "", r"no ### runner"),
    "subsections out of order": (CHECK + RUNNER, RUNNER + CHECK, r"in order"),
    "unknown level": (
        "| `LOOSE_PIN` | SHOULD |",
        "| `LOOSE_PIN` | Should |",
        r"LOOSE_PIN.*Should",
    ),
    "MAY row in the parse and schema table": (
        "| `BAD_ID` | schema | MUST |",
        "| `BAD_ID` | schema | MAY |",
        r"BAD_ID.*a MAY row is allowed only in the runner table",
    ),
    "MAY row in the validator table": (
        "| `LOOSE_PIN` | SHOULD |",
        "| `LOOSE_PIN` | MAY |",
        r"LOOSE_PIN.*a MAY row is allowed only in the runner table",
    ),
    "MAY row in the check table": (
        "| `NO_RECORD` | MUST |",
        "| `NO_RECORD` | MAY |",
        r"NO_RECORD.*a MAY row is allowed only in the runner table",
    ),
    "keyword contradicts level": (
        "No reference to an output built once has a pin",
        "No reference to an output built once MUST have a pin",
        r"LOOSE_PIN.*MUST",
    ),
    "keyword in a code span contradicts level": (
        "Every planned result has a record |",
        "Every planned result has a record (`SHOULD`) |",
        r"NO_RECORD.*SHOULD",
    ),
    "keyword against a code span": (
        "Every planned result has a record |",
        "Every planned result has a record, see`SHOULD` |",
        r"NO_RECORD.*SHOULD",
    ),
    "keyword against a link": (
        "Every planned result has a record |",
        "Every planned result has a [record](#a)SHOULD |",
        r"NO_RECORD.*SHOULD",
    ),
    **{
        f"keyword split by {split}": (
            "No reference to an output built once has a pin",
            f"No reference to an output built once {written} have a pin",
            r"LOOSE_PIN.*MUST",
        )
        for split, written in {
            "intraword emphasis": "MU*ST*",
            "a link on part of it": "[MU](#x)ST",
            "a code span": "`MU`ST",
            "empty inline HTML": "MU<span></span>ST",
            "a soft hyphen": "MU&shy;ST",
            "a zero-width space": "MU\u200bST",
        }.items()
    },
    "two sentences in a rule": (
        "No reference to an output built once has a pin",
        "No reference to an output built once has a pin. A pin is redundant there",
        r"LOOSE_PIN.*more than one sentence",
    ),
    "two sentences in a rule, after a closing bracket": (
        "Every planned result has a record |",
        "Every planned result has a record (§8.) It is valid |",
        r"NO_RECORD.*more than one sentence",
    ),
    "two sentences in a rule, the mark in emphasis": (
        "A runner runs each recipe in a sandbox",
        "A runner runs each recipe in a *sandbox.* It may",
        r"NO_SANDBOX.*more than one sentence",
    ),
    "escape lost when written back": (
        "No reference to an output built once has a pin",
        r"No reference to an \*output\* built once has a pin",
        r"LOOSE_PIN.*Rule cell can't be written back",
    ),
    "image in a cell": (
        "No reference to an output built once has a pin",
        "No reference to an ![output](output.png) built once has a pin",
        r"LOOSE_PIN.*Rule cell holds a image",
    ),
    "rule table outside a subsection": (
        "### parse and schema\n",
        (
            "| Code | Level | Rule | Source |\n|---|---|---|---|\n"
            "| `SNEAKY` | MUST | A rule outside the subsections | §9 |\n\n"
            "### parse and schema\n"
        ),
        r"line 15: a rule table .* must be under one of §9's ### subsections",
    ),
    "no section 9": ("## 9. Conformance", "## 9. Rules", r"9\. Conformance"),
    "source in a code span": (
        "| §4, 0003 |",
        "| §4, `0003` |",
        r"BAD_ID.*Source cell holds a code_inline, but it must be plain text",
    ),
    "source as a link": (
        "| 0005 §1 |",
        "| [0005 §1](https://example.org/0005) |",
        r"NO_RECORD.*Source cell holds a link_open, but it must be plain text",
    ),
    "source in emphasis": (
        "| 0003 |\n\n### check",
        "| *0003* |\n\n### check",
        r"LOOSE_PIN.*Source cell holds a em_open, but it must be plain text",
    ),
    "unknown source token": ("| §4, 0003 |", "| §4, D5 |", r"BAD_ID.*Source.*'D5'"),
    "RFC number not four digits": (
        "| 0003 |\n\n### check",
        "| 3 |\n\n### check",
        r"LOOSE_PIN.*Source.*'3'",
    ),
    "RFC section without its sign": (
        "| 0005 §1 |",
        "| 0005 1 |",
        r"NO_RECORD.*Source.*'0005 1'",
    ),
    "source tokens not separated by a comma and a space": (
        "| §4, 0003 |",
        "| §4; 0003 |",
        r"BAD_ID.*Source.*'§4; 0003'",
    ),
}


@pytest.mark.parametrize("old, new, message", MALFORMED.values(), ids=MALFORMED)
def test_malformed_section_9_fails(old, new, message):
    assert old in VALID
    with pytest.raises(ValueError, match=message):
        extract_rules(VALID.replace(old, new, 1))


def test_keywords_that_agree_with_the_level_are_allowed():
    """A keyword of the rule's own level is fine, and a code that contains a keyword's letters is not one."""
    text = VALID.replace(
        "A runner runs each recipe in a sandbox",
        "A runner MAY run each recipe in a sandbox",
    ).replace(
        "No reference to an output built once has a pin",
        "No reference SHOULD have a pin, as `MISSING_REQUIRED_OPTION` says",
    )
    statements = [rule["statement"] for rule in extract_rules(text)]
    assert "A runner MAY run each recipe in a sandbox" in statements


def test_a_mark_that_ends_no_sentence_is_allowed():
    """A `.` in a code span, against one, inside a number or ending the cell leaves the rule one sentence."""
    rule = "Every `{inputs.<entry>}` names an entry of `a. b`, written in.`x` with 0.5 cores."
    text = VALID.replace("Every planned result has a record", rule)
    (found,) = [r for r in extract_rules(text) if r["code"] == "NO_RECORD"]
    assert found["statement"] == rule


def test_every_form_of_source_token_is_allowed():
    """An RFC number with or without its section, `tidy-up`, `main`, `#n` and `§n`, plain and separated by `, `."""
    sources = "0005 §1, 0005 §3, 0004, tidy-up, main, #73, §4"
    text = VALID.replace("| §4, 0003 |", f"| {sources} |")
    (rule,) = [rule for rule in extract_rules(text) if rule["code"] == "BAD_ID"]
    assert rule["source"] == sources


QUOTED = {
    "quoted": quoted(RUNNER_TABLE),
    "quoted without a space": quoted(RUNNER_TABLE, ">"),
    "indented and quoted": quoted(RUNNER_TABLE, "   > "),
    "quoted twice": quoted(RUNNER_TABLE, "> > "),
    "quoted in a list item": "1.  A list item\n\n" + quoted(RUNNER_TABLE, "    > "),
}


@pytest.mark.parametrize("table", QUOTED.values(), ids=QUOTED)
def test_a_quoted_rule_table_reads_as_the_same_rules(table):
    """A rule table in a blockquote is the same rules: its rows' cells are counted without the `>` markers."""
    assert RUNNER in VALID
    text = VALID.replace(RUNNER, "### runner\n\n" + table + "\n")
    assert extract_rules(text) == extract_rules(VALID)


# --- rules.json: the rules ---


def test_rules_json_has_its_three_parts():
    catalogue = rules_catalogue()
    assert sorted(catalogue) == ["$comment", "errors", "rules"]
    assert re.fullmatch(rf".* version (?:{VERSION})", catalogue["$comment"])


def test_rules_json_has_every_rule_of_section_9_in_order():
    assert rules_catalogue()["rules"] == extract_rules(specification())


def test_every_rule_has_its_fields():
    """`code`, `layer`, `level`, `statement` and `source`, and `status` exactly for the check layer."""
    common = {"code", "layer", "level", "statement", "source"}
    wrong = [
        rule["code"]
        for rule in rules_catalogue()["rules"]
        if set(rule) != (common | {"status"} if rule["layer"] == "check" else common)
    ]
    assert wrong == []


def test_every_fixture_rule_is_a_code_in_rules_json():
    codes = {rule["code"] for rule in rules_catalogue()["rules"]}
    rules = {fixture_header(path)[0] for path in fixtures("invalid")}
    assert sorted(rules - codes) == []


# --- rules.json: the error map ---

ANNOTATIONS = {"$comment", "$id", "$schema", "description", "title"}
APPLICATORS = {
    "$defs",
    "$ref",
    "properties",
    "items",
    "additionalProperties",
    "propertyNames",
    "then",
    "else",
    "oneOf",
    "anyOf",
    "allOf",
}
REPORTING = {
    "type",
    "enum",
    "const",
    "pattern",
    "minimum",
    "maximum",
    "minItems",
    "maxItems",
    "minProperties",
    "maxProperties",
    "uniqueItems",
    "required",
    "propertyNames",
    "oneOf",
    "anyOf",
    "not",
    "if",
}
"""The keywords that report an error of their own. Nothing inside an `if` or a `not` has an entry: no error there makes
the instance fail, and a tool drops it (spec §10, "From an error to its code")."""


def reporting_keywords(node: dict, pointer: str = "") -> Iterator[str]:
    """The JSON Pointer of every keyword in the schema `node` whose error can make the instance fail
    (`additionalProperties: false` too)."""
    for keyword, value in node.items():
        here = pointer + json_pointer([keyword])
        if keyword in REPORTING or (
            keyword == "additionalProperties" and value is False
        ):
            yield here
        if keyword in ("$defs", "properties"):
            for name, sub in value.items():
                yield from reporting_keywords(sub, here + json_pointer([name]))
        elif keyword in ("oneOf", "anyOf", "allOf"):
            for index, sub in enumerate(value):
                yield from reporting_keywords(sub, here + json_pointer([index]))
        elif keyword in (
            "items",
            "additionalProperties",
            "propertyNames",
            "then",
            "else",
        ):
            if isinstance(value, dict):
                yield from reporting_keywords(value, here)
        else:
            assert keyword in REPORTING | ANNOTATIONS | APPLICATORS, (
                f"{here}: unknown keyword"
            )


def locations(prefix: str) -> dict[str, str]:
    """The entries of the error map whose location is in the schema resource `prefix` (`<$id>#`)."""
    return {
        location.removeprefix(prefix): code
        for location, code in rules_catalogue()["errors"].items()
        if location.startswith(prefix)
    }


@pytest.mark.parametrize("name", SCHEMAS)
def test_every_keyword_that_can_fail_has_one_code(name):
    """The error map holds exactly the keywords of the three schemas whose error can make an instance fail, each
    once."""
    schema = load(name)
    assert sorted(locations(schema["$id"] + "#")) == sorted(reporting_keywords(schema))


def test_error_map_covers_only_the_three_schemas():
    ids = tuple(load(name)["$id"] + "#" for name in SCHEMAS)
    assert [
        location
        for location in rules_catalogue()["errors"]
        if not location.startswith(ids)
    ] == []


def test_every_code_in_the_error_map_is_a_schema_code():
    """And every schema-layer code is enforced somewhere, while the parse-layer codes are left to loaders."""
    layers = {rule["code"]: rule["layer"] for rule in rules_catalogue()["rules"]}
    codes = set(rules_catalogue()["errors"].values())
    assert sorted(codes) == sorted(
        code for code, layer in layers.items() if layer == "schema"
    )
    assert {code for code, layer in layers.items() if layer == "parse"} == {
        "INVALID_SYNTAX",
        "DUPLICATE_KEY",
    }


def test_open_variant_has_the_closed_constraints_but_unknown_fields():
    closed = {
        location: code
        for location, code in locations(RECORD).items()
        if code != "UNKNOWN_FIELD"
    }
    assert locations(OPEN) == closed
    assert "UNKNOWN_FIELD" in locations(RECORD).values()


@pytest.mark.parametrize("name", SCHEMAS)
def test_error_map_is_built_from_the_schema(name):
    """`build_error_map` on the committed schema and its LinkML source gives the committed entries."""
    schema = load(name)
    view = SchemaView(str(SOURCES / f"{SCHEMAS[name]}.yaml"))
    expected = {
        schema["$id"] + "#" + pointer: code
        for pointer, code in locations(schema["$id"] + "#").items()
    }
    assert build_error_map(schema, view) == expected


DECLARATION = "/$defs/AnalysisDeclaration__identifier_optional"
CODES = {
    # Patterns, by their type
    ANALYSIS + DECLARATION + "/properties/commit/pattern": "INVALID_COMMIT",
    ANALYSIS
    + "/$defs/Option__identifier_optional/properties/insights/items/pattern": "INVALID_ID",
    ANALYSIS
    + "/$defs/Universe__identifier_optional/properties/derived_from/pattern": "INVALID_ID",
    ANALYSIS
    + "/$defs/Universe__identifier_optional/properties/decisions/additionalProperties/pattern": "INVALID_ID",
    ANALYSIS
    + "/$defs/Output__identifier_optional/properties/inputs/items/pattern": "INVALID_REFERENCE",
    ANALYSIS
    + "/$defs/Output__identifier_optional/properties/decisions/items/pattern": "INVALID_REFERENCE",
    ANALYSIS
    + "/$defs/Output__identifier_optional/properties/when/items/pattern": "INVALID_REFERENCE",
    ANALYSIS
    + "/$defs/Option__identifier_optional/properties/requires/items/pattern": "INVALID_REFERENCE",
    ANALYSIS + "/$defs/Evidence/properties/artifact/pattern": "INVALID_REFERENCE",
    ANALYSIS + "/properties/spec_version/pattern": "INVALID_VALUE",
    RECORD + "/properties/content_hash/pattern": "INVALID_VALUE",
    RECORD + "/$defs/Generation/properties/started/pattern": "INVALID_VALUE",
    RECORD + "/$defs/Generation/properties/commit/pattern": "INVALID_COMMIT",
    RECORD + "/properties/address/pattern": "INVALID_REFERENCE",
    # Map keys, whatever their key's type, and whatever the key's own type
    ANALYSIS + "/properties/outputs/propertyNames": "INVALID_ID",
    ANALYSIS + "/properties/outputs/propertyNames/pattern": "INVALID_ID",
    ANALYSIS + "/properties/outputs/propertyNames/type": "INVALID_ID",
    ANALYSIS
    + "/$defs/Universe__identifier_optional/properties/decisions/propertyNames": "INVALID_ID",
    ANALYSIS
    + "/$defs/Universe__identifier_optional/properties/decisions/propertyNames/pattern": "INVALID_ID",
    # Patterns, by their slot
    ANALYSIS
    + "/$defs/Input__identifier_optional/properties/path/pattern": "INVALID_PATH",
    ANALYSIS + DECLARATION + "/properties/path/pattern": "INVALID_PATH",
    ANALYSIS
    + "/$defs/Option__identifier_optional/properties/excluded/pattern": "BLANK_EXCLUDED",
    ANALYSIS
    + "/$defs/Output__identifier_optional/properties/format/pattern": "INVALID_VALUE",
    ANALYSIS + "/$defs/Evidence/properties/doi/pattern": "INVALID_VALUE",
    ANALYSIS + DECLARATION + "/properties/url/pattern": "INVALID_VALUE",
    RECORD + "/$defs/Environment/properties/iri/pattern": "INVALID_VALUE",
    OPEN + "/$defs/Environment/properties/iri/pattern": "INVALID_VALUE",
    # Class rules and exactly-one-of, each a guarded member of `allOf`: the exactly-one-of first, then the rule
    ANALYSIS + DECLARATION + "/allOf/0/if": "INVALID_DECLARATION_SOURCE",
    ANALYSIS + DECLARATION + "/allOf/0/then/oneOf": "INVALID_DECLARATION_SOURCE",
    ANALYSIS
    + DECLARATION
    + "/allOf/0/then/oneOf/0/required": "INVALID_DECLARATION_SOURCE",
    ANALYSIS
    + DECLARATION
    + "/allOf/0/then/oneOf/1/required": "INVALID_DECLARATION_SOURCE",
    ANALYSIS + DECLARATION + "/allOf/1/if": "URL_WITHOUT_COMMIT",
    ANALYSIS + DECLARATION + "/allOf/1/then/required": "URL_WITHOUT_COMMIT",
    ANALYSIS + "/$defs/Evidence/allOf/0/if": "INVALID_EVIDENCE_SOURCE",
    ANALYSIS + "/$defs/Evidence/allOf/0/then/oneOf": "INVALID_EVIDENCE_SOURCE",
    ANALYSIS + "/$defs/Evidence/allOf/1/if": "INVALID_EVIDENCE_SOURCE",
    ANALYSIS + "/$defs/Evidence/allOf/1/then/not": "INVALID_EVIDENCE_SOURCE",
    # Defaults
    ANALYSIS + "/required": "MISSING_FIELD",
    ANALYSIS + "/$defs/Output__identifier_optional/required": "MISSING_FIELD",
    ANALYSIS + "/additionalProperties": "UNKNOWN_FIELD",
    RECORD + "/$defs/Runner/additionalProperties": "UNKNOWN_FIELD",
    ANALYSIS + "/properties/tags/type": "WRONG_TYPE",
    ANALYSIS + "/properties/outputs/minProperties": "EMPTY_COLLECTION",
    ANALYSIS
    + "/$defs/Insight__identifier_optional/properties/evidence/minItems": "EMPTY_COLLECTION",
    ANALYSIS + "/properties/tags/uniqueItems": "DUPLICATE_ENTRY",
    ANALYSIS + "/$defs/OutputType/enum": "INVALID_VALUE",
    ANALYSIS + "/$defs/Resources/properties/gpus/minimum": "INVALID_VALUE",
    RECORD + "/properties/size/minimum": "INVALID_VALUE",
}
"""A code for each kind of constraint: patterns by type and by slot, map keys, class rules, and the defaults."""


def test_each_kind_of_constraint_has_its_code():
    error_map = rules_catalogue()["errors"]
    assert {location: error_map.get(location) for location in CODES} == CODES


def test_open_variant_has_no_unknown_fields():
    assert OPEN + "/additionalProperties" not in rules_catalogue()["errors"]


def test_every_map_key_is_an_id():
    """A map key that doesn't match its key's type is `INVALID_ID`, whatever that type (an `address` included), and so
    is a key that isn't a string: every keyword under a `propertyNames` takes the key's code, its `type` too."""
    keys = {
        location: code
        for location, code in rules_catalogue()["errors"].items()
        if "/propertyNames" in location
    }
    expected = {
        schema["$id"] + "#" + pointer
        for schema in map(load, SCHEMAS)
        for pointer in reporting_keywords(schema)
        if "/propertyNames" in pointer
    }
    assert sorted(keys) == sorted(expected)
    assert any(location.endswith("/propertyNames/type") for location in keys)
    assert {code for code in keys.values()} == {"INVALID_ID"}


def schema_objects(node: Any, pointer: str = "") -> Iterator[tuple[str, dict]]:
    """`(pointer, object)` for every object in the schema `node`, the root included."""
    if isinstance(node, dict):
        yield pointer, node
        for key, child in node.items():
            yield from schema_objects(child, pointer + json_pointer([key]))
    elif isinstance(node, list):
        for index, child in enumerate(node):
            yield from schema_objects(child, pointer + json_pointer([index]))


@pytest.mark.parametrize("name", SCHEMAS)
def test_no_schema_has_an_empty_required(name):
    """An empty `required` checks nothing, so no schema keeps one and the error map gives none a code."""
    empty = [
        pointer
        for pointer, node in schema_objects(load(name))
        if node.get("required") == []
    ]
    assert empty == []


def test_catalogue_is_built_from_the_sources():
    """`build_catalogue` on the specification, the committed schemas and their LinkML sources gives `rules.json`."""
    schemas = [
        (load(name), SchemaView(str(SOURCES / f"{module}.yaml")))
        for name, module in SCHEMAS.items()
    ]
    built = build_catalogue(specification(), schemas)
    assert built == {
        "rules": rules_catalogue()["rules"],
        "errors": rules_catalogue()["errors"],
    }


# --- The error map, on scratch schemas ---

SCRATCH = """\
id: https://example.org/scratch
name: scratch
version: 0.0.0
prefixes:
  linkml: https://w3id.org/linkml/
  ex: https://example.org/
default_prefix: ex
default_range: string
imports:
  - linkml:types
classes:
  Thing:
    tree_root: true
    attributes:
      name:
        pattern: "^[a-z]+$"
        annotations:
          rule: INVALID_ID
      url:
        description: Where it is.
      commit:
        description: Its commit.
    exactly_one_of:
      - slot_conditions:
          name:
            required: true
        annotations:
          rule: INVALID_DECLARATION_SOURCE
      - slot_conditions:
          url:
            required: true
        annotations:
          rule: INVALID_DECLARATION_SOURCE
    rules:
      - preconditions:
          slot_conditions:
            url:
              value_presence: PRESENT
        postconditions:
          slot_conditions:
            commit:
              value_presence: PRESENT
        annotations:
          rule: URL_WITHOUT_COMMIT
"""

UNCODED = {
    "a pattern with no code": (
        "        annotations:\n          rule: INVALID_ID\n",
        "",
        r"Thing\.name",
    ),
    "a class rule with no code": (
        "        annotations:\n          rule: URL_WITHOUT_COMMIT\n",
        "",
        r"Thing's class rule",
    ),
    "an exactly_one_of branch with no code": (
        "        annotations:\n          rule: INVALID_DECLARATION_SOURCE\n",
        "",
        r"each branch of Thing's exactly_one_of",
    ),
}


def scratch_schema(tmp_path, text: str) -> tuple[dict, SchemaView]:
    source = tmp_path / "scratch.yaml"
    source.write_text(text, encoding="utf-8")
    return generate(source), SchemaView(str(source))


def test_scratch_schema_has_its_codes(tmp_path):
    error_map = build_error_map(*scratch_schema(tmp_path, SCRATCH))
    base = "https://example.org/scratch#"
    expected = {
        "/properties/name/pattern": "INVALID_ID",
        "/allOf/0/if": "INVALID_DECLARATION_SOURCE",
        "/allOf/0/then/oneOf": "INVALID_DECLARATION_SOURCE",
        "/allOf/0/then/oneOf/1/required": "INVALID_DECLARATION_SOURCE",
        "/allOf/1/if": "URL_WITHOUT_COMMIT",
        "/allOf/1/then/required": "URL_WITHOUT_COMMIT",
    }
    assert {pointer: error_map.get(base + pointer) for pointer in expected} == expected
    # Nothing inside an `if` has a code: it only guards its check.
    assert [location for location in error_map if "/if/" in location] == []


@pytest.mark.parametrize("old, new, message", UNCODED.values(), ids=UNCODED)
def test_a_constraint_without_a_code_fails(tmp_path, old, new, message):
    assert old in SCRATCH
    with pytest.raises(ValueError, match=message):
        build_error_map(*scratch_schema(tmp_path, SCRATCH.replace(old, new, 1)))


MINIMUMS = {
    "of a list": (
        [
            (
                "        description: Its commit.\n",
                (
                    "        description: Its commit.\n      tags:\n        multivalued: true\n"
                    "        minimum_cardinality: {n}\n"
                ),
            )
        ],
        "/properties/tags/minItems",
    ),
    "of a map": (
        [
            (
                "classes:\n",
                (
                    "classes:\n  Part:\n    attributes:\n      id:\n        key: true\n"
                    "        pattern: '^[a-z]+$'\n        annotations:\n          rule: INVALID_ID\n"
                    "      size:\n        range: integer\n"
                ),
            ),
            (
                "        description: Its commit.\n",
                (
                    "        description: Its commit.\n      parts:\n        range: Part\n"
                    "        multivalued: true\n        inlined: true\n        minimum_cardinality: {n}\n"
                ),
            ),
        ],
        "/properties/parts/minProperties",
    ),
}
"""A minimum number of entries on the scratch schema: each edit of SCRATCH it takes, with `{n}` the minimum, and the
keyword it becomes."""


def with_minimum(edits: list[tuple[str, str]], n: int) -> str:
    text = SCRATCH
    for old, new in edits:
        assert old in text
        text = text.replace(old, new.format(n=n), 1)
    return text


@pytest.mark.parametrize("edits, keyword", MINIMUMS.values(), ids=MINIMUMS)
def test_a_minimum_of_one_is_empty_collection(tmp_path, edits, keyword):
    error_map = build_error_map(*scratch_schema(tmp_path, with_minimum(edits, 1)))
    assert error_map["https://example.org/scratch#" + keyword] == "EMPTY_COLLECTION"


@pytest.mark.parametrize("edits, keyword", MINIMUMS.values(), ids=MINIMUMS)
def test_a_minimum_above_one_fails(tmp_path, edits, keyword):
    """`EMPTY_COLLECTION` says "at least one entry", so a minimum of 2 has no code, and the build fails on it."""
    schema_and_view = scratch_schema(tmp_path, with_minimum(edits, 2))
    with pytest.raises(ValueError, match=re.escape(keyword) + ": no code"):
        build_catalogue(specification(), [schema_and_view])


UNUSED = {
    "on a class": (
        "  Thing:\n    tree_root: true\n",
        "  Thing:\n    tree_root: true\n    annotations:\n      rule: INVALID_VALUE\n",
        r"annotation of the class Thing$",
    ),
    "on a slot with no pattern": (
        "        description: Where it is.\n",
        "        description: Where it is.\n        annotations:\n          rule: INVALID_VALUE\n",
        r"annotation of Thing\.url$",
    ),
    "on a type no slot uses": (
        "classes:\n",
        (
            "types:\n  code:\n    typeof: string\n    pattern: '^[a-z]+$'\n"
            "    annotations:\n      rule: INVALID_ID\nclasses:\n"
        ),
        r"annotation of the type code$",
    ),
}


def test_scratch_catalogue_builds(tmp_path):
    """The scratch schema's annotations all give codes, so the cases below fail for their one extra annotation."""
    assert build_catalogue(specification(), [scratch_schema(tmp_path, SCRATCH)])[
        "errors"
    ]


@pytest.mark.parametrize("old, new, message", UNUSED.values(), ids=UNUSED)
def test_a_rule_annotation_that_gives_no_code_fails(tmp_path, old, new, message):
    assert old in SCRATCH
    schema_and_view = scratch_schema(tmp_path, SCRATCH.replace(old, new, 1))
    with pytest.raises(ValueError, match=message):
        build_catalogue(specification(), [schema_and_view])


def test_a_code_that_is_not_a_schema_code_fails(tmp_path):
    """Every code the schema names is a schema-layer rule of §9: here, a validator-layer one."""
    schema, view = scratch_schema(
        tmp_path, SCRATCH.replace("rule: INVALID_ID", "rule: UNKNOWN_OPTION")
    )
    with pytest.raises(ValueError, match="UNKNOWN_OPTION"):
        build_catalogue(specification(), [(schema, view)])


# --- absolute_keyword_location, where jsonschema's paths need resolving ---

RECIPE = {"command": "python make.py '{output}'"}
"""A valid recipe."""

DOCUMENT = {
    "spec_version": "0.1.0",
    "outputs": {"o": {"type": "metric", "format": "csv", "recipe": RECIPE}},
}

LOCATED = {
    "oneOf and its branches, in an allOf member's then": (
        {**DOCUMENT, "analyses": {"a": {}}},
        {
            ("/analyses/a", ANALYSIS + DECLARATION + "/allOf/0/then/oneOf"),
            ("/analyses/a", ANALYSIS + DECLARATION + "/allOf/0/then/oneOf/0/required"),
            ("/analyses/a", ANALYSIS + DECLARATION + "/allOf/0/then/oneOf/1/required"),
        },
    ),
    "then, after an if, in an allOf member": (
        {**DOCUMENT, "analyses": {"a": {"url": "https://example.org/repo"}}},
        {("/analyses/a", ANALYSIS + DECLARATION + "/allOf/1/then/required")},
    ),
    "then/not, in a list item": (
        {
            **DOCUMENT,
            "findings": {
                "f": {"claim": "c", "evidence": [{"artifact": "o", "version": 2}]}
            },
        },
        {("/findings/f/evidence/0", ANALYSIS + "/$defs/Evidence/allOf/1/then/not")},
    ),
    "a declaration that isn't an object, its checks skipped": (
        {**DOCUMENT, "analyses": {"a": "../a"}},
        {("/analyses/a", ANALYSIS + DECLARATION + "/type")},
    ),
    "a field of the wrong type, its checks skipped": (
        {**DOCUMENT, "analyses": {"a": {"path": "a", "url": None}}},
        {("/analyses/a/url", ANALYSIS + DECLARATION + "/properties/url/type")},
    ),
    "a map's propertyNames": (
        {
            **DOCUMENT,
            "outputs": {"O": {"type": "metric", "format": "csv", "recipe": RECIPE}},
        },
        {("/outputs", ANALYSIS + "/properties/outputs/propertyNames/pattern")},
    ),
    "a map's propertyNames, inside a $ref": (
        {**DOCUMENT, "universes": {"u": {"decisions": {"A": "b"}}}},
        {
            (
                "/universes/u/decisions",
                ANALYSIS
                + "/$defs/Universe__identifier_optional/properties/decisions/propertyNames/pattern",
            )
        },
    ),
    "a map's additionalProperties, compact form": (
        {**DOCUMENT, "universes": {"u": {"decisions": {"a": "B"}}}},
        {
            (
                "/universes/u/decisions/a",
                ANALYSIS
                + "/$defs/Universe__identifier_optional/properties/decisions/additionalProperties/pattern",
            )
        },
    ),
    "a map's additionalProperties, object form": (
        {**DOCUMENT, "outputs": {"o": {"type": "metric", "recipe": RECIPE}}},
        {("/outputs/o", ANALYSIS + "/$defs/Output__identifier_optional/required")},
    ),
    "an enum through a $ref with a sibling": (
        {
            **DOCUMENT,
            "outputs": {"o": {"type": "movie", "format": "csv", "recipe": RECIPE}},
        },
        {("/outputs/o/type", ANALYSIS + "/$defs/OutputType/enum")},
    ),
    "the root": (
        {**DOCUMENT, "extra": 1},
        {("(root)", ANALYSIS + "/additionalProperties")},
    ),
}


@pytest.mark.parametrize("doc, expected", LOCATED.values(), ids=LOCATED)
def test_absolute_keyword_location(doc, expected):
    assert {
        (pointer, location)
        for pointer, location, _ in errors(validator("Analysis"), doc)
    } == expected


def test_absolute_keyword_location_finds_the_subschema_by_identity():
    """An error whose subschema isn't the schema's own object, even an equal copy, has no location."""
    copy = Draft201909Validator(copy_module.deepcopy(validator("Analysis").schema))
    (error,) = copy.iter_errors({**DOCUMENT, "extra": 1})
    with pytest.raises(ValueError, match="isn't found in the schema"):
        absolute_keyword_location(validator("Analysis"), error)


# --- Spec §10's filter, on a validator that writes JSON Schema's standard output formats ---

NAMED = {"$defs", "properties"}
"""The keywords that hold subschemas by name: in a keyword location, the name follows the keyword."""
INDEXED = {"allOf", "anyOf", "oneOf"}
"""The keywords that hold a list of subschemas: in a keyword location, the index follows the keyword."""
LISTED_ABOVE = {"properties", "items", "$ref", "allOf", "then"}
"""The applicators that standard output lists above an error, with an `additionalProperties` that holds a schema: a
tool drops them, as it drops the subschemas listed there (spec §10)."""
OUTPUT_SCHEMAS = {
    "Analysis": "analysis.schema.json",
    "ProvenanceRecord": "provenance.schema.json",
}
"""The committed schema of the documents rooted at each class."""


@functools.cache
def jschon_catalog() -> None:
    """jschon's catalog of JSON Schema 2019-09, which it reads a schema's `$schema` from, made once."""
    create_catalog("2019-09")


@functools.cache
def jschon_schema(root: str) -> JSONSchema:
    """The committed schema of documents rooted at `root`, read by jschon, a JSON Schema 2019-09 validator that writes
    the standard output formats."""
    jschon_catalog()
    return JSONSchema(load(OUTPUT_SCHEMAS[root]))


def jschon_units(root: str, document: Any, output_format: str) -> list[dict[str, Any]]:
    """The failing output units jschon writes for `document`, in its `basic` or `verbose` format.

    Basic output lists a unit only below units that fail too, so it leaves out what fails below an `allOf` member or
    a `oneOf` that passes. Verbose output lists every unit: each failing one is taken, a subschema (the root,
    `…/allOf/0`) as well as a keyword, which is everything a validator writing a standard format could list, so the
    filter is tested on all of it.
    """
    result = jschon_schema(root).evaluate(JSON(document))
    if output_format == "basic":
        return result.output("basic").get("errors", [])

    def walk(unit: dict[str, Any]) -> Iterator[dict[str, Any]]:
        if not unit["valid"]:
            yield unit
        for child in unit.get("errors", unit.get("annotations", [])):
            yield from walk(child)

    return list(walk(result.output("verbose")))


def keyword_steps(location: str) -> list[tuple[str, str | None, str]]:
    """`(keyword, name or index, location)` for each keyword a keyword location runs through, in order.

    A keyword location (a unit's `keywordLocation`, its evaluation path) is a JSON Pointer through the schema, `$ref`s
    included. The name or index is the token after a keyword that holds subschemas by name or in a list (`properties/x`,
    `oneOf/0`), or None; `location` is the keyword's own keyword location. A unit that names a keyword, not a
    subschema, ends in a step with None.
    """
    tokens = [
        token.replace("~1", "/").replace("~0", "~") for token in location.split("/")[1:]
    ]
    steps, here = [], ""
    while tokens:
        keyword = tokens.pop(0)
        here += json_pointer([keyword])
        argument = tokens.pop(0) if keyword in NAMED | INDEXED and tokens else None
        steps.append((keyword, argument, here))
        if argument is not None:
            here += json_pointer([argument])
    return steps


def _within(inner: str, outer: str) -> bool:
    """True if the JSON Pointer `inner` is `outer` or below it."""
    return inner == outer or inner.startswith(outer + "/")


def _schema_at(schema: dict[str, Any], location: str) -> Any:
    """The value at an absolute keyword location of `schema`."""
    value: Any = schema
    for token in location.split("#", 1)[1].split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def listed_above(unit: dict[str, Any], schema: dict[str, Any]) -> bool:
    """True if `unit` is what standard output lists above an error (spec §10): a subschema (the root, `…/allOf/0`) or
    an applicator."""
    steps = keyword_steps(unit["keywordLocation"])
    if not steps or steps[-1][1] is not None:
        return True
    keyword = steps[-1][0]
    return keyword in LISTED_ABOVE or (
        keyword == "additionalProperties"
        and isinstance(_schema_at(schema, unit["absoluteKeywordLocation"]), dict)
    )


def makes_the_instance_fail(unit: dict[str, Any], units: list[dict[str, Any]]) -> bool:
    """False if spec §10 drops `unit`, of the failing `units`, as an error that doesn't make the instance fail.

    That is an error inside an `if` or a `not`, an `if` whose `then` doesn't fail, and an error inside a branch of a
    `oneOf` or an `anyOf` that isn't reported as failing. A unit fails below another when its instance location is the
    other's or below it.
    """
    *above, (keyword, _, here) = keyword_steps(unit["keywordLocation"])
    at = unit["instanceLocation"]
    if any(step in ("if", "not") for step, _, _ in above):
        return False
    if keyword == "if":
        then = here.removesuffix("if") + "then"
        return any(
            _within(other["keywordLocation"], then)
            and _within(other["instanceLocation"], at)
            for other in units
        )
    return all(
        any(
            other["keywordLocation"] == location
            and _within(at, other["instanceLocation"])
            for other in units
        )
        for step, _, location in above
        if step in ("oneOf", "anyOf")
    )


def section_10(
    units: list[dict[str, Any]], schema: dict[str, Any]
) -> set[tuple[str, str]]:
    """`(pointer, location)` for each of the failing `units` that spec §10 has a tool keep: not a subschema or an
    applicator listed above an error, and making the instance fail.

    An error inside a `propertyNames` is at its map's pointer: jschon writes the key at the end of its instance
    location, as if it named the key's entry, and that last token goes.
    """
    kept = set()
    for unit in units:
        if listed_above(unit, schema) or not makes_the_instance_fail(unit, units):
            continue
        at = unit["instanceLocation"]
        if any(
            step == "propertyNames"
            for step, _, _ in keyword_steps(unit["keywordLocation"])[:-1]
        ):
            at = at.rsplit("/", 1)[0]
        kept.add((at or "(root)", unit["absoluteKeywordLocation"]))
    return kept


SCHEMA_FIXTURES = [
    path for path in fixtures("invalid") if fixture_header(path)[1] != "parse"
]
"""The invalid fixtures that fail at the schema layer."""


def fixture_document(path: Path) -> tuple[str, Any]:
    """`(root, document)` for a fixture: the class it is a document of, and its JSON form, with any entry whose key
    isn't a string left out (spec §3)."""
    document = load_json(path) if path.suffix == ".json" else load_document(path)[0]
    return path.name.split("-", 1)[0], document


@pytest.mark.parametrize("output_format", ["basic", "verbose"])
@pytest.mark.parametrize("path", SCHEMA_FIXTURES, ids=lambda path: path.stem)
def test_section_10_filter_gives_the_codes_jsonschema_gives(path, output_format):
    """On jschon's standard output for each schema-layer invalid fixture, every error spec §10 keeps has an entry, and
    the `(pointer, code)` pairs are those of `jsonschema`'s errors."""
    root, document = fixture_document(path)
    error_map = rules_catalogue()["errors"]
    kept = section_10(
        jschon_units(root, document, output_format), load(OUTPUT_SCHEMAS[root])
    )
    assert sorted(location for _, location in kept if location not in error_map) == []
    assert {(pointer, error_map[location]) for pointer, location in kept} == {
        (pointer, error_map[location])
        for pointer, location, _ in errors(validator(root), document)
    }


LEAKS = {
    "Analysis-150-short-commit": {
        # The failing branch of a `oneOf` that passes: its entry's code would be wrong.
        ANALYSIS + DECLARATION + "/allOf/0/then/oneOf/0/required",
    },
    "Analysis-166-doi-directory-not-10": {
        ANALYSIS + "/$defs/Evidence/allOf/0/then/oneOf/1/required",
        # An `if` whose `then` doesn't fail, and the `not` inside it, which has no entry.
        ANALYSIS + "/$defs/Evidence/allOf/1/if",
        ANALYSIS + "/$defs/Evidence/allOf/1/if/not",
    },
}


@pytest.mark.parametrize("name, leaked", LEAKS.items(), ids=LEAKS)
def test_section_10_filter_drops_what_doesnt_make_the_instance_fail(name, leaked):
    """jschon's verbose output lists failures that don't make the instance fail, as a validator writing a standard
    format may: spec §10's filter drops exactly those."""
    (path,) = [path for path in SCHEMA_FIXTURES if path.stem == name]
    root, document = fixture_document(path)
    schema = load(OUTPUT_SCHEMAS[root])
    units = jschon_units(root, document, "verbose")
    assert {
        unit["absoluteKeywordLocation"]
        for unit in units
        if not listed_above(unit, schema) and not makes_the_instance_fail(unit, units)
    } == leaked
