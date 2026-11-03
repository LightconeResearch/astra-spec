"""`rules.json`: the rules extracted from the specification's §9, and the error map derived from the schema (design D13).

The extractor is strict, so it is tested on small specifications, one per way a §9 can be malformed. The committed
`rules.json` holds every rule of §9 in order, and a code for every keyword of the three JSON Schemas that can report an
error, each a schema-layer code. `absolute_keyword_location` is checked where `jsonschema`'s paths need resolving.
"""

import json
import re
from collections.abc import Iterator
from typing import Any

import pytest
from jsonschema_generator import generate
from linkml_runtime import SchemaView
from rules import build_catalogue, build_error_map, extract_rules

from .conftest import (
    GENERATED,
    REPO_ROOT,
    errors,
    fixture_header,
    fixtures,
    rules_catalogue,
    validator,
)

SPECIFICATION = REPO_ROOT / "docs" / "specification.md"
SOURCES = REPO_ROOT / "src" / "astra" / "schema"
NAMESPACE = "https://w3id.org/astra/"
SCHEMAS = {
    "analysis.schema.json": "analysis",
    "provenance.schema.json": "provenance",
    "provenance.open.schema.json": "provenance",
}
"""Each generated JSON Schema, with the LinkML module it is generated from."""

ANALYSIS = NAMESPACE + "analysis.schema.json#"
RECORD = NAMESPACE + "provenance.schema.json#"
OPEN = NAMESPACE + "provenance.open.schema.json#"


def load(name: str) -> dict[str, Any]:
    return json.loads((GENERATED / name).read_text(encoding="utf-8"))


def specification() -> str:
    return SPECIFICATION.read_text(encoding="utf-8")


# --- The extractor, on small specifications ---

RUNNER = """\
### runner

| Code | Level | Rule | Source |
|---|---|---|---|
| `NO_SANDBOX` | MAY | A runner runs each recipe in a sandbox | `main` |

"""

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

### check

| Status | Means |
|---|---|
| `missing` | The result has no record (`MAY`) |

| Code | Level | Rule | Status when broken | Source |
|---|---|---|---|---|
| `NO_RECORD` | MUST | Every planned result has a record | `missing` | 0005 §1 |

