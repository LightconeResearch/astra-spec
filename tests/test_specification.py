"""`docs/specification.md` against the fixtures and the contract.

Its rule catalogue (section 9): every code once, every fixture's rule a parse or schema code in it, every parse and
schema code with a fixture and with the loader error or JSON Schema keywords the harness checks it by. Its links to
the schema reference, and its examples: every whole document among them is valid.
"""

import json
import re
from collections import Counter

import pytest

from .conftest import (
    PARSE_ERRORS,
    REPO_ROOT,
    SCHEMA_KEYWORDS,
    fixture_header,
    fixtures,
    load_yaml,
    load_yaml_text,
    validator,
)

SPECIFICATION = REPO_ROOT / "docs" / "specification.md"
CONFORMANCE = "## 9. Conformance"
LAYERS = ["parse and schema", "validator", "check", "runner"]
_ROW = re.compile(r"\| `([A-Z][A-Z_]*)` \|")
_REFERENCE_LINK = re.compile(r"\]\(elements/([^)#]+)\.md(?:#[^)]*)?\)")
_FENCE = re.compile(r"^```(yaml|json)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
EXAMPLE_ROOTS = {"yaml": "Analysis", "json": "ProvenanceRecord"}
"""The document a whole example in each language is: an `astra.yaml` in YAML, a record in JSON (section 3)."""
SCHEMA_MODULES = [
    REPO_ROOT / "src" / "astra" / "schema" / f"{name}.yaml"
    for name in ("types", "analysis", "insight", "provenance")
]


def catalogue() -> dict[str, list[str]]:
    """`{subheading: [CODE, …]}`, from the table rows of `## 9. Conformance` up to the next `## ` heading."""
    lines = SPECIFICATION.read_text(encoding="utf-8").splitlines()
    assert CONFORMANCE in lines, f"{SPECIFICATION.name} has no '{CONFORMANCE}' heading"
    codes: dict[str, list[str]] = {}
    heading = None
    for line in lines[lines.index(CONFORMANCE) + 1 :]:
        if line.startswith("## "):
            break
        if line.startswith("### "):
            heading = line[len("### ") :]
            codes[heading] = []
        elif (row := _ROW.match(line)) is not None:
            assert heading is not None, (
                f"a rule row comes before the first subheading: {line}"
            )
            codes[heading].append(row[1])
    return codes


def all_codes() -> list[str]:
    return [code for codes in catalogue().values() for code in codes]


def parse_and_schema_layers() -> dict[str, str]:
    """`{CODE: layer}` from the Layer column of the parse and schema table."""
    lines = SPECIFICATION.read_text(encoding="utf-8").splitlines()
    start = lines.index("### parse and schema", lines.index(CONFORMANCE))
    layers = {}
    for line in lines[start + 1 :]:
        if line.startswith("#"):
            break
        if (row := _ROW.match(line)) is not None:
            layers[row[1]] = line.split(" | ")[1]
    return layers


def test_catalogue_has_one_table_per_layer():
    found = catalogue()
    assert list(found) == LAYERS
    assert [layer for layer, codes in found.items() if not codes] == []


def test_catalogue_codes_are_unique():
    assert [code for code, n in Counter(all_codes()).items() if n > 1] == []


def test_every_fixture_rule_is_in_the_catalogue():
    """Each invalid fixture breaks a parse or schema rule: the other layers need more than one document."""
    rules = {fixture_header(path)[0] for path in fixtures("invalid")}
    assert sorted(rules - set(catalogue()["parse and schema"])) == []


def test_harness_checks_every_parse_and_schema_code():
    """Each parse code has its loader error, and each schema code its JSON Schema keywords (Ruling R24)."""
    parse = [
        code for code, layer in parse_and_schema_layers().items() if layer == "parse"
    ]
    schema = [
        code for code, layer in parse_and_schema_layers().items() if layer == "schema"
    ]
    assert (sorted(PARSE_ERRORS), sorted(SCHEMA_KEYWORDS)) == (
        sorted(parse),
        sorted(schema),
    )


def test_every_schema_rule_has_a_fixture():
    rules = {fixture_header(path)[0] for path in fixtures("invalid")}
    assert sorted(set(catalogue()["parse and schema"]) - rules) == []


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


def examples() -> list[tuple[str, object]]:
    """`(language, document)` for every fenced YAML or JSON block of the specification, read as its kind of file is."""
    blocks = _FENCE.findall(SPECIFICATION.read_text(encoding="utf-8"))
    return [
        (language, json.loads(text) if language == "json" else load_yaml_text(text))
        for language, text in blocks
    ]


WHOLE_EXAMPLES = [
    (language, doc)
    for language, doc in examples()
    if isinstance(doc, dict) and "spec_version" in doc
]
"""The examples that are whole documents, with a top-level `spec_version`; the others are fragments."""


def test_specification_has_whole_examples():
    """Both kinds of document appear whole at least once, so the next test checks something."""
    assert {language for language, _ in WHOLE_EXAMPLES} == set(EXAMPLE_ROOTS)


@pytest.mark.parametrize(
    "language, doc",
    WHOLE_EXAMPLES,
    ids=[f"{language}-{n}" for n, (language, _) in enumerate(WHOLE_EXAMPLES)],
)
def test_every_whole_example_is_valid(language, doc):
    v = validator(EXAMPLE_ROOTS[language])
    assert [f"{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(doc)] == []
