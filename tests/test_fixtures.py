"""Every fixture, through the committed JSON Schema: valid ones pass, invalid ones fail where they say (design §9)."""

from pathlib import Path

import pytest
from ruamel.yaml.constructor import DuplicateKeyError

from .conftest import error_pointers, fixture_header, fixtures, load_yaml, validator


def root_of(path: Path) -> str:
    """The class a fixture is a document of: its file name up to the first `-`."""
    return path.name.split("-", 1)[0]


@pytest.mark.parametrize("path", fixtures("valid"), ids=lambda path: path.stem)
def test_valid_fixture(path):
    v = validator(root_of(path))
    assert [f"{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(load_yaml(path))] == []


@pytest.mark.parametrize("path", fixtures("invalid"), ids=lambda path: path.stem)
def test_invalid_fixture(path):
    _, fails_at = fixture_header(path)
    if fails_at == "parse":
        with pytest.raises(DuplicateKeyError):
            load_yaml(path)
    else:
        assert fails_at in error_pointers(validator(root_of(path)), load_yaml(path))
