"""The published page shows every cell of its codes tables as the same text as `rules.json`, every in-page link of the
specification goes to an element of it, the All rules page shows every rule of `rules.json` under its layer, and the
field reference shows every pattern as the LinkML sources write it.

`tools/rules.py` reads the codes tables as CommonMark with GFM tables, but the site renders them with Python-Markdown
and Zensical's extensions. So a cell could read one way in `rules.json` and another on the page: `~~`, `==`, `^^`,
emoji, smart symbols (`-->`, `1/2`), `$…$`, footnotes, attribute lists, `\\|` in a code span, or a codes table right
after a paragraph, which Python-Markdown doesn't read as a table. Pinning the site's extensions can't remove the last
two.

So a test reads the built page and compares the text of each cell of every codes table (a table whose first column is
Code) with the matching field of `rules.json`, rendered by markdown-it: the same rules, in the same order, word for
word, each table under the heading of the section its rules name as their source. Another checks that every link of
the page to a fragment of the page names an element there.

The field reference's pages are built from `gen-doc`'s Markdown, where a pattern's backtick, `|`, `[^` or `^` would be
read as Markdown. So another test reads each element's page and compares its Regex Pattern cell with the pattern the
LinkML sources write. The All rules page (`tools/rules_page.py`) is written by the docs build, and a last test reads
it. The tests run in CI after the docs build (`main.yaml`, `test_pages_build.yaml`), and are skipped when there is no
`site/`.
"""

from collections import defaultdict
from html.parser import HTMLParser
from typing import Any
from urllib.parse import unquote

import pytest
from linkml_runtime.utils.formatutils import camelcase
from markdown_it import MarkdownIt
from ruamel.yaml import YAML

from .conftest import REPO_ROOT, rules_catalogue

SITE = REPO_ROOT / "site"
PAGE = SITE / "specification" / "index.html"
ELEMENTS = SITE / "elements"
"""The field reference: one directory per element, named as `gen-doc` names its page."""
SOURCES = REPO_ROOT / "src" / "astra" / "schema"
"""The LinkML sources."""

COLUMNS = {
    "Code": "code",
    "Layer": "layer",
    "Level": "level",
    "Rule": "statement",
    "Status when broken": "status",
}
"""Each column of a codes table, with the field of a rule in `rules.json` it shows."""

MARKDOWN = {"statement", "status"}
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


def expected_text(rule: dict[str, Any], field: str) -> str:
    """The text a rule's field shows: inline Markdown rendered by markdown-it, a code, layer or level as it is."""
    value = rule[field]
    return (
        html_text(MarkdownIt("commonmark").renderInline(value))
        if field in MARKDOWN
        else value
    )


def page_rules() -> list[tuple[str, dict[str, str]]]:
    """Each row of the page's codes tables, in order, with the text of the `<h3>` above its table, and the text of each
    of its cells keyed by its column."""
    parser = _Tables(("h1", "h2", "h3"))
    parser.feed(PAGE.read_text(encoding="utf-8"))
    parser.close()
    return [
        (heading, {column: text for column, (text, _) in zip(header, row)})
        for heading, header, rows in parser.tables
        if header[:1] == ["Code"]
        for row in rows
    ]


def test_page_shows_every_rule_as_rules_json_words_it():
    """The page's codes tables hold the rules of `rules.json`, in order, each cell the text of its field, and each table
    under the heading of its rules' section (`### 7. Inputs` for `§7 Inputs`)."""
    assert PAGE.is_file(), f"{PAGE} is missing: build the site with `zensical build`"
    page = page_rules()
    rules = rules_catalogue()["rules"]
    assert [row.get("Code") for _, row in page] == [rule["code"] for rule in rules], (
        "the page's codes tables don't hold the rules of rules.json, in order: rebuild the site after `just gen-schema`"
    )
    differences = []
    for (heading, row), rule in zip(page, rules):
        number, _, title = rule["source"].removeprefix("§").partition(" ")
        if heading != f"{number}. {title}":
            differences.append(
                f"{rule['code']}: its table is under {heading!r}, not its source, {rule['source']!r}"
            )
        fields = sorted(field for field in rule if field != "source")
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


