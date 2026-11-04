"""The harness's YAML loader: YAML 1.2.2 under the core schema only (design §9, Ruling R19).

`tests/yaml-test-suite/` holds the error cases of yaml-test-suite (https://github.com/yaml/yaml-test-suite, MIT,
see its LICENSE), each case's `in.yaml` at its id, from the release `data-2022-01-17` (commit 6e6c296a): the 94
cases with an `error` file, each a text YAML 1.2.2 makes ill-formed.
"""

import math
from pathlib import Path

import pytest
from ruamel.yaml.constructor import ConstructorError, DuplicateKeyError
from ruamel.yaml.error import YAMLError
from ruamel.yaml.scanner import ScannerError

from .conftest import REPO_ROOT, load_yaml

YAML_TEST_SUITE = REPO_ROOT / "tests" / "yaml-test-suite"


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


# --- YAML 1.2.2 where ruamel.yaml departs from it ---


def _suite_cases() -> list[Path]:
    """The `in.yaml` of every vendored yaml-test-suite error case."""
    return sorted(YAML_TEST_SUITE.glob("**/in.yaml"))


def test_the_yaml_test_suite_is_vendored():
    assert len(_suite_cases()) == 94


@pytest.mark.parametrize(
    "path",
    _suite_cases(),
    ids=lambda path: path.parent.relative_to(YAML_TEST_SUITE).as_posix(),
)
def test_yaml_test_suite_error_case_raises(path):
    with pytest.raises(YAMLError):
        load_yaml(path)


@pytest.mark.parametrize(
    "text",
    [
        'a: "x"# c\n',
        "a: 'x'# c\n",
        "a: [x]# c\n",
        "a: {b: x}# c\n",
        "a: [x,# c\n  y]\n",
    ],
)
def test_a_comment_needs_white_space_before_it(load, text):
    with pytest.raises(ScannerError):
        load(text)


@pytest.mark.parametrize(
    "text, value",
    [
        ('a: "x" # c\n', {"a": "x"}),
        ("a: [x] # c\n", {"a": ["x"]}),
        ("a: [x, # c\n  y]\n", {"a": ["x", "y"]}),
        ("# c\na: x# not a comment\n", {"a": "x# not a comment"}),
    ],
)
def test_a_comment_after_white_space_is_read(load, text, value):
    assert load(text) == value


@pytest.mark.parametrize(
    "text",
    [
        "a: [x,\ny]\n",
        "a: [x, y\n]\n",
        "a: {b: x,\n}\n",
        "a: [x\ny]\n",
        'a: "x\ny"\n',
        "a: 'x\ny'\n",
        'a: "x\n\ty"\n',
        'a:\n  b: "x\n  y"\n',
        "- a: [x,\n  y]\n",
    ],
)
def test_a_flow_or_quoted_line_is_indented_past_its_block(load, text):
    with pytest.raises(ScannerError):
        load(text)


@pytest.mark.parametrize(
    "text, value",
    [
        ("a: [x,\n y]\n", {"a": ["x", "y"]}),
        ("a: {b: x,\n }\n", {"a": {"b": "x"}}),
        ('a: "x\n y"\n', {"a": "x y"}),
        ('a: "x\n\n y"\n', {"a": "x\ny"}),
        ('a: "x\n \ty"\n', {"a": "x y"}),
        ("a: [x,\n# c\n y]\n", {"a": ["x", "y"]}),
        ('a:\n  b: "x\n   y"\n', {"a": {"b": "x y"}}),
        ("- a: [x,\n   y]\n", [{"a": ["x", "y"]}]),
        ("[x,\ny]\n", ["x", "y"]),
    ],
)
def test_an_indented_flow_or_quoted_line_is_read(load, text, value):
    assert load(text) == value


@pytest.mark.parametrize(
    "text", ["a: [-]\n", "a: [-, -]\n", "a: {b: -}\n", "a: [x, :]\n"]
)
def test_an_indicator_starts_a_plain_scalar_only_before_a_safe_character(load, text):
    with pytest.raises(ScannerError):
        load(text)


def test_an_indicator_before_a_safe_character_starts_a_plain_scalar(load):
    assert load("a: [-x, -1, :x]\n") == {"a": ["-x", -1, ":x"]}


@pytest.mark.parametrize(
    "scalar, value",
    [
        ("! 12", "12"),
        ("! '12'", "12"),
        ("! true", "true"),
        ("! null", "null"),
        ("!", ""),
    ],
)
def test_a_scalar_tagged_bang_is_a_string(load, scalar, value):
    assert load(f"a: {scalar}\n") == {"a": value}


def test_a_collection_tagged_bang_keeps_its_kind(load):
    assert load("a: ! [1]\nb: ! {c: 1}\n") == {"a": [1], "b": {"c": 1}}


def test_the_verbatim_tag_bang_is_an_error(load):
    with pytest.raises(ScannerError):
        load("a: !<!> x\n")


def test_a_verbatim_core_tag_is_allowed(load):
    assert load("a: !<tag:yaml.org,2002:str> 12\n") == {"a": "12"}


@pytest.mark.parametrize(
    "keys",
    [
        ("a", "'a'"),
        ("a", '"\\x61"'),
        ("a", "! a"),
        ("a", "!!str a"),
        (".nan", ".nan"),
        ("0x1f", "31"),
        ("1e3", "1000.0"),
        ("0.0", "-0.0"),
        ("~", "null"),
    ],
)
def test_keys_that_are_equal_nodes_are_duplicates(load, keys):
    first, second = keys
    with pytest.raises(DuplicateKeyError):
        load(f"{first}: x\n{second}: y\n")


def test_keys_of_another_tag_are_distinct(load):
    assert load('1: x\n"1": y\n') == {1: "x", "1": "y"}


@pytest.mark.parametrize("keys", [("1", "1.0"), ("1", "true"), ("0", "false")])
def test_distinct_keys_python_cant_hold_apart_are_an_error(load, keys):
    first, second = keys
    with pytest.raises(ConstructorError):
        load(f"{first}: x\n{second}: y\n")


@pytest.mark.parametrize(
    "escape, cause", [("\\U00110000", ValueError), ("\\UFFFFFFFF", OverflowError)]
)
def test_an_escape_beyond_unicode_is_a_yaml_error(load, escape, cause):
    with pytest.raises(ScannerError) as raised:
        load(f'a: "{escape}"\n')
    assert isinstance(raised.value.__cause__, cause)


def test_the_last_code_point_is_read(load):
    assert load('a: "\\U0010FFFF"\n') == {"a": "\U0010ffff"}
