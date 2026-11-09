"""The published page shows every cell of its codes table as the same text as `rules.json`, every in-page link of the
specification goes to an element of it, and the field reference shows every pattern as the LinkML sources write it.

`tools/rules.py` reads the codes table as CommonMark with GFM tables, but the site renders it with Python-Markdown and
Zensical's extensions. So a cell could read one way in `rules.json` and another on the page: `~~`, `==`, `^^`, emoji,
smart symbols (`-->`, `1/2`), `$…$`, footnotes, attribute lists, `\\|` in a code span, or a codes table right after a
paragraph, which Python-Markdown doesn't read as a table. Pinning the site's extensions can't remove the last two.

So a test reads the built page and compares the text of the codes table (the table whose first column is Code) with
`rules.json`, rendered by markdown-it: the same rules, in the same order, word for word, each under the layer row of
its layer, the table under the Rules heading. Another checks that every link of the page to a fragment of the page
names an element there.

The field reference's pages are built from `gen-doc`'s Markdown, where a pattern's backtick, `|`, `[^` or `^` would be
read as Markdown. So another test reads each element's page and compares its Regex Pattern cell with the pattern the
LinkML sources write. The tests run in CI after the docs build (`main.yaml`, `test_pages_build.yaml`), and are skipped
when there is no `site/`.
"""

import itertools
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

RULES = "Rules"
"""The heading of the section that holds the codes table."""

STATUS = "→"
"""The mark in a check row's Rule cell between its part of the statement and its status."""

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


def page_rows() -> list[tuple[str, dict[str, str]]]:
    """Each row of the page's codes table, in order, with the text of the heading above the table, and the text of
    each of its cells keyed by its column."""
    parser = _Tables(("h1", "h2", "h3"))
    parser.feed(PAGE.read_text(encoding="utf-8"))
    parser.close()
    return [
        (heading, {column: text for column, (text, _) in zip(header, row)})
        for heading, header, rows in parser.tables
        if header[:1] == ["Code"]
        for row in rows
    ]


def page_rules() -> list[dict[str, Any]]:
    """The rules the page's codes table shows, in order: for each, the heading above the table, the first word of the
    layer row above it, its code and level, and the text of its rows' Rule cells, each a check row's split at its `→`
    into its part of the statement and its status."""
    rules: list[dict[str, Any]] = []
    layer = None
    for heading, row in page_rows():
        if not row.get("Level") and not row.get("Rule"):
            layer = "".join(itertools.takewhile(str.isalpha, row.get("Code", "")))
            continue
        statement, status = row.get("Rule", ""), None
        if layer == "check":
            statement, _, status = statement.partition(STATUS)
            statement, status = statement.strip(), status.strip()
        last = rules[-1] if rules else None
        if last is not None and (last["code"], last["layer"]) == (
            row.get("Code"),
            layer,
        ):
            last["parts"].append(statement)
            last["statuses"].append(status)
            continue
        rules.append(
            {
                "heading": heading,
                "layer": layer,
                "code": row.get("Code"),
                "level": row.get("Level"),
                "parts": [statement],
                "statuses": [status],
                "columns": sorted(row),
            }
        )
    return rules


def test_page_shows_every_rule_as_rules_json_words_it():
    """The page's codes table holds the rules of `rules.json`, in order, under the Rules heading, each under the layer
    row of its layer: its code and level, and its rows' Rule cells, joined with `; `, its statement then, for a check
    rule, its status after each `→`, each the text of its field."""
    assert PAGE.is_file(), f"{PAGE} is missing: build the site with `zensical build`"
    page = page_rules()
    rules = rules_catalogue()["rules"]
    assert [shown["code"] for shown in page] == [rule["code"] for rule in rules], (
        "the page's codes table doesn't hold the rules of rules.json, in order: rebuild the site after `just gen-schema`"
    )
    differences = []
    for shown, rule in zip(page, rules):
        code = rule["code"]
        if shown["columns"] != sorted(["Code", "Level", "Rule"]):
            differences.append(f"{code}: the page shows the columns {shown['columns']}")
            continue
        if shown["heading"] != RULES:
            differences.append(
                f"{code}: its table is under {shown['heading']!r}, not {RULES!r}"
            )
        if shown["layer"] != rule["layer"]:
            differences.append(
                f"{code}: under the layer row of {shown['layer']!r}, not {rule['layer']!r}"
            )
        if shown["level"] != rule["level"]:
            differences.append(
                f"{code}: the page shows the level {shown['level']!r}, rules.json {rule['level']!r}"
            )
        statement = "; ".join(shown["parts"])
        if statement != expected_text(rule, "statement"):
            differences.append(
                f"{code}: the page shows {statement!r}, rules.json {expected_text(rule, 'statement')!r}"
            )
        statuses = {expected_text(rule, "status") if "status" in rule else None}
        if set(shown["statuses"]) != statuses:
            differences.append(
                f"{code}: the page shows the statuses {shown['statuses']}, rules.json {statuses}"
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
    """Every link of the specification's page to one of its own fragments (`#rules`) names an element of the page: a
    section's heading, as the site makes its anchor."""
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

    A named type's page, under its CamelCase name, shows its `pattern`, or its structured pattern's syntax with each
    `{name}` filled in from the settings. A slot's page, under its own name, shows the pattern of the classes that
    define the slot, where they all give it the same one: `Input.path` and `AnalysisDeclaration.path` share a page."""
    yaml = YAML(typ="safe", pure=True)
    sources = [
        yaml.load(module.read_text(encoding="utf-8"))
        for module in sorted(SOURCES.glob("*.yaml"))
    ]
    settings = {}
    for source in sources:
        settings.update(source.get("settings") or {})
    expected = {}
    slots = defaultdict(list)
    for source in sources:
        for name, definition in (source.get("types") or {}).items():
            structured = definition.get("structured_pattern") or {}
            pattern = definition.get("pattern") or structured.get("syntax")
            if pattern and structured.get("interpolated"):
                for key, value in settings.items():
                    pattern = pattern.replace("{" + key + "}", value)
            if pattern:
                expected[camelcase(name)] = [pattern]
        for definition in (source.get("classes") or {}).values():
            for name, slot in ((definition or {}).get("attributes") or {}).items():
                slots[name].append((slot or {}).get("pattern"))
    for name, patterns in slots.items():
        if patterns[0] is not None and len(set(patterns)) == 1:
            expected[name] = patterns[:1]
    return expected


def test_element_pages_show_their_patterns():
    """Every Regex Pattern cell of the field reference shows its element's pattern exactly as the LinkML sources
    write it, each `{name}` filled in, and every pattern they write has its cell, whatever backtick, `|`, `[^` or `^`
    it holds.

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
