"""Every fixture, through the committed JSON Schema: valid ones pass, invalid ones fail where they say, and why (design §9).

Why is read from `rules.json`, as a tool reads it: each error's absolute keyword location maps to its code (D13).
"""

from pathlib import Path

import pytest
from ruamel.yaml.error import YAMLError

from .conftest import (
    DATA,
    errors,
    fixture_header,
    fixtures,
    load_document,
    load_yaml,
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

    A parse fixture's loader error has its rule's code (`parse_code`), and the fixture has no `# also:` line. A
    schema fixture's errors are reported at `fails at`, where `rules.json` gives them its rule, and nowhere else but
    at the pointer of its `# also:` line, if it has one, where they must be reported too, with that line's code. A
    key that isn't a string is an `INVALID_ID` error at its map: `load_document` reports it and leaves its entry out,
    so it isn't found through `rules.json`, and the validator checks the rest of the document (spec §3).
    """
    rule, fails_at, also = fixture_header(path)
    if fails_at == "parse":
        assert layer_of(rule) == "parse", f"{rule} is not a parse-layer code"
        assert also is None, "a parse fixture has no '# also:' line"
        try:
            load_yaml(path)
        except YAMLError as error:
            code = parse_code(error)
        else:
            code = None
        assert code == rule
        return
    assert layer_of(rule) == "schema", f"{rule} is not a schema-layer code"
    expected = {fails_at: rule}
    if also is not None:
        also_code, also_at = also
        assert layer_of(also_code) == "schema", (
            f"{also_code} is not a schema-layer code"
        )
        assert also_at != fails_at, "'# also:' names the place it fails at"
        expected[also_at] = also_code
    error_map = rules_catalogue()["errors"]
    document, left_out = load_document(path)
    found = errors(validator(root_of(path)), document)
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
    assert codes == {at: {code} for at, code in expected.items()}


@pytest.mark.parametrize("path", fixtures("valid"), ids=lambda path: path.stem)
def test_valid_fixture(path):
    v = validator(root_of(path))
    assert [
        f"{list(e.absolute_path)}: {e.message}" for e in v.iter_errors(load_yaml(path))
    ] == []


@pytest.mark.parametrize("path", fixtures("invalid"), ids=lambda path: path.stem)
def test_invalid_fixture(path):
    check_invalid_fixture(path)


# --- The check itself: it fails a fixture whose header says less, or other, than what fails ---

_TWO_SOURCES_AND_A_SHORT_COMMIT = """\
spec_version: "0.1.0"
outputs:
  result:
    type: metric
    format: json
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
