"""The fixture harness: YAML 1.2 loading, the generated validators and the fixture headers (design §9)."""

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft201909Validator
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATED = REPO_ROOT / "src" / "astra" / "schema" / "generated"
DATA = REPO_ROOT / "tests" / "data"

_SCHEMA_NAMES = {"Analysis": "analysis", "ProvenanceRecord": "provenance"}
"""Each fixture root, with the name of its generated schema."""

_RULE_LINE = re.compile(r"# rule: ([A-Z][A-Z_]*)")
_FAILS_AT_LINE = re.compile(r"# fails at: (\(root\)|parse|(/[^/]*)+)")


def load_yaml(path: Path) -> Any:
    """The document in `path`, read as YAML 1.2; raises `DuplicateKeyError` on a repeated key."""
    return YAML(typ="safe", pure=True).load(path)


def validator(root: str, *, closed: bool = True) -> Draft201909Validator:
    """A validator for documents rooted at `root`, from the committed schema (its open variant if not `closed`)."""
    suffix = ".schema.json" if closed else ".open.schema.json"
    schema = json.loads((GENERATED / f"{_SCHEMA_NAMES[root]}{suffix}").read_text(encoding="utf-8"))
    return Draft201909Validator(schema)


def _pointer(path) -> str:
    """The JSON Pointer for a path of keys and indices, or `(root)` for the document."""
    if not path:
        return "(root)"
    return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in path)


def error_pointers(v: Draft201909Validator, doc: Any) -> set[str]:
    """The JSON Pointer of every error `v` reports for `doc`, and of every error in each one's context."""
    return {_pointer(e.absolute_path) for error in v.iter_errors(doc) for e in (error, *error.context)}


def fixture_header(path: Path) -> tuple[str, str]:
    """`(rule, fails_at)` from an invalid fixture's first two lines."""
    lines = path.read_text(encoding="utf-8").splitlines()[:2]
    rule = _RULE_LINE.fullmatch(lines[0]) if lines else None
    fails_at = _FAILS_AT_LINE.fullmatch(lines[1]) if len(lines) > 1 else None
    if rule is None or fails_at is None:
        raise ValueError(f"{path.name}: lines 1-2 must be '# rule: <CODE>' and '# fails at: <location>'")
    return rule[1], fails_at[1]


def fixtures(kind: str) -> list[Path]:
    """The fixtures of `kind` (`valid` or `invalid`), sorted."""
    return sorted((DATA / kind).glob("*.yaml"))
