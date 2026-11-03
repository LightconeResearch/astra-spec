"""Every fixture, through the committed JSON Schema: valid ones pass, invalid ones fail where they say, and why (design §9).

Why is read from `rules.json`, as a tool reads it: each error's absolute keyword location maps to its code (D13).
"""

from pathlib import Path

import pytest

from .conftest import (
    COMBINATORS,
    PARSE_ERRORS,
    errors,
    fixture_header,
    fixtures,
    is_ancestor,
    load_yaml,
    rules_catalogue,
    validator,
)


def root_of(path: Path) -> str:
    """The class a fixture is a document of: its file name up to the first `-`."""
    return path.name.split("-", 1)[0]


def layer_of(code: str) -> str | None:
    """The layer of the rule `code` in `rules.json`, or None if it has no such rule."""
    return {rule["code"]: rule["layer"] for rule in rules_catalogue()["rules"]}.get(
        code
    )


def keyword_of(location: str) -> str:
    """The keyword an absolute keyword location ends in."""
    return location.rsplit("/", 1)[-1]


@pytest.mark.parametrize("path", fixtures("valid"), ids=lambda path: path.stem)
def test_valid_fixture(path):
    v = validator(root_of(path))
    assert [
        f"{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(load_yaml(path))
    ] == []


@pytest.mark.parametrize("path", fixtures("invalid"), ids=lambda path: path.stem)
def test_invalid_fixture(path):
    """It fails at `fails_at` and nowhere else (a combinator at an ancestor aside), by an error `rules.json` gives its rule."""
    rule, fails_at = fixture_header(path)
    if fails_at == "parse":
        assert layer_of(rule) == "parse", f"{rule} is not a parse-layer code"
        with pytest.raises(PARSE_ERRORS[rule]):
            load_yaml(path)
        return
    assert layer_of(rule) == "schema", f"{rule} is not a schema-layer code"
    error_map = rules_catalogue()["errors"]
    found = errors(validator(root_of(path)), load_yaml(path))
    assert sorted({location for _, location, _ in found} - error_map.keys()) == []
    elsewhere = {
        (pointer, location)
        for pointer, location, _ in found
        if pointer != fails_at
        and not (keyword_of(location) in COMBINATORS and is_ancestor(pointer, fails_at))
    }
    assert elsewhere == set()
    codes = {
        error_map[location]
        for pointer, location, explains in found
        if pointer == fails_at and not explains
    }
    assert codes == {rule}
