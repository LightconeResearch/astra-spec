"""The named types of types.yaml, through a harness with one field per type (design §4)."""

from pathlib import Path

import pytest

from jsonschema_generator import generate

from .conftest import Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
HARNESS = REPO_ROOT / "tests" / "generator" / "types_harness.yaml"

HEX_40 = "0123456789abcdef0123456789abcdef01234567"
HEX_64 = "0123456789abcdef" * 4

# Each type: the values it accepts, then the values it rejects. Each type rejects a
# valid value plus a final "\n", as ECMA-262 reads the pattern's `$`.
TABLE = {
    "id": (
        ["a", "f1_score", "seed_42", "a_"],
        ["A", "1a", "_a", "rf-standard", "a.b", "", "séed", "a\n"],
    ),
    "address": (
        ["a", "iris.random_seed", "a.b.c"],
        ["a.", ".a", "a..b", "a#u", "A.b", "iris.random_seed\n"],
    ),
    "reference": (
        ["f1_score", "f1_score#rf_standard", "classification.accuracy#baseline"],
        ["a#", "#u", "a#u#v", "a#U", "a.b#u.v", "f1_score#rf_standard\n"],
    ),
    "option_reference": (
        ["scaling.standard", "iris.random_seed.seed_42"],
        ["scaling", "~scaling.standard", "a.b#u", "scaling.standard\n"],
    ),
    "commit_id": (
        [HEX_40, HEX_64],
        [HEX_40[:7], HEX_40 + "a", HEX_40.upper(), "main", HEX_40 + "\n"],
    ),
    "content_hash": (
        ["sha256:" + HEX_64],
        [
            HEX_64,
            "sha1:" + HEX_64,
            "sha256:" + HEX_64.upper(),
            "sha256:" + HEX_64[:63],
            "sha256:" + HEX_64 + "\n",
        ],
    ),
    "spec_version": (
        ["0.1.0", "1.12.3", "10.0.0"],
        ["0.1", "v0.1.0", "01.1.0", "0.1.0-rc1", "0.1.0\n"],
    ),
    "timestamp": (
        [
            "2026-10-26T14:00:00.000Z",
            "2026-12-31T23:59:59.999Z",
            "2026-01-01T00:00:00.000Z",
        ],
        [
            "2026-10-26T14:00:00Z",
            "2026-10-26T14:00:00.000+00:00",
            "2026-10-26 14:00:00.000Z",
            "2026-10-26T14:00:00.0000Z",
            "2026-10-26T14:00:00.000Z\n",
            "2026-13-01T00:00:00.000Z",
            "2026-01-32T00:00:00.000Z",
            "2026-01-01T24:00:00.000Z",
            "2026-01-01T00:60:00.000Z",
            "2026-01-01T00:00:60.000Z",
        ],
    ),
    "iri": (
        [
            "http://tools.ietf.org/rfc/rfc7111",
            "urn:example-runner:env:sha256:5d1338d7",
            "prov:env:1",
            "https://example.org/caf%C3%A9#r%20s",
            "https://example.org/café",
        ],
        [
            "rfc7111",
            "RFC 7111",
            "1http://example.org",
            "x:",
            "urn:x<y>",
            "urn:a b",
            "urn:x#a#b",
            "urn:x%zz",
            "urn:a" + chr(0x202E) + "b",
            "urn:a" + chr(0x85) + "b",
            "http://tools.ietf.org/rfc/rfc7111\n",
        ],
    ),
}

CASES = [
    pytest.param(
        type_, value, valid, id=f"{type_}-{'valid' if valid else 'invalid'}-{value!r}"
    )
    for type_, (accepted, rejected) in TABLE.items()
    for values, valid in [(accepted, True), (rejected, False)]
    for value in values
]


@pytest.fixture(scope="module")
def validator():
    return Validator(generate(HARNESS))


def failures(validator, instance):
    """The JSON Pointers at which `instance` fails; empty if it is valid."""
    return {
        "".join(f"/{part}" for part in error.absolute_path)
        for error in validator.iter_errors(instance)
    }


@pytest.mark.parametrize("type_, value, valid", CASES)
def test_named_type(validator, type_, value, valid):
    assert failures(validator, {type_: value}) == (set() if valid else {f"/{type_}"})
