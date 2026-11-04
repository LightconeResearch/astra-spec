"""The published page shows every cell of §9's rule tables as the same text as `rules.json`.

`tools/rules.py` reads §9 as CommonMark with GFM tables, as §9 says, but the site renders it with Python-Markdown and
Zensical's extensions. So a cell could read one way in `rules.json` and another on the page: `~~`, `==`, `^^`, emoji,
smart symbols (`-->`, `1/2`), `$…$`, footnotes, attribute lists, `\\|` in a code span, or a rule table right after a
paragraph, which Python-Markdown doesn't read as a table. Pinning the site's extensions can't remove the last two.

This test reads the built page and compares the text of each cell of its §9 rule tables (the tables with a Code column)
with the matching field of `rules.json`, rendered by markdown-it: the same rules, in the same order, word for word. It
runs in CI after `zensical build` (`test_pages_build.yaml`), and is skipped when there is no `site/`.
"""

from html.parser import HTMLParser
from typing import Any

import pytest
from markdown_it import MarkdownIt

from .conftest import REPO_ROOT, rules_catalogue

SITE = REPO_ROOT / "site"
PAGE = SITE / "specification" / "index.html"
SECTION = "9. Conformance"
"""The text of the `<h2>` whose rule tables are the catalogue, its permalink left out."""

COLUMNS = {
    "Code": "code",
    "Layer": "layer",
    "Level": "level",
    "Rule": "statement",
    "Status when broken": "status",
    "Source": "source",
}
"""Each column of a rule table, with the field of a rule in `rules.json` it shows."""

MARKDOWN = {"statement", "status", "source"}
"""The fields that are inline Markdown, rendered by markdown-it before their text is compared."""

pytestmark = pytest.mark.skipif(
    not SITE.is_dir(),
    reason="no built site: CI runs this test after `zensical build`",
)


def _words(text: str) -> str:
    """`text` with each run of white space as one space, and none at either end."""
    return " ".join(text.split())


class _Text(HTMLParser):
    """The text of an HTML fragment, its character references decoded."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_text(html: str) -> str:
    parser = _Text()
    parser.feed(html)
    parser.close()
    return _words("".join(parser.parts))


class _RuleTables(HTMLParser):
    """The tables of the page's §9, between its `<h2>` and the next `<h1>` or `<h2>`: each table's header and the text
    of each of its body rows' cells. The text of a heading leaves out its permalink (`<a class="headerlink">`)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[tuple[list[str], list[list[str]]]] = []
        self.sections = 0
        """How many `<h2>`s read `SECTION`."""
        self._inside = False
        self._heading: list[str] | None = None
        self._permalink = 0
        self._table: tuple[list[str], list[list[str]]] | None = None
        self._head = False
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("h1", "h2"):
            self._heading = []
        elif tag == "a" and self._heading is not None:
            if (
                self._permalink
                or "headerlink" in (dict(attrs).get("class") or "").split()
            ):
                self._permalink += 1
        elif not self._inside:
            return
        elif tag == "table":
            self._table = ([], [])
        elif tag == "thead":
            self._head = True
        elif tag == "tr":
            self._row = []
        elif tag in ("th", "td"):
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("h1", "h2") and self._heading is not None:
            text = _words("".join(self._heading))
            self._heading = None
            self._inside = text == SECTION
            self.sections += self._inside
        elif tag == "a" and self._permalink:
            self._permalink -= 1
        elif not self._inside:
            return
        elif tag in ("th", "td") and self._cell is not None and self._row is not None:
            self._row.append(_words("".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._head:
                self._table[0].extend(self._row)
            else:
                self._table[1].append(self._row)
            self._row = None
        elif tag == "thead":
            self._head = False
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None

    def handle_data(self, data: str) -> None:
        if self._heading is not None and not self._permalink:
            self._heading.append(data)
        if self._inside and self._cell is not None:
            self._cell.append(data)


def page_rules() -> list[dict[str, str]]:
    """Each row of the page's §9 rule tables, in order, as the text of each cell keyed by its column."""
    parser = _RuleTables()
    parser.feed(PAGE.read_text(encoding="utf-8"))
    parser.close()
    assert parser.sections == 1, (
        f"{PAGE} has {parser.sections} '{SECTION}' headings, not one"
    )
    return [
        dict(zip(header, row))
        for header, rows in parser.tables
        if "Code" in header
        for row in rows
    ]


def expected_text(rule: dict[str, Any], field: str) -> str:
    """The text a rule's field shows: inline Markdown rendered by markdown-it, a code, layer or level as it is."""
    value = rule[field]
    return (
        html_text(MarkdownIt("commonmark").renderInline(value))
        if field in MARKDOWN
        else value
    )


def test_page_shows_every_rule_as_rules_json_words_it():
    """The page's §9 rule tables hold the rules of `rules.json`, in order, each cell the text of its field."""
    assert PAGE.is_file(), f"{PAGE} is missing: build the site with `zensical build`"
    page = page_rules()
    rules = rules_catalogue()["rules"]
    assert [row.get("Code") for row in page] == [rule["code"] for rule in rules], (
        "the page's §9 rule tables don't hold the rules of rules.json, in order: rebuild the site after `just gen-schema`"
    )
    differences = []
    for row, rule in zip(page, rules):
        # Only the parse and schema table has a Layer column: the other tables' layer is their subsection.
        fields = sorted(field for field in rule if field != "layer" or "Layer" in row)
        shown = sorted(COLUMNS.get(column, column) for column in row)
        if shown != fields:
            differences.append(
                f"{rule['code']}: the page shows {shown}, rules.json has {fields}"
            )
            continue
        for column, text in row.items():
            expected = expected_text(rule, COLUMNS[column])
            if text != expected:
                differences.append(
                    f"{rule['code']}, {column}: the page shows {text!r}, rules.json {expected!r}"
                )
    assert differences == []
