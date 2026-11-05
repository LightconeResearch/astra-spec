"""The harness's loaders: an `astra.yaml` as UTF-8 read by YAML 1.2.2's characters, tabs and line breaks, under the
core schema only (design §9, Ruling R19), and a record as strict JSON (spec §3).

`tests/yaml-test-suite/` holds cases of yaml-test-suite (https://github.com/yaml/yaml-test-suite, MIT, see its
LICENSE), each case's `in.yaml` at its id, from the release `data-2022-01-17` (commit 6e6c296a): the 94 cases with an
`error` file, each a text YAML 1.2.2 makes ill-formed, and, each with its `in.json`, the 217 well-formed cases that use
nothing spec §3 refuses (an anchor, an alias, a tag outside the core schema, a second document, a `%YAML` directive
other than 1.2) and whose keys are all strings, but four. JEF9/02 and L24T/01 are left out: each ends the file in a
block scalar with no line break after it, which the suite reads as if a line break followed, and YAML 1.2.2's grammar
as the end of the file, and spec §3 doesn't say which reading holds. So are HWV9 and QT73, each a `...` with no
document before it, which the loader refuses.
"""

import json
from pathlib import Path

import pytest
from ruamel.yaml.composer import ComposerError
from ruamel.yaml.constructor import ConstructorError, DuplicateKeyError
from ruamel.yaml.error import YAMLError
from ruamel.yaml.reader import ReaderError
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
from .test_fixtures import check_schema_errors

YAML_TEST_SUITE = REPO_ROOT / "tests" / "yaml-test-suite"

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


# --- YAML 1.2.2 where ruamel.yaml departs from it ---


def _suite_cases(*, well_formed: bool) -> list[Path]:
    """The `in.yaml` of every vendored yaml-test-suite case that is well-formed, with its `in.json` beside it, or of
    every error case, with none."""
    return sorted(
        path
        for path in YAML_TEST_SUITE.glob("**/in.yaml")
        if path.with_name("in.json").is_file() == well_formed
    )


def _case_id(path: Path) -> str:
    return path.parent.relative_to(YAML_TEST_SUITE).as_posix()


def test_the_yaml_test_suite_is_vendored():
    assert len(_suite_cases(well_formed=False)) == 94
    assert len(_suite_cases(well_formed=True)) == 217


@pytest.mark.parametrize("path", _suite_cases(well_formed=False), ids=_case_id)
def test_yaml_test_suite_error_case_raises(path):
    with pytest.raises(YAMLError):
        load_yaml(path)


@pytest.mark.parametrize("path", _suite_cases(well_formed=True), ids=_case_id)
def test_yaml_test_suite_well_formed_case_loads_to_its_json(path):
    """Each well-formed case loads to its `in.json`, with JSON's types; an empty `in.json` is a file with no
    document, which is null (spec §3)."""
    loaded = load_yaml(path)
    text = path.with_name("in.json").read_text(encoding="utf-8")
    expected = json.loads(text) if text.strip() else None
    assert _typed(loaded) == _typed(expected)


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
    "text",
    [
        "a: [-]\n",
        "a: [-, -]\n",
        "a: {b: -}\n",
        "a: [?]\n",
        "a: {?}\n",
        "a: [x, ?]\n",
        "a: {b, ?}\n",
    ],
)
def test_an_indicator_starts_a_plain_scalar_only_before_a_safe_character(load, text):
    """In a flow collection, `-` or `?` before a flow indicator starts no plain scalar ([126] `ns-plain-first`), and
    `?` there is no explicit key indicator either, which needs white space after it ([142], [150])."""
    with pytest.raises(ScannerError):
        load(text)


def test_an_indicator_before_a_safe_character_starts_a_plain_scalar(load):
    assert load("a: [-x, -1, :x, ?x, ?#]\n") == {"a": ["-x", -1, ":x", "?x", "?#"]}


