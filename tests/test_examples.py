"""Every `astra.yaml` under `examples/` is a valid analysis document, and the conformance suite's cases 002 and 003 are
copies of the examples, byte for byte."""

import pytest

from .conftest import REPO_ROOT, load_yaml, validator

EXAMPLES = REPO_ROOT / "examples"
ANALYSES = REPO_ROOT / "conformance" / "analyses"


def test_every_example_is_valid():
    paths = sorted(EXAMPLES.glob("**/astra.yaml"))
    v = validator("Analysis")
    errors = {
        path.relative_to(EXAMPLES).as_posix(): [
            f"{list(e.absolute_path)}: {e.message}"
            for e in v.iter_errors(load_yaml(path))
        ]
        for path in paths
    }
    assert {name: found for name, found in errors.items() if found} == {}
    assert sorted(errors) == [
        "iris/astra.yaml",
        "iris_pipeline/astra.yaml",
        "iris_pipeline/classification/astra.yaml",
        "iris_pipeline/feature_extraction/astra.yaml",
    ]


def _files(folder):
    """Each file under `folder`, keyed by its path relative to it, with its bytes."""
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


@pytest.mark.parametrize(
    ("example", "case"), [("iris", "002-iris"), ("iris_pipeline", "003-iris-pipeline")]
)
def test_conformance_case_copies_the_example(example, case):
    """An example and its conformance case's `files/` hold the same files, byte for byte: a change to one is made to
    the other."""
    assert _files(ANALYSES / case / "files") == _files(EXAMPLES / example)
