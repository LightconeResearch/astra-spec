"""Every fixture, through the committed JSON Schema: valid ones pass, invalid ones fail where they say, and why (design §9)."""

from pathlib import Path

import pytest

from .conftest import (
    COMBINATORS,
    PARSE_ERRORS,
    SCHEMA_KEYWORDS,
    errors,
    fixture_header,
    fixtures,
    is_ancestor,
    load_yaml,
    validator,
)


def root_of(path: Path) -> str:
    """The class a fixture is a document of: its file name up to the first `-`."""
    return path.name.split("-", 1)[0]


@pytest.mark.parametrize("path", fixtures("valid"), ids=lambda path: path.stem)
def test_valid_fixture(path):
    v = validator(root_of(path))
    assert [
        f"{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(load_yaml(path))
    ] == []


@pytest.mark.parametrize("path", fixtures("invalid"), ids=lambda path: path.stem)
def test_invalid_fixture(path):
    """It fails at `fails_at` and nowhere else (a combinator at an ancestor aside), by a keyword its rule implies."""
    rule, fails_at = fixture_header(path)
    if fails_at == "parse":
        assert rule in PARSE_ERRORS, f"{rule} is not a parse-layer code"
        with pytest.raises(PARSE_ERRORS[rule]):
            load_yaml(path)
        return
    assert rule in SCHEMA_KEYWORDS, f"{rule} is not a schema-layer code"
    found = errors(validator(root_of(path)), load_yaml(path))
    elsewhere = {
        (pointer, keyword)
        for pointer, keyword, _ in found
        if pointer != fails_at
        and not (keyword in COMBINATORS and is_ancestor(pointer, fails_at))
    }
    assert elsewhere == set()
    keywords = {
        keyword
        for pointer, keyword, explains in found
        if pointer == fails_at and not explains
    }
    assert keywords
    assert keywords <= SCHEMA_KEYWORDS[rule]
