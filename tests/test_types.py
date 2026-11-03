"""The named types of types.yaml, through a harness with one field per type (design §4)."""

from pathlib import Path

import pytest
from jsonschema import Draft201909Validator

from jsonschema_generator import generate

REPO_ROOT = Path(__file__).resolve().parent.parent
HARNESS = REPO_ROOT / "tests" / "generator" / "types_harness.yaml"

HEX_40 = "0123456789abcdef0123456789abcdef01234567"
HEX_64 = "0123456789abcdef" * 4

# Each type: the values it accepts, then the values it rejects.
TABLE = {
    "id": (
        ["a", "f1_score", "seed_42"],
        ["A", "1a", "_a", "rf-standard", "a.b", "", "séed"],
    ),
    "address": (
        ["a", "iris.random_seed", "a.b.c"],
        ["a.", ".a", "a..b", "a#u", "A.b"],
    ),
    "reference": (
        ["f1_score", "f1_score#rf_standard", "classification.accuracy#baseline"],
        ["a#", "#u", "a#u#v", "a#U", "a.b#u.v"],
    ),
    "option_reference": (
        ["scaling.standard", "iris.random_seed.seed_42"],
        ["scaling", "~scaling.standard", "a.b#u"],
    ),
    "condition": (
        ["scaling.standard", "~scaling.standard", "~iris.random_seed.seed_42"],
        ["scaling", "~~a.b", "!a.b", "~ a.b"],
    ),
    "commit_id": (
        [HEX_40, HEX_64],
        [HEX_40[:7], HEX_40 + "a", HEX_40.upper(), "main"],
    ),
    "content_hash": (
        ["sha256:" + HEX_64],
        [HEX_64, "sha1:" + HEX_40, "sha256:" + HEX_64.upper(), "sha256:" + HEX_64[:63]],
    ),
    "spec_version": (
        ["0.1.0", "1.12.3", "10.0.0"],
        ["0.1", "v0.1.0", "01.1.0", "0.1.0-rc1"],
    ),
    "timestamp": (
        ["2026-10-26T14:00:00.000Z"],
        [
            "2026-10-26T14:00:00Z",
            "2026-10-26T14:00:00.000+00:00",
            "2026-10-26 14:00:00.000Z",
            "2026-10-26T14:00:00.0000Z",
        ],
    ),
}

CASES = [
    pytest.param(type_, value, valid, id=f"{type_}-{'valid' if valid else 'invalid'}-{value!r}")
    for type_, (accepted, rejected) in TABLE.items()
    for values, valid in [(accepted, True), (rejected, False)]
    for value in values
]


@pytest.fixture(scope="module")
def validator():
    return Draft201909Validator(generate(HARNESS))


def failures(validator, instance):
    """The JSON Pointers at which `instance` fails; empty if it is valid."""
    return {"".join(f"/{part}" for part in error.absolute_path) for error in validator.iter_errors(instance)}


@pytest.mark.parametrize("type_, value, valid", CASES)
def test_named_type(validator, type_, value, valid):
    assert failures(validator, {type_: value}) == (set() if valid else {f"/{type_}"})
