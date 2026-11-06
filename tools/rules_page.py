"""The All rules page: every rule of the specification, by layer, then its recommendations and permissions.

`rules_page.py SPEC OUT` reads the specification `SPEC` and writes the page, Markdown, to `OUT`; the docs build writes
it as `docs/rules.md`, and it is never edited by hand. Each rule is linked to the section that states it, its source:
`§7 Inputs` links to the heading `### 7. Inputs` of `specification.md`, at the anchor the site gives it.
"""

import argparse
import re
import unicodedata
from pathlib import Path

from rules import SECTION_LAYERS, extract_notes, extract_rules

SPECIFICATION = "specification.md"
"""The specification's page, as the page links to it."""

INTRO = (
    "This page is generated from the [specification](specification.md): every rule, by layer, with a link to the"
    " section that states it."
)


def anchor(source: str) -> str:
    """The anchor of the section `source` names: `§7 Inputs` names the heading `7. Inputs`, whose anchor is `7-inputs`.

    The anchor is the heading's text as the site's table of contents makes it: in ASCII, with its punctuation dropped,
    in lower case, and each run of spaces and hyphens one hyphen.
    """
    number, _, title = source.removeprefix("§").partition(" ")
    if not (source.startswith("§") and number.isascii() and number.isdigit() and title):
        raise ValueError(f"{source!r} is not a section, `§<n> <title>`")
    text = unicodedata.normalize("NFKD", f"{number}. {title}")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def _link(source: str) -> str:
    """A link to the section `source` names, with `source` as its text."""
    return f"[{source}]({SPECIFICATION}#{anchor(source)})"


def _row(cells: list[str]) -> str:
    """A table row of `cells`, each inline Markdown, with any `|` escaped so that it stays in its cell."""
    return "| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |"


def render_rules_page(rules: list[dict], notes: list[dict]) -> str:
    """The page, Markdown, for `rules` (as `rules.json` gives them) and `notes` (as `extract_notes` gives them).

    A `## <Layer>` per layer that has rules, in the order of `SECTION_LAYERS`, with a table of its rules in their
    order: Code, Level, Rule, Status when broken for the check layer, and Section. Then, if there are notes, a
    `## Recommendations and permissions` with one item each.
    """
    unknown = [rule["code"] for rule in rules if rule["layer"] not in SECTION_LAYERS]
    if unknown:
        raise ValueError(f"rules of no layer of {SECTION_LAYERS}: {unknown}")
    lines = ["# All rules", "", INTRO, ""]
    for layer in SECTION_LAYERS:
        layer_rules = [rule for rule in rules if rule["layer"] == layer]
        if not layer_rules:
            continue
        columns = ["Code", "Level", "Rule"]
        if layer == "check":
            columns.append("Status when broken")
        lines += [f"## {layer.capitalize()}", "", _row([*columns, "Section"])]
        lines.append("|" + "---|" * (len(columns) + 1))
        for rule in layer_rules:
            cells = [f"`{rule['code']}`", rule["level"], rule["statement"]]
            if layer == "check":
                cells.append(rule["status"])
            lines.append(_row([*cells, _link(rule["source"])]))
        lines.append("")
    if notes:
        lines += ["## Recommendations and permissions", ""]
        for note in notes:
            kind = note["kind"].capitalize()
            lines.append(f"- **{kind}** ({_link(note['source'])}): {note['text']}")
        lines.append("")
    return "\n".join(lines)


def read_specification(markdown: str) -> tuple[list[dict], list[dict]]:
    """The rules and the notes of the specification `markdown`: those of the codes tables and the notes of its Part II
    (`tools/rules.py`)."""
    return extract_rules(markdown), extract_notes(markdown)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Write the All rules page, from the specification."
    )
    parser.add_argument("specification", type=Path, help="the specification (Markdown)")
    parser.add_argument("out", type=Path, help="the page to write (Markdown)")
    args = parser.parse_args(argv)
    rules, notes = read_specification(args.specification.read_text(encoding="utf-8"))
    args.out.write_text(render_rules_page(rules, notes), encoding="utf-8")


if __name__ == "__main__":
    main()
