"""Every fixture, through the committed JSON Schema: valid ones pass, invalid ones fail where they say, and why (design §9).

Why is read from `rules.json`, as a tool reads it: each error's absolute keyword location maps to its code (D13).
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

from .conftest import (
    DATA,
    PARSE_ERRORS,
    errors,
    fixture_header,
    fixtures,
    header_file,
    load_document,
    load_fixture,
    load_json,
    parse_code,
    rules_catalogue,
    validator,
)


def root_of(path: Path) -> str:
    """The class a fixture is a document of: its file name up to the first `-`."""
    return path.name.split("-", 1)[0]


def layer_of(code: str) -> str | None:
    """The layer of the rule `code` in `rules.json`, or None if it has no such rule."""
    return {rule["code"]: rule["layer"] for rule in rules_catalogue()["rules"]}.get(
        code
    )


def check_invalid_fixture(path: Path) -> None:
    """Assert that the fixture at `path` fails exactly as its header says.

    A record (`.json`) is read by `load_json`, and its header is in its sidecar (`header_file`). A parse fixture's
    loader error has its rule's code (`parse_code`), and the fixture has no `# also:` line. A schema fixture's errors
    are reported at `fails at`, where `rules.json` gives them its rule, and nowhere else but at the pointer of its
    `# also:` line, if it has one, where they must be reported too, with that line's code. A key of an `astra.yaml`
    that isn't a string is an `INVALID_ID` error at its map: `load_document` reports it and leaves its entry out, so
    it isn't found through `rules.json`, and the validator checks the rest of the document (spec §3).
    """
    rule, fails_at, also = fixture_header(path)
    if fails_at == "parse":
        assert layer_of(rule) == "parse", f"{rule} is not a parse-layer code"
        assert also is None, "a parse fixture has no '# also:' line"
        try:
            load_fixture(path)
        except PARSE_ERRORS as error:
            code = parse_code(error)
        else:
            code = None
        assert code == rule
        return
    assert layer_of(rule) == "schema", f"{rule} is not a schema-layer code"
    expected = {fails_at: {rule}}
    if also is not None:
        also_code, also_at = also
        assert layer_of(also_code) == "schema", (
            f"{also_code} is not a schema-layer code"
        )
        assert also_at != fails_at, "'# also:' names the place it fails at"
        expected[also_at] = {also_code}
    document, left_out = (
        (load_json(path), []) if path.suffix == ".json" else load_document(path)
    )
    check_schema_errors(root_of(path), document, expected, left_out)


def check_schema_errors(
    root: str,
    document: Any,
    expected: dict[str, set[str]],
    left_out: Sequence[tuple[str, str]] = (),
    *,
    closed: bool = True,
) -> None:
    """Assert that `document`, rooted at `root`, fails the committed schema (its open variant if not `closed`) exactly
    as `expected` says: at each of its pointers, with errors that `rules.json` gives exactly that pointer's codes, and
    nowhere else.

    An error that explains a failing `oneOf` at its own pointer adds no code. Each of `left_out`, the map pointer and
    key of an entry `load_document` left out since its key isn't a string, is an `INVALID_ID` error at that map.
    """
    error_map = rules_catalogue()["errors"]
    found = errors(validator(root, closed=closed), document)
    assert sorted({location for _, location, _ in found} - error_map.keys()) == []
    keys = {(pointer, "INVALID_ID") for pointer, _ in left_out}
    elsewhere = {
        (pointer, location) for pointer, location, _ in found if pointer not in expected
    } | {(pointer, code) for pointer, code in keys if pointer not in expected}
    assert elsewhere == set()
    codes = {
        at: {
            error_map[location]
            for pointer, location, explains in found
            if pointer == at and not explains
        }
        | {code for pointer, code in keys if pointer == at}
        for at in expected
    }
    assert codes == expected


@pytest.mark.parametrize("path", fixtures("valid"), ids=lambda path: path.stem)
def test_valid_fixture(path):
    v = validator(root_of(path))
    assert [
        f"{list(e.absolute_path)}: {e.message}"
        for e in v.iter_errors(load_fixture(path))
    ] == []


@pytest.mark.parametrize("path", fixtures("invalid"), ids=lambda path: path.stem)
def test_invalid_fixture(path):
    check_invalid_fixture(path)


_PRE_0_1 = """\
version: "0.0.11"
name: Iris classification
outputs:
  accuracy:
    type: metric
    format: json
    recipe:
      command: python make.py '{output}'
