"""The patch guard of `just release` (`tools/check_patch.py`): a patch release changes nothing that is valid.

It is tested on copies of the committed contract, stamped as releases of 0.1, and once through git, as `just release`
runs it.
"""

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from check_patch import RULES, SCHEMAS, differences, location, unversioned

from .conftest import PROJECT, REPO_ROOT

CLI = REPO_ROOT / "tools" / "check_patch.py"
NAMESPACE = "https://w3id.org/astra/"
"""Where the contract is published, before each file's series."""


def contract(series: str = "0.1", version: str = "0.1.0") -> dict[str, Any]:
    """The committed JSON Schemas and `rules.json`, parsed, with their ids under `series` and stamped `version`."""
    files = {}
    for name in (*SCHEMAS, RULES):
        document = json.loads((PROJECT / location(name)).read_text(encoding="utf-8"))
        if name == RULES:
            document["errors"] = {
                _restamp(key, series): code for key, code in document["errors"].items()
            }
        else:
            document["$id"] = _restamp(document["$id"], series)
        document["$comment"] = document["$comment"].rsplit(" ", 1)[0] + " " + version
        files[name] = document
    return files


def _restamp(uri: str, series: str) -> str:
    """`uri`, an `$id` or a location under one, with its series replaced by `series`."""
    base, hash_, pointer = uri.partition("#")
    namespace, _, name = base.rpartition("/")
    return namespace.rpartition("/")[0] + "/" + series + "/" + name + hash_ + pointer


def texts(files: dict[str, Any]) -> dict[str, str]:
    return {
        name: json.dumps(document, indent=2) + "\n" for name, document in files.items()
    }


def test_unversioned_drops_the_series():
    assert (
        unversioned(NAMESPACE + "0.1/analysis.schema.json#/properties/a/b")
        == NAMESPACE + "analysis.schema.json#/properties/a/b"
    )
    assert unversioned(NAMESPACE + "0.1.0rc1/rules.json") == NAMESPACE + "rules.json"


def test_the_same_contract_passes():
    release = contract()
    assert differences(texts(release), texts(copy.deepcopy(release))) == []


def test_descriptions_titles_and_comments_may_change():
    release, patch = contract(), contract(version="0.1.1")
    analysis = patch["analysis.schema.json"]
    analysis["description"] = "Reworded."
    analysis["title"] = "reworded"
    first = next(iter(analysis["$defs"].values()))
    first["description"] = "Reworded too."
    patch[RULES]["rules"][0]["statement"] = "Reworded as well"
    assert differences(texts(release), texts(patch)) == []


def test_a_pre_release_of_a_patch_is_compared_without_its_series():
    assert differences(texts(contract()), texts(contract("0.1.1rc1", "0.1.1rc1"))) == []


def test_a_changed_pattern_fails():
    release, patch = contract(), contract(version="0.1.2")
    properties = patch["analysis.schema.json"]["properties"]
    properties["spec_version"]["pattern"] = "^[0-9]+$"
    lines = differences(texts(release), texts(patch), "v0.1.0")
    assert lines[:2] == [
        "--- v0.1.0:analysis.schema.json\n",
        "+++ analysis.schema.json\n",
    ]
    assert any(line.startswith("+") and "^[0-9]+$" in line for line in lines)


def test_a_field_named_like_an_annotation_is_compared():
    """Only a string-valued `description`, `title` or `$comment` is an annotation: a field of that name is not."""
    release, patch = contract(), contract(version="0.1.1")
    field = patch["analysis.schema.json"]["$defs"]["Insight__identifier_optional"][
        "properties"
    ]["description"]
    field["description"] = "Reworded."
    assert differences(texts(release), texts(patch)) == []
    field["type"] = "integer"
    assert differences(texts(release), texts(patch)) != []
    del patch["analysis.schema.json"]["$defs"]["Insight__identifier_optional"][
        "properties"
    ]["description"]
    assert differences(texts(release), texts(patch)) != []


@pytest.mark.parametrize("change", ["code", "key", "added"])
def test_a_changed_error_map_fails(change):
    release, patch = contract(), contract(version="0.1.1")
    errors = patch[RULES]["errors"]
    key = next(iter(errors))
    if change == "code":
        errors[key] = "WRONG_TYPE" if errors[key] != "WRONG_TYPE" else "INVALID_ID"
    elif change == "key":
        errors[key + "/x"] = errors.pop(key)
    else:
        errors[key + "/x"] = errors[key]
    lines = differences(texts(release), texts(patch))
    assert lines and lines[0] == "--- release:rules.json\n"


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_the_cli_compares_with_a_tag_through_git(tmp_path):
    """As `just release` runs it: the release's files come from the tag, the patch's from the working tree."""
    project = tmp_path / "project"

    def write(files: dict[str, Any]) -> None:
        for name, text in texts(files).items():
            path = project / location(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    git(tmp_path, "init", "--quiet")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "user.email", "test@example.org")
    write(contract())
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "--quiet", "-m", "Release v0.1.0")
    git(tmp_path, "tag", "v0.1.0")

    def run() -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(CLI), "v0.1.0"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

    patch = contract(version="0.1.1")
    patch["analysis.schema.json"]["description"] = "Reworded."
    write(patch)
    passed = run()
    assert passed.returncode == 0, passed.stderr
    assert passed.stdout.startswith("Nothing a patch release may not change")

    patch["analysis.schema.json"]["properties"]["spec_version"]["pattern"] = "^x$"
    write(patch)
    failed = run()
    assert failed.returncode == 1
    assert "+++ analysis.schema.json" in failed.stdout
    assert "changes what is valid since v0.1.0" in failed.stderr

    missing = subprocess.run(
        [sys.executable, str(CLI), "v9.9.9"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode != 0
    assert "v9.9.9" in missing.stderr
