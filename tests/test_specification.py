"""`docs/specification.md` against the fixtures and the contract.

Its rule catalogue, the codes tables at the end of Part II's sections, read by `tools/rules.py`'s extractor, the one
parser of them: every layer, every code once, each rule's source a section of Part II, every link to a code pointing at
the section whose table lists it, every fixture's rule a parse or schema code in it, and every parse and schema code
with a fixture and a loader error or a place in the schema that enforces it. Its links to the schema reference, and
every example block, once the commits, hashes and sizes it shows as placeholders are filled: whole documents validated,
marked fragments validated over a stub, and the `rules.json` excerpt a subset of the generated file. Annex C's ABNF is
matched with the named types' patterns in `test_grammar.py`.
"""

import hashlib
import json
import re
from collections import Counter
from typing import Any, NamedTuple

import pytest
from markdown_it import MarkdownIt
from markdown_it.token import Token
from rules import extract_rules
from rules_page import anchor

from .conftest import (
    GENERATED,
    PARSE_CODES,
    REPO_ROOT,
    fixture_header,
    fixtures,
    load_json,
    load_yaml,
    rules_catalogue,
    validator,
)

SPECIFICATION = REPO_ROOT / "docs" / "specification.md"
LAYERS = ["parse", "schema", "validator", "check", "runner"]
_REFERENCE_LINK = re.compile(r"\]\(elements/([^)#]+)\.md(?:#[^)]*)?\)")
EXAMPLE_ROOTS = {"yaml": "Analysis", "json": "ProvenanceRecord"}
"""The document a whole example in each language is: an `astra.yaml` in YAML, a record in JSON (Annex A)."""

FRAGMENT = "<!-- fragment: Analysis -->"
EXCERPT = "<!-- excerpt: rules.json -->"
MARKERS = {FRAGMENT: "yaml", EXCERPT: "json"}
"""The comments that mark a block as other than a whole document, each with the language of the blocks it marks: a
piece of an `astra.yaml`, and an abridged `rules.json`. A marker is on the line before its block."""

_MARKER_LIKE = re.compile(r"<!--[ \t]*(?:fragment|excerpt)\b")

FRAGMENT_STUB = {
    "spec_version": "0.1.0",
    "outputs": {
        "stub": {
            "type": "metric",
            "format": "json",
            "recipe": {"command": "python make.py '{output}'"},
        }
    },
}
"""The `astra.yaml` a fragment is validated over."""

SCHEMA_MODULES = [
    REPO_ROOT / "src" / "astra" / "schema" / f"{name}.yaml"
    for name in ("types", "analysis", "insight", "provenance")
]


def catalogue() -> list[dict]:
    """The rules of Part II's codes tables, in document order, as `tools/rules.py` extracts them."""
    return extract_rules(SPECIFICATION.read_text(encoding="utf-8"))


def codes(*layers: str) -> list[str]:
    """The codes of the catalogue's rules in `layers`, in order."""
    return [rule["code"] for rule in catalogue() if rule["layer"] in layers]


def test_catalogue_has_every_layer():
    assert sorted({rule["layer"] for rule in catalogue()}) == sorted(LAYERS)


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


def _part_ii_sections() -> list[str]:
    """The numbered `###` sections of Part II, in order, each as a rule names it: `§<n> <title>` for `### <n>. <title>`."""
    tokens = MarkdownIt("commonmark").parse(SPECIFICATION.read_text(encoding="utf-8"))
    sections, inside = [], False
    for i, token in enumerate(tokens):
        if token.type != "heading_open":
            continue
        text = tokens[i + 1].content
        if token.tag in ("h1", "h2"):
            inside = text == "Part II: The specification"
        elif token.tag == "h3" and inside:
            number, separator, title = text.partition(". ")
            if separator and number.isdigit():
                sections.append(f"§{number} {title}")
    return sections


def test_every_rule_is_stated_in_a_section_of_part_ii():
    """Each rule of `rules.json` names, as its source, a section of Part II, and the rules come in the sections' order:
    each section's codes table is at its end."""
    sections = _part_ii_sections()
    sources = [rule["source"] for rule in rules_catalogue()["rules"]]
    assert sorted({source for source in sources if source not in sections}) == []
    order = [sections.index(source) for source in sources]
    assert order == sorted(order)


CODE = re.compile(r"[A-Z][A-Z0-9_]*")
"""What a code looks like."""


class CodeSpan(NamedTuple):
    """A code span of the specification that holds what looks like a code, outside fenced blocks."""

    line: int
    """The first line of the block it is in, from 1."""
    code: str
    href: str | None
    """The target of the link it is in, if it is in one."""
    code_cell: bool
    """Whether it is the Code cell of a codes table."""


