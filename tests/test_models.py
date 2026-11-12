"""The generated Pydantic models, `generated/analysis.py` and `generated/provenance.py`: each compiles cleanly, and reads
every valid document as it is written, each entry of a map keyed by `id` with its key as its `id`.

The models are a typed view of a document the JSON Schema accepted, never a validator: they don't check the named
types' patterns, the class rules or the maps' keys, so they accept documents the JSON Schema refuses.
"""

import warnings

import pytest
from pydantic import BaseModel

from astra.schema.generated import analysis, provenance

from .conftest import GENERATED, REPO_ROOT, fixtures, load_fixture

MODELS = {
    "Analysis": analysis.Analysis,
    "ProvenanceRecord": provenance.ProvenanceRecord,
}
EXAMPLES = sorted((REPO_ROOT / "examples").glob("**/astra.yaml"))
DOCUMENTS = [*fixtures("valid"), *EXAMPLES]
ANALYSES = [path for path in DOCUMENTS if path.suffix == ".yaml"]


def _name(path):
    return path.relative_to(REPO_ROOT).as_posix()


def _model(path) -> BaseModel:
    root = "ProvenanceRecord" if path.suffix == ".json" else "Analysis"
    return MODELS[root].model_validate(load_fixture(path))


def _entries(model: BaseModel):
    """Each `(key, entry)` of every map of objects in `model`, at any depth."""
    for name in type(model).model_fields:
        value = getattr(model, name)
        if isinstance(value, dict):
            items = list(value.items())
        elif isinstance(value, list):
            items = [(None, item) for item in value]
        else:
            items = [(None, value)]
        for key, item in items:
            if isinstance(item, BaseModel):
                if key is not None:
                    yield key, item
                yield from _entries(item)


@pytest.mark.parametrize("name", ["analysis.py", "provenance.py"])
def test_model_compiles_without_warnings(name):
    """LinkML writes each pattern and description as a Python string, which a `"` in a pattern or a backslash in a
    description breaks, so the schema writes `\\x22` and "the backslash" instead."""
    path = GENERATED / name
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


@pytest.mark.parametrize("path", DOCUMENTS, ids=_name)
def test_valid_document_loads(path):
    _model(path)


@pytest.mark.parametrize("path", ANALYSES, ids=_name)
def test_each_entry_takes_its_key_as_its_id(path):
    entries = list(_entries(_model(path)))
    assert bool(entries) == any(
        isinstance(value, dict) and value for value in load_fixture(path).values()
    )
    assert [(key, entry.id) for key, entry in entries if entry.id != key] == []
