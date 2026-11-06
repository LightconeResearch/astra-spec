"""The harness's loaders: an `astra.yaml` read by a stock YAML 1.2 parser under the core schema, its content a JSON value
(spec Annex A), and a record as JSON (spec Annex A).

These tests check ASTRA's rules. YAML's own grammar is the parser's to read, and isn't tested here.
"""

import pytest

from .conftest import (
    PARSE_ERRORS,
    DuplicateNameError,
    JSONError,
    error_pointers,
    load_json,
    load_yaml,
    parse_code,
    validator,
)

_RECIPE = "recipe: {command: \"python make.py '{output}'\"}"
"""An output's recipe, as an entry of a flow mapping."""


@pytest.fixture
def load(tmp_path):
    """Load `text` as a YAML file, through the harness's `load_yaml`: its bytes, or a text written as UTF-8."""

    def _load(text: str | bytes):
        path = tmp_path / "doc.yaml"
        path.write_bytes(text.encode("utf-8") if isinstance(text, str) else text)
        return load_yaml(path)

    return _load


@pytest.fixture
def refused(load):
    """The parse code of the loader error `text` raises, as a file; the test fails if it loads."""

    def _refused(text: str | bytes) -> str:
        with pytest.raises(PARSE_ERRORS) as raised:
            load(text)
        return parse_code(raised.value)

    return _refused


# --- Documents: at most one ---


@pytest.mark.parametrize(
    "text, value",
    [
        ("---\na: 1\n", {"a": 1}),
        ("a: 1\n...\n", {"a": 1}),
        ("", None),
        ("# c\n", None),
        ("---\n", None),
    ],
)
def test_a_file_holds_at_most_one_document(load, text, value):
    """A file with no document is null, which fails as WRONG_TYPE."""
    assert load(text) == value


@pytest.mark.parametrize(
    "text", ["a: 1\n---\nb: 2\n", "---\na: 1\n...\n---\nb: 2\n", "---\n---\n"]
)
def test_a_second_document_is_invalid_syntax(refused, text):
    assert refused(text) == "INVALID_SYNTAX"


# --- The core schema: plain scalars typed by its table, and only its tags ---


@pytest.mark.parametrize(
    "scalar, value",
    [
        # null
        ("null", None),
        ("Null", None),
        ("NULL", None),
        ("~", None),
        ("", None),
        # bool: the table's words, and no others
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
        ("010", 10),
        ("0777", 777),
        ("0o17", 15),
        ("0x1f", 31),
        ("0x1F", 31),
        ("-0x1F", "-0x1F"),
        ("1_000", "1_000"),
        ("0b101", "0b101"),
        ("1:30", "1:30"),
        ("12:30", "12:30"),
        # float
        ("1.5", 1.5),
        ("-1.5", -1.5),
        (".5", 0.5),
        ("-.5", -0.5),
        ("1e3", 1000.0),
        ("1.2", 1.2),
        ("1_000.5", "1_000.5"),
        ("+.nan", "+.nan"),
        # everything else, timestamps included, is a string
        ("0.1.0", "0.1.0"),
        ("2026-10-26", "2026-10-26"),
        ("2026-10-26T14:00:00.000Z", "2026-10-26T14:00:00.000Z"),
        ("=", "="),
        ("<<", "<<"),
        ("seed_42", "seed_42"),
        # an all-digit commit id
        (
            "1234567890123456789012345678901234567890",
            1234567890123456789012345678901234567890,
        ),
    ],
)
def test_a_plain_scalar_is_typed_by_the_core_table(load, scalar, value):
    loaded = load(f"a: {scalar}\n")["a"]
    assert loaded == value
    assert type(loaded) is type(value)


def test_quoted_and_block_scalars_are_strings(load):
    assert load(
        'a: \'true\'\nb: "42"\nc: "null"\n"true": {}\nd: |\n  1\ne: >-\n  ~\n'
    ) == {"a": "true", "b": "42", "c": "null", "true": {}, "d": "1\n", "e": "~"}


def test_merge_key_is_an_ordinary_key(load):
    assert load("other: {<<: {x: 1}}\n") == {"other": {"<<": {"x": 1}}}


