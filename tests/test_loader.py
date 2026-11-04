"""The harness's loaders: an `astra.yaml` as YAML 1.2.2 under the core schema only (design §9, Ruling R19), and a
record as strict JSON (spec §3).

`tests/yaml-test-suite/` holds the error cases of yaml-test-suite (https://github.com/yaml/yaml-test-suite, MIT,
see its LICENSE), each case's `in.yaml` at its id, from the release `data-2022-01-17` (commit 6e6c296a): the 94
cases with an `error` file, each a text YAML 1.2.2 makes ill-formed.
"""

from pathlib import Path

import pytest
from ruamel.yaml.composer import ComposerError
from ruamel.yaml.constructor import ConstructorError, DuplicateKeyError
from ruamel.yaml.error import YAMLError
from ruamel.yaml.scanner import ScannerError

from .conftest import (
    REPO_ROOT,
    DuplicateNameError,
    JSONError,
    error_pointers,
    load_document,
    load_json,
    load_yaml,
    parse_code,
    validator,
)

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


@pytest.mark.parametrize(
    "text", ["a: !!str [1]\n", "a: !!int {}\n", "a: !!seq x\n", "a: !!map x\n"]
)
def test_a_core_tag_is_on_a_node_of_its_kind(load, text):
    with pytest.raises(ConstructorError):
        load(text)


def test_merge_key_is_an_ordinary_key(load):
    assert load("other: {<<: {x: 1}}\n") == {"other": {"<<": {"x": 1}}}


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


@pytest.mark.parametrize(
    "text",
    [
        "%TAG ! tag:yaml.org,2002:\n---\na: !str x\n",
        "a: !<tag:yaml.org,2002:str> x\n",
    ],
)
def test_a_tag_expanding_to_a_core_tag_is_allowed(load, text):
    assert load(text) == {"a": "x"}


def test_a_core_handle_expanding_elsewhere_is_an_error(load):
    with pytest.raises(ConstructorError):
        load("%TAG !! tag:example.com,2000:\n---\na: !!str x\n")


@pytest.mark.parametrize(
    "text, found",
    [
        ("a: &x 1\n", "anchor"),
        ("a: &x [1]\n", "anchor"),
        ("a: &x {b: 1}\n", "anchor"),
        ("&k a: 1\n", "anchor"),
        ("a: &x 1\nb: *x\n", "anchor"),
        ("a: *x\n", "alias"),
        ("a: [1, *x]\n", "alias"),
    ],
)
def test_anchors_and_aliases_are_errors(load, text, found):
    with pytest.raises(ComposerError, match=f"found the {found}"):
        load(text)


@pytest.mark.parametrize(
    "text", ["a: 1\n---\n", "a: 1\n---\nb: 2\n", "---\na: 1\n...\n---\n", "---\n---\n"]
)
def test_a_second_document_is_an_error(load, text):
    with pytest.raises(ComposerError, match="a single document"):
        load(text)


@pytest.mark.parametrize(
    "text, value",
    [
        ("---\na: 1\n", {"a": 1}),
        ("a: 1\n...\n", {"a": 1}),
        ("---\na: 1\n...\n# c\n", {"a": 1}),
        ("", None),
        ("# c\n", None),
    ],
)
def test_a_file_holds_at_most_one_document(load, text, value):
    assert load(text) == value


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


# --- The examples of the specification's §3 ---


