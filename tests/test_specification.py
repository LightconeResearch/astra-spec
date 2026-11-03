"""`docs/specification.md` against the fixtures and the contract.

Its rule catalogue (section 9), read by `tools/rules.py`'s extractor, the one parser of it: every layer's table, every
code once, every fixture's rule a parse or schema code in it, and every parse and schema code with a fixture and a
loader error or a place in the schema that enforces it. Its links to the schema reference, and its examples: every
whole document among them is valid.
"""

import json
import re
from collections import Counter

import pytest
from rules import extract_rules

from .conftest import (
    PARSE_ERRORS,
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
_FENCE = re.compile(r"^```(yaml|json)\n(.*?)^```$", re.MULTILINE | re.DOTALL)
EXAMPLE_ROOTS = {"yaml": "Analysis", "json": "ProvenanceRecord"}
"""The document a whole example in each language is: an `astra.yaml` in YAML, a record in JSON (section 3)."""
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
    """Each parse code has its loader error, and each schema code a place in the schema that enforces it (R24, D13)."""
    enforced = set(rules_catalogue()["errors"].values())
    assert (sorted(PARSE_ERRORS), sorted(enforced)) == (
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
