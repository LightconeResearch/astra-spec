"""The harness's loaders: an `astra.yaml` read by a stock YAML 1.2 parser, with ASTRA's rules checked on its text, on
the parser's events and on the value (spec §3), and a record as strict JSON (spec §3).

These tests check ASTRA's rules. YAML's own grammar is the parser's to read, and isn't tested here.
"""

import pytest

from .conftest import (
    PARSE_ERRORS,
    DuplicateNameError,
    JSONError,
    error_pointers,
    load_document,
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


# --- The text: UTF-8, and the characters a file holds nowhere ---


@pytest.mark.parametrize("data", [b"a: \xc3\xa9\n", b"\xef\xbb\xbfa: \xc3\xa9\n"])
def test_utf_8_loads_with_or_without_a_byte_order_mark(load, data):
    assert load(data) == {"a": "\u00e9"}


@pytest.mark.parametrize(
    "data",
    [
        "\ufeffa: \u00e9\n".encode("utf-16-le"),
        "\ufeffa: \u00e9\n".encode("utf-16-be"),
        "\ufeffa: \u00e9\n".encode("utf-32-le"),
        "a: \u00e9\n".encode("latin-1"),
        b"a: \xed\xa0\x80\n",
    ],
    ids=["utf-16-le", "utf-16-be", "utf-32-le", "latin-1", "encoded-surrogate"],
)
def test_bytes_that_arent_utf_8_are_invalid_syntax(refused, data):
    """UTF-16 and UTF-32, which YAML 1.2.2 §5.2 also reads, each with a byte order mark, Latin-1, and a surrogate
    encoded as UTF-8 would encode a character."""
    assert refused(data) == "INVALID_SYNTAX"


FORBIDDEN = [
    "\t",
    "\x00",
    "\x01",
    "\x08",
    "\x0b",
    "\x0c",
    "\x0e",
    "\x1b",
    "\x1f",
    "\x7f",
    "\x80",
    "\x85",
    "\x96",
    "\x9f",
    "\u2028",
    "\u2029",
    "\ufeff",
    "\ufffe",
    "\uffff",
]
"""Characters a file holds nowhere, written raw: a tab, C0 controls other than LF and CR, DEL, C1 controls (NEL
included), LS, PS, a byte order mark past the first character, U+FFFE and U+FFFF."""


@pytest.mark.parametrize(
    "template",
    [
        "a: x{}y\n",
        'a: "x{}y"\n',
        "a: 'x{}y'\n",
        "a: |\n  x{}y\n",
        "a: >\n  x{}y\n",
        "x{}y: a\n",
        '"x{}y": a\n',
        "a: x{}\n",
        "a: x # {}\n",
        "# {}\na: x\n",
        "%YAML 1.2 # {}\n---\na: x\n",
    ],
    ids=[
        "plain",
        "double-quoted",
        "single-quoted",
        "literal",
        "folded",
        "plain-key",
        "quoted-key",
        "line-end",
        "comment",
        "comment-line",
        "directive",
    ],
)
@pytest.mark.parametrize(
    "character", FORBIDDEN, ids=[f"U+{ord(c):04X}" for c in FORBIDDEN]
)
def test_a_forbidden_character_written_raw_is_invalid_syntax_anywhere(
    refused, template, character
):
    """Quoted or not (spec §3)."""
    assert refused(template.format(character)) == "INVALID_SYNTAX"


@pytest.mark.parametrize(
    "text",
    [
        "a:\tb\n",
        "a: b\t# c\n",
        "a:\n\tb: 1\n",
        "a:\n  b: 1\n \tc: 2\n",
        "-\tx\n",
        "- a\n\t- b\n",
        "a: 1\n\t\nb: 2\n",
        "a: |\n\tx\n",
        "a: |\t\n  x\n",
        "a: [x,\tb]\n",
        "%YAML\t1.2\n---\na: x\n",
    ],
    ids=[
        "after-a-colon",
        "before-a-comment",
        "indentation",
        "after-indentation",
        "after-a-dash",
        "before-a-dash",
        "blank-line",
        "block-scalar-indentation",
        "block-scalar-header",
        "flow-collection",
        "directive",
    ],
)
def test_a_tab_is_invalid_syntax_as_white_space_too(refused, text):
    """A tab separates in YAML 1.2.2 wherever white space other than indentation does (§6.2); a file holds none."""
    assert refused(text) == "INVALID_SYNTAX"


@pytest.mark.parametrize(
    "text",
    ["\ufeff\ufeffa: 1\n", "a: 1\n...\n\ufeff# c\n", "a: 1\n\ufeff"],
    ids=["second-at-the-start", "after-document-end", "at-the-end"],
)
def test_a_byte_order_mark_only_starts_the_file(refused, text):
    """One byte order mark may start the file; YAML 1.2.2 §5.2 also allows one at the start of each document."""
    assert refused(text) == "INVALID_SYNTAX"


@pytest.mark.parametrize(
    "escape, character",
    [
        ("\\t", "\t"),
        ("\\0", "\x00"),
        ("\\x01", "\x01"),
        ("\\x7F", "\x7f"),
        ("\\x96", "\x96"),
        ("\\x85", "\x85"),
        ("\\N", "\x85"),
        ("\\L", "\u2028"),
        ("\\P", "\u2029"),
        ("\\uFEFF", "\ufeff"),
        ("\\uFFFE", "\ufffe"),
        ("\\uFFFF", "\uffff"),
    ],
)
def test_an_escape_writes_a_character_the_text_cant_hold(load, escape, character):
    """A double-quoted scalar writes any of them with an escape."""
    assert load(f'a: "x{escape}y"\n') == {"a": f"x{character}y"}


# --- Line breaks ---


@pytest.mark.parametrize(
    "text, value",
    [
        ("a: 1\nb: 2\n", {"a": 1, "b": 2}),
        ("a: 1\r\nb: 2\r\n", {"a": 1, "b": 2}),
        ("a: 1\rb: 2\r", {"a": 1, "b": 2}),
        ("# note\rb: 1\na: 2\n", {"b": 1, "a": 2}),
        ('a: "x\r  y"\n', {"a": "x y"}),
        ("a: |\r  x\r  y\r", {"a": "x\ny\n"}),
    ],
    ids=["lf", "cr-lf", "cr", "cr-ends-a-comment", "cr-in-quotes", "cr-in-a-block"],
)
def test_lf_cr_lf_and_a_lone_cr_each_end_a_line(load, text, value):
    assert load(text) == value


@pytest.mark.parametrize(
    "text, value",
    [
        ("a: 1", {"a": 1}),
        ("a: |\n  x", {"a": "x\n"}),
        ("a: >\n  x", {"a": "x\n"}),
        ("- |\n  x\n  y", ["x\ny\n"]),
        ("a: |\r  x", {"a": "x\n"}),
        ("a: 1\n# c", {"a": 1}),
    ],
)
def test_a_missing_final_line_break_is_read_as_present(load, text, value):
    """A block scalar at the end of the file keeps its final line break."""
    assert load(text) == value


# --- Directives and documents ---


@pytest.mark.parametrize(
    "text",
    [
        "%YAML 1.2\n---\na: yes\n",
        "%YAML 1.2 # the version\n---\na: yes\n",
        "# c\n%YAML 1.2\n---\na: yes\n",
    ],
)
def test_the_yaml_1_2_directive_is_allowed(load, text):
    assert load(text) == {"a": "yes"}


@pytest.mark.parametrize(
    "directive",
    [
        "%YAML 1.1",
        "%YAML 1.0",
        "%YAML 1.3",
        "%YAML 2.0",
        "%YAML 1.02",
        "%YAML 1.20",
        "%TAG ! tag:example.com,2000:",
        "%TAG !! tag:yaml.org,2002:",
        "%TAG !e! tag:example.com,2000:",
        "%FOO bar",
    ],
)
def test_any_other_directive_is_invalid_syntax(refused, directive):
    """The only directive is `%YAML 1.2`, written so: no other version, no `%TAG`, no reserved directive."""
    assert refused(f"{directive}\n---\na: x\n") == "INVALID_SYNTAX"


@pytest.mark.parametrize(
    "text, value",
    [
        ("---\na: 1\n", {"a": 1}),
        ("# c\n---\na: 1\n", {"a": 1}),
        ("--- {a: 1}\n", {"a": 1}),
        ("a: 1\n...\n", {"a": 1}),
        ("a: 1\n... # c\n", {"a": 1}),
        ("---\na: 1\n...\n# c\n\n", {"a": 1}),
        ("", None),
        ("\n\n", None),
        ("# c\n", None),
        ("---\n", None),
        ("---\n...\n", None),
    ],
)
def test_a_file_holds_at_most_one_document(load, text, value):
    """A file with no document is null, which fails as WRONG_TYPE."""
    assert load(text) == value


@pytest.mark.parametrize(
    "text",
    [
        "a: 1\n---\n",
        "a: 1\n---\nb: 2\n",
        "---\na: 1\n---\n",
        "---\na: 1\n...\n---\nb: 2\n",
        "---\n---\n",
        "...\n",
        "# c\n...\n",
        "...\na: 1\n",
        "a: 1\n...\n...\n",
        "a: 1\n...\nb: 2\n",
        "a: 1\n... b\n",
    ],
    ids=[
        "start-after-content",
        "second-document",
        "second-start",
        "second-document-after-end",
        "two-starts",
        "end-alone",
        "end-after-a-comment",
        "end-before-content",
        "two-ends",
        "content-after-end",
        "content-on-the-end-line",
    ],
)
def test_a_document_marker_out_of_place_is_invalid_syntax(refused, text):
    """At most one `---`, before the content, and at most one `...`, after it, with nothing but comments after."""
    assert refused(text) == "INVALID_SYNTAX"


# --- Aliases and anchors ---


@pytest.mark.parametrize(
    "text",
    [
        "a: &x 1\nb: *x\n",
        "a: *x\n",
        "a: [1, *x]\n",
        "a: &x {b: 1}\nc:\n  <<: *x\n",
        "a: &x 1\n*x : b\n",
    ],
    ids=["alias", "undefined", "in-a-list", "merge", "key"],
)
def test_an_alias_is_invalid_syntax(refused, text):
    assert refused(text) == "INVALID_SYNTAX"


@pytest.mark.parametrize(
    "text, value",
    [
        ("a: &x 1\n", {"a": 1}),
        ("a: &x [1]\n", {"a": [1]}),
        ("a: &x {b: 1}\n", {"a": {"b": 1}}),
        ("&k a: 1\n", {"a": 1}),
        ("--- &x\na: 1\n", {"a": 1}),
    ],
)
def test_an_anchor_alone_means_nothing(load, text, value):
    assert load(text) == value


# --- Tags ---


@pytest.mark.parametrize(
    "text",
    [
        "a: !!str 42\n",
        "a: !!int '42'\n",
        "a: !!float 1\n",
        "a: !!bool true\n",
        "a: !!null ''\n",
        "a: !!seq [1]\n",
        "a: !!map {b: 1}\n",
        "a: !!set {x, y}\n",
        "a: !!binary aGk=\n",
        "a: !!omap [x: 1]\n",
        "a: !!timestamp 2026-10-26\n",
        "a: !!merge x\n",
        "a: !include b.yaml\n",
        "a: ! 12\n",
        "a: ! [1]\n",
        "a: !<tag:yaml.org,2002:str> x\n",
        "a: !<!> x\n",
        "!!str a: 1\n",
        "--- !!map\na: 1\n",
    ],
)
def test_a_tag_is_invalid_syntax(refused, text):
    """No node has a tag, a core schema tag or `!` included."""
    assert refused(text) == "INVALID_SYNTAX"


# --- Plain scalars, by YAML 1.2.2 §10.3.2's table ---


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
        # an all-digit commit id, and one of digits and a single `e`
        (
            "1234567890123456789012345678901234567890",
            1234567890123456789012345678901234567890,
        ),
        (
            "1234567890123456789012345678901234567e12",
            1234567890123456789012345678901234567e12,
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


# --- Escapes of surrogates ---


@pytest.mark.parametrize(
    "text",
    [
        'a: "\\uD800"\n',
        'a: "\\uDC80"\n',
        'a: "\\uDE00\\uD83D"\n',
        'a: "\\uD83D\\uDE00"\n',
        'a: "x\\U0000D800"\n',
        'a: "\\U0000D83D\\U0000DE00"\n',
        '"\\uD800": x\n',
    ],
    ids=["high", "low", "reversed", "pair", "long", "long-pair", "key"],
)
def test_an_escape_of_a_surrogate_is_invalid_syntax(refused, text):
    """Lone or paired: a character beyond U+FFFF is written as itself, or with `\\U`."""
    assert refused(text) == "INVALID_SYNTAX"


@pytest.mark.parametrize(
    "scalar, value",
    [
        ('"\\U0001F600"', "\U0001f600"),
        ('"\U0001f600"', "\U0001f600"),
        ('"\\U0010FFFF"', "\U0010ffff"),
        ('"\\uFFFD"', "\ufffd"),
    ],
)
def test_a_character_beyond_the_basic_plane_is_read(load, scalar, value):
    assert load(f"a: {scalar}\n") == {"a": value}


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
        "1:\n  a: x\n  a: y\n",
        "? {a: x, a: y}\n: z\n",
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
        "in-a-left-out-entry",
        "in-a-key",
    ],
)
def test_equal_string_keys_are_a_duplicate_key(refused, text):
    """Two string keys of one map are equal once their escapes are read, in an entry left out or a key too."""
    assert refused(text) == "DUPLICATE_KEY"