@pytest.mark.parametrize(
    "scalar, value",
    [
        # strings, and valid ids
        ("yes", "yes"),
        ("no", "no"),
        ("on", "on"),
        ("off", "off"),
        # timestamps are not types
        ("2026-10-26", "2026-10-26"),
        # booleans and nulls, in the table's spellings
        ("true", True),
        ("false", False),
        ("null", None),
        ("True", True),
        ("~", None),
        # numbers by the table
        ("1e3", 1000.0),
        ("0x1F", 31),
        ("-.5", -0.5),
        ("010", 10),
        # strings, since they match no row of the table
        ("1_000", "1_000"),
        ("0b101", "0b101"),
        ("12:30", "12:30"),
        ("+.nan", "+.nan"),
        # an all-digit commit id, one of digits and a single `e`, and a version
        (
            "1234567890123456789012345678901234567890",
            1234567890123456789012345678901234567890,
        ),
        (
            "1234567890123456789012345678901234567e12",
            1234567890123456789012345678901234567e12,
        ),
        ("1.2", 1.2),
        # quoted, they are strings
        ('"0dbb615a"', "0dbb615a"),
        ('"0.1.0"', "0.1.0"),
    ],
)
def test_a_scalar_of_section_3_is_read_as_it_says(load, scalar, value):
    loaded = load(f"a: {scalar}\n")["a"]
    assert loaded == value
    assert type(loaded) is type(value)


def test_a_quoted_key_of_section_3_is_a_string(load):
    assert load('"true": {}\n') == {"true": {}}


@pytest.mark.parametrize("version, valid", [("2.0", True), ("2.5", False)])
def test_a_number_is_typed_as_json_schema_types_it(load, version, valid):
    """§3: `2.0` is an integer, since JSON Schema counts a number with a zero fractional part as one."""
    doc = load(
        'spec_version: "0.1.0"\n'
        "outputs:\n"
        "  result: {type: metric, format: json}\n"
        "prior_insights:\n"
        "  noise:\n"
        "    claim: Forests resist noise.\n"
        "    evidence:\n"
        f"      - {{doi: 10.5555/12345678, version: {version}}}\n"
    )
    assert isinstance(doc["prior_insights"]["noise"]["evidence"][0]["version"], float)
    expected = set() if valid else {"/prior_insights/noise/evidence/0/version"}
    assert error_pointers(validator("Analysis"), doc) == expected


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
        ("0x1f", "31"),
        ("true", "True"),
        ("1e3", "1000.0"),
        ("0.0", "-0.0"),
        ("~", "null"),
    ],
)
def test_keys_that_are_equal_nodes_are_duplicates(load, keys):
    first, second = keys
    with pytest.raises(DuplicateKeyError):
        load(f"{first}: x\n{second}: y\n")


def test_a_key_written_twice_is_a_duplicate_whatever_its_type(load):
    with pytest.raises(DuplicateKeyError):
        load("true: x\ntrue: y\n")


# --- Values with no JSON form (spec §3) ---


@pytest.mark.parametrize("key", ["~", "[a, b]", "{a: 1}"])
def test_a_key_that_isnt_a_string_is_left_out_and_reported(key):
    assert load_document(f"? {key}\n: x\nb: y\n") == ({"b": "y"}, [("(root)", key)])


@pytest.mark.parametrize("keys", [("1", "1.0"), ("1", "true"), ("0", "false")])
def test_keys_of_two_tags_are_two_keys_left_out(keys):
    """Keys that are distinct YAML nodes are two keys, even where they are one Python value (`1 == 1.0 == True`)."""
    first, second = keys
    assert load_document(f"{first}: x\n{second}: y\n") == (
        {},
        [("(root)", first), ("(root)", second)],
    )


def test_keys_of_another_tag_are_distinct():
    """`1` and `"1"` are two keys: the string is kept, and the integer left out."""
    assert load_document('1: x\n"1": y\n') == ({"1": "y"}, [("(root)", "1")])


def test_a_key_left_out_is_reported_at_its_map():
    assert load_document(
        "a:\n  - b/c:\n      true: x\n      d: 1\n  - 2: {3: y}\n"
    ) == (
        {"a": [{"b/c": {"d": 1}}, {}]},
        [("/a/0/b~1c", "true"), ("/a/1", "2")],
    )


def test_a_key_inside_a_left_out_entry_isnt_reported():
    assert load_document("1:\n  true: x\n? {2: y}\n: z\n") == (
        {},
        [("(root)", "1"), ("(root)", "{2: y}")],
    )


def test_load_yaml_refuses_a_key_that_isnt_a_string(load):
    with pytest.raises(ValueError, match="'1' at /a"):
        load("a: {1: x}\n")