"""
"""An `astra.yaml` as written before 0.1: a `version` and a `name`, and no `spec_version`."""


def test_a_file_without_spec_version_reports_every_schema_error():
    """A file whose `spec_version` is missing is checked against the validator's own schema, and every schema error
    in it is reported (spec §1, §9 *What is checked*): a pre-0.1 file lacks `spec_version` (MISSING_FIELD) and has
    `version` and `name` (UNKNOWN_FIELD), both at the document. An invalid fixture names one code at each place, so
    this is a test of its own."""
    document, left_out = load_document(_PRE_0_1)
    assert left_out == []
    error_map = rules_catalogue()["errors"]
    found = errors(validator("Analysis"), document)
    assert {
        (pointer, error_map[location]) for pointer, location, explains in found
    } == {("(root)", "MISSING_FIELD"), ("(root)", "UNKNOWN_FIELD")}


SUFFIXES = {"Analysis": ".yaml", "ProvenanceRecord": ".json"}
"""The file suffix of each fixture root: an `astra.yaml` is YAML, a record JSON (spec §3)."""


def test_every_fixture_is_written_as_its_kind_of_file():
    """Every file in the fixture folders is an `astra.yaml` (`.yaml`), a record (`.json`), or a record's header
    sidecar (`.header`) beside its record, and every invalid record has one."""
    problems = []
    for kind in ("valid", "invalid"):
        for path in sorted((DATA / kind).iterdir()):
            if path.suffix == ".header":
                if not path.with_suffix(".json").is_file():
                    problems.append(f"{kind}/{path.name}: no record beside it")
            elif SUFFIXES.get(root_of(path)) != path.suffix:
                problems.append(f"{kind}/{path.name}: not a {root_of(path)} fixture")
            elif kind == "invalid" and not header_file(path).is_file():
                problems.append(f"{kind}/{path.name}: no header sidecar")
    assert problems == []


# --- The check itself: it fails a fixture whose header says less, or other, than what fails ---

_TWO_SOURCES_AND_A_SHORT_COMMIT = """\
spec_version: "0.1.0"
outputs:
  result:
    type: metric
    format: json
    recipe:
      command: python make.py '{output}'
analyses:
  up:
    path: up
    url: https://x/y
    commit: "abc1234"
"""
"""A declaration with both `path` and `url` (INVALID_DECLARATION_SOURCE) and a short commit (INVALID_COMMIT)."""

_FIXTURE_159 = DATA / "invalid" / "Analysis-159-path-null-beside-url.yaml"
_FIXTURE_101 = DATA / "invalid" / "Analysis-101-duplicate-output.yaml"


def _body(path: Path) -> str:
    """A committed fixture's document, without its two header lines."""
    return "".join(path.read_text(encoding="utf-8").splitlines(keepends=True)[2:])


MISLABELLED = {
    "duplicate-key-headed-syntax": (
        "# rule: INVALID_SYNTAX\n"
        "# fails at: parse\n"
        'spec_version: "0.1.0"\n'
        'spec_version: "0.1.0"\n'
    ),
    "second-break-undeclared": (
        "# rule: INVALID_COMMIT\n"
        "# fails at: /analyses/up/commit\n" + _TWO_SOURCES_AND_A_SHORT_COMMIT
    ),
    "second-break-declared-with-another-code": (
        "# rule: INVALID_COMMIT\n"
        "# fails at: /analyses/up/commit\n"
        "# also: INVALID_EVIDENCE_SOURCE at /analyses/up\n"
        + _TWO_SOURCES_AND_A_SHORT_COMMIT
    ),
    "also-not-reported": (
        "# rule: WRONG_TYPE\n"
        "# fails at: /analyses/up/path\n"
        "# also: INVALID_DECLARATION_SOURCE at /analyses/up\n" + _body(_FIXTURE_159)
    ),
    "also-on-a-parse-fixture": (
        "# rule: DUPLICATE_KEY\n"
        "# fails at: parse\n"
        "# also: INVALID_ID at /outputs\n" + _body(_FIXTURE_101)
    ),
}
"""Scratch fixtures whose header doesn't say exactly how they fail, each of which the check must reject.

The first's loader error is DUPLICATE_KEY. The next two break two rules, and declare the second not at all, or with
the wrong code. Analysis-159 reports WRONG_TYPE alone (its declaration's checks are guarded by type), so an
`# also:` line on it names an error that isn't reported. A parse fixture has no `# also:` line.
"""