@pytest.mark.parametrize(
    "text, loaded",
    [
        ("true: x\ntrue: y\n", ({}, [("(root)", "true"), ("(root)", "true")])),
        ("1: x\n1.0: y\n", ({}, [("(root)", "1"), ("(root)", "1.0")])),
        ("~: x\nnull: y\n", ({}, [("(root)", "~"), ("(root)", "null")])),
        ('1: x\n"1": y\n', ({"1": "y"}, [("(root)", "1")])),
        ("true: x\n'true': y\n", ({"true": "y"}, [("(root)", "true")])),
    ],
)
def test_a_key_that_isnt_a_string_is_never_a_duplicate(text, loaded):
    """Keys that aren't strings take no part: each is left out, and reported (INVALID_ID)."""
    assert load_document(text) == loaded


# --- Values: numbers ---


@pytest.mark.parametrize(
    "text",
    [
        "a: .inf\n",
        "a: -.Inf\n",
        "a: +.INF\n",
        "a: .nan\n",
        ".inf: x\n",
        ".nan: x\n",
        "a: 1e400\n",
        "a: -1e400\n",
        "a: 1" + "0" * 399 + "\n",
        "a: 1" + "0" * 4999 + "\n",
        "a: 0x" + "f" * 300 + "\n",
        "a: 0o" + "7" * 400 + "\n",
        "a: 1234e" + "1" * 35 + "\n",
        "? [.nan]\n: x\n",
        "1: {a: .nan}\n",
    ],
)
def test_a_number_with_no_json_form_is_invalid_syntax(refused, text):
    """A number that isn't finite or is beyond a double's range, as a value or a key, or inside a key or an entry left
    out (an unquoted commit id of digits and an `e` included)."""
    assert refused(text) == "INVALID_SYNTAX"