class _Links(HTMLParser):
    """The `id` of every element of a page, and the `href` of each of its links."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        found = dict(attrs)
        if found.get("id"):
            self.ids.add(found["id"] or "")
        if tag == "a" and found.get("href") is not None:
            self.hrefs.append(found["href"] or "")


def test_every_in_page_link_resolves():
    """Every link of the specification's page to one of its own fragments (`#5-the-astrayaml-file`) names an element
    of the page: a section's heading, as the site makes its anchor."""
    assert PAGE.is_file(), f"{PAGE} is missing: build the site with `zensical build`"
    links = _Links()
    links.feed(PAGE.read_text(encoding="utf-8"))
    links.close()
    fragments = [href[1:] for href in links.hrefs if href.startswith("#")]
    assert fragments
    assert sorted({f for f in fragments if unquote(f) not in links.ids}) == []


class _Rows(HTMLParser):
    """The text of each cell of each table row of a page, as written: character references decoded, white space
    kept."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in ("th", "td") and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("th", "td") and self._cell is not None and self._row is not None:
            self._row.append("".join(self._cell))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def shown_patterns() -> dict[str, list[str]]:
    """The text of each Regex Pattern cell of the field reference, keyed by its element's page."""
    shown = {}
    for page in sorted(ELEMENTS.glob("*/index.html")):
        parser = _Rows()
        parser.feed(page.read_text(encoding="utf-8"))
        parser.close()
        cells = [
            row[1]
            for row in parser.rows
            if len(row) == 2 and row[0].strip() == "Regex Pattern"
        ]
        if cells:
            shown[page.parent.name] = cells
    return shown


def schema_patterns() -> dict[str, list[str]]:
    """Each pattern the LinkML sources write, as they write it, keyed by the page that shows it.

    A named type's page, under its CamelCase name, shows its `pattern`, or its structured pattern's syntax, which
    `gen-doc` shows uninterpolated. A slot's page, under its own name, shows the pattern of the one class that defines
    the slot. A slot that more than one class defines, as `Input.path` and `AnalysisDeclaration.path`, has one page,
    which shows none, even where every class gives it the same pattern."""
    yaml = YAML(typ="safe", pure=True)
    expected = {}
    slots = defaultdict(list)
    for module in sorted(SOURCES.glob("*.yaml")):
        source = yaml.load(module.read_text(encoding="utf-8"))
        for name, definition in (source.get("types") or {}).items():
            pattern = definition.get("pattern") or (
                definition.get("structured_pattern") or {}
            ).get("syntax")
            if pattern:
                expected[camelcase(name)] = [pattern]
        for definition in (source.get("classes") or {}).values():
            for name, slot in ((definition or {}).get("attributes") or {}).items():
                slots[name].append((slot or {}).get("pattern"))
    for name, patterns in slots.items():
        if len(patterns) == 1 and patterns[0] is not None:
            expected[name] = patterns
    return expected


def test_element_pages_show_their_patterns():
    """Every Regex Pattern cell of the field reference shows its element's pattern exactly as the LinkML sources
    write it, and every pattern they write has its cell, whatever backtick, `|`, `[^` or `^` it holds.

    The description of `FragmentSelector.value` lists characters one by one, `[`, `\\` and `]` among them: its page
    shows it word for word, as markdown-it renders it."""
    assert ELEMENTS.is_dir(), (
        f"{ELEMENTS} is missing: build the site with `zensical build`"
    )
    assert shown_patterns() == schema_patterns()

    yaml = YAML(typ="safe", pure=True)
    source = yaml.load((SOURCES / "insight.yaml").read_text(encoding="utf-8"))
    description = source["classes"]["FragmentSelector"]["attributes"]["value"][
        "description"
    ]
    page = (ELEMENTS / "value" / "index.html").read_text(encoding="utf-8")
    assert html_text(MarkdownIt("commonmark").renderInline(description)) in html_text(
        page
    )