def code_spans() -> list[CodeSpan]:
    """Every code span of the specification that looks like a code, in order, with the link it is in, if any."""
    tokens = (
        MarkdownIt("commonmark")
        .enable("table")
        .parse(SPECIFICATION.read_text(encoding="utf-8"))
    )
    found = []
    codes_table, column = False, 0
    for i, token in enumerate(tokens):
        if token.type == "table_open":
            header = next(t for t in tokens[i:] if t.type == "inline")
            codes_table = header.content.strip() == "Code"
        elif token.type == "tr_open":
            column = 0
        elif token.type in ("th_open", "td_open"):
            column += 1
        elif token.type == "inline":
            in_cell = tokens[i - 1].type == "td_open"
            href = None
            for child in token.children or []:
                if child.type == "link_open":
                    href = str(child.attrs.get("href", ""))
                elif child.type == "link_close":
                    href = None
                elif child.type == "code_inline" and CODE.fullmatch(child.content):
                    found.append(
                        CodeSpan(
                            (token.map or [0])[0] + 1,
                            child.content,
                            href,
                            codes_table and in_cell and column == 1,
                        )
                    )
    return found


def _table_anchor(source: str) -> str | None:
    """The anchor of the section `source` names, or None if it names none."""
    try:
        return anchor(source)
    except ValueError:
        return None


def test_every_code_link_points_to_its_table():
    """A link whose text is a code goes to the section whose codes table lists that code, and a link to a section names
    a code of the catalogue."""
    tables = {
        rule["code"]: _table_anchor(rule["source"])
        for rule in rules_catalogue()["rules"]
    }
    problems = []
    for span in code_spans():
        if span.href is None:
            continue
        if span.code not in tables:
            if span.href.startswith("#"):
                problems.append(
                    f"line {span.line}: {span.code} is no code of the catalogue"
                )
        elif tables[span.code] is None or span.href != "#" + tables[span.code]:
            problems.append(
                f"line {span.line}: {span.code} links {span.href}, not its table's section"
            )
    assert problems == []


def test_every_code_in_the_text_is_a_link():
    """Outside the Code cell of its own table and outside fenced blocks, a code is written as a link to its table."""
    codes = {rule["code"] for rule in rules_catalogue()["rules"]}
    assert [
        f"line {span.line}: {span.code}"
        for span in code_spans()
        if span.code in codes and span.href is None and not span.code_cell
    ] == []


def reference_pages() -> set[str]:
    """The pages `gen-doc` makes for the schema's elements: each class and enum by its name, each type in UpperCamelCase,
    and each slot a class defines by its name."""
    pages = {"index"}
    for path in SCHEMA_MODULES:
        module = load_yaml(path)
        pages.update(module.get("classes") or {})
        pages.update(module.get("enums") or {})
        pages.update(
            "".join(part[:1].upper() + part[1:] for part in name.split("_"))
            for name in module.get("types") or {}
        )
        for definition in (module.get("classes") or {}).values():
            pages.update((definition or {}).get("attributes") or {})
    return pages


def test_reference_links_name_schema_classes():
    """Every `elements/<Element>.md` link names a class, enum, type or slot of the four schema modules (or the
    index)."""
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
    """Its text, its placeholders filled, read as its kind of file is."""


def _tokens() -> list[Token]:
    return MarkdownIt("commonmark").parse(SPECIFICATION.read_text(encoding="utf-8"))


def _language(fence: Token) -> str:
    """The language of a fenced block: the first word of its info string."""
    return fence.info.split()[0] if fence.info.strip() else ""


COMMIT = "0123456789abcdef0123456789abcdef01234567"
"""The commit id that fills `<commit>`."""

_HASH = re.compile(r"sha256:<hash of ([^>]*)>")
_SIZE = re.compile(r"<size of ([^>]*)>")


def fill_placeholders(text: str) -> str:
    """`text` with the placeholders an example may show filled in: `<commit>` with a commit id, `sha256:<hash of X>`
    with `sha256:` and the SHA-256 of `X`, and `<size of X>` with the length of `X`, in bytes, both of `X` in UTF-8.
    Any other `<…>` is left as it is."""
    text = text.replace("<commit>", COMMIT)
    text = _HASH.sub(
        lambda m: "sha256:" + hashlib.sha256(m[1].encode("utf-8")).hexdigest(), text
    )
    return _SIZE.sub(lambda m: str(len(m[1].encode("utf-8"))), text)


