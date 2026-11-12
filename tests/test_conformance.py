"""The conformance suite's analysis cases (`conformance/analyses/`) are well formed, as `conformance/README.md` says.

Each case's folder holds its files, its `expected.json` and perhaps a `setup.sh`, and nothing else. Its files hold no
`.gitignore` and nothing astra-spec's `.gitignore` ignores. Its `expected.json` follows `expected.schema.json`, names
rules of `rules.json`, gives a pointer only for a parse or schema code, and its
`valid` agrees with the levels of the codes it must report. The case builds: its `setup.sh` runs to completion, or its
files are committed once, and the folder `root` holds an `astra.yaml` in a git repository (in none, for a case of
`NOT_IN_REPOSITORY`), with no placeholder left.
The documents (`conformance/documents/`) are checked by `test_fixtures.py`.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft201909Validator

from .conftest import REPO_ROOT, rules_catalogue

CONFORMANCE = REPO_ROOT / "conformance"
ANALYSES = CONFORMANCE / "analyses"
CASES = sorted(ANALYSES.glob("[0-9]*"))
CASE_NAME = re.compile(r"[0-9]{3}(-[a-z0-9]+)+")

IDENTITY = {
    "NAME": "ASTRA conformance",
    "EMAIL": "conformance@astra.invalid",
    "DATE": "2026-01-01T00:00:00Z",
}
"""The author and committer of every commit a case makes, and its date."""

PLACEHOLDERS = (b"@commit:", b"@url:")
"""The start of each placeholder that `setup.sh` writes over: a commit's id, a remote's URL."""


def name(case: Path) -> str:
    """The case's folder, from `conformance/analyses/`."""
    return case.relative_to(ANALYSES).as_posix()


def expected(case: Path) -> dict[str, Any]:
    """The case's `expected.json`."""
    return json.loads((case / "expected.json").read_text(encoding="utf-8"))


def environment(place: Path) -> dict[str, str]:
    """What a case's git commands run with: no git configuration of the user's or the system's, git's file protocol
    allowed for submodules, a fixed identity and date, no repository found above `place`, and a folder in `place` for
    the case's remotes."""
    home = place / "home"
    remotes = place / "remotes"
    home.mkdir(exist_ok=True)
    remotes.mkdir(exist_ok=True)
    return {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "protocol.file.allow",
        "GIT_CONFIG_VALUE_0": "always",
        "GIT_CEILING_DIRECTORIES": str(place),
        "ASTRA_CASE_REMOTES": str(remotes),
        **{
            f"GIT_{who}_{what}": value
            for who in ("AUTHOR", "COMMITTER")
            for what, value in IDENTITY.items()
        },
    }


def build(case: Path, place: Path) -> Path:
    """Build `case` in the empty folder `place`, as `conformance/README.md` says: its files copied into a working
    folder, then its `setup.sh` run there, or, without one, a repository made with one commit of everything. Gives the
    working folder."""
    work = place / "work"
    shutil.copytree(case / "files", work, symlinks=True)
    setup = case / "setup.sh"
    if setup.is_file():
        commands = [["sh", "-eu", str(setup)]]
    else:
        commands = [
            ["git", "init", "--quiet"],
            ["git", "add", "--all"],
            ["git", "commit", "--quiet", "--message", "files"],
        ]
    for command in commands:
        process = subprocess.run(
            command, cwd=work, env=environment(place), capture_output=True, text=True
        )
        assert process.returncode == 0, process.stderr
    return work


def test_the_analyses_folder_holds_only_cases():
    assert [
        entry.name
        for entry in ANALYSES.iterdir()
        if not CASE_NAME.fullmatch(entry.name)
    ] == []
    assert CASES, "conformance/analyses/ holds no case"


@pytest.mark.parametrize("case", CASES, ids=name)
def test_a_case_holds_its_files_and_expected_json(case):
    assert (case / "files").is_dir()
    assert {entry.name for entry in case.iterdir()} - {"setup.sh"} == {
        "files",
        "expected.json",
    }


@pytest.mark.parametrize("case", CASES, ids=name)
def test_files_holds_what_astra_spec_keeps(case, tmp_path):
    """No `.gitignore`, which git would apply in astra-spec's own repository, and no path that astra-spec's
    `.gitignore` ignores, which that repository would leave out."""
    paths = [
        path.relative_to(REPO_ROOT).as_posix() for path in (case / "files").rglob("*")
    ]
    assert [path for path in paths if path.endswith("/.gitignore")] == []
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin"],
        cwd=REPO_ROOT,
        input="\n".join(paths),
        env=environment(tmp_path),
        capture_output=True,
        text=True,
    )
    assert ignored.returncode in (0, 1), ignored.stderr
    assert ignored.stdout.splitlines() == []


@pytest.mark.parametrize("case", CASES, ids=name)
def test_expected_json_follows_its_schema(case):
    schema = json.loads(
        (CONFORMANCE / "expected.schema.json").read_text(encoding="utf-8")
    )
    Draft201909Validator.check_schema(schema)
    errors = Draft201909Validator(schema).iter_errors(expected(case))
    assert [f"{list(e.absolute_path)}: {e.message}" for e in errors] == []


@pytest.mark.parametrize("case", CASES, ids=name)
def test_expected_json_names_rules(case):
    """Every code is a parse, schema or validator rule of `rules.json`; only a parse or schema code has a pointer,
    since the specification places no other (Schema files); `valid` is false exactly when a code that must be reported
    is a `MUST`; and no code is both reported and not."""
    case_expected = expected(case)
    rules = {
        rule["code"]: rule
        for rule in rules_catalogue()["rules"]
        if rule["layer"] in ("parse", "schema", "validator")
    }
    entries = case_expected.get("must_report", [])
    reported = [entry["code"] for entry in entries]
    not_reported = case_expected.get("must_not_report", [])
    assert [code for code in reported + not_reported if code not in rules] == []
    assert [
        entry["code"]
        for entry in entries
        if "pointer" in entry and rules[entry["code"]]["layer"] == "validator"
    ] == []
    assert case_expected["valid"] == all(
        rules[code]["level"] != "MUST" for code in reported
    )
    assert set(reported) & set(not_reported) == set()


@pytest.mark.parametrize("case", CASES, ids=name)
def test_a_case_builds(case, tmp_path):
    """The folder `root` holds an `astra.yaml`, in a git repository unless the case is one of `NOT_IN_REPOSITORY`, and
    no placeholder is left in the working folder."""
    case_expected = expected(case)
    work = build(case, tmp_path)
    root = work / case_expected.get("root", ".")
    assert (root / "astra.yaml").is_file()
    top = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        env=environment(tmp_path),
        capture_output=True,
        text=True,
    )
    outside = "NOT_IN_REPOSITORY" in [
        entry["code"] for entry in case_expected.get("must_report", [])
    ]
    assert (top.returncode != 0) == outside, top.stderr or top.stdout
    left = [
        path.relative_to(work).as_posix()
        for path in work.rglob("*")
        if ".git" not in path.relative_to(work).parts
        and path.is_file()
        and any(placeholder in path.read_bytes() for placeholder in PLACEHOLDERS)
    ]
    assert left == [], "setup.sh leaves a placeholder"
