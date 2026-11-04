"""`docs/specification.md` against the fixtures and the contract.

Its rule catalogue (section 9), read by `tools/rules.py`'s extractor, the one parser of it: every layer's table, every
code once, every fixture's rule a parse or schema code in it, and every parse and schema code with a fixture and a
loader error or a place in the schema that enforces it. Its links to the schema reference, and every example block:
whole documents validated, marked fragments validated over a stub, and the `rules.json` excerpt a subset of the
generated file. Section 4's ABNF is matched with the named types' patterns in `test_grammar.py`.
"""

import json
import re
from collections import Counter
from typing import Any, NamedTuple

import pytest
from markdown_it import MarkdownIt
from markdown_it.token import Token
from rules import extract_rules

from .conftest import (
    PARSE_CODES,
    REPO_ROOT,
    fixture_header,
    fixtures,
    load_yaml,
    load_yaml_text,
    rules_catalogue,
    validator,
)

SPECIFICATION = REPO_ROOT / "docs" / "specification.md"
LAYERS = ["parse", "schema", "validator", "check", "runner"]
_REFERENCE_LINK = re.compile(r"\]\(elements/([^)#]+)\.md(?:#[^)]*)?\)")
EXAMPLE_ROOTS = {"yaml": "Analysis", "json": "ProvenanceRecord"}
"""The document a whole example in each language is: an `astra.yaml` in YAML, a record in JSON (section 3)."""

FRAGMENT = "<!-- fragment: Analysis -->"
EXCERPT = "<!-- excerpt: rules.json -->"
MARKERS = {FRAGMENT: "yaml", EXCERPT: "json"}
"""The comments that mark a block as other than a whole document, each with the language of the blocks it marks: a
piece of an `astra.yaml`, and an abridged `rules.json`. A marker is on the line before its block."""

_MARKER_LIKE = re.compile(r"<!--[ \t]*(?:fragment|excerpt)\b")

FRAGMENT_STUB = {
    "spec_version": "0.1.0",
    "outputs": {"stub": {"type": "metric", "format": "json"}},
}
"""The `astra.yaml` a fragment is validated over."""

SCHEMA_MODULES = [
    REPO_ROOT / "src" / "astra" / "schema" / f"{name}.yaml"
    for name in ("types", "analysis", "insight", "provenance")
]


def catalogue() -> list[dict]:
    """The rules of `## 9. Conformance`, in order, as `tools/rules.py` extracts them."""
    return extract_rules(SPECIFICATION.read_text(encoding="utf-8"))


def codes(*layers: str) -> list[str]:
    """The codes of the catalogue's rules in `layers`, in order."""
    return [rule["code"] for rule in catalogue() if rule["layer"] in layers]


def test_catalogue_has_every_layer_in_order():
    found = [rule["layer"] for rule in catalogue()]
    assert sorted(set(found), key=found.index) == LAYERS


def test_catalogue_codes_are_unique():
    assert [code for code, n in Counter(codes(*LAYERS)).items() if n > 1] == []


def test_every_fixture_rule_is_in_the_catalogue():
    """Each invalid fixture breaks a parse or schema rule: the other layers need more than one document."""
    rules = {fixture_header(path)[0] for path in fixtures("invalid")}
    assert sorted(rules - set(codes("parse", "schema"))) == []


def test_harness_checks_every_parse_and_schema_code():
    """Each parse code is one `parse_code` gives, and each schema code has a place in the schema that enforces it (R24, D13)."""
    enforced = set(rules_catalogue()["errors"].values())
    assert (sorted(PARSE_CODES), sorted(enforced)) == (
        sorted(codes("parse")),
        sorted(codes("schema")),
    )


def test_every_schema_rule_has_a_fixture():
    rules = {fixture_header(path)[0] for path in fixtures("invalid")}
    assert sorted(set(codes("parse", "schema")) - rules) == []


def reference_pages() -> set[str]:
    """The pages `gen-doc` makes for the schema's elements: each class and enum by its name, each type in UpperCamelCase."""
    pages = {"index"}
    for path in SCHEMA_MODULES:
        module = load_yaml(path)
        pages.update(module.get("classes") or {})
        pages.update(module.get("enums") or {})
        pages.update(
            "".join(part[:1].upper() + part[1:] for part in name.split("_"))
            for name in module.get("types") or {}
        )
    return pages


def test_reference_links_name_schema_classes():
    """Every `elements/<Class>.md` link names a class, enum or type of the four schema modules (or the index)."""
    linked = set(_REFERENCE_LINK.findall(SPECIFICATION.read_text(encoding="utf-8")))
    assert linked
    assert sorted(linked - reference_pages()) == []


class Example(NamedTuple):
    """A fenced YAML or JSON block of the specification."""

    line: int
    """The line of its opening fence, from 1."""
    language: str
    marker: str | None
    """The comment on the line before it, if that is a marker, as written."""
    document: Any
    """Its text, read as its kind of file is."""


def _tokens() -> list[Token]:
    return MarkdownIt("commonmark").parse(SPECIFICATION.read_text(encoding="utf-8"))