@pytest.mark.parametrize(
    "text, value",
    [
        ("{ ?foo: bar }\n", {"?foo": "bar"}),
        ("{?foo}\n", {"?foo": None}),
        ("{a: ?x}\n", {"a": "?x"}),
        ("{? foo: bar}\n", {"foo": "bar"}),
        ("{?\tfoo: bar}\n", {"foo": "bar"}),
        ("{?\n foo: bar}\n", {"foo": "bar"}),
        ("[? foo: bar]\n", [{"foo": "bar"}]),
    ],
)
def test_a_question_mark_in_a_flow_collection_is_a_key_indicator_only_before_white_space(
    load, text, value
):
    """`?` is the explicit key indicator where white space or a line break follows it (YAML 1.2.2 [142], [150]), and
    before a safe character starts a plain scalar, as in the block context (yaml-test-suite 652Z, HM87/01)."""
    assert load(text) == value


@pytest.mark.parametrize(
    "text, value",
    [
        (
            '{\nunquoted : "separate",\nhttp://foo.com,\nomitted value:,\n}\n',
            {"unquoted": "separate", "http://foo.com": None, "omitted value": None},
        ),
        ("{a:}\n", {"a": None}),
        ("{a:, b}\n", {"a": None, "b": None}),
        ("[a:]\n", [{"a": None}]),
        ("[a :, b]\n", [{"a": None}, "b"]),
        ("{a:x, b::}\n", {"a:x": None, "b:": None}),
        ("[a:x]\n", ["a:x"]),
        ("{ :x}\n", {":x": None}),
        ("{a, :x}\n", {"a": None, ":x": None}),
        ("{!!str :x}\n", {":x": None}),
        ("{? :x}\n", {":x": None}),
        ("x: {a: :x}\n", {"x": {"a": ":x"}}),
        ("{a: b,\n c: :x}\n", {"a": "b", "c": ":x"}),
        ("{a: !!str :x}\n", {"a": ":x"}),
    ],
)
def test_a_colon_in_a_flow_collection_is_a_value_indicator_only_before_an_unsafe_character(
    load, text, value
):
    """After a key that isn't JSON-like, or none, `:` is the value indicator before white space, a line break or a flow
    indicator ([147] `c-ns-flow-map-separate-value`), and before a safe character is part of a plain scalar, or starts
    one, in a key or a value ([130] `ns-plain-char`, [126]). So `omitted value:,` has the key `omitted value`
    (yaml-test-suite 4ABK)."""
    assert load(text) == value


@pytest.mark.parametrize(
    "text",
    [
        "{a:[b]}\n",
        "{a:{b: c}}\n",
        "[a:[b]]\n",
        "[:[b]]\n",
        "{ :[b]}\n",
        "{a, :[b]}\n",
        "{!!str :[b]}\n",
    ],
)
def test_a_value_after_a_key_that_isnt_json_like_is_separated_from_its_colon(text):
    """After a plain key or an empty one (nothing, or a tag alone), white space separates a value from its `:` ([147]),
    so a `:` right before a flow collection is refused: only a JSON-like key takes an adjacent value ([149])."""
    with pytest.raises(YAMLError):
        load_document(text)


@pytest.mark.parametrize(
    "text, loaded",
    [
        ('["a":b]\n', ([{"a": "b"}], [])),
        ("['a':b]\n", ([{"a": "b"}], [])),
        ('["a" :b]\n', ([{"a": "b"}], [])),
        ('["a":[b]]\n', ([{"a": ["b"]}], [])),
        ("{\"a\":b, 'c':{d: e}}\n", ({"a": "b", "c": {"d": "e"}}, [])),
        ('a: {? "a":b}\n', ({"a": {"a": "b"}}, [])),
        ('a: [? "a":b]\n', ({"a": [{"a": "b"}]}, [])),
        ('{\n? "a":b}\n', ({"a": "b"}, [])),
        ('[\n? "a":b]\n', ([{"a": "b"}], [])),
        ("a: {? [x]:b}\n", ({"a": {}}, [("/a", "[x]")])),
    ],
)
def test_a_json_like_key_takes_an_adjacent_value(text, loaded):
    """After a quoted scalar or a flow collection that is a key, `:` is the value indicator before anything, in a flow
    sequence as in a flow mapping ([149] `c-ns-flow-map-adjacent-value`, [153]; yaml-test-suite 9MMW), and after `?`
    too ([142], [150], then [143] `ns-flow-map-explicit-entry`), whatever the flow collection is in. A key that isn't a
    string is left out of its map and reported, as anywhere."""
    assert load_document(text) == loaded


