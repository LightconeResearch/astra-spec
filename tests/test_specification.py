"""`docs/specification.md` against the fixtures and the contract.

Its rule catalogue, the codes table of its Rules section, read by `tools/rules.py`'s extractor, the one parser of it:
every layer, every code once, every fixture's rule a parse or schema code in it, and every parse and schema code with a
fixture and a loader error or a place in the schema that enforces it. Its links to the field reference, if any, and
every YAML or JSON block, once the commit ids, hashes, sizes and URL it shows as placeholders are filled: whole
documents validated, the snippets of an `astra.yaml` validated over a stub, and those that leave fields out (a line
`...`) validated over it but for the fields they leave out.
"""

import hashlib
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
    load_json,
    load_yaml,
    rules_catalogue,
    validator,
)

SPECIFICATION = REPO_ROOT / "docs" / "specification.md"
LAYERS = ["parse", "schema", "validator", "check", "runner"]
_REFERENCE_LINK = re.compile(r"\]\(elements/([^)#]+)\.md(?:#[^)]*)?\)")
EXAMPLE_ROOTS = {"yaml": "Analysis", "json": "ProvenanceRecord"}
"""The document a whole example in each language is: an `astra.yaml` in YAML, a record in JSON."""

ELISION = re.compile(r"^([ \t]*)\.\.\.[ \t]*$", re.MULTILINE)
"""A line that is `...`: the snippet leaves out what would be there, such as an output's other fields."""

ELIDED_KEY = "__elided__"
"""The key a line `...` is read as, `true` at its indentation, to mark the map it leaves fields out of."""

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
"""The `astra.yaml` a snippet is validated over."""

SCHEMA_MODULES = [
    REPO_ROOT / "src" / "astra" / "schema" / f"{name}.yaml"
    for name in ("types", "analysis", "insight", "provenance")
]


def catalogue() -> list[dict]:
    """The rules of the codes table, in document order, as `tools/rules.py` extracts them."""
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
    """Each parse code is one `parse_code` gives, and each schema code has a place in the schema that enforces it."""
    enforced = set(rules_catalogue()["errors"].values())
    assert (sorted(PARSE_CODES), sorted(enforced)) == (
        sorted(codes("parse")),
        sorted(codes("schema")),
    )


def test_every_schema_rule_has_a_fixture():
    rules = {fixture_header(path)[0] for path in fixtures("invalid")}
    assert sorted(set(codes("parse", "schema")) - rules) == []


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
    assert sorted(linked - reference_pages()) == []


class Example(NamedTuple):
    """A fenced YAML or JSON block of the specification."""

    line: int
    """The line of its opening fence, from 1."""
    language: str
    elided: tuple[tuple[Any, ...], ...]
    """The paths of the maps it leaves fields out of, each on a line `...`; empty if it leaves nothing out. Those lines
    are dropped from the document."""
    document: Any
    """Its text, its placeholders filled, read as its kind of file is."""


def _tokens() -> list[Token]:
    return MarkdownIt("commonmark").parse(SPECIFICATION.read_text(encoding="utf-8"))


def _language(fence: Token) -> str:
    """The language of a fenced block: the first word of its info string."""
    return fence.info.split()[0] if fence.info.strip() else ""


COMMIT = "0123456789abcdef0123456789abcdef01234567"
"""The commit id that fills `<commit id>`."""

HASH = "sha256:" + hashlib.sha256(b"").hexdigest()
"""The content hash that fills `sha256:<hash>`."""

SIZE = "0"
"""The size that fills `<size>`."""

URL = "https://example.org/repository.git"
"""The URL that fills `<url of a git repository>`."""

PLACEHOLDERS = {
    "<commit id>": COMMIT,
    "sha256:<hash>": HASH,
    "<size>": SIZE,
    "<url of a git repository>": URL,
}
"""Each placeholder an example may show, with what fills it."""


def fill_placeholders(text: str) -> str:
    """`text` with each placeholder of `PLACEHOLDERS` filled. Any other `<…>` is left as it is."""
    for placeholder, value in PLACEHOLDERS.items():
        text = text.replace(placeholder, value)
    return text