def examples() -> list[Example]:
    """Every fenced YAML or JSON block of the specification, with the marker before it, if any, its placeholders filled
    (`fill_placeholders`)."""
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
        text = fill_placeholders(token.content)
        document = load_json(text) if _language(token) == "json" else load_yaml(text)
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


PLACEHOLDER_RECORD = """\
{
  "spec_version": "0.1.0",
  "address": "output1#u1",
  "content_hash": "sha256:<hash of output1>",
  "size": <size of output1>,
  "generated_by": {
    "commit": "<commit>",
    "inputs": [
      {
        "entry": "input1",
        "content_hash": "sha256:<hash of input1>",
        "size": <size of input1>
      }
    ],
    "environment": {"iri": "urn:example:env:1"},
    "runner": {"id": "example-runner", "version": "1.2.0"}
  }
}
"""
"""A record written as an example writes one: its commit, hashes and sizes as placeholders."""


def test_placeholders_are_filled():
    """Once filled, the record is valid: a full commit id, each hash the SHA-256 of its text, each size its length."""
    record = load_json(fill_placeholders(PLACEHOLDER_RECORD))
    v = validator("ProvenanceRecord")
    assert [
        f"{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(record)
    ] == []
    assert (
        record["generated_by"]["commit"] == "0123456789abcdef0123456789abcdef01234567"
    )
    assert record["content_hash"] == "sha256:" + hashlib.sha256(b"output1").hexdigest()
    assert record["size"] == len(b"output1")
    (read,) = record["generated_by"]["inputs"]
    assert read["content_hash"] == "sha256:" + hashlib.sha256(b"input1").hexdigest()
    assert read["size"] == len(b"input1")


def test_fill_placeholders_leaves_unknown_ones():
    text = 'a: "<other>"\nb: "<hash of input1>"\nc: "sha256:<other>"\nd: "<size>"\n'
    assert fill_placeholders(text) == text


PLACEHOLDER = re.compile(r"<[^>]+>")
"""A value that is a placeholder: `<`, then anything but `>`, then `>`."""


def placeholders(value: Any) -> list[str]:
    """The strings in `value`, keys included, that are a placeholder, `<…>`, or hold `sha256:<`."""
    if isinstance(value, dict):
        return [
            found for item in [*value, *value.values()] for found in placeholders(item)
        ]
    if isinstance(value, list):
        return [found for item in value for found in placeholders(item)]
    if isinstance(value, str) and (PLACEHOLDER.fullmatch(value) or "sha256:<" in value):
        return [value]
    return []


def test_no_example_keeps_a_placeholder():
    """Every placeholder of an example is one `fill_placeholders` fills."""
    assert {
        _id(example): placeholders(example.document)
        for example in EXAMPLES
        if placeholders(example.document)
    } == {}


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


EXCERPT_LOCATION = re.compile(
    r"(https://w3id\.org/astra/[0-9]+\.[0-9]+/([a-z.]+\.schema\.json))(#.*)", re.DOTALL
)
"""An error-map key as the specification writes it: the namespace, a minor version, `/`, a schema's file name, `#` and
a JSON Pointer."""


def committed_location(key: str) -> str | None:
    """The excerpt's error-map `key` with the committed file's series in place of its minor version, which differs
    between releases (`dev/` on main), or None if `key` isn't written as the specification writes one."""
    match = EXCERPT_LOCATION.fullmatch(key)
    if match is None or not (GENERATED / match[2]).is_file():
        return None
    return (
        json.loads((GENERATED / match[2]).read_text(encoding="utf-8"))["$id"] + match[3]
    )


@pytest.mark.parametrize("example", EXCERPTS, ids=_id)
def test_the_rules_excerpt_is_a_subset_of_the_generated_file(example):
    """Each `errors` entry of the excerpt is one of the committed `rules.json`, once its key takes the committed series;
    each rule equals the committed rule with its code, and they come in catalogue order. Its `$comment` is left out: the
    version stamped in it varies."""
    excerpt, generated = example.document, rules_catalogue()
    assert isinstance(excerpt, dict)
    assert sorted(excerpt.keys() - {"$comment"} - {"errors", "rules"}) == []
    errors = excerpt.get("errors", {})
    assert {
        key: code
        for key, code in errors.items()
        if generated["errors"].get(committed_location(key)) != code
    } == {}
    order = [rule["code"] for rule in generated["rules"]]
    by_code = dict(zip(order, generated["rules"]))
    rules = excerpt.get("rules", [])
    assert [rule for rule in rules if by_code.get(rule.get("code")) != rule] == []
    positions = [order.index(rule["code"]) for rule in rules]
    assert positions == sorted(set(positions))