@pytest.mark.parametrize(
    "text, value",
    [
        ("a: !!str 42\n", {"a": "42"}),
        ("a: !!int '42'\n", {"a": 42}),
        ("a: !!float 1\n", {"a": 1.0}),
        ("a: !!bool true\n", {"a": True}),
        ("a: !!null ''\n", {"a": None}),
        ("a: !!seq [1]\n", {"a": [1]}),
        ("a: !!map {b: 1}\n", {"a": {"b": 1}}),
        ("a: !<tag:yaml.org,2002:str> x\n", {"a": "x"}),
        ("a: ! 12\n", {"a": "12"}),
        ("a: ! [1]\n", {"a": [1]}),
        ("!!str 1: a\n", {"1": "a"}),
        ("--- !!map\na: 1\n", {"a": 1}),
    ],
)
def test_a_core_schema_tag_is_read_as_the_core_schema_reads_it(load, text, value):
    """A core tag reads its node as its own type, and the non-specific `!` as a string, a list or a map by its kind."""
    loaded = load(text)
    assert loaded == value
    assert [type(x) for x in loaded.values()] == [type(x) for x in value.values()]


@pytest.mark.parametrize(
    "text",
    [
        "a: !!set {x, y}\n",
        "a: !!omap [x: 1]\n",
        "a: !!binary aGk=\n",
        "a: !!timestamp 2026-10-26\n",
        "a: !!merge x\n",
        "a: !include b.yaml\n",
        "a: !<tag:example.com,2000:x> y\n",
        "%TAG !! tag:example.com,2000:\n---\na: !!str x\n",
        "a: !!int 1.5\n",
        "a: !!bool yes\n",
        "a: !!null x\n",
        "a: !!str [1]\n",
        "a: !!map [1]\n",
        "a: !!seq x\n",
    ],
)
def test_any_other_tag_is_invalid_syntax(refused, text):
    """A tag outside the core schema (an `!!` tag the core schema lacks, a local tag, `!!` bound elsewhere by `%TAG`), or
    a core tag on a node it doesn't read."""
    assert refused(text) == "INVALID_SYNTAX"


# --- The content is a JSON value ---


@pytest.mark.parametrize(
    "text",
    [
        "a: .inf\n",
        "a: -.Inf\n",
        "a: +.INF\n",
        "a: .nan\n",
        "a: !!float .inf\n",
        "a: [1, .NaN]\n",
        "a: {b: .inf}\n",
    ],
)
def test_a_number_that_isnt_finite_is_invalid_syntax(refused, text):
    assert refused(text) == "INVALID_SYNTAX"


@pytest.mark.parametrize("version, valid", [("2.0", True), ("2.5", False)])
def test_a_number_is_typed_as_json_schema_types_it(load, version, valid):
    """Annex A: `2.0` is an integer, since JSON Schema counts a number with a zero fractional part as one."""
    doc = load(
        'spec_version: "0.1.0"\n'
        "outputs:\n"
        "  result: {type: metric, format: json, " + _RECIPE + "}\n"
        "prior_insights:\n"
        "  noise:\n"
        "    claim: Forests resist noise.\n"
        "    evidence:\n"
        f"      - {{doi: 10.5555/12345678, version: {version}}}\n"
    )
    assert isinstance(doc["prior_insights"]["noise"]["evidence"][0]["version"], float)
    expected = set() if valid else {"/prior_insights/noise/evidence/0/version"}
    assert error_pointers(validator("Analysis"), doc) == expected


@pytest.mark.parametrize(
    "text",
    [
        "~: x\n",
        "true: x\n",
        "1: x\n",
        "1.5: x\n",
        "? [a, b]\n: x\n",
        "? {a: 1}\n: x\n",
        "a:\n  - b: {1: x}\n",
        "true: x\n'true': y\n",
    ],
)
def test_a_key_that_isnt_a_string_is_invalid_syntax(refused, text):
    """A key the core table reads as a null, a boolean or a number, or a key that is a list or a map, anywhere."""
    assert refused(text) == "INVALID_SYNTAX"


@pytest.mark.parametrize(
    "text, value",
    [
        ("a: &x [1]\nb: *x\n", {"a": [1], "b": [1]}),
        ("a: &k x\n*k : y\n", {"a": "x", "x": "y"}),
        ("a: &x {b: 1}\nc:\n  <<: *x\n", {"a": {"b": 1}, "c": {"<<": {"b": 1}}}),
    ],
)
def test_an_alias_is_read_as_the_node_it_names(load, text, value):
    assert load(text) == value


@pytest.mark.parametrize("text", ["a: &x [1, *x]\n", "a: &x {b: *x}\n", "a: *x\n"])
def test_an_alias_that_gives_no_json_value_is_invalid_syntax(refused, text):
    """An alias inside the node it names makes the content no JSON value, as does one that names no node."""
    assert refused(text) == "INVALID_SYNTAX"