@pytest.mark.parametrize("name", MISLABELLED)
def test_check_rejects_a_fixture_whose_header_is_wrong(tmp_path, name):
    path = tmp_path / f"Analysis-901-{name}.yaml"
    path.write_text(MISLABELLED[name], encoding="utf-8")
    with pytest.raises(AssertionError):
        check_invalid_fixture(path)


_RECORD_201 = DATA / "invalid" / "ProvenanceRecord-201-no-content-hash.json"

MISLABELLED_RECORDS = {
    "repeated-name-headed-syntax": (
        "# rule: INVALID_SYNTAX\n# fails at: parse\n",
        '{"spec_version": "0.1.0", "spec_version": "0.1.0"}\n',
    ),
    "comment-headed-duplicate-key": (
        "# rule: DUPLICATE_KEY\n# fails at: parse\n",
        '// a comment\n{"spec_version": "0.1.0"}\n',
    ),
    "schema-break-headed-parse": (
        "# rule: INVALID_SYNTAX\n# fails at: parse\n",
        _RECORD_201.read_text(encoding="utf-8"),
    ),
    "schema-break-at-another-place": (
        "# rule: MISSING_FIELD\n# fails at: /generated_by\n",
        _RECORD_201.read_text(encoding="utf-8"),
    ),
}
"""Scratch records, each a `(header, record)`, whose header doesn't say exactly how they fail: a repeated name is
DUPLICATE_KEY, a comment INVALID_SYNTAX, and record 201 parses, and fails at `(root)`."""


@pytest.mark.parametrize("name", MISLABELLED_RECORDS)
def test_check_rejects_a_record_whose_header_is_wrong(tmp_path, name):
    header, record = MISLABELLED_RECORDS[name]
    path = tmp_path / f"ProvenanceRecord-901-{name}.json"
    path.write_text(record, encoding="utf-8")
    path.with_suffix(".header").write_text(header, encoding="utf-8")
    with pytest.raises(AssertionError):
        check_invalid_fixture(path)


def test_a_record_without_its_header_sidecar_is_an_error(tmp_path):
    path = tmp_path / "ProvenanceRecord-901-no-header.json"
    path.write_text(_RECORD_201.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(ValueError, match="header file"):
        fixture_header(path)


def test_check_accepts_the_second_error_its_also_line_declares(tmp_path):
    path = tmp_path / "Analysis-901-second-break-declared.yaml"
    path.write_text(
        "# rule: INVALID_COMMIT\n"
        "# fails at: /analyses/up/commit\n"
        "# also: INVALID_DECLARATION_SOURCE at /analyses/up\n"
        + _TWO_SOURCES_AND_A_SHORT_COMMIT,
        encoding="utf-8",
    )
    check_invalid_fixture(path)


def test_fixture_header_reads_a_code_with_a_digit(tmp_path):
    """A code is `[A-Z][A-Z0-9_]*`, as the specification's §9 and `tools/rules.py` write it."""
    path = tmp_path / "Analysis-901-digit-code.yaml"
    path.write_text(
        "# rule: SHA256_MISMATCH\n"
        "# fails at: /outputs\n"
        "# also: SHA256_MISMATCH at (root)\n"
        'spec_version: "0.1.0"\n',
        encoding="utf-8",
    )
    assert fixture_header(path) == (
        "SHA256_MISMATCH",
        "/outputs",
        ("SHA256_MISMATCH", "(root)"),
    )
