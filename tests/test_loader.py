"""The harness's YAML loader: YAML 1.2 under the core schema only (design §9, Ruling R19)."""

import math

import pytest
from ruamel.yaml.constructor import DuplicateKeyError
from ruamel.yaml.error import YAMLError

from .conftest import load_yaml


@pytest.fixture
def load(tmp_path):
    """Load `text` as a YAML file, through the harness's `load_yaml`."""

    def _load(text: str):
        path = tmp_path / "doc.yaml"
        path.write_text(text, encoding="utf-8")
        return load_yaml(path)

    return _load


@pytest.mark.parametrize(
    "scalar, value",
    [
        # null
        ("null", None),
        ("Null", None),
        ("NULL", None),
        ("~", None),
        ("", None),
        # bool: the core schema's words, and no others
        ("true", True),
        ("false", False),
        ("True", True),
        ("FALSE", False),
        ("yes", "yes"),
        ("no", "no"),
        ("on", "on"),
        ("off", "off"),
        ("y", "y"),
        ("n", "n"),
        # int: decimal, 0o and 0x, without `_`
        ("42", 42),
        ("-7", -7),
        ("+7", 7),
        ("017", 17),
        ("0o17", 15),
        ("0x1f", 31),
        ("1_000", "1_000"),
        ("0b101", "0b101"),
        ("1:30", "1:30"),
        # float
        ("1.5", 1.5),
        ("-1.5", -1.5),
        (".5", 0.5),
        ("1e3", 1000.0),
        ("1.2", 1.2),
        ("1_000.5", "1_000.5"),
        (".inf", math.inf),
        ("-.Inf", -math.inf),
        # everything else, timestamps included, is a string
        ("0.1.0", "0.1.0"),
        ("2026-10-26", "2026-10-26"),
        ("2026-10-26T14:00:00.000Z", "2026-10-26T14:00:00.000Z"),
        ("=", "="),
        ("seed_42", "seed_42"),
    ],
)
def test_plain_scalars_resolve_by_the_core_schema(load, scalar, value):
    assert load(f"a: {scalar}\n") == {"a": value}


def test_nan_is_a_float(load):
    assert math.isnan(load("a: .nan\n")["a"])


def test_quoted_scalars_are_strings(load):
    assert load('a: \'true\'\nb: "42"\nc: "null"\n') == {
        "a": "true",
        "b": "42",
        "c": "null",
    }


def test_core_tags_are_allowed(load):
    assert load(
        "a: !!str 42\nb: !!int '42'\nc: !!float 1\nd: !!bool true\ne: !!null ''\n"
    ) == {
        "a": "42",
        "b": 42,
        "c": 1.0,
        "d": True,
        "e": None,
    }


@pytest.mark.parametrize(
    "text", ["a: !!int 1_000\n", "a: !!int x\n", "a: !!bool yes\n", "a: !!null x\n"]
)
def test_a_core_tag_takes_only_its_core_form(load, text):
    with pytest.raises(YAMLError):
        load(text)


def test_merge_key_is_an_ordinary_key(load):
    assert load("base: &b {x: 1}\nother:\n  <<: *b\n") == {
        "base": {"x": 1},
        "other": {"<<": {"x": 1}},
    }


@pytest.mark.parametrize(
    "text",
    [
        "a: !!set {x, y}\n",
        "a: !!binary aGk=\n",
        "a: !!omap [x: 1]\n",
        "a: !!pairs [x: 1]\n",
        "a: !!timestamp 2026-10-26\n",
        "a: !!merge x\n",
        "a: !local x\n",
    ],
)
def test_other_tags_are_errors(load, text):
    with pytest.raises(YAMLError):
        load(text)


def test_yaml_1_2_directive_is_allowed(load):
    assert load("%YAML 1.2\n---\na: yes\n") == {"a": "yes"}


@pytest.mark.parametrize("version", ["1.1", "1.0", "1.3"])
def test_other_yaml_directives_are_errors(load, version):
    with pytest.raises(YAMLError):
        load(f"%YAML {version}\n---\na: yes\n")


def test_duplicate_keys_raise(load):
    with pytest.raises(DuplicateKeyError):
        load("a: 1\na: 2\n")


def test_malformed_yaml_raises(load):
    with pytest.raises(YAMLError):
        load("outputs: {result: {type: metric\n")
