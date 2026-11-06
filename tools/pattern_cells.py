"""Write each Regex Pattern cell of the field reference as HTML, so that the site shows the pattern exactly.

`gen-doc` writes a pattern as a Markdown code span in a table row, `| Regex Pattern | `<pattern>` |`. On the site, a
backtick in the pattern ends the span early, a `|` splits the cell, `[^` reads as a footnote and `^…^` as superscript.
So `just gen-doc` runs this on `docs/elements/` after `gen-doc`: each such cell becomes `<code>…</code>`, with every
character other than an ASCII letter or digit written as a numeric character reference, which no Markdown extension
reads. A row already written so is left as it is; any other Regex Pattern row fails.

Usage: python tools/pattern_cells.py <directory>
"""

import argparse
import sys
from pathlib import Path

ROW = "| Regex Pattern | "
"""How a Regex Pattern row starts."""

SPAN = ("`", "` |")
"""What `gen-doc` writes around a pattern, after `ROW`."""

HTML = ("<code>", "</code> |")
"""What this writes around a pattern, after `ROW`."""


def as_html(pattern: str) -> str:
    """`pattern`'s characters, each other than an ASCII letter or digit as a numeric character reference."""
    return "".join(
        c if c.isascii() and c.isalnum() else f"&#{ord(c)};" for c in pattern
    )


def rewrite(text: str, name: str) -> str:
    """`text`, a page of the field reference, with each Regex Pattern cell written as HTML."""
    lines = text.split("\n")
    for number, line in enumerate(lines, 1):
        if not line.startswith(ROW):
            continue
        cell = line[len(ROW) :]
        if cell.startswith(HTML[0]) and cell.endswith(HTML[1]):
            continue
        start, end = SPAN
        if not (
            cell.startswith(start)
            and cell.endswith(end)
            and len(cell) > len(start) + len(end)
        ):
            raise ValueError(
                f"{name}:{number}: a Regex Pattern row not written as `{ROW}{start}…{end}`"
            )
        pattern = cell[len(start) : -len(end)]
        lines[number - 1] = f"{ROW}{HTML[0]}{as_html(pattern)}{HTML[1]}"
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "directory", type=Path, help="the field reference's pages, docs/elements/"
    )
    args = parser.parse_args(argv)
    try:
        for page in sorted(args.directory.glob("*.md")):
            text = page.read_text(encoding="utf-8")
            rewritten = rewrite(text, str(page))
            if rewritten != text:
                page.write_text(rewritten, encoding="utf-8")
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