@pytest.mark.parametrize(
    "text, value",
    [
        ('{"a"\n: b}\n', {"a": "b"}),
        ("{a\n # c\n :\n b}\n", {"a": "b"}),
        ('[{"a\n b"\n :c}]\n', [{"a b": "c"}]),
        ("{" + "k" * 1100 + ": v}\n", {"k" * 1100: "v"}),
    ],
    ids=[
        "colon-on-the-next-line",
        "comment-before-the-colon",
        "multi-line",
        "1100-characters",
    ],
)
def test_an_implicit_key_of_a_flow_mapping_may_span_lines_and_exceed_1024_characters(
    load, text, value
):
    """An implicit key of a flow mapping is any flow node, which white space, line breaks and comments may separate
    from its `:` ([145], [148]; yaml-test-suite 4MUZ, 5MUD, K3WX, NJ66, 9SA2): only a key in the block context or of
    a single pair in a flow sequence is limited to one line and 1024 characters ([154], [155])."""
    assert load(text) == value


@pytest.mark.parametrize(
    "text",
    ["[a\n: b]\n", '["a"\n :b]\n', "[" + "k" * 1100 + ": v]\n", "k" * 1100 + ": v\n"],
    ids=[
        "colon-on-the-next-line",
        "adjacent-value-on-the-next-line",
        "1100-characters",
        "block-1100-characters",
    ],
)
def test_a_key_of_a_single_pair_or_a_block_mapping_is_one_line_of_1024_characters_at_most(
    text,
):
    """An implicit key of a single pair in a flow sequence, or in the block context, is on the line of its `:`, and
    1024 characters long at most ([154], [155]; yaml-test-suite ZXT5, an error case)."""
    with pytest.raises(YAMLError):
        load_document(text)


@pytest.mark.parametrize(
    "text, loaded",
    [
        (
            '- [ YAML : separate ]\n- [ "JSON like":adjacent ]\n- [ {JSON: like}:adjacent ]\n',
            (
                [[{"YAML": "separate"}], [{"JSON like": "adjacent"}], [{}]],
                [("/2/0", "{JSON: like}")],
            ),
        ),
        (
            "- [ : empty key ]\n- [: another empty key]\n",
            ([[{}], [{}]], [("/0/0", ""), ("/1/0", "")]),
        ),
        ("[x, :]\n", (["x", {}], [("/1", "")])),
        ("[ : ]\n", ([{}], [("/0", "")])),
    ],
    ids=["9MMW", "CFD4", "empty-key-and-value", "empty-key-and-value-spaced"],
)
def test_a_single_pair_in_a_flow_sequence_may_have_any_key(text, loaded):
    """A single pair's key may be JSON-like, with an adjacent value, or empty ([151] `c-ns-flow-map-empty-key-entry`):
    yaml-test-suite 9MMW and CFD4. A key that isn't a string is left out of its map and reported, as anywhere."""
    assert load_document(text) == loaded


@pytest.mark.parametrize(
    "text, value",
    [
        ("{a: !!str, b: !!str}\n", {"a": "", "b": ""}),
        ("[!!str, !!null]\n", ["", None]),
        ("[!!str,x]\n", ["", "x"]),
        ("{a: !, b: c}\n", {"a": "", "b": "c"}),
        ("[!]\n", [""]),
        ("{a: !<tag:yaml.org,2002:str>, b: c}\n", {"a": "", "b": "c"}),
        ("[!<tag:yaml.org,2002:str>]\n", [""]),
        ("[!<tag:yaml.org,2002:str> x]\n", ["x"]),
    ],
)
def test_a_tag_in_a_flow_collection_may_end_its_entry(load, text, value):
    """A shorthand tag holds no flow indicator ([40] `ns-tag-char`), and a tag before `,`, `]` or `}` is on an empty
    node ([105] `e-scalar`), as `!!str,` is the empty string (yaml-test-suite WZ62); a verbatim tag holds `,`."""
    assert load(text) == value