"""
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
            "source": "`main`",
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
        ).replace("| `main` |", "| `main` | none |"),
        r"### runner.*Notes",
    ),
    "no rule table": (
        RUNNER,
        RUNNER.replace("| Code |", "| Name |"),
        r"### runner.*no rule table",
    ),
    "unknown layer": (
        "| `BAD_ID` | schema |",
        "| `BAD_ID` | semantic |",
        r"BAD_ID.*semantic",
    ),
    "unknown layer heading": ("### runner", "### executor", r"executor"),
    "missing layer heading": (RUNNER, "", r"no ### runner"),
    "unknown level": (
        "| `LOOSE_PIN` | SHOULD |",
        "| `LOOSE_PIN` | Should |",
        r"LOOSE_PIN.*Should",
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
    "no section 9": ("## 9. Conformance", "## 9. Rules", r"9\. Conformance"),
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


# --- rules.json: the rules ---


def test_rules_json_has_its_three_parts():
    catalogue = rules_catalogue()
    assert sorted(catalogue) == ["$comment", "errors", "rules"]
    assert re.fullmatch(r".* version [0-9]+\.[0-9]+\.[0-9]+", catalogue["$comment"])


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
"""The keywords that report an error of their own. Nothing inside an `if` or a `not` is ever reported."""


def reporting_keywords(node: dict, pointer: str = "") -> Iterator[str]:
    """The JSON Pointer of every keyword in the schema `node` that can report an error (`additionalProperties: false` too)."""
    for keyword, value in node.items():
        here = f"{pointer}/{keyword}"
        if keyword in REPORTING or (
            keyword == "additionalProperties" and value is False
        ):
            yield here
        if keyword in ("$defs", "properties"):
            for name, sub in value.items():
                yield from reporting_keywords(sub, f"{here}/{name}")
        elif keyword in ("oneOf", "anyOf", "allOf"):
            for index, sub in enumerate(value):
                yield from reporting_keywords(sub, f"{here}/{index}")
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
    """The error map holds exactly the keywords of the three schemas that can report an error, each once."""
    schema = load(name)
    assert sorted(locations(schema["$id"] + "#")) == sorted(reporting_keywords(schema))


def test_error_map_covers_only_the_three_schemas():
    ids = tuple(NAMESPACE + name + "#" for name in SCHEMAS)
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
    # Map keys, whatever their key's type
    ANALYSIS + "/properties/outputs/propertyNames": "INVALID_ID",
    ANALYSIS + "/properties/outputs/propertyNames/pattern": "INVALID_ID",
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
    # Class rules and exactly-one-of
    ANALYSIS + DECLARATION + "/oneOf": "INVALID_DECLARATION_SOURCE",
    ANALYSIS + DECLARATION + "/oneOf/0/required": "INVALID_DECLARATION_SOURCE",
    ANALYSIS + DECLARATION + "/oneOf/1/required": "INVALID_DECLARATION_SOURCE",
    ANALYSIS + DECLARATION + "/if": "URL_WITHOUT_COMMIT",
    ANALYSIS + DECLARATION + "/then/required": "URL_WITHOUT_COMMIT",
    ANALYSIS + "/$defs/Evidence/oneOf": "INVALID_EVIDENCE_SOURCE",
    ANALYSIS + "/$defs/Evidence/if": "INVALID_EVIDENCE_SOURCE",
    ANALYSIS + "/$defs/Evidence/then/not": "INVALID_EVIDENCE_SOURCE",
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
    assert {
        "/properties/name/pattern": error_map[base + "/properties/name/pattern"],
        "/oneOf": error_map[base + "/oneOf"],
        "/oneOf/1/required": error_map[base + "/oneOf/1/required"],
        "/if": error_map[base + "/if"],
        "/then/required": error_map[base + "/then/required"],
    } == {
        "/properties/name/pattern": "INVALID_ID",
        "/oneOf": "INVALID_DECLARATION_SOURCE",
        "/oneOf/1/required": "INVALID_DECLARATION_SOURCE",
        "/if": "URL_WITHOUT_COMMIT",
        "/then/required": "URL_WITHOUT_COMMIT",
    }


@pytest.mark.parametrize("old, new, message", UNCODED.values(), ids=UNCODED)
def test_a_constraint_without_a_code_fails(tmp_path, old, new, message):
    assert old in SCRATCH
    with pytest.raises(ValueError, match=message):
        build_error_map(*scratch_schema(tmp_path, SCRATCH.replace(old, new, 1)))


def test_a_code_that_is_not_a_schema_code_fails(tmp_path):
    """Every code the schema names is a schema-layer rule of §9: here, a validator-layer one."""
    schema, view = scratch_schema(
        tmp_path, SCRATCH.replace("rule: INVALID_ID", "rule: UNKNOWN_OPTION")
    )
    with pytest.raises(ValueError, match="UNKNOWN_OPTION"):
        build_catalogue(specification(), [(schema, view)])


# --- absolute_keyword_location, where jsonschema's paths need resolving ---

DOCUMENT = {
    "spec_version": "0.1.0",
    "outputs": {"o": {"type": "metric", "format": "csv"}},
}

LOCATED = {
    "oneOf and its branches": (
        {**DOCUMENT, "analyses": {"a": {}}},
        {
            ("/analyses/a", ANALYSIS + DECLARATION + "/oneOf"),
            ("/analyses/a", ANALYSIS + DECLARATION + "/oneOf/0/required"),
            ("/analyses/a", ANALYSIS + DECLARATION + "/oneOf/1/required"),
        },
    ),
    "then, after an if": (
        {**DOCUMENT, "analyses": {"a": {"url": "https://example.org/repo"}}},
        {("/analyses/a", ANALYSIS + DECLARATION + "/then/required")},
    ),
    "then/not, in a list item": (
        {
            **DOCUMENT,
            "findings": {
                "f": {"claim": "c", "evidence": [{"artifact": "o", "version": 2}]}
            },
        },
        {("/findings/f/evidence/0", ANALYSIS + "/$defs/Evidence/then/not")},
    ),
    "a map's propertyNames": (
        {**DOCUMENT, "outputs": {"O": {"type": "metric", "format": "csv"}}},
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
        {**DOCUMENT, "outputs": {"o": {"type": "metric"}}},
        {("/outputs/o", ANALYSIS + "/$defs/Output__identifier_optional/required")},
    ),
    "an enum through a $ref with a sibling": (
        {**DOCUMENT, "outputs": {"o": {"type": "movie", "format": "csv"}}},
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
