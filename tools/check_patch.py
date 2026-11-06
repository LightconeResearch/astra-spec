"""Check that a patch release leaves what is valid as an earlier release of its minor version has it.

A patch release never changes what is valid (spec §5), so `just release` runs this before it commits a version whose
minor version already has a release, against that minor version's greatest release `<tag>`. The regenerated files in
`src/astra/schema/generated/` must match the tag's:

- each of the three JSON Schemas, once every string-valued `description`, `title` and `$comment` is dropped;
- `rules.json`'s `errors`, keys and codes.

The series a file's ids carry is set aside, so that a pre-release (whose ids carry its whole version) is compared too.
Any other difference is printed as a diff, and the exit status is 1. The check covers the schema layer: the validator
and check layers rest on review.
"""

import argparse
import difflib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMAS = (
    "analysis.schema.json",
    "provenance.schema.json",
    "provenance.open.schema.json",
)
"""The JSON Schemas compared, by file name."""

RULES = "rules.json"

TEXT = ("description", "title", "$comment")
"""Keywords whose string value a patch release may change: they annotate a schema and constrain nothing."""

GENERATED = Path("src/astra/schema/generated")


def unversioned(uri: str) -> str:
    """`uri`, a schema's `$id` or a location under it, with the series in front of its file name left out.

    `https://w3id.org/astra/0.1/analysis.schema.json#/properties` becomes
    `https://w3id.org/astra/analysis.schema.json#/properties`.
    """
    base, hash_, pointer = uri.partition("#")
    namespace, _, name = base.rpartition("/")
    return namespace.rpartition("/")[0] + "/" + name + hash_ + pointer


def constraints(node: Any) -> Any:
    """`node`, a JSON Schema or part of one, without its annotations, and with its `$id` unversioned."""
    if isinstance(node, list):
        return [constraints(item) for item in node]
    if not isinstance(node, dict):
        return node
    result = {
        key: constraints(value)
        for key, value in node.items()
        if not (key in TEXT and isinstance(value, str))
    }
    if isinstance(result.get("$id"), str):
        result["$id"] = unversioned(result["$id"])
    return result


def error_map(catalogue: dict[str, Any]) -> dict[str, str]:
    """`rules.json`'s `errors`, with each key unversioned."""
    return {unversioned(key): code for key, code in catalogue.get("errors", {}).items()}


def comparable(name: str, text: str) -> str:
    """What of the file `name`, holding `text`, a patch release must keep, as indented JSON with sorted keys."""
    document = json.loads(text)
    kept = error_map(document) if name == RULES else constraints(document)
    return json.dumps(kept, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def differences(
    release: dict[str, str], patch: dict[str, str], tag: str = "release"
) -> list[str]:
    """A unified diff, line by line, of what the files `patch` change from `release` (each a file name and its text).

    Empty when the patch changes nothing a patch release may not change.
    """
    lines: list[str] = []
    for name in (*SCHEMAS, RULES):
        before = comparable(name, release[name]).splitlines(keepends=True)
        after = comparable(name, patch[name]).splitlines(keepends=True)
        lines += difflib.unified_diff(before, after, f"{tag}:{name}", name)
    return lines


def released(tag: str, directory: Path) -> dict[str, str]:
    """The text of each compared file in `directory` as it was at `tag`, read through `git show`."""
    files = {}
    for name in (*SCHEMAS, RULES):
        path = (directory / name).as_posix()
        shown = subprocess.run(
            ["git", "show", f"{tag}:./{path}"],
            capture_output=True,
            check=False,
        )
        if shown.returncode != 0:
            raise SystemExit(
                f"{tag}:{path}: {shown.stderr.decode(errors='replace').strip()}"
            )
        files[name] = shown.stdout.decode("utf-8")
    return files


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Fail if the generated contract changes what is valid since the release TAG of its minor version."
    )
    parser.add_argument("tag", help="the release to compare with, such as v0.1.0")
    parser.add_argument(
        "--generated",
        type=Path,
        default=GENERATED,
        metavar="DIR",
        help=f"the directory of the generated files, relative to the repository's working tree (default: {GENERATED})",
    )
    args = parser.parse_args(argv)
    patch = {
        name: (args.generated / name).read_text(encoding="utf-8")
        for name in (*SCHEMAS, RULES)
    }
    lines = differences(released(args.tag, args.generated), patch, args.tag)
    if lines:
        sys.stdout.writelines(lines)
        raise SystemExit(
            f"A patch release changes what is valid since {args.tag}: only descriptions, titles and comments may change."
        )
    print(f"Nothing a patch release may not change differs from {args.tag}.")


if __name__ == "__main__":
    main()