class _Tables(HTMLParser):
    """The tables of a page, each with the text of the last heading of one of `levels` above it, its permalink left
    out, its header, and for each body row the text of each cell and the `href` of each link in it."""

    def __init__(self, levels: tuple[str, ...]) -> None:
        super().__init__(convert_charrefs=True)
        self.levels = levels
        self.tables: list[tuple[str, list[str], list[list[tuple[str, list[str]]]]]] = []
        self._section = ""
        self._heading: list[str] | None = None
        self._permalink = 0
        self._table: tuple[str, list[str], list[list[tuple[str, list[str]]]]] | None = (
            None
        )
        self._head = False
        self._row: list[tuple[str, list[str]]] | None = None
        self._cell: list[str] | None = None
        self._links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.levels:
            self._heading = []
        elif tag == "a" and self._heading is not None:
            if (
                self._permalink
                or "headerlink" in (dict(attrs).get("class") or "").split()
            ):
                self._permalink += 1
        elif tag == "a" and self._cell is not None:
            self._links.append(dict(attrs).get("href") or "")
        elif tag == "table":
            self._table = (self._section, [], [])
        elif tag == "thead":
            self._head = True
        elif tag == "tr":
            self._row = []
        elif tag in ("th", "td"):
            self._cell, self._links = [], []

    def handle_endtag(self, tag: str) -> None:
        if tag in self.levels and self._heading is not None:
            self._section = _words("".join(self._heading))
            self._heading = None
        elif tag == "a" and self._permalink:
            self._permalink -= 1
        elif tag in ("th", "td") and self._cell is not None and self._row is not None:
            self._row.append((_words("".join(self._cell)), self._links))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table is not None:
            if self._head:
                self._table[1].extend(text for text, _ in self._row)
            else:
                self._table[2].append(self._row)
            self._row = None
        elif tag == "thead":
            self._head = False
        elif tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None

    def handle_data(self, data: str) -> None:
        if self._heading is not None and not self._permalink:
            self._heading.append(data)
        if self._cell is not None:
            self._cell.append(data)


RULES_PAGE = SITE / "rules" / "index.html"
"""The All rules page, generated from the specification (`tools/rules_page.py`)."""

PAGE_COLUMNS = {"Level": "level", "Rule": "statement", "Status when broken": "status"}
"""The columns of the All rules page that show a field of a rule, with that field."""


def test_all_rules_page_lists_every_rule():
    """The All rules page lists every rule of `rules.json` once, under its layer's heading, showing its level, its rule
    and, for a check rule, its status as `rules.json` words them, with a link to a heading of the specification's
    page."""
    assert RULES_PAGE.is_file(), (
        f"{RULES_PAGE} is missing: build the site with `just docs`"
    )
    parser = _Tables(("h1", "h2"))
    parser.feed(RULES_PAGE.read_text(encoding="utf-8"))
    parser.close()
    ids = _Links()
    ids.feed(PAGE.read_text(encoding="utf-8"))
    ids.close()
    shown = [
        (layer, dict(zip(header, row)))
        for layer, header, rows in parser.tables
        for row in rows
    ]
    rules = {rule["code"]: rule for rule in rules_catalogue()["rules"]}
    assert sorted(row["Code"][0] for _, row in shown) == sorted(rules)
    differences = []
    for layer, row in shown:
        rule = rules[row["Code"][0]]
        if layer != rule["layer"].capitalize():
            differences.append(f"{rule['code']}: under {layer!r}, not its layer")
        for column, field in PAGE_COLUMNS.items():
            if (column in row) != (field in rule):
                differences.append(f"{rule['code']}: the page's {column} column")
            elif column in row and row[column][0] != expected_text(rule, field):
                differences.append(
                    f"{rule['code']}, {column}: the page shows {row[column][0]!r}, rules.json"
                    f" {expected_text(rule, field)!r}"
                )
        links = row["Section"][1]
        page, _, fragment = links[0].partition("#") if len(links) == 1 else ("", "", "")
        if (
            page.rstrip("/").rsplit("/", 1)[-1] != "specification"
            or fragment not in ids.ids
        ):
            differences.append(
                f"{rule['code']}: its section link, {links}, is not to a heading of the specification"
            )
    assert differences == []
