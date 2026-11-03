"""The rule catalogue of `docs/specification.md` (its section 9) against the fixtures: every code once, every fixture's rule in it, every schema rule with a fixture."""

import re
from collections import Counter

from .conftest import REPO_ROOT, fixture_header, fixtures, load_yaml

SPECIFICATION = REPO_ROOT / "docs" / "specification.md"
CONFORMANCE = "## 9. Conformance"
LAYERS = ["parse and schema", "validator", "check", "runner"]
_ROW = re.compile(r"\| `([A-Z][A-Z_]*)` \|")
_REFERENCE_LINK = re.compile(r"\]\(elements/([^)#]+)\.md(?:#[^)]*)?\)")
SCHEMA_MODULES = [REPO_ROOT / "src" / "astra" / "schema" / f"{name}.yaml" for name in ("types", "analysis", "insight", "provenance")]


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
            assert heading is not None, f"a rule row comes before the first subheading: {line}"
            codes[heading].append(row[1])
    return codes


def all_codes() -> list[str]:
    return [code for codes in catalogue().values() for code in codes]


def test_catalogue_has_one_table_per_layer():
    found = catalogue()
    assert list(found) == LAYERS
    assert [layer for layer, codes in found.items() if not codes] == []


def test_catalogue_codes_are_unique():
    assert [code for code, n in Counter(all_codes()).items() if n > 1] == []


def test_every_fixture_rule_is_in_the_catalogue():
    rules = {fixture_header(path)[0] for path in fixtures("invalid")}
    assert sorted(rules - set(all_codes())) == []


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
        pages.update("".join(part[:1].upper() + part[1:] for part in name.split("_")) for name in module.get("types") or {})
    return pages


def test_reference_links_name_schema_classes():
    """Every `elements/<Class>.md` link names a class, enum or type of the four schema modules (or the index)."""
    linked = set(_REFERENCE_LINK.findall(SPECIFICATION.read_text(encoding="utf-8")))
    assert linked
    assert sorted(linked - reference_pages()) == []
