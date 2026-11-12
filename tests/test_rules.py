"""`rules.json`: the rules extracted from the codes table of the specification's Rules section, and the error map
derived from the schema.

The extractor is strict, so it is tested on small specifications, one per way the codes table can be malformed. The
committed `rules.json` holds every rule of the specification in order, and a code for every keyword of the three JSON
Schemas whose error can make an instance fail, each a schema-layer code. `absolute_keyword_location` is checked where
`jsonschema`'s paths need resolving.
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
from rules import (
    build_catalogue,
    build_error_map,
    extract_rules,
    json_pointer,
)

from .conftest import (
    GENERATED,
    REPO_ROOT,
    absolute_keyword_location,
    errors,
    fixture_header,
    fixtures,
    load_fixture,
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


def quoted(table: str, prefix: str = "> ") -> str:
    """`table` in a blockquote: each of its lines after `prefix`."""
    return "".join(prefix + line for line in table.splitlines(keepends=True))


CODES_TABLE = """\
| Code | Level | Rule |
|---|---|---|
| **schema** | | |
| `BAD_ID` | MUST | Every `id` matches the [*id* grammar](#elements) |
| `BAD_ID` | MUST | A key is an id |
| `EMPTY_MAP` | MUST | No map is empty |
| ***validator, in each universe*** | | |
| `LOOSE_PIN` | SHOULD | No input has a pin |
| **check** | | |
| `NO_RECORD` | MUST | Every planned result has a record → `missing` |
"""

SPEC = (
    """\
# A specification

## Elements

| Edit | Effect |
|---|---|
| A path changes | Its results are stale |

## Rules

Each rule has a code.

"""
    + CODES_TABLE
    + """
Recommendations and a permission:

| Who | Level | Recommendation or permission |
|---|---|---|
| A checker | MAY | stop at the first `NO_RECORD` |

## Schema files

| File | What it is |
|---|---|
| `rules.json` | every rule |
"""
)
"""A small specification: a codes table in its Rules section, with four layer rows' worth of rules, one of them in
two rows, and tables that aren't a codes table before it, after it in its section, and in the next section. Its lines
are numbered from 1: the codes table starts at line 13, its rows of `BAD_ID` are lines 16 and 17, and `NO_RECORD`'s
is line 22."""


def test_the_codes_table_is_read_in_document_order():
    """Every rule of the codes table, in order, with the layer of the layer row above it: the rows of one code joined,
    links reduced to their text, and a check rule's status after its `→`."""
    assert extract_rules(SPEC) == [
        {
            "code": "BAD_ID",
            "layer": "schema",
            "level": "MUST",
            "statement": "Every `id` matches the *id* grammar; A key is an id",
        },
        {
            "code": "EMPTY_MAP",
            "layer": "schema",
            "level": "MUST",
            "statement": "No map is empty",
        },
        {
            "code": "LOOSE_PIN",
            "layer": "validator",
            "level": "SHOULD",
            "statement": "No input has a pin",
        },
        {
            "code": "NO_RECORD",
            "layer": "check",
            "level": "MUST",
            "statement": "Every planned result has a record",
            "status": "`missing`",
        },
    ]


def codes_table(code: str) -> str:
    """A codes table of one rule, `code`, in the validator layer."""
    return (
        "| Code | Level | Rule |\n|---|---|---|\n| **validator** | | |\n"
        f"| `{code}` | MUST | Nothing is out of place |\n"
    )


MALFORMED = {
    "a codes table before the Rules section": (
        "| Edit | Effect |",
        "| Code | Effect |",
        r"^line 5: a codes table .* must be in the '## Rules' section",
    ),
    "a codes table after the Rules section": (
        "| `rules.json` | every rule |\n",
        "| `rules.json` | every rule |\n\n" + codes_table("LATE"),
        r"^line 36: a codes table .* must be in the '## Rules' section",
    ),
    "two codes tables": (
        "Recommendations and a permission:\n",
        codes_table("EXTRA_RULE") + "\nRecommendations and a permission:\n",
        r"^line 24: a second codes table, but the specification has one, at line 13",
    ),
    "no Rules heading": (
        "## Rules",
        "## Rule list",
        r"^the specification must have one '## Rules' heading, not 0$",
    ),
    "two Rules headings": (
        "## Schema files",
        "## Rules",
        r"^line 30: a second '## Rules' heading, but the specification has one$",
    ),
    "no codes table": (
        "| Code | Level | Rule |",
        "| Key | Level | Rule |",
        r"^the '## Rules' section has no codes table$",
    ),
    "a Layer column": (
        "| Code | Level | Rule |\n|---|---|---|",
        "| Code | Layer | Level | Rule |\n|---|---|---|---|",
        r"^line 13: the codes table's columns are Code, Level and Rule, not Code, Layer, Level, Rule$",
    ),
    "columns out of order": (
        "| Code | Level | Rule |",
        "| Code | Rule | Level |",
        r"^line 13: the codes table's columns are Code, Level and Rule, not Code, Rule, Level$",
    ),
    "an unknown layer": (
        "| **check** |",
        "| **checker** |",
        r"^line 21, row \*\*checker\*\*: unknown layer 'checker': a layer row's first word is parse, schema,"
        r" validator, check or runner$",
    ),
    "a layer word with a digit": (
        "| **check** |",
        "| **check2** |",
        r"^line 21, row \*\*check2\*\*: unknown layer 'check2'",
    ),
    "a layer in capitals": (
        "| **check** |",
        "| **Check** |",
        r"^line 21, row \*\*Check\*\*: unknown layer 'Check'",
    ),
    "a layer row not in strong emphasis": (
        "| **check** |",
        "| check |",
        r"^line 21, row check: its Level cell is empty$",
    ),
    "a layer row in emphasis only": (
        "| **check** |",
        "| *check* |",
        r"^line 21, row \*check\*: its Level cell is empty$",
    ),
    "a layer row with text outside its strong emphasis": (
        "| **check** |",
        "| **check** rules |",
        r"^line 21, row \*\*check\*\* rules: its Level cell is empty$",
    ),
    "a layer row with a level": (
        "| **check** | | |",
        "| **check** | MUST | |",
        r"^line 21, row \*\*check\*\*: a layer row's Level and Rule cells must be empty$",
    ),
    "a rule row before any layer row": (
        "| **schema** | | |\n",
        "",
        r"^line 15, row `BAD_ID`: it comes before any layer row",
    ),
    "a MAY row": (
        "| `LOOSE_PIN` | SHOULD |",
        "| `LOOSE_PIN` | MAY |",
        r"^line 20, row `LOOSE_PIN`: unknown level 'MAY': a level is MUST or SHOULD$",
    ),
    "an unknown level": (
        "| `LOOSE_PIN` | SHOULD |",
        "| `LOOSE_PIN` | Should |",
        r"^line 20, row `LOOSE_PIN`: unknown level 'Should': a level is MUST or SHOULD$",
    ),
    "a code repeated apart": (
        "| `LOOSE_PIN` |",
        "| `BAD_ID` |",
        r"^line 20, row `BAD_ID`: the code BAD_ID is already the code of the rule at line 16: the rows of a rule are"
        r" consecutive, under one layer row$",
    ),
    "a code repeated under the next layer row": (
        "| `LOOSE_PIN` | SHOULD |",
        "| `EMPTY_MAP` | MUST |",
        r"^line 20, row `EMPTY_MAP`: the code EMPTY_MAP is already the code of the rule at line 18",
    ),
    "the rows of a rule at two levels": (
        "| `BAD_ID` | MUST | A key is an id |",
        "| `BAD_ID` | SHOULD | A key is an id |",
        r"^line 17, row `BAD_ID`: its level is SHOULD, but the row of BAD_ID at line 16 is MUST: the rows of a rule"
        r" share its level$",
    ),
    "the rows of a check rule with two statuses": (
        "| `NO_RECORD` | MUST | Every planned result has a record → `missing` |\n",
        "| `NO_RECORD` | MUST | Every planned result has a record → `missing` |\n"
        "| `NO_RECORD` | MUST | Its record is current → `stale` |\n",
        r"^line 23, row `NO_RECORD`: its status is '`stale`', but the row of NO_RECORD at line 22 gives '`missing`':"
        r" the rows of a check rule give one status$",
    ),
    "a code not in a code span": (
        "| `LOOSE_PIN` |",
        "| LOOSE_PIN |",
        r"^line 20, row LOOSE_PIN: the Code cell must be one code span",
    ),
    "a code not in capitals": (
        "| `LOOSE_PIN` |",
        "| `Loose_pin` |",
        r"^line 20, row `Loose_pin`: the Code cell must be one code span",
    ),
    "an empty cell": (
        "| No input has a pin |",
        "|  |",
        r"^line 20, row `LOOSE_PIN`: its Rule cell is empty$",
    ),
    "an extra cell": (
        "| No input has a pin |",
        "| No input has a pin | x |",
        r"^line 20, row `LOOSE_PIN`: it has 4 cells, but the table has 3 columns$",
    ),
    "a missing cell": (
        "| SHOULD | No input has a pin |",
        "| No input has a pin |",
        r"^line 20, row `LOOSE_PIN`: it has 2 cells, but the table has 3 columns$",
    ),
    "a quoted row with an extra cell": (
        CODES_TABLE,
        quoted(
            CODES_TABLE.replace("| No input has a pin |", "| No input has a pin | x |")
        ),
        r"^line 20, row `LOOSE_PIN`: it has 4 cells, but the table has 3 columns$",
    ),
    "a check row without a status": (
        "a record → `missing` |",
        "a record |",
        r"^line 22, row `NO_RECORD`: its Rule cell must have one →, followed by the status a broken check rule gives$",
    ),
    "a check row with two →": (
        "a record → `missing` |",
        "a record → `missing` → `stale` |",
        r"^line 22, row `NO_RECORD`: its Rule cell must have one →",
    ),
    "a check row whose → is in a code span": (
        "a record → `missing` |",
        "a record `→ missing` |",
        r"^line 22, row `NO_RECORD`: its Rule cell must have one →",
    ),
    "a → in emphasis": (
        "a record → `missing` |",
        "a *record → `missing`* |",
        r"^line 22, row `NO_RECORD`: its → is inside emphasis or a link$",
    ),
    "a → in a link": (
        "a record → `missing` |",
        "a [record → `missing`](#rules) |",
        r"^line 22, row `NO_RECORD`: its → is inside emphasis or a link$",
    ),
    "nothing before the →": (
        "Every planned result has a record → `missing` |",
        "→ `missing` |",
        r"^line 22, row `NO_RECORD`: its Rule cell has nothing before its →$",
    ),
    "no status after the →": (
        "a record → `missing` |",
        "a record → |",
        r"^line 22, row `NO_RECORD`: its Rule cell has no status after its →$",
    ),
    "a → in a row that isn't a check row": (
        "No input has a pin",
        "No input has a pin → `missing`",
        r"^line 20, row `LOOSE_PIN`: its Rule cell has a →, but only a check row gives a status after one$",
    ),
    "a keyword that contradicts the level": (
        "No input has a pin",
        "No input MUST have a pin",
        r"^line 20, row `LOOSE_PIN`: its rule says MUST, which contradicts its level, SHOULD$",
    ),
    "MAY in a rule": (
        "No input has a pin",
        "No input MAY have a pin",
        r"^line 20, row `LOOSE_PIN`: its rule says MAY, which contradicts its level, SHOULD$",
    ),
    "a keyword in a code span that contradicts the level": (
        "Every planned result has a record →",
        "Every planned result has a record (`SHOULD`) →",
        r"^line 22, row `NO_RECORD`: its rule says SHOULD, which contradicts its level, MUST$",
    ),
    "a keyword in the status that contradicts the level": (
        "→ `missing` |",
        "→ `missing`, as SHOULD be |",
        r"^line 22, row `NO_RECORD`: its rule says SHOULD, which contradicts its level, MUST$",
    ),
    "a keyword against a code span": (
        "Every planned result has a record →",
        "Every planned result has a record, see`SHOULD` →",
        r"^line 22, row `NO_RECORD`: its rule says SHOULD",
    ),
    "a keyword against a link": (
        "Every planned result has a record →",
        "Every planned result has a [record](#a)SHOULD →",
        r"^line 22, row `NO_RECORD`: its rule says SHOULD",
    ),
    **{
        f"a keyword split by {split}": (
            "No input has a pin",
            f"No input {written} have a pin",
            r"^line 20, row `LOOSE_PIN`: its rule says MUST, which contradicts its level, SHOULD$",
        )
        for split, written in {
            "intraword emphasis": "MU*ST*",
            "a link on part of it": "[MU](#x)ST",
            "a code span": "`MU`ST",
            "empty inline HTML": "MU<span></span>ST",
            "a soft hyphen": "MU&shy;ST",
            "a zero-width space": "MU​ST",
        }.items()
    },
    "two sentences in a rule": (
        "No input has a pin",
        "No input has a pin. A pin is ignored",
        r"^line 20, row `LOOSE_PIN`: its Rule cell has more than one sentence",
    ),
    "two sentences in a rule, after a closing bracket": (
        "Every planned result has a record →",
        "Every planned result has a record (see above.) It is valid →",
        r"^line 22, row `NO_RECORD`: its Rule cell has more than one sentence",
    ),
    "two sentences in a rule, the mark in emphasis": (
        "No input has a pin",
        "No input has a *pin.* It may",
        r"^line 20, row `LOOSE_PIN`: its Rule cell has more than one sentence",
    ),
    "an escape lost when written back": (
        "No input has a pin",
        r"No \*input\* has a pin",
        r"^line 20, row `LOOSE_PIN`: its Rule cell can't be written back",
    ),
    "an escape lost in the status": (
        "→ `missing` |",
        r"→ \*missing\* |",
        r"^line 22, row `NO_RECORD`: its status can't be written back",
    ),
    "an image in a cell": (
        "No input has a pin",
        "No input has a ![pin](pin.png)",
        r"^line 20, row `LOOSE_PIN`: its Rule cell holds a image",
    ),
}


@pytest.mark.parametrize("old, new, message", MALFORMED.values(), ids=MALFORMED)
def test_a_malformed_codes_table_fails(old, new, message):
    assert old in SPEC
    with pytest.raises(ValueError, match=message):
        extract_rules(SPEC.replace(old, new, 1))


def test_keywords_that_agree_with_the_level_are_allowed():
    """A keyword of the rule's own level is fine, and a code that contains a keyword's letters is not one."""
    rule = "No input SHOULD have a pin, as `MISSING_REQUIRED_OPTION` says"
    text = SPEC.replace("No input has a pin", rule)
    (found,) = [r for r in extract_rules(text) if r["code"] == "LOOSE_PIN"]
    assert found["statement"] == rule


def test_a_mark_that_ends_no_sentence_is_allowed():
    """A `.` in a code span, against one, inside a number or ending the cell leaves the rule one sentence."""
    rule = "Every `{inputs.<entry>}` names an entry of `a. b`, written in.`x` with 0.5 cores."
    text = SPEC.replace("No input has a pin", rule)
    (found,) = [r for r in extract_rules(text) if r["code"] == "LOOSE_PIN"]
    assert found["statement"] == rule


def test_a_status_keeps_its_markup():
    """The status is the cell's inline Markdown after the `→`, its links reduced to their text, as a statement is."""
    text = SPEC.replace(
        "→ `missing` |", "→ the [cited](#rules) result's *record* status |"
    )
    (found,) = [r for r in extract_rules(text) if r["code"] == "NO_RECORD"]
    assert (found["statement"], found["status"]) == (
        "Every planned result has a record",
        "the cited result's *record* status",
    )


def test_the_rows_of_a_check_rule_are_joined():
    """Each row of a check rule gives its part of the statement before its `→`, and the same status after it."""
    text = SPEC.replace(
        "| `NO_RECORD` | MUST | Every planned result has a record → `missing` |\n",
        "| `NO_RECORD` | MUST | Every planned result has a record → `missing` |\n"
        "| `NO_RECORD` | MUST | its record parses →  `missing` |\n",
    )
    (found,) = [r for r in extract_rules(text) if r["code"] == "NO_RECORD"]
    assert (found["statement"], found["status"]) == (
        "Every planned result has a record; its record parses",
        "`missing`",
    )


QUOTED = {
    "quoted": quoted(CODES_TABLE),
    "quoted without a space": quoted(CODES_TABLE, ">"),
    "indented and quoted": quoted(CODES_TABLE, "   > "),
    "quoted twice": quoted(CODES_TABLE, "> > "),
    "quoted in a list item": "1.  A list item\n\n" + quoted(CODES_TABLE, "    > "),
}


@pytest.mark.parametrize("table", QUOTED.values(), ids=QUOTED)
def test_a_quoted_codes_table_reads_as_the_same_rules(table):
    """A codes table in a blockquote is the same rules: its rows' cells are counted without the `>` markers."""
    assert extract_rules(SPEC.replace(CODES_TABLE, table)) == extract_rules(SPEC)


# --- rules.json: the rules ---


def test_rules_json_has_its_three_parts():
    catalogue = rules_catalogue()
    assert sorted(catalogue) == ["$comment", "errors", "rules"]
    assert re.fullmatch(rf".* version (?:{VERSION})", catalogue["$comment"])


def test_rules_json_has_every_rule_of_the_specification_in_order():
    assert rules_catalogue()["rules"] == extract_rules(specification())


def test_every_rule_has_its_fields():
    """`code`, `layer`, `level` and `statement`, and `status` exactly for the check layer."""
    common = {"code", "layer", "level", "statement"}
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
the instance fail, and a tool drops it."""


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
    + "/$defs/Option__identifier_optional/properties/requires/items/pattern": "INVALID_REFERENCE",
    ANALYSIS + "/$defs/Evidence/properties/artifact/pattern": "INVALID_REFERENCE",
    ANALYSIS
    + "/$defs/Output__identifier_optional/properties/cases/additionalProperties/pattern": "INVALID_REFERENCE",
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
    ANALYSIS
    + "/$defs/Output__identifier_optional/properties/cases/propertyNames": "INVALID_ID",
    # Patterns, by their slot
    ANALYSIS
    + "/$defs/Input__identifier_optional/properties/path/pattern": "INVALID_PATH",
    ANALYSIS + DECLARATION + "/properties/path/pattern": "INVALID_PATH",
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
    ANALYSIS
    + "/$defs/Output__identifier_optional/allOf/0/then/required": "MISSING_FIELD",
    ANALYSIS + "/$defs/Output__identifier_optional/allOf/1/if": "INVALID_SWITCH",
    ANALYSIS + "/$defs/Output__identifier_optional/allOf/3/then/not": "INVALID_SWITCH",
    # Defaults
    ANALYSIS + "/required": "MISSING_FIELD",
    ANALYSIS + "/additionalProperties": "UNKNOWN_FIELD",
    RECORD + "/$defs/Runner/additionalProperties": "UNKNOWN_FIELD",
    ANALYSIS + "/properties/tags/type": "WRONG_TYPE",
    ANALYSIS
    + "/$defs/Decision__identifier_optional/properties/options/minProperties": "EMPTY_COLLECTION",
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
    """A map key that doesn't match its key's type is `INVALID_ID`, whatever that type (an `address` included): every
    keyword under a `propertyNames`, and the `propertyNames` itself, takes the key's code. A key is never of another
    JSON type, so a `propertyNames` holds only its `pattern`."""
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
    assert {location.rsplit("/propertyNames", 1)[1] for location in keys} == {
        "",
        "/pattern",
    }
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


def test_a_default_code_that_is_not_a_schema_code_fails(tmp_path):
    """Every code a keyword takes by default is a schema-layer rule of the specification, even one no keyword of the
    schemas takes: here, `INVALID_VALUE`, which the scratch schema's keywords don't."""
    text = "".join(
        line
        for line in specification().splitlines(keepends=True)
        if not line.startswith("| `INVALID_VALUE` |")
    )
    assert text != specification()
    with pytest.raises(
        ValueError,
        match=r"^the default codes INVALID_VALUE are not schema-layer codes of the specification$",
    ):
        build_catalogue(text, [scratch_schema(tmp_path, SCRATCH)])


def test_a_code_that_is_not_a_schema_code_fails(tmp_path):
    """Every code the schema names is a schema-layer rule of the specification: here, a validator-layer one."""
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
        {
            (
                "/outputs/o",
                ANALYSIS + "/$defs/Output__identifier_optional/allOf/0/then/required",
            )
        },
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


# --- The errors that make the instance fail, on a validator that writes JSON Schema's standard output formats ---

NAMED = {"$defs", "properties"}
"""The keywords that hold subschemas by name: in a keyword location, the name follows the keyword."""
INDEXED = {"allOf", "anyOf", "oneOf"}
"""The keywords that hold a list of subschemas: in a keyword location, the index follows the keyword."""
LISTED_ABOVE = {"properties", "items", "$ref", "allOf", "then"}
"""The applicators that standard output lists above an error, with an `additionalProperties` that holds a schema: each
fails only through the keyword that fails inside it, and has no entry, so a tool drops them, as it drops the subschemas
listed there, and reports that keyword."""
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
    """True if `unit` is what standard output lists above an error: a subschema (the root, `…/allOf/0`) or an
    applicator, which fails only through the keyword that fails inside it."""
    steps = keyword_steps(unit["keywordLocation"])
    if not steps or steps[-1][1] is not None:
        return True
    keyword = steps[-1][0]
    return keyword in LISTED_ABOVE or (
        keyword == "additionalProperties"
        and isinstance(_schema_at(schema, unit["absoluteKeywordLocation"]), dict)
    )


def makes_the_instance_fail(unit: dict[str, Any], units: list[dict[str, Any]]) -> bool:
    """False if a tool drops `unit`, of the failing `units`, as an error that doesn't make the instance fail.

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


def kept_errors(
    units: list[dict[str, Any]], schema: dict[str, Any]
) -> set[tuple[str, str]]:
    """`(pointer, location)` for each of the failing `units` that a tool keeps: not a subschema or an applicator listed
    above an error, and making the instance fail.

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
    """`(root, document)` for a fixture: the class it is a document of, and its JSON value."""
    return path.name.split("-", 1)[0], load_fixture(path)


@pytest.mark.parametrize("output_format", ["basic", "verbose"])
@pytest.mark.parametrize("path", SCHEMA_FIXTURES, ids=lambda path: path.stem)
def test_the_error_filter_gives_the_codes_jsonschema_gives(path, output_format):
    """On jschon's standard output for each schema-layer invalid fixture, every error a tool keeps has an entry, and
    the `(pointer, code)` pairs are those of `jsonschema`'s errors."""
    root, document = fixture_document(path)
    error_map = rules_catalogue()["errors"]
    kept = kept_errors(
        jschon_units(root, document, output_format), load(OUTPUT_SCHEMAS[root])
    )
    assert sorted(location for _, location in kept if location not in error_map) == []
    assert {(pointer, error_map[location]) for pointer, location in kept} == {
        (pointer, error_map[location])
        for pointer, location, _ in errors(validator(root), document)
    }


SWITCH_LEAKS = {
    # The `if`s of a switch's seven rules, which an ordinary output fails.
    *(
        ANALYSIS + "/$defs/Output__identifier_optional/allOf/" + f"{n}/if" + tail
        for n in range(1, 8)
        for tail in ("", "/required")
    ),
    # The `required` inside the `not` of the `if` an ordinary output passes, which fails as the `not` holds.
    ANALYSIS + "/$defs/Output__identifier_optional/allOf/0/if/not/required",
}
"""What jschon lists, and the filter drops, for each ordinary output: the checks of a switch, which it isn't."""

LEAKS = {
    "Analysis-150-short-commit": {
        # The failing branch of a `oneOf` that passes: its entry's code would be wrong.
        ANALYSIS + DECLARATION + "/allOf/0/then/oneOf/0/required",
        # The `if`s of an import's four rules, which an ordinary universe fails.
        *(
            ANALYSIS + "/$defs/Universe__identifier_optional/allOf/" + f"{n}/if" + tail
            for n in range(4)
            for tail in ("", "/required")
        ),
        *SWITCH_LEAKS,
    },
    "Analysis-166-doi-directory-not-10": {
        ANALYSIS + "/$defs/Evidence/allOf/0/then/oneOf/1/required",
        # An `if` whose `then` doesn't fail, and the `not` inside it, which has no entry.
        ANALYSIS + "/$defs/Evidence/allOf/1/if",
        ANALYSIS + "/$defs/Evidence/allOf/1/if/not",
        *SWITCH_LEAKS,
    },
}


@pytest.mark.parametrize("name, leaked", LEAKS.items(), ids=LEAKS)
def test_the_error_filter_drops_what_doesnt_make_the_instance_fail(name, leaked):
    """jschon's verbose output lists failures that don't make the instance fail, as a validator writing a standard
    format may: a tool drops exactly those."""
    (path,) = [path for path in SCHEMA_FIXTURES if path.stem == name]
    root, document = fixture_document(path)
    schema = load(OUTPUT_SCHEMAS[root])
    units = jschon_units(root, document, "verbose")
    assert {
        unit["absoluteKeywordLocation"]
        for unit in units
        if not listed_above(unit, schema) and not makes_the_instance_fail(unit, units)
    } == leaked