# --- Duplicate keys ---


@pytest.mark.parametrize(
    "text",
    [
        "a: x\na: y\n",
        "a: x\n'a': y\n",
        'a: x\n"\\x61": y\n',
        "'a': x\n\"a\": y\n",
        "\"1\": x\n'1': y\n",
        "a: {b: 1, b: 2}\n",
        "- a: 1\n  a: 2\n",
        "a:\n  b: 1\n  c: 2\n  b: 3\n",
    ],
    ids=[
        "plain",
        "plain-and-quoted",
        "escaped",
        "two-quotings",
        "quoted-digits",
        "flow",
        "in-a-list",
        "nested",
    ],
)
def test_equal_keys_are_a_duplicate_key(refused, text):
    """Two keys of one map are equal once their escapes are read."""
    assert refused(text) == "DUPLICATE_KEY"


# --- Anything else is YAML's to read ---


def test_text_the_parser_refuses_is_invalid_syntax(refused):
    assert refused("outputs: {result: {type: metric\n") == "INVALID_SYNTAX"


# --- Records: JSON text (RFC 8259) in UTF-8, with distinct names (spec Annex A) ---


@pytest.mark.parametrize(
    "text",
    [
        '{"a": 1, "a": 1}',
        '{"a": 1, "\\u0061": 2}',
        '{"x": [{"a": 1, "b": 2, "a": 3}]}',
    ],
)
def test_a_name_written_twice_in_a_record_is_a_duplicate_key(text):
    """`json.loads` keeps the last of two names; the harness refuses the second, comparing names once their escapes
    are read."""
    with pytest.raises(DuplicateNameError) as raised:
        load_json(text)
    assert parse_code(raised.value) == "DUPLICATE_KEY"


@pytest.mark.parametrize(
    "text",
    [
        "",
        '{"a": 1,}',
        "[1, 2,]",
        '{"a": 1} // a comment',
        '{"a": 1 /* a comment */}',
        '{"a": 1} # a comment',
        "{'a': 1}",
        '{"a": 0x2DC}',
        '{"a": +1}',
        '{"a": .5}',
        '{"a": 01}',
        "{a: 1}",
        "a: 1\n",
        '{"a": 1}\n{"b": 2}',
        '{"a": "tab\there"}',
        '{"a": 1}\u00a0',
        '{"a": NaN}',
        '{"a": Infinity}',
        '{"a": -Infinity}',
    ],
)
def test_text_that_isnt_json_is_invalid_syntax(text):
    """Anything but RFC 8259's forms, YAML's included."""
    with pytest.raises(JSONError) as raised:
        load_json(text)
    assert not isinstance(raised.value, DuplicateNameError)
    assert parse_code(raised.value) == "INVALID_SYNTAX"


@pytest.mark.parametrize(
    "data", [b'{"a": "\xe9t\xe9"}', b'{"a": "\xed\xa0\x80"}', b"\xff\xfe{\x00}\x00"]
)
def test_a_record_that_isnt_utf_8_is_invalid_syntax(tmp_path, data):
    """Latin-1, an encoded surrogate and UTF-16 are not UTF-8."""
    path = tmp_path / "record.json"
    path.write_bytes(data)
    with pytest.raises(JSONError) as raised:
        load_json(path)
    assert parse_code(raised.value) == "INVALID_SYNTAX"


@pytest.mark.parametrize(
    "text, value",
    [
        (
            ' \t\r\n{"a": [1, 2.5, true, false, null]}\n',
            {"a": [1, 2.5, True, False, None]},
        ),
        ('{"a": "\U0001f600 \u00e9t\u00e9"}', {"a": "\U0001f600 \u00e9t\u00e9"}),
        ('{"a": 1, "A": 2}', {"a": 1, "A": 2}),
        ("1", 1),
    ],
)
def test_a_records_json_is_read(text, value):
    """JSON's white space and values, and names that differ only in case as two. Any JSON value is read: the schema
    checks it is an object."""
    loaded = load_json(text)
    assert loaded == value
    assert [type(x) for x in _leaves(loaded)] == [type(x) for x in _leaves(value)]


def _leaves(value):
    """The scalars of a JSON value, in order."""
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in _leaves(item)]
    if isinstance(value, list):
        return [leaf for item in value for leaf in _leaves(item)]
    return [value]