@pytest.mark.parametrize(
    "scalar, value",
    [
        ("1e-400", 0.0),
        ("1e308", 1e308),
        ("1" + "0" * 308, 10**308),
        ("0" * 400 + "1", 1),
        ("9007199254740993", 9007199254740993),
    ],
)
def test_a_number_within_a_doubles_range_is_read(load, scalar, value):
    """A number too small for a double is 0, and one within its range is read exactly."""
    loaded = load(f"a: {scalar}\n")["a"]
    assert loaded == value
    assert type(loaded) is type(value)


@pytest.mark.parametrize("version, valid", [("2.0", True), ("2.5", False)])
def test_a_number_is_typed_as_json_schema_types_it(load, version, valid):
    """§3: `2.0` is an integer, since JSON Schema counts a number with a zero fractional part as one."""
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


# --- Values: keys ---


@pytest.mark.parametrize("key", ["~", "true", "1", "1.5", "[a, b]", "{a: 1}"])
def test_a_key_that_isnt_a_string_is_left_out_and_reported(key):
    assert load_document(f"? {key}\n: x\nb: y\n") == ({"b": "y"}, [("(root)", key)])


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


# --- Anything else is YAML's to read ---


def test_text_the_parser_refuses_is_invalid_syntax(refused):
    assert refused("outputs: {result: {type: metric\n") == "INVALID_SYNTAX"


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
