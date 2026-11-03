"""Every `astra.yaml` under `examples/` is a valid analysis document (design §1, §9)."""

from .conftest import REPO_ROOT, load_yaml, validator

EXAMPLES = REPO_ROOT / "examples"


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
