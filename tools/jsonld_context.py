"""LinkML's JSON-LD context for a schema, with every IRI written in full and no term a prefix.

LinkML's ``gen-jsonld-context`` declares the schema's prefixes as terms
(``"prov": "http://www.w3.org/ns/prov#"``) and writes the other terms' ``@id``
and ``@type`` as CURIEs over them (``"prov:used"``). A simple term whose IRI
ends in ``/`` or ``#`` carries JSON-LD 1.1's prefix flag, so a value written
``prov:env:1`` where an IRI is expected (an environment's ``iri``) is read as a
compact IRI and becomes ``http://www.w3.org/ns/prov#env:1``. This module
instead:

1. drops every prefix term, after using it to write each ``@id`` and ``@type``
   as a full IRI (a bare name, such as ``commit``, under ``@vocab``);
2. adds ``"@version": 1.1``, so that a JSON-LD 1.0 processor, which treats
   every term as a prefix (``commit:env`` as ``https://w3id.org/astra/commitenv``),
   rejects the context rather than reading it;
3. drops LinkML's ``comments``, which would name it as the only generator.

A term that maps to an IRI without being a prefix becomes an expanded
definition, which JSON-LD 1.1 never reads as a prefix. No term is then a
prefix, so every IRI a document writes is read exactly as written, whatever
its scheme. :func:`prefix_free` fails on any IRI it can't write in full.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from linkml.generators.jsonldcontextgen import ContextGenerator

VERSION = 1.1
"""The JSON-LD version the context declares (`@version`)."""

GEN_DELIMS = tuple(":/?#[]@")
"""RFC 3986's gen-delims: a simple term whose IRI ends in one is a prefix in JSON-LD 1.1."""

IRI_ENTRIES = ("@id", "@type")
"""The entries of an expanded term definition that hold an IRI or a keyword."""


def _full(value: str, prefixes: dict[str, str], vocab: str | None) -> str:
    """`value`, a keyword, a CURIE over `prefixes`, a name under `vocab` or an absolute IRI, written as a full IRI."""
    if value.startswith("@"):
        return value
    prefix, colon, local = value.partition(":")
    if not colon:
        if vocab is None:
            raise ValueError(f"{value!r} is a bare name, and the context has no @vocab")
        return vocab + value
    if prefix in prefixes:
        return prefixes[prefix] + local
    if local.startswith("//"):
        return value
    raise ValueError(
        f"{value!r} is a CURIE whose prefix {prefix!r} the context doesn't declare"
    )


def is_prefix(term: str, definition: Any) -> bool:
    """Whether JSON-LD 1.1 lets `term` serve as a prefix in a compact IRI: a simple term whose IRI ends in a
    gen-delim or is a blank node, or a definition with `@prefix: true` (JSON-LD 1.1 API §4.2.2)."""
    if isinstance(definition, str):
        return (
            ":" not in term
            and "/" not in term
            and not definition.startswith("@")
            and (definition.endswith(GEN_DELIMS) or definition.startswith("_:"))
        )
    return isinstance(definition, dict) and definition.get("@prefix") is True


def prefix_free(context: dict[str, Any]) -> dict[str, Any]:
    """The `@context` `context` with `@version` 1.1 first, its prefix terms dropped, and every other term an
    expanded definition (or a keyword alias) whose `@id` and `@type` are written in full."""
    vocab = context.get("@vocab")
    prefixes = {
        term: definition if isinstance(definition, str) else definition["@id"]
        for term, definition in context.items()
        if not term.startswith("@") and is_prefix(term, definition)
    }
    result: dict[str, Any] = {"@version": VERSION}
    for term, definition in context.items():
        if term in prefixes:
            continue
        if term.startswith("@"):
            result[term] = definition
            continue
        if isinstance(definition, str) and not definition.startswith("@"):
            definition = {"@id": definition}
        if isinstance(definition, dict):
            definition = {
                key: _full(value, prefixes, vocab) if key in IRI_ENTRIES else value
                for key, value in definition.items()
            }
        result[term] = definition
    return result


def generate(schema: str | Path) -> dict[str, Any]:
    """The JSON-LD context document of the LinkML `schema`: LinkML's, made prefix-free (:func:`prefix_free`)."""
    stock = json.loads(ContextGenerator(str(schema), metadata=False).serialize())
    return {"@context": prefix_free(stock["@context"])}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Write the JSON-LD context of a LinkML schema, with no term a prefix, to stdout."
    )
    parser.add_argument("schema", type=Path, help="the LinkML schema (YAML)")
    args = parser.parse_args(argv)
    print(json.dumps(generate(args.schema), indent=2))


if __name__ == "__main__":
    main()