@pytest.mark.parametrize(
    "outputs, expected",
    [
        (
            "{?result: {type: metric, format: json, " + _RECIPE + "}}",
            {"/outputs": {"INVALID_ID"}},
        ),
        ("{? result: {type: metric, format: json, " + _RECIPE + "}}", {}),
        ("{result\n  : {type: metric, format: json, " + _RECIPE + "}}", {}),
        ('{"result"\n  :{type: metric, format: json, ' + _RECIPE + "}}", {}),
        ('{? "result":{type: metric, format: json, ' + _RECIPE + "}}", {}),
        ("{" + "r" * 1100 + ": {type: metric, format: json, " + _RECIPE + "}}", {}),
        (
            "{result: {type: metric, format: json, "
            + _RECIPE
            + ", description: !!str, label: x}}",
            {},
        ),
        (
            "{result: {type: metric, format: json, " + _RECIPE + ", tags: [x:]}}",
            {"/outputs/result/tags/0": {"WRONG_TYPE"}},
        ),
        (
            "{result: {type: metric, format: json, " + _RECIPE + ", :x}}",
            {"/outputs/result": {"UNKNOWN_FIELD"}},
        ),
        (
            "{result: {type: metric, format: json, " + _RECIPE + ", tags: [: x]}}",
            {"/outputs/result/tags/0": {"INVALID_ID", "WRONG_TYPE"}},
        ),
    ],
    ids=[
        "question-mark-glued-to-a-key",
        "explicit-key",
        "colon-on-the-next-line",
        "adjacent-value-on-the-next-line",
        "explicit-key-with-an-adjacent-value",
        "key-of-1100-characters",
        "core-tag-before-a-comma",
        "colon-before-a-flow-indicator",
        "colon-before-a-safe-character-after-no-key",
        "single-pair-with-an-empty-key",
    ],
)
def test_a_flow_form_has_the_verdict_of_its_yaml_1_2_2_reading(outputs, expected):
    """`outputs` written in a flow form YAML 1.2.2 reads as ruamel.yaml doesn't: `?result` is a key that isn't an id
    (`INVALID_ID`), a key may be long or have its `:` on the next line, an explicit quoted key takes an adjacent value,
    `!!str,` is an empty description, `x:` in a list of tags is a map, `:x` with no key before it is a key (an unknown
    field), and a single pair with an empty key has a key that isn't a string."""
    document, left_out = load_document(f'spec_version: "0.1.0"\noutputs: {outputs}\n')
    check_schema_errors("Analysis", document, expected, left_out)


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


# --- Characters, tabs and line breaks: an astra.yaml is UTF-8, read by YAML 1.2.2's characters (spec §3) ---


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
    ],
    ids=["utf-16-le", "utf-16-be", "utf-32-le", "latin-1"],
)
def test_bytes_that_arent_utf_8_are_invalid_syntax(load, data):
    """UTF-16 and UTF-32, which YAML 1.2.2 §5.2 also reads, each with a byte order mark, and Latin-1."""
    with pytest.raises(ReaderError) as raised:
        load(data)
    assert parse_code(raised.value) == "INVALID_SYNTAX"


_MINIMAL = (
    'spec_version: "0.1.0"\noutputs:\n  result:\n    type: metric\n    format: json\n'
    "    recipe:\n      command: python make.py '{output}'\n"
)
"""A minimal valid `astra.yaml`, which F066's tab cases change."""


