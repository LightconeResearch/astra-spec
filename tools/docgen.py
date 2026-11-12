"""LinkML's `gen-doc`, with each description in a table cut at the end of its first sentence or of a word, each range
linked to its type, each `<` and `&` of a description shown as written, and no two pages whose names differ only in
case.

`just gen-doc` runs this in place of `gen-doc`, with the same arguments. It changes four things:

1. A table of the field reference (on the index, a class's slots, a slot's classes) shows each element's description
   cut short. LinkML 1.12.1 cuts it at its first `.`, wherever it is (`the folder of the astra` for `astra.yaml`), and
   at 80 characters, inside a code span or not. Here it shows the description's first sentence: up to its first `.`,
   `?` or `!` followed by white space or the end, outside code spans, and, where that shows more than 80 characters (a
   code span's backticks aside), up to its last space outside code spans before the 80th it shows, less a `,`, `;` or
   `:` before that space, then `…`. Its own page shows the whole description.
2. `gen-doc` links a name to the first element it finds under it among the classes, then the slots, then the types, so
   a range of the type `id` links to the slot `id`. Here a name that is a type's links to the type, and a slot's page
   links each slot of its Usages table by its definition (`slot.md.jinja2`).
3. A description is Markdown, which reads a `<` or `&` outside a code span as HTML (`command`'s `<entry>`, which the
   page would hide). Here each is written as a character reference, in a table and on a slot's page
   (`slot.md.jinja2`), so that the page shows it as the LinkML sources write it.
4. `gen-doc` names a class's or a type's page in CamelCase and a slot's as it is, so the class `Decision` and the slot
   `decision` have pages that differ only in case, and a case-insensitive file system (macOS, Windows) keeps only one
   of them. Here such a slot's page takes the suffix `-slot` (`decision-slot.md`), and each link to it follows. The
   class and type pages keep their names, which the specification links to. Pages that would still differ only in
   case fail the run.

Usage: python tools/docgen.py <gen-doc's arguments>
"""

import re
from collections import Counter

from jinja2 import Environment
from linkml.generators import docgen
from linkml_runtime.linkml_model.meta import Definition, DefinitionName

SENTENCE_END = re.compile(r"`[^`]*`|[.?!](?=\s|$)")
"""A code span, or the end of a sentence: a `.`, `?` or `!` followed by white space or the end."""

WORD_END = re.compile(r"`[^`]*`| ")
"""A code span, or a space."""

CODE_SPAN = re.compile(r"`([^`]*)`")
"""A code span, with the text it shows."""

HTML = re.compile(r"`[^`]*`|[&<]")
"""A code span, or a character that Markdown reads as the start of HTML outside one."""

TABLE_WIDTH = 80
"""The most characters a description in a table shows, `gen-doc`'s too."""

SLOT_SUFFIX = "-slot"
"""What a slot's page name takes when another page's name differs from it only in case."""

LINK = re.compile(r"\]\(([^()/\s]+)\.md\)")
"""The target of a link from a page of the field reference to another, `](<page>.md)`, with the page's name."""


def width(text: str) -> int:
    """The number of characters `text` shows: each code span's text, without its backticks."""
    return len(CODE_SPAN.sub(r"\1", text))


def first_sentence(text: str | None) -> str:
    """`text`'s first sentence, each run of white space in it as one space, cut at its last space outside code spans
    before the `TABLE_WIDTH`th character it shows, less a `,`, `;` or `:` before that space, and ended with `…` where
    it shows more (`width`), and escaped (`escape`)."""
    if text is None:
        return ""
    text = " ".join(text.split())
    for match in SENTENCE_END.finditer(text):
        if not match[0].startswith("`"):
            text = text[: match.end()]
            break
    if width(text) > TABLE_WIDTH:
        spaces = [
            match.start()
            for match in WORD_END.finditer(text)
            if match[0] == " " and width(text[: match.start()]) < TABLE_WIDTH
        ]
        if spaces:
            text = text[: spaces[-1]].rstrip(",;:") + "…"
    return escape(text)


def escape(text: str | None) -> str:
    """`text` with each `&` and `<` outside its code spans as a character reference."""
    return HTML.sub(lambda m: {"&": "&amp;", "<": "&lt;"}.get(m[0], m[0]), text or "")


class DocGenerator(docgen.DocGenerator):
    """LinkML's documentation generator, changed as the module's docstring says."""

    def customize_environment(self, env: Environment) -> None:
        super().customize_environment(env)
        if self.truncate_descriptions:
            env.filters["enshorten"] = first_sentence
        env.filters["escape_html"] = escape

    def link(self, e: Definition | DefinitionName, index_link: bool = False) -> str:
        if isinstance(e, str) and self.schemaview.get_type(e) is not None:
            e = self.schemaview.get_type(e)
        return super().link(e, index_link)

    def serialize(self, directory: str | None = None) -> None:
        # The new names are worked out from the schema before any page is written, so that the file system never
        # sees two names that differ only in case.
        view = self.schemaview
        others = {
            self.name(element).casefold()
            for elements in (view.all_classes(), view.all_enums(), view.all_types())
            for element in elements.values()
        }
        self.moved = {
            name: name + SLOT_SUFFIX
            for name in map(self.name, view.all_slots().values())
            if name.casefold() in others
        }
        self.written = set()
        super().serialize(directory)
        names = Counter(name.casefold() for name in self.written)
        twins = sorted(name for name, count in names.items() if count > 1)
        if twins:
            raise ValueError(
                f"pages of the field reference whose names differ only in case: {twins}"
            )

    def _write(self, out_str: str, directory: str, name: str) -> None:
        name = self.moved.get(name, name)
        self.written.add(name)
        linked = LINK.sub(lambda m: f"]({self.moved.get(m[1], m[1])}.md)", out_str)
        super()._write(linked, directory, name)


if __name__ == "__main__":
    docgen.DocGenerator = DocGenerator  # the generator `gen-doc`'s command line builds
    docgen.cli()
