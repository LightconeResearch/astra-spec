"""`rules.json`: the rules extracted from the codes tables of the specification's Part II, and the error map derived from
the schema (design D13).

The extractor is strict, so it is tested on small specifications, one per way a codes table or a note can be malformed;
so is the All rules page, which reads them. The committed `rules.json` holds every rule of the specification in order,
and a code for every keyword of the three JSON Schemas whose error can make an instance fail (spec Annex D), each a
schema-layer code. `absolute_keyword_location` is checked where `jsonschema`'s paths need resolving.
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
from markdown_it import MarkdownIt
from rules import (
    build_catalogue,
    build_error_map,
    extract_notes,
    extract_rules,
    json_pointer,
)
from rules_page import anchor, read_specification, render_rules_page

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


INPUTS_TABLE = """\
| Code | Layer | Level | Rule |
|---|---|---|---|
| `LOOSE_PIN` | validator | SHOULD | No input has a pin |
"""

SECTIONS = (
    """\
# A specification

## Part I: How it works

### 1. What it is

| Layer | Who checks it |
|---|---|
| parse | A loader |

## Part II: The specification

### 5. The astra.yaml file

An `astra.yaml` file is YAML.

| Code | Layer | Level | Rule |
|---|---|---|---|
| `BAD_ID` | schema | MUST | Every `id` matches the [*id* grammar](#c-grammars) |
| `EMPTY_MAP` | schema | MUST | No map is empty |

### 6. Names

Names have no codes.

### 7. Inputs

"""
    + INPUTS_TABLE
    + """
### 19. Records

Recommendation: branches that hold records SHOULD be merged, not
squashed or rebased.

### 20. Checking results

| Code | Layer | Level | Rule | Status when broken |
|---|---|---|---|---|
| `NO_RECORD` | check | MUST | Every planned result has a record | `missing` |

Permission: a checker MAY stop at the first [`NO_RECORD`](#20-checking-results).

## Glossary

- **tracked:** in git's index.

## Part III: For tool builders

### A. Reading files

An `astra.yaml` file is read as YAML 1.2.
"""
)
"""A small specification: codes tables in §5, §7 and §20 of Part II, none in §6, a table that isn't a
codes table in Part I, a recommendation in §19 and a permission after §20's table. Its lines are numbered from 1:
§5's table starts at line 17, §7's at line 28 and §20's at line 39."""


def test_section_tables_are_read_in_document_order():
    """Every row of Part II's codes tables, in order, with its section as its source; links reduced to their text."""
    assert extract_rules(SECTIONS) == [
        {
            "code": "BAD_ID",
            "layer": "schema",
            "level": "MUST",
            "statement": "Every `id` matches the *id* grammar",
            "source": "§5 The astra.yaml file",
        },
        {
            "code": "EMPTY_MAP",
            "layer": "schema",
            "level": "MUST",
            "statement": "No map is empty",
            "source": "§5 The astra.yaml file",
        },
        {
            "code": "LOOSE_PIN",
            "layer": "validator",
            "level": "SHOULD",
            "statement": "No input has a pin",
            "source": "§7 Inputs",
        },
        {
            "code": "NO_RECORD",
            "layer": "check",
            "level": "MUST",
            "statement": "Every planned result has a record",
            "status": "`missing`",
            "source": "§20 Checking results",
        },
    ]


def codes_table(code: str, layer: str = "validator") -> str:
    """A codes table of one rule, `code`, in `layer`."""
    return (
        "| Code | Layer | Level | Rule |\n|---|---|---|---|\n"
        f"| `{code}` | {layer} | MUST | Nothing is out of place |\n"
    )


MALFORMED_SECTIONS = {
    "a table in Part I": (
        "| Layer | Who checks it |",
        "| Code | Who checks it |",
        r"^line 7: a codes table .* must be in a ### section of Part II",
    ),
    "a table in Part II before its first section": (
        "## Part II: The specification\n\n",
        "## Part II: The specification\n\n" + codes_table("EARLY") + "\n",
        r"^line 13: a codes table .* must be in a ### section of Part II",
    ),
    "a table in the glossary": (
        "- **tracked:** in git's index.\n",
        "- **tracked:** in git's index.\n\n" + codes_table("LATE"),
        r"^line 49: a codes table .* must be in a ### section of Part II",
    ),
    "a table in Part III": (
        "is read as YAML 1.2.\n",
        "is read as YAML 1.2.\n\n" + codes_table("LATE", "parse"),
        r"^line 55: a codes table .* must be in a ### section of Part II",
    ),
    "two tables in one section": (
        INPUTS_TABLE,
        INPUTS_TABLE + "\n" + codes_table("EXTRA_RULE"),
        r"^line 32, ### 7\. Inputs: a second codes table, but a section has at most one",
    ),
    "a table followed by a paragraph": (
        INPUTS_TABLE,
        INPUTS_TABLE + "\nInputs are files.\n",
        r"^line 32, ### 7\. Inputs: a paragraph follows the codes table of line 28, which must be the section's last"
        r" block",
    ),
    "a table followed by a list": (
        INPUTS_TABLE,
        INPUTS_TABLE + "\n- Inputs are files.\n",
        r"^line 32, ### 7\. Inputs: a bullet list follows the codes table of line 28",
    ),
    "a table followed by a heading": (
        INPUTS_TABLE,
        INPUTS_TABLE + "\n#### More on inputs\n",
        r"^line 32, ### 7\. Inputs: a heading follows the codes table of line 28",
    ),
    "a table with a Source column": (
        INPUTS_TABLE,
        INPUTS_TABLE.replace(
            "| Rule |\n|---|---|---|---|", "| Rule | Source |\n|---|---|---|---|---|"
        ).replace("a pin |", "a pin | 0003 |"),
        r"^line 28, ### 7\. Inputs: a codes table's columns are Code, Layer, Level and Rule, and Status when broken"
        r" after them in a table of check rules, not Code, Layer, Level, Rule, Source",
    ),
    "columns out of order": (
        INPUTS_TABLE,
        INPUTS_TABLE.replace("| Layer | Level |", "| Level | Layer |").replace(
            "| validator | SHOULD |", "| SHOULD | validator |"
        ),
        r"^line 28, ### 7\. Inputs: a codes table's columns are .*, not Code, Level, Layer, Rule$",
    ),
    "a check row in a four-column table": (
        "| `LOOSE_PIN` | validator |",
        "| `LOOSE_PIN` | check |",
        r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: its layer is check, but its table has no Status when broken"
        r" column",
    ),
    "a five-column table with a validator row": (
        "| `NO_RECORD` | check |",
        "| `NO_RECORD` | validator |",
        r"^line 41, ### 20\. Checking results, row `NO_RECORD`: its layer is validator, but only check rows are in a"
        r" table with a Status when broken column",
    ),
    "an unknown layer": (
        "| `LOOSE_PIN` | validator |",
        "| `LOOSE_PIN` | semantic |",
        r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: unknown layer 'semantic': a layer is parse, schema, validator,"
        r" check or runner",
    ),
    "a MAY row on a validator": (
        "| `LOOSE_PIN` | validator | SHOULD |",
        "| `LOOSE_PIN` | validator | MAY |",
        r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: unknown level 'MAY': a level is MUST or SHOULD",
    ),
    "a MAY row on a runner": (
        "| `LOOSE_PIN` | validator | SHOULD |",
        "| `LOOSE_PIN` | runner | MAY |",
        r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: unknown level 'MAY': a level is MUST or SHOULD",
    ),
    "a keyword that contradicts the level": (
        "No input has a pin",
        "No input MUST have a pin",
        r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: its rule says MUST, which contradicts its level, SHOULD",
    ),
    "a duplicate code across sections": (
        "| `LOOSE_PIN` |",
        "| `BAD_ID` |",
        r"^line 30, ### 7\. Inputs, row `BAD_ID`: the code BAD_ID is already the code of the row at line 19",
    ),
    "a code not in a code span": (
        "| `LOOSE_PIN` |",
        "| LOOSE_PIN |",
        r"^line 30, ### 7\. Inputs, row LOOSE_PIN: the Code cell must be one code span",
    ),
    "an empty cell": (
        "| No input has a pin |",
        "|  |",
        r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: its Rule cell is empty",
    ),
    "an extra cell": (
        "| No input has a pin |",
        "| No input has a pin | x |",
        r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: it has 5 cells, but the table has 4 columns",
    ),
    "two sentences in a rule": (
        "No input has a pin",
        "No input has a pin. A pin is ignored",
        r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: its Rule cell has more than one sentence",
    ),
    "a code not in capitals": (
        "| `LOOSE_PIN` |",
        "| `Loose_pin` |",
        r"^line 30, ### 7\. Inputs, row `Loose_pin`: the Code cell must be one code span",
    ),
    "a missing cell": (
        "| SHOULD | No input has a pin |",
        "| No input has a pin |",
        r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: it has 3 cells, but the table has 4 columns",
    ),
    "a quoted row with an extra cell": (
        INPUTS_TABLE,
        quoted(
            INPUTS_TABLE.replace("| No input has a pin |", "| No input has a pin | x |")
        ),
        r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: it has 5 cells, but the table has 4 columns",
    ),
    "an unknown level": (
        "| `LOOSE_PIN` | validator | SHOULD |",
        "| `LOOSE_PIN` | validator | Should |",
        r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: unknown level 'Should': a level is MUST or SHOULD",
    ),
    "MAY in a rule": (
        "No input has a pin",
        "No input MAY have a pin",
        r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: its rule says MAY, which contradicts its level, SHOULD",
    ),
    "a keyword in a code span that contradicts the level": (
        "Every planned result has a record |",
        "Every planned result has a record (`SHOULD`) |",
        r"^line 41, ### 20\. Checking results, row `NO_RECORD`: its rule says SHOULD, which contradicts its level, MUST",
    ),
    "a keyword against a code span": (
        "Every planned result has a record |",
        "Every planned result has a record, see`SHOULD` |",
        r"^line 41, ### 20\. Checking results, row `NO_RECORD`: its rule says SHOULD",
    ),
    "a keyword against a link": (
        "Every planned result has a record |",
        "Every planned result has a [record](#a)SHOULD |",
        r"^line 41, ### 20\. Checking results, row `NO_RECORD`: its rule says SHOULD",
    ),
    **{
        f"a keyword split by {split}": (
            "No input has a pin",
            f"No input {written} have a pin",
            r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: its rule says MUST, which contradicts its level, SHOULD",
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
    "two sentences in a rule, after a closing bracket": (
        "Every planned result has a record |",
        "Every planned result has a record (see above.) It is valid |",
        r"^line 41, ### 20\. Checking results, row `NO_RECORD`: its Rule cell has more than one sentence",
    ),
    "two sentences in a rule, the mark in emphasis": (
        "No input has a pin",
        "No input has a *pin.* It may",
        r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: its Rule cell has more than one sentence",
    ),
    "an escape lost when written back": (
        "No input has a pin",
        r"No \*input\* has a pin",
        r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: its Rule cell can't be written back",
    ),
    "an image in a cell": (
        "No input has a pin",
        "No input has a ![pin](pin.png)",
        r"^line 30, ### 7\. Inputs, row `LOOSE_PIN`: its Rule cell holds a image",
    ),
    "a section heading without its number": (
        "### 7. Inputs",
        "### Inputs",
        r"^line 26, ### Inputs: a section with a codes table or a note is numbered, as in '### 7\. Inputs'",
    ),
    "no Part II": (
        "## Part II: The specification",
        "## Part II: Rules",
        r"^the specification must have one '## Part II: The specification' heading, not 0$",
    ),
    "two Part IIs": (
        "## Glossary",
        "## Part II: The specification",
        r"^line 45: a second '## Part II: The specification' heading, but the specification has one$",
    ),
}


@pytest.mark.parametrize(
    "old, new, message", MALFORMED_SECTIONS.values(), ids=MALFORMED_SECTIONS
)
def test_malformed_section_tables_fail(old, new, message):
    assert old in SECTIONS
    with pytest.raises(ValueError, match=message):
        extract_rules(SECTIONS.replace(old, new, 1))


def test_keywords_that_agree_with_the_level_are_allowed():
    """A keyword of the rule's own level is fine, and a code that contains a keyword's letters is not one."""
    rule = "No input SHOULD have a pin, as `MISSING_REQUIRED_OPTION` says"
    text = SECTIONS.replace("No input has a pin", rule)
    (found,) = [r for r in extract_rules(text) if r["code"] == "LOOSE_PIN"]
    assert found["statement"] == rule


def test_a_mark_that_ends_no_sentence_is_allowed():
    """A `.` in a code span, against one, inside a number or ending the cell leaves the rule one sentence."""
    rule = "Every `{inputs.<entry>}` names an entry of `a. b`, written in.`x` with 0.5 cores."
    text = SECTIONS.replace("Every planned result has a record", rule)
    (found,) = [r for r in extract_rules(text) if r["code"] == "NO_RECORD"]
    assert found["statement"] == rule


QUOTED = {
    "quoted": quoted(INPUTS_TABLE),
    "quoted without a space": quoted(INPUTS_TABLE, ">"),
    "indented and quoted": quoted(INPUTS_TABLE, "   > "),
    "quoted twice": quoted(INPUTS_TABLE, "> > "),
    "quoted in a list item": "1.  A list item\n\n" + quoted(INPUTS_TABLE, "    > "),
}


@pytest.mark.parametrize("table", QUOTED.values(), ids=QUOTED)
def test_a_quoted_codes_table_reads_as_the_same_rules(table):
    """A codes table in a blockquote is the same rules: its rows' cells are counted without the `>` markers, and the
    block that holds it is the section's last block."""
    assert extract_rules(SECTIONS.replace(INPUTS_TABLE, table)) == extract_rules(
        SECTIONS
    )


def test_notes_are_read():
    """A `Recommendation:` and a `Permission:`, each with its level and section: the text after the label, its links
    reduced to their text and its lines joined."""
    assert extract_notes(SECTIONS) == [
        {
            "kind": "recommendation",
            "level": "SHOULD",
            "text": "branches that hold records SHOULD be merged, not squashed or rebased.",
            "source": "§19 Records",
        },
        {
            "kind": "permission",
            "level": "MAY",
            "text": "a checker MAY stop at the first `NO_RECORD`.",
            "source": "§20 Checking results",
        },
    ]


WRONG_NOTES = {
    "a recommendation that says MAY": (
        "records SHOULD be merged",
        "records MAY be merged",
        r"^line 34, ### 19\. Records, Recommendation: it says MAY, but a Recommendation: says SHOULD once and no other"
        r" keyword",
    ),
    "a recommendation that says SHOULD twice": (
        "records SHOULD be merged, not\nsquashed",
        "records SHOULD be merged, and SHOULD NOT be\nsquashed",
        r"^line 34, ### 19\. Records, Recommendation: it says SHOULD, SHOULD, but a Recommendation: says SHOULD once",
    ),
    "a recommendation with no keyword": (
        "records SHOULD be merged",
        "records are merged",
        r"^line 34, ### 19\. Records, Recommendation: it says no keyword, but a Recommendation: says SHOULD once",
    ),
    "a permission that says SHOULD": (
        "a checker MAY stop",
        "a checker SHOULD stop",
        r"^line 43, ### 20\. Checking results, Permission: it says SHOULD, but a Permission: says MAY once",
    ),
    "a permission whose rendered text says MUST": (
        "a checker MAY stop",
        "a checker MAY stop, and MU*ST* go on,",
        r"^line 43, ### 20\. Checking results, Permission: it says MUST, but a Permission: says MAY once",
    ),
}


@pytest.mark.parametrize("old, new, message", WRONG_NOTES.values(), ids=WRONG_NOTES)
def test_a_note_with_the_wrong_keyword_fails(old, new, message):
    """Both readers fail on it, so no `rules.json` is made from such a specification."""
    assert old in SECTIONS
    text = SECTIONS.replace(old, new, 1)
    for extract in (extract_notes, extract_rules):
        with pytest.raises(ValueError, match=message):
            extract(text)


MISPLACED_NOTES = {
    "in Part I": (
        "| parse | A loader |\n",
        "| parse | A loader |\n\nPermission: a loader MAY stop.\n",
        11,
    ),
    "in the glossary": (
        "- **tracked:** in git's index.\n",
        "- **tracked:** in git's index.\n\nRecommendation: a reader SHOULD read it.\n",
        49,
    ),
}


@pytest.mark.parametrize(
    "old, new, line", MISPLACED_NOTES.values(), ids=MISPLACED_NOTES
)
def test_a_note_outside_part_ii_fails(old, new, line):
    """A note belongs to a section of Part II, where its rules are: elsewhere, both readers fail on it."""
    assert old in SECTIONS
    text = SECTIONS.replace(old, new, 1)
    message = rf"^line {line}: a (Recommendation|Permission): note must be in a ### section of Part II"
    for extract in (extract_notes, extract_rules):
        with pytest.raises(ValueError, match=message):
            extract(text)


# --- The All rules page ---

PAGE_RULES = [
    {
        "code": "LOOSE_PIN",
        "layer": "validator",
        "level": "SHOULD",
        "statement": "No input has a pin",
        "source": "§7 Inputs",
    },
    {
        "code": "BAD_ID",
        "layer": "schema",
        "level": "MUST",
        "statement": "Every `id` matches the *id* grammar",
        "source": "§5 The astra.yaml file",
    },
    {
        "code": "NO_RECORD",
        "layer": "check",
        "level": "MUST",
        "statement": "Every planned result has a record",
        "status": "`missing`",
        "source": "§20 Checking results",
    },
    {
        "code": "EMPTY_MAP",
        "layer": "schema",
        "level": "MUST",
        "statement": "No map is empty",
        "source": "§5 The astra.yaml file",
    },
]
"""Rules of three layers, out of the layers' order."""

PAGE_NOTES = [
    {
        "kind": "recommendation",
        "level": "SHOULD",
        "text": "branches that hold records SHOULD be merged, not squashed or rebased.",
        "source": "§19 Records",
    },
    {
        "kind": "permission",
        "level": "MAY",
        "text": "a runner MAY enforce `UNDECLARED_READ`.",
        "source": "§21 Runners",
    },
]


def page_blocks(page: str) -> list[tuple[str, Any]]:
    """The headings, tables and list items of a page, in order: `(h1 or h2, its text)`, `("table", (header, rows))`
    with each cell's inline Markdown, and `("li", its inline Markdown)`."""
    tokens = MarkdownIt("commonmark").enable("table").parse(page)
    blocks: list[tuple[str, Any]] = []
    for i, t in enumerate(tokens):
        if t.type == "heading_open":
            blocks.append((t.tag, tokens[i + 1].content))
        elif t.type == "table_open":
            blocks.append(("table", ([], [])))
        elif t.type == "tr_open":
            blocks[-1][1][1].append([])
        elif t.type == "inline" and tokens[i - 1].type in ("th_open", "td_open"):
            header, rows = blocks[-1][1]
            (header if tokens[i - 1].type == "th_open" else rows[-1]).append(t.content)
        elif t.type == "inline" and tokens[i - 2].type == "list_item_open":
            blocks.append(("li", t.content))
    for kind, value in blocks:
        if kind == "table":
            value[1].pop(0)  # The header's row.
    return blocks


def test_rules_page_groups_by_layer_in_order():
    """One table per layer that has rules, in the layers' order, each rule linked to its section's anchor."""
    blocks = page_blocks(render_rules_page(PAGE_RULES, []))
    assert blocks[0] == ("h1", "All rules")
    assert blocks[1:] == [
        ("h2", "Schema"),
        (
            "table",
            (
                ["Code", "Level", "Rule", "Section"],
                [
                    [
                        "`BAD_ID`",
                        "MUST",
                        "Every `id` matches the *id* grammar",
                        "[§5 The astra.yaml file](specification.md#5-the-astrayaml-file)",
                    ],
                    [
                        "`EMPTY_MAP`",
                        "MUST",
                        "No map is empty",
                        "[§5 The astra.yaml file](specification.md#5-the-astrayaml-file)",
                    ],
                ],
            ),
        ),
        ("h2", "Validator"),
        (
            "table",
            (
                ["Code", "Level", "Rule", "Section"],
                [
                    [
                        "`LOOSE_PIN`",
                        "SHOULD",
                        "No input has a pin",
                        "[§7 Inputs](specification.md#7-inputs)",
                    ]
                ],
            ),
        ),
        ("h2", "Check"),
        (
            "table",
            (
                ["Code", "Level", "Rule", "Status when broken", "Section"],
                [
                    [
                        "`NO_RECORD`",
                        "MUST",
                        "Every planned result has a record",
                        "`missing`",
                        "[§20 Checking results](specification.md#20-checking-results)",
                    ]
                ],
            ),
        ),
    ]


def test_rules_page_lists_notes():
    """After the rules, one item per recommendation or permission, linked to its section."""
    blocks = page_blocks(render_rules_page(PAGE_RULES, PAGE_NOTES))
    assert blocks[-3:] == [
        ("h2", "Recommendations and permissions"),
        (
            "li",
            "**Recommendation** ([§19 Records](specification.md#19-records)): branches that hold records SHOULD be"
            " merged, not squashed or rebased.",
        ),
        (
            "li",
            "**Permission** ([§21 Runners](specification.md#21-runners)): a runner MAY enforce `UNDECLARED_READ`.",
        ),
    ]


ANCHORS = {
    "§5 The astra.yaml file": "5-the-astrayaml-file",
    "§9 Conditions": "9-conditions",
    "§13 Pins, and outputs built per universe or once": "13-pins-and-outputs-built-per-universe-or-once",
    "§17 Analyses from another commit or repository": "17-analyses-from-another-commit-or-repository",
}
"""Sources, with the anchor the site gives their section's heading (`### 5. The astra.yaml file`)."""


@pytest.mark.parametrize("source, expected", ANCHORS.items(), ids=ANCHORS)
def test_section_links_use_the_sites_anchors(source, expected):
    assert anchor(source) == expected


def test_rules_page_reads_part_ii():
    assert read_specification(SECTIONS) == (
        extract_rules(SECTIONS),
        extract_notes(SECTIONS),
    )


def test_rules_page_reads_the_specification():
    """The page lists the rules of `rules.json`, and the specification's recommendations and permission."""
    rules, notes = read_specification(specification())
    assert rules == rules_catalogue()["rules"]
    assert [(note["kind"], note["source"]) for note in notes] == [
        ("recommendation", "§17 Analyses from another commit or repository"),
        ("recommendation", "§19 Records"),
        ("recommendation", "§21 Runners"),
        ("permission", "§21 Runners"),
    ]


# --- rules.json: the rules ---


def test_rules_json_has_its_three_parts():
    catalogue = rules_catalogue()
    assert sorted(catalogue) == ["$comment", "errors", "rules"]
    assert re.fullmatch(rf".* version (?:{VERSION})", catalogue["$comment"])


def test_rules_json_has_every_rule_of_the_specification_in_order():
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
the instance fail, and a tool drops it (spec Annex D, "From an error to its code")."""


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
    """A map key that doesn't match its key's type is `INVALID_ID`, whatever that type (an `address` included): every
    keyword under a `propertyNames`, and the `propertyNames` itself, takes the key's code. A key is never of another
    JSON type (spec Annex A), so a `propertyNames` holds only its `pattern`."""
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


# --- Annex D's filter of errors, on a validator that writes JSON Schema's standard output formats ---

NAMED = {"$defs", "properties"}
"""The keywords that hold subschemas by name: in a keyword location, the name follows the keyword."""
INDEXED = {"allOf", "anyOf", "oneOf"}
"""The keywords that hold a list of subschemas: in a keyword location, the index follows the keyword."""
LISTED_ABOVE = {"properties", "items", "$ref", "allOf", "then"}
"""The applicators that standard output lists above an error, with an `additionalProperties` that holds a schema: each
fails only through the keyword that fails inside it, and has no entry, so a tool drops them, as it drops the subschemas
listed there, and reports that keyword (spec Annex D)."""
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
    applicator, which fails only through the keyword that fails inside it (spec Annex D)."""
    steps = keyword_steps(unit["keywordLocation"])
    if not steps or steps[-1][1] is not None:
        return True
    keyword = steps[-1][0]
    return keyword in LISTED_ABOVE or (
        keyword == "additionalProperties"
        and isinstance(_schema_at(schema, unit["absoluteKeywordLocation"]), dict)
    )


def makes_the_instance_fail(unit: dict[str, Any], units: list[dict[str, Any]]) -> bool:
    """False if spec Annex D drops `unit`, of the failing `units`, as an error that doesn't make the instance fail.

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
    """`(pointer, location)` for each of the failing `units` that spec Annex D has a tool keep: not a subschema or an
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
    """`(root, document)` for a fixture: the class it is a document of, and its JSON value (spec Annex A)."""
    return path.name.split("-", 1)[0], load_fixture(path)


@pytest.mark.parametrize("output_format", ["basic", "verbose"])
@pytest.mark.parametrize("path", SCHEMA_FIXTURES, ids=lambda path: path.stem)
def test_the_error_filter_gives_the_codes_jsonschema_gives(path, output_format):
    """On jschon's standard output for each schema-layer invalid fixture, every error spec Annex D keeps has an entry, and
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
    },
    "Analysis-166-doi-directory-not-10": {
        ANALYSIS + "/$defs/Evidence/allOf/0/then/oneOf/1/required",
        # An `if` whose `then` doesn't fail, and the `not` inside it, which has no entry.
        ANALYSIS + "/$defs/Evidence/allOf/1/if",
        ANALYSIS + "/$defs/Evidence/allOf/1/if/not",
    },
}


@pytest.mark.parametrize("name, leaked", LEAKS.items(), ids=LEAKS)
def test_the_error_filter_drops_what_doesnt_make_the_instance_fail(name, leaked):
    """jschon's verbose output lists failures that don't make the instance fail, as a validator writing a standard
    format may: spec Annex D's filter drops exactly those."""
    (path,) = [path for path in SCHEMA_FIXTURES if path.stem == name]
    root, document = fixture_document(path)
    schema = load(OUTPUT_SCHEMAS[root])
    units = jschon_units(root, document, "verbose")
    assert {
        unit["absoluteKeywordLocation"]
        for unit in units
        if not listed_above(unit, schema) and not makes_the_instance_fail(unit, units)
    } == leaked