@pytest.mark.parametrize(
    "text",
    [
        _MINIMAL.replace("type: metric", "type: metric\t# the F1 score"),
        _MINIMAL.replace("type: metric", "type:\tmetric"),
        _MINIMAL.replace("type: metric", "type: metric\t"),
        _MINIMAL.replace("type: metric\n", "type: metric\n\t\n"),
        _MINIMAL.replace("type: metric\n", "type: metric\n \t\n"),
        _MINIMAL.replace('"0.1.0"', '\t"0.1.0"'),
        _MINIMAL.replace("type: metric\n", "type:\n      \tmetric\n"),
        _MINIMAL.replace("type: metric\n", "type: !!str\tmetric\n"),
        "%YAML\t1.2\t# the version\n---\n" + _MINIMAL,
    ],
    ids=[
        "before-a-comment",
        "after-a-colon",
        "at-a-lines-end",
        "on-a-blank-line",
        "on-a-blank-line-after-spaces",
        "before-a-value",
        "after-a-value-lines-indentation",
        "after-a-tag",
        "in-a-directive",
    ],
)
def test_a_tab_separates(load, text):
    """A tab is white space wherever YAML 1.2.2 allows white space outside indentation (§6.2): F066's cases and more."""
    assert load(text) == load(_MINIMAL)


@pytest.mark.parametrize(
    "text, value",
    [
        ("a:\n  - result\t#svm\n", {"a": ["result"]}),
        ("a: x\ty\n", {"a": "x\ty"}),
        ("a: x\n  \ty\n", {"a": "x y"}),
        ("a: x\n  \t\n  y\n", {"a": "x\ny"}),
        ("-\tx\n-\t-1\n", ["x", -1]),
        ("?\ta\n:\tb\n", {"a": "b"}),
        ("- a:\t[x]\n", [{"a": ["x"]}]),
        ("a: |\n  \tx\n", {"a": "\tx\n"}),
        ("a:\t|\n  x\n", {"a": "x\n"}),
        ("a: |\t# c\n  x\n", {"a": "x\n"}),
        ("a: |\t\n  x\n", {"a": "x\n"}),
        ("a: >-\t\n  x\n", {"a": "x"}),
        ("- |\t\n  x\n", ["x\n"]),
        ("--- |\t\n  x\n", "x\n"),
    ],
)
def test_a_tab_is_read_as_yaml_reads_it(load, text, value):
    """Before a comment (F066's `- result<TAB>#svm`), inside a plain scalar, after a continuation line's indentation,
    on a plain scalar's empty line, after a block indicator before a node that isn't a block collection, in a block
    scalar's content, before a block scalar, and in a block scalar's header ([162] `c-b-block-header`)."""
    assert load(text) == value


@pytest.mark.parametrize(
    "text",
    [
        "a:\n\tb: 1\n",
        "a:\n\tb\n",
        "a:\n  b: 1\n \tc: 2\n",
        "a:\n \tb: 1\n",
        "-\t- x\n",
        "- \t- x\n",
        "?\t- x\n",
        "-\tk: v\n",
        "- a\n\t- b\n",
        "a: |\n\tx\n",
        "a: |\n  x\n\t\nb: 1\n",
    ],
)
def test_a_tab_in_indentation_is_invalid_syntax(load, text):
    """A tab before a token on a line with no more spaces than its block, a tab before a block collection, and a tab
    in a block scalar's indentation (YAML 1.2.2 §6.1, §8.1.1)."""
    with pytest.raises(ScannerError) as raised:
        load(text)
    assert parse_code(raised.value) == "INVALID_SYNTAX"


@pytest.mark.parametrize(
    "text, value",
    [
        ("a: json\x85\n", {"a": "json\x85"}),
        ("a: metric\u2028\n", {"a": "metric\u2028"}),
        ('a: "x\x85y"\n', {"a": "x\x85y"}),
        ("a: 'x\u2029\n  y'\n", {"a": "x\u2029 y"}),
        ("a: |\n  x\u2028y\n", {"a": "x\u2028y\n"}),
        ("a: |\n  x\u2029y\n", {"a": "x\u2029y\n"}),
        ("a: >\n  x\x85y\n  z\n", {"a": "x\x85y z\n"}),
        ("a: x # y\x85z\n", {"a": "x"}),
        ("a\x85b: 1\n", {"a\x85b": 1}),
        ('a: "\\N\\L\\P\\uE000"\n', {"a": "\x85\u2028\u2029\ue000"}),
        ("a: \ue000\x85\n", {"a": "\ue000\x85"}),
    ],
)
def test_nel_ls_and_ps_are_ordinary_characters(load, text, value):
    """YAML 1.2 reads NEL, LS and PS as ordinary characters, not line breaks (§5.4), in every kind of scalar, in a
    comment and in a key; an escape writes its own character, and a character of the private use area is kept."""
    assert load(text) == value