def _elided_maps(node: Any, path: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    """The paths, below `path`, of the maps in `node` that hold `ELIDED_KEY`, each key popped."""
    found = []
    if isinstance(node, dict):
        if node.pop(ELIDED_KEY, None) is not None:
            found.append(path)
        for key, value in node.items():
            found.extend(_elided_maps(value, (*path, key)))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(_elided_maps(item, (*path, index)))
    return found


def examples() -> list[Example]:
    """Every fenced YAML or JSON block of the specification, its placeholders filled (`fill_placeholders`) and, in
    YAML, each line `...` dropped, the map it was in noted."""
    found = []
    for token in _tokens():
        if token.type != "fence" or _language(token) not in EXAMPLE_ROOTS:
            continue
        if _language(token) == "json":
            document = load_json(fill_placeholders(token.content))
            elided: tuple[tuple[Any, ...], ...] = ()
        else:
            text = ELISION.sub(rf"\1{ELIDED_KEY}: true", token.content)
            document = load_yaml(fill_placeholders(text))
            elided = tuple(_elided_maps(document))
        found.append(Example(token.map[0] + 1, _language(token), elided, document))
    return found


EXAMPLES = examples()


def _whole(example: Example) -> bool:
    """Whether an example is a whole document: one with a top-level `spec_version`, leaving nothing out."""
    return (
        not example.elided
        and isinstance(example.document, dict)
        and "spec_version" in example.document
    )


WHOLE_EXAMPLES = [example for example in EXAMPLES if _whole(example)]

SNIPPETS = [example for example in EXAMPLES if not _whole(example)]
"""The examples that are part of an `astra.yaml`."""

FRAGMENTS = [example for example in SNIPPETS if not example.elided]

ELIDED = [example for example in SNIPPETS if example.elided]


def _id(example: Example) -> str:
    return f"{example.language}-line-{example.line}"


def test_every_snippet_is_part_of_an_astra_yaml():
    """A block that isn't a whole document is a YAML map, part of an `astra.yaml`: a record is shown whole."""
    assert [
        _id(example)
        for example in SNIPPETS
        if example.language != "yaml" or not isinstance(example.document, dict)
    ] == []


def test_specification_has_whole_examples():
    """Both kinds of document appear whole at least once, so the next test checks something."""
    assert {example.language for example in WHOLE_EXAMPLES} == set(EXAMPLE_ROOTS)


PLACEHOLDER_RECORD = """\
{
  "spec_version": "0.1.0",
  "address": "output1",
  "content_hash": "sha256:<hash>",
  "size": <size>,
  "generated_by": {
    "commit": "<commit id>",
    "inputs": [
      {"entry": "input1", "content_hash": "sha256:<hash>", "size": <size>}
    ],
    "environment": {"iri": "urn:example:environment1"},
    "runner": {"id": "example-runner", "version": "1.0.0"}
  }
}
"""
"""A record written as an example writes one: its commit, hashes and sizes as placeholders."""


def test_placeholders_are_filled():
    """Once filled, the record is valid: a full commit id, each hash a SHA-256, each size a number."""
    record = load_json(fill_placeholders(PLACEHOLDER_RECORD))
    v = validator("ProvenanceRecord")
    assert [
        f"{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(record)
    ] == []
    assert record["generated_by"]["commit"] == COMMIT
    assert record["content_hash"] == HASH
    assert record["size"] == int(SIZE)
    (read,) = record["generated_by"]["inputs"]
    assert (read["content_hash"], read["size"]) == (HASH, int(SIZE))


def test_a_filled_url_is_a_declarations_url():
    """`<url of a git repository>`, filled, is a valid `url` of a declaration."""
    document = {
        **FRAGMENT_STUB,
        "analyses": {
            "upstream": {
                "url": fill_placeholders("<url of a git repository>"),
                "commit": COMMIT,
            }
        },
    }
    assert [
        f"{list(e.absolute_path)}: {e.message}"
        for e in validator("Analysis").iter_errors(document)
    ] == []


def test_fill_placeholders_leaves_unknown_ones():
    text = 'a: "<other>"\nb: "<hash of input1>"\nc: "sha256:<other>"\nd: "<size of input1>"\n'
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


def _over_the_stub(example: Example) -> list:
    """The schema errors of a snippet over the stub: its keys replace the stub's (its own `outputs` replace the stub
    output)."""
    assert isinstance(example.document, dict)
    return list(
        validator("Analysis").iter_errors({**FRAGMENT_STUB, **example.document})
    )


@pytest.mark.parametrize("example", FRAGMENTS, ids=_id)
def test_every_fragment_is_valid_over_the_stub(example):
    """A snippet that leaves nothing out, over the stub, is valid.

    That checks the schema layer only: a snippet can name what the stub doesn't declare.
    """
    assert [
        f"{list(e.absolute_path)}: {e.message}" for e in _over_the_stub(example)
    ] == []


@pytest.mark.parametrize("example", ELIDED, ids=_id)
def test_every_elided_snippet_is_valid_but_for_what_it_leaves_out(example):
    """A snippet that leaves fields out, on a line `...`, is valid over the stub but for those fields: its only errors
    are fields `required` and missing from a map that holds a line `...`."""
    assert [
        f"{list(e.absolute_path)}: {e.message}"
        for e in _over_the_stub(example)
        if not (e.validator == "required" and tuple(e.absolute_path) in example.elided)
    ] == []