def _language(fence: Token) -> str:
    """The language of a fenced block: the first word of its info string."""
    return fence.info.split()[0] if fence.info.strip() else ""


def examples() -> list[Example]:
    """Every fenced YAML or JSON block of the specification, with the marker before it, if any."""
    tokens = _tokens()
    found = []
    for i, token in enumerate(tokens):
        if token.type != "fence" or _language(token) not in EXAMPLE_ROOTS:
            continue
        before = tokens[i - 1] if i else None
        marker = (
            before.content.strip()
            if before is not None
            and before.type == "html_block"
            and _MARKER_LIKE.match(before.content)
            else None
        )
        text = token.content
        document = (
            json.loads(text) if _language(token) == "json" else load_yaml_text(text)
        )
        found.append(Example(token.map[0] + 1, _language(token), marker, document))
    return found


EXAMPLES = examples()

WHOLE_EXAMPLES = [example for example in EXAMPLES if example.marker is None]
"""The examples that are whole documents: every block without a marker."""

FRAGMENTS = [example for example in EXAMPLES if example.marker == FRAGMENT]

EXCERPTS = [example for example in EXAMPLES if example.marker == EXCERPT]


def _id(example: Example) -> str:
    return f"{example.language}-line-{example.line}"


def test_every_marker_marks_the_block_after_it():
    """A comment that looks like a marker is one of `MARKERS`, on the line before a block in that marker's language.

    It is a block of its own, so that it is the token just before the fence, and it is nowhere else.
    """
    tokens = _tokens()
    problems, markers = [], 0
    for i, token in enumerate(tokens):
        if token.type != "html_block" or not _MARKER_LIKE.match(token.content):
            continue
        markers += 1
        marker, line = token.content.strip(), token.map[0] + 1
        after = tokens[i + 1] if i + 1 < len(tokens) else None
        if marker not in MARKERS:
            problems.append(f"line {line}: {marker} is not a marker")
        elif after is None or after.type != "fence" or after.map[0] != token.map[1]:
            problems.append(f"line {line}: {marker} is not on the line before a block")
        elif _language(after) != MARKERS[marker]:
            problems.append(
                f"line {line}: {marker} is before a {_language(after)!r} block, not {MARKERS[marker]}"
            )
    text = SPECIFICATION.read_text(encoding="utf-8")
    if len(_MARKER_LIKE.findall(text)) != markers:
        problems.append("a marker that isn't a block of its own, on a line by itself")
    assert problems == []


def test_every_example_is_whole_or_marked():
    """A YAML or JSON block is a whole document, with a top-level `spec_version` and no marker, or it is marked."""
    problems = []
    for example in EXAMPLES:
        whole = (
            isinstance(example.document, dict) and "spec_version" in example.document
        )
        if example.marker is None and not whole:
            problems.append(f"line {example.line}: no `spec_version`, and no marker")
        if example.marker is not None and whole:
            problems.append(
                f"line {example.line}: a whole document, marked {example.marker}"
            )
    assert problems == []


def test_specification_has_whole_examples():
    """Both kinds of document appear whole at least once, so the next test checks something."""
    assert {example.language for example in WHOLE_EXAMPLES} == set(EXAMPLE_ROOTS)


@pytest.mark.parametrize("example", WHOLE_EXAMPLES, ids=_id)
def test_every_whole_example_is_valid(example):
    v = validator(EXAMPLE_ROOTS[example.language])
    assert [
        f"{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(example.document)
    ] == []


@pytest.mark.parametrize("example", FRAGMENTS, ids=_id)
def test_every_fragment_is_valid_over_the_stub(example):
    """The fragment's keys replace the stub's (its own `outputs` replace the stub output), and the result is valid.

    That checks the schema layer only: a fragment can name what the stub doesn't declare.
    """
    assert isinstance(example.document, dict)
    document = {**FRAGMENT_STUB, **example.document}
    v = validator("Analysis")
    assert [
        f"{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(document)
    ] == []


@pytest.mark.parametrize("example", EXCERPTS, ids=_id)
def test_the_rules_excerpt_is_a_subset_of_the_generated_file(example):
    """Each `errors` entry of the excerpt is one of the committed `rules.json`; each rule equals the committed rule with
    its code, and they come in catalogue order. Its `$comment` is left out: the version stamped in it varies."""
    excerpt, generated = example.document, rules_catalogue()
    assert isinstance(excerpt, dict)
    assert sorted(excerpt.keys() - {"$comment"} - {"errors", "rules"}) == []
    errors = excerpt.get("errors", {})
    assert {
        key: code
        for key, code in errors.items()
        if generated["errors"].get(key) != code
    } == {}
    order = [rule["code"] for rule in generated["rules"]]
    by_code = dict(zip(order, generated["rules"]))
    rules = excerpt.get("rules", [])
    assert [rule for rule in rules if by_code.get(rule.get("code")) != rule] == []
    positions = [order.index(rule["code"]) for rule in rules]
    assert positions == sorted(set(positions))