@pytest.mark.parametrize(
    "character", ["\x96", "\x7f", "\x80", "\x9f", "\ufffe", "\uffff", "\ufeff"]
)
def test_a_quoted_scalar_takes_any_character_but_a_c0_control(load, character):
    """DEL, the C1 controls, U+FFFE, U+FFFF and U+FEFF, written raw (YAML 1.2.2 §5.1)."""
    assert load(f"a: \"F1{character}score\"\nb: 'x{character}y'\n") == {
        "a": f"F1{character}score",
        "b": f"x{character}y",
    }


@pytest.mark.parametrize(
    "template",
    [
        "a: x{}y\n",
        "a: x # {}\n",
        "# {}\na: x\n",
        "a: |\n  x{}y\n",
        "a: |  # {}\n  x\n",
        "a: |\t# {}\n  x\n",
        "%YAML 1.2 # {}\n---\na: x\n",
    ],
    ids=[
        "plain",
        "comment",
        "comment-line",
        "block-scalar",
        "block-scalar-header",
        "block-scalar-header-after-a-tab",
        "directive",
    ],
)
@pytest.mark.parametrize(
    "character", ["\x96", "\x7f", "\x92", "\ufffe", "\uffff", "\ufeff"]
)
def test_a_character_only_quoted_scalars_take_is_invalid_syntax_elsewhere(
    load, template, character
):
    """DEL, a C1 control other than NEL, U+FFFE, U+FFFF and U+FEFF in a plain scalar, a comment, a block scalar or a
    directive (YAML 1.2.2 [1] `c-printable`, [27] `nb-char`)."""
    with pytest.raises(ScannerError) as raised:
        load(template.format(character))
    assert parse_code(raised.value) == "INVALID_SYNTAX"


@pytest.mark.parametrize(
    "text", ["a: 1\n...\n\ufeff# c\n", "a: 1\n...\n\ufeff", "\ufeff\ufeffa: 1\n"]
)
def test_a_byte_order_mark_only_starts_the_file(load, text):
    """A byte order mark after `...`, though YAML 1.2.2 §5.2 allows one at the start of each document, and a second
    one at the start: spec §3 allows one only at the start of the file, outside a quoted scalar."""
    with pytest.raises(ScannerError) as raised:
        load(text)
    assert parse_code(raised.value) == "INVALID_SYNTAX"


@pytest.mark.parametrize(
    "text", ['a: "x\x01y"\n', "a: 'x\x1by'\n", "a: x\x00\n", "# \x08\na: 1\n"]
)
def test_a_c0_control_is_invalid_syntax_anywhere(load, text):
    """A C0 control other than tab, LF and CR, even in a quoted scalar (YAML 1.2.2 §5.1)."""
    with pytest.raises(ReaderError) as raised:
        load(text)
    assert parse_code(raised.value) == "INVALID_SYNTAX"


@pytest.mark.parametrize(
    "text, value",
    [
        ("# note\rb: 1\na: 2\n", {"b": 1, "a": 2}),
        ("a: 1\rb: 2\r", {"a": 1, "b": 2}),
        ("a: 1\r\nb: 2\r\n", {"a": 1, "b": 2}),
        ('a: "x\r  y"\n', {"a": "x y"}),
    ],
)
def test_a_cr_on_its_own_ends_a_line(load, text, value):
    """A CR, with or without an LF after it, is a line break (YAML 1.2.2 §5.4): it ends a comment."""
    assert load(text) == value


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
    assert _typed(load_json(text)) == _typed(value)


def _typed(value):
    """A JSON value with each scalar paired with its type, so that two compare equal only where each scalar has the
    same type too (`1`, `1.0` and `True` are equal in Python); a map's order doesn't count, as in JSON."""
    if isinstance(value, dict):
        return {key: _typed(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_typed(item) for item in value]
    return type(value), value