@pytest.mark.parametrize(
    "text",
    [
        "a: .inf\n",
        "a: -.Inf\n",
        "a: .nan\n",
        ".inf: x\n",
        "-.Inf: x\n",
        ".nan: x\n",
        "a: 1e400\n",
        "a: -1e400\n",
        "a: 1" + "0" * 399 + "\n",
        "a: 0x" + "f" * 300 + "\n",
        "a: 1234e" + "1" * 35 + "\n",
        'a: "\\uD800"\n',
        'a: "\\uDC80"\n',
        'a: "\\uDE00\\uD83D"\n',
        'a: "x\\U0000D800"\n',
        '"\\uD800": x\n',
        "? [.nan]\n: x\n",
        "1: {a: .nan}\n",
    ],
)
def test_a_value_with_no_json_form_is_invalid_syntax(text):
    """A number that isn't finite or is beyond a double's range, and a lone surrogate, as a value, a key or inside a
    key or a left-out entry (an unquoted commit id of digits and an `e` included)."""
    with pytest.raises(YAMLError) as raised:
        load_document(text)
    assert parse_code(raised.value) == "INVALID_SYNTAX"


@pytest.mark.parametrize(
    "scalar, value",
    [
        ("1e-400", 0.0),
        ("1e308", 1e308),
        ("1" + "0" * 308, 10**308),
        ("9007199254740993", 9007199254740993),
        ('"\\uD83D\\uDE00"', "\U0001f600"),
        ('"\\U0001F600"', "\U0001f600"),
    ],
)
def test_a_value_with_a_json_form_is_read(load, scalar, value):
    """A number too small for a double is 0, one within its range is read exactly, and an escaped surrogate pair is
    the one character it encodes, as in JSON."""
    loaded = load(f"a: {scalar}\n")["a"]
    assert loaded == value
    assert type(loaded) is type(value)


@pytest.mark.parametrize(
    "escape, cause", [("\\U00110000", ValueError), ("\\UFFFFFFFF", OverflowError)]
)
def test_an_escape_beyond_unicode_is_a_yaml_error(load, escape, cause):
    with pytest.raises(ScannerError) as raised:
        load(f'a: "{escape}"\n')
    assert isinstance(raised.value.__cause__, cause)


def test_the_last_code_point_is_read(load):
    assert load('a: "\\U0010FFFF"\n') == {"a": "\U0010ffff"}


# --- Records: RFC 8259 JSON text in UTF-8 with no byte order mark, and distinct names (spec §3) ---


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
        '{"a": 1e400}',
        '{"a": -1e400}',
        '{"a": 1' + "0" * 399 + "}",
        '{"a": 1' + "0" * 4999 + "}",
        '{"a": "\\ud800"}',
        '{"a": "\\udc80"}',
        '{"a": "\\ude00\\ud83d"}',
        '{"\\ud800": 1}',
        '[{"a": ["x", "\\udfff"]}]',
        "\ufeff{}",
    ],
)
def test_text_that_isnt_a_records_json_is_invalid_syntax(text):
    """Anything but RFC 8259's forms (YAML's included), a number beyond a double's range, a lone surrogate, as a
    value or a name, and a byte order mark."""
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
        ('{"a": 1e-400}', {"a": 0.0}),
        ('{"a": 1e308}', {"a": 1e308}),
        ('{"a": 1' + "0" * 308 + "}", {"a": 10**308}),
        ('{"a": 9007199254740993}', {"a": 9007199254740993}),
        ('{"a": "\\ud83d\\ude00"}', {"a": "\U0001f600"}),
        ('{"a": "\U0001f600 \u00e9t\u00e9"}', {"a": "\U0001f600 \u00e9t\u00e9"}),
        ('{"a": 1, "A": 2}', {"a": 1, "A": 2}),
        ("1", 1),
    ],
)
def test_a_records_json_is_read(text, value):
    """JSON's white space, numbers within a double's range read exactly, an escaped surrogate pair as one character,
    and names that differ only in case as two. Any JSON value is read: the schema checks it is an object."""
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
