"""LinkML's `gen-doc`, with each range linked to its type, and each `<` and `&` of a description shown as written.

`just gen-doc` runs this in place of `gen-doc`, with the same arguments. It changes two things:

1. `gen-doc` links a name to the first element it finds under it among the classes, then the slots, then the types, so
   a range of the type `id` links to the slot `id`. Here a name that is a type's links to the type, and a slot's page
   links each slot of its Usages table by its definition (`slot.md.jinja2`).
2. A description is Markdown, which reads a `<` or `&` outside a code span as HTML (`command`'s `<entry>`, which the
   page would hide). Here each is written as a character reference, in a table and on a slot's page
   (`slot.md.jinja2`), so that the page shows it as the LinkML sources write it.

Usage: python tools/docgen.py <gen-doc's arguments>
"""

import re

from jinja2 import Environment
from linkml.generators import docgen
from linkml_runtime.linkml_model.meta import Definition, DefinitionName

HTML = re.compile(r"`[^`]*`|[&<]")
"""A code span, or a character that Markdown reads as the start of HTML outside one."""


def escape(text: str | None) -> str:
    """`text` with each `&` and `<` outside its code spans as a character reference."""
    return HTML.sub(lambda m: {"&": "&amp;", "<": "&lt;"}.get(m[0], m[0]), text or "")


class DocGenerator(docgen.DocGenerator):
    """LinkML's documentation generator, changed as the module's docstring says."""

    def customize_environment(self, env: Environment) -> None:
        super().customize_environment(env)
        shorten = env.filters["enshorten"]
        env.filters["enshorten"] = lambda text: escape(shorten(text))
        env.filters["escape_html"] = escape

    def link(self, e: Definition | DefinitionName, index_link: bool = False) -> str:
        if isinstance(e, str) and self.schemaview.get_type(e) is not None:
            e = self.schemaview.get_type(e)
        return super().link(e, index_link)


if __name__ == "__main__":
    docgen.DocGenerator = DocGenerator  # the generator `gen-doc`'s command line builds
    docgen.cli()
