"""The provenance record: its open variant, and its RDF reading, which is PROV-O (spec §10; design §3, §6, D10).

A record's RDF is what JSON-LD 1.1's toRdf gives for it with the published context, plus each node's class URI as its
`rdf:type` (:func:`as_rdf`, with rdflib). The context comes from LinkML's, with every IRI in full and no term a prefix
(`tools/jsonld_context.py`), so that an environment's `iri` is its node exactly as written, whatever its scheme.
"""

import copy
import json
import re
import warnings
from functools import cache
from pathlib import Path
from typing import Any

import pytest
from jsonld_context import prefix_free
from linkml_runtime import SchemaView
from rdflib import RDF, XSD, BNode, Graph, Literal, Namespace, URIRef

from .conftest import (
    DATA,
    GENERATED,
    REPO_ROOT,
    error_pointers,
    fixtures,
    load_yaml,
    validator,
)
from .test_specification import EXAMPLE_ROOTS, WHOLE_EXAMPLES

SCHEMA = REPO_ROOT / "src" / "astra" / "schema" / "provenance.yaml"
CONTEXT = GENERATED / "provenance.context.jsonld"
PROV = Namespace("http://www.w3.org/ns/prov#")
ASTRA = Namespace("https://w3id.org/astra/")
SCHEMA_ORG = Namespace("http://schema.org/")
PREFIXES = ("astra", "linkml", "prov", "schema", "xsd")
"""The prefixes LinkML's context declares as terms, which the published one drops."""


def invalid_fixture(number: str) -> Any:
    """The document of the one invalid fixture `ProvenanceRecord-<number>-….yaml`."""
    (path,) = (DATA / "invalid").glob(f"ProvenanceRecord-{number}-*.yaml")
    return load_yaml(path)


def context(path: Path) -> dict[str, Any]:
    """The `@context` of the JSON-LD context file at `path`."""
    return json.loads(path.read_text(encoding="utf-8"))["@context"]


def test_unknown_field_passes_the_open_variant():
    record = invalid_fixture("215")
    assert error_pointers(validator("ProvenanceRecord"), record) == {"(root)"}
    assert list(validator("ProvenanceRecord", closed=False).iter_errors(record)) == []


@pytest.mark.parametrize(
    "where", [("generated_by",), ("generated_by", "runner")], ids=".".join
)
def test_unknown_nested_field_passes_only_the_open_variant(where):
    record = copy.deepcopy(load_yaml(DATA / "valid" / "ProvenanceRecord-001-full.yaml"))
    target = record
    for field in where:
        target = target[field]
    target["added_by_a_newer_version"] = "x"
    assert error_pointers(validator("ProvenanceRecord"), record) == {
        "/" + "/".join(where)
    }
    assert list(validator("ProvenanceRecord", closed=False).iter_errors(record)) == []


def test_open_variant_still_checks_known_fields():
    open_ = validator("ProvenanceRecord", closed=False)
    assert error_pointers(open_, invalid_fixture("206")) == {"/content_hash"}
    assert error_pointers(open_, invalid_fixture("210")) == {"/generated_by/commit"}


def test_context_maps_the_record_onto_prov():
    terms = context(CONTEXT)
    slots = [
        "generated_by",
        "inputs",
        "environment",
        "runner",
        "started",
        "finished",
        "version",
    ]
    assert {slot: terms[slot]["@id"] for slot in slots} == {
        "generated_by": str(PROV.wasGeneratedBy),
        "inputs": str(PROV.used),
        "environment": str(PROV.used),
        "runner": str(PROV.wasAssociatedWith),
        "started": str(PROV.startedAtTime),
        "finished": str(PROV.endedAtTime),
        "version": str(SCHEMA_ORG.softwareVersion),
    }
    times = ["started", "finished"]
    assert {time: terms[time].get("@type") for time in times} == dict.fromkeys(
        times, str(XSD.dateTime)
    )
    assert terms["iri"] == "@id"


def test_no_term_is_a_prefix():
    """JSON-LD 1.1 and no prefix terms: every term is the `iri` alias or a definition whose IRIs are written in full,
    and none carries `@prefix`, so none can expand a compact IRI."""
    terms = context(CONTEXT)
    assert terms["@version"] == 1.1
    assert [prefix for prefix in PREFIXES if prefix in terms] == []
    problems = []
    for term, definition in terms.items():
        if term.startswith("@") or definition == "@id":
            continue
        if not isinstance(definition, dict) or "@prefix" in definition:
            problems.append(f"{term}: {definition!r}")
            continue
        problems += [
            f"{term}: {key} {value!r} is not written in full"
            for key, value in definition.items()
            if key in ("@id", "@type")
            and not value.startswith("@")
            and "://" not in value
        ]
    assert problems == []


def test_prefix_free_writes_every_iri_in_full():
    stock = {
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "ex": {"@id": "http://example.org/ns", "@prefix": True},
        "prov": "http://www.w3.org/ns/prov#",
        "@vocab": "https://w3id.org/astra/",
        "iri": "@id",
        "label": "http://schema.org/name",
        "commit": {"@id": "commit"},
        "used": {"@type": "@id", "@id": "prov:used"},
        "when": {"@type": "xsd:dateTime", "@id": "ex:when"},
        "Thing": {"@id": "http://example.org/Thing"},
    }
    assert prefix_free(stock) == {
        "@version": 1.1,
        "@vocab": "https://w3id.org/astra/",
        "iri": "@id",
        "label": {"@id": "http://schema.org/name"},
        "commit": {"@id": "https://w3id.org/astra/commit"},
        "used": {"@type": "@id", "@id": "http://www.w3.org/ns/prov#used"},
        "when": {
            "@type": "http://www.w3.org/2001/XMLSchema#dateTime",
            "@id": "http://example.org/nswhen",
        },
        "Thing": {"@id": "http://example.org/Thing"},
    }


@pytest.mark.parametrize(
    ("stock", "message"),
    [
        ({"used": {"@id": "prov:used"}}, "prefix 'prov' the context doesn't declare"),
        ({"commit": {"@id": "commit"}}, "no @vocab"),
    ],
)
def test_prefix_free_fails_on_what_it_cannot_write_in_full(stock, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        prefix_free(stock)


@cache
def class_uri(name: str) -> str:
    """The URI of the schema class `name`, expanded."""
    return SchemaView(str(SCHEMA)).get_uri(name, expand=True)


def as_rdf(record: dict[str, Any]) -> Graph:
    """The record's RDF (spec §10): JSON-LD 1.1 toRdf with the published context, plus each node's class URI as its
    `rdf:type`."""
    typed = copy.deepcopy(record)
    run = typed["generated_by"]
    nodes = [
        (typed, "ProvenanceRecord"),
        (run, "Generation"),
        (run["environment"], "Environment"),
        (run["runner"], "Runner"),
        *((item, "RecordedInput") for item in run.get("inputs", [])),
    ]
    for node, name in nodes:
        node["@type"] = class_uri(name)
    graph = Graph()
    with warnings.catch_warnings():
        # rdflib 7's JSON-LD parser builds a ConjunctiveGraph, which rdflib itself deprecates.
        warnings.filterwarnings(
            "ignore", "ConjunctiveGraph is deprecated", DeprecationWarning
        )
        graph.parse(data=json.dumps(typed), format="json-ld", context=context(CONTEXT))
    return graph


def records() -> dict[str, Any]:
    """Every valid record fixture, and every record among the specification's examples, by name."""
    found = {
        path.stem: load_yaml(path)
        for path in fixtures("valid")
        if path.name.startswith("ProvenanceRecord-")
    }
    for example in WHOLE_EXAMPLES:
        if EXAMPLE_ROOTS[example.language] == "ProvenanceRecord":
            found[f"specification-line-{example.line}"] = example.document
    return found


RECORDS = records()


def test_records_include_the_specifications_example():
    assert any(name.startswith("specification-") for name in RECORDS)


@pytest.mark.parametrize("record", RECORDS.values(), ids=RECORDS.keys())
def test_a_record_reads_as_prov(record):
    """The root node is the result, a `prov:Entity` made by the run, a `prov:Activity` that used its inputs and its
    environment, each a `prov:Entity`, and was associated with its runner, a `prov:SoftwareAgent`."""
    graph = as_rdf(record)
    run = record["generated_by"]
    (result,) = set(graph.subjects(PROV.wasGeneratedBy, None))
    assert isinstance(result, BNode)
    assert set(graph.objects(result, RDF.type)) == {PROV.Entity}
    described = {
        field: graph.value(result, ASTRA[field]).toPython()
        for field in ("spec_version", "address", "content_hash", "size")
    }
    assert described == {
        field: record[field]
        for field in ("spec_version", "address", "content_hash", "size")
    }
    activity = graph.value(result, PROV.wasGeneratedBy)
    assert set(graph.objects(activity, RDF.type)) == {PROV.Activity}
    environment = URIRef(run["environment"]["iri"])
    used = set(graph.objects(activity, PROV.used))
    assert environment in used
    entries = {
        graph.value(item, ASTRA.entry).toPython() for item in used - {environment}
    }
    assert entries == {item["entry"] for item in run.get("inputs", [])}
    assert len(used) == 1 + len(run.get("inputs", []))
    for entity in used:
        assert set(graph.objects(entity, RDF.type)) == {PROV.Entity}
    runner = graph.value(activity, PROV.wasAssociatedWith)
    assert set(graph.objects(runner, RDF.type)) == {PROV.SoftwareAgent}
    assert graph.value(runner, SCHEMA_ORG.softwareVersion) == Literal(
        run["runner"]["version"]
    )
    for field, predicate in (
        ("started", PROV.startedAtTime),
        ("finished", PROV.endedAtTime),
    ):
        time = graph.value(activity, predicate)
        expected = Literal(run[field], datatype=XSD.dateTime) if field in run else None
        assert time == expected
    assert {s for s in graph.subjects() if (s, RDF.type, None) not in graph} == set()


SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*")
"""An IRI's scheme (RFC 3987 §2.2)."""

IRIS = sorted(
    {
        "urn:example-runner:env:1",
        "tag:example.org,2026:env:1",
        *(f"{prefix}:env:1" for prefix in PREFIXES),
        *(f"{term}:env:1" for term in context(CONTEXT) if SCHEME.fullmatch(term)),
    }
)
"""Environment IRIs whose scheme is a prefix of LinkML's context, a term of the published one, or neither."""


@pytest.mark.parametrize("iri", IRIS)
def test_an_iri_is_read_exactly_as_written(iri):
    """The specification's example with another environment `iri`: valid, and its node is that IRI, a `prov:Entity`
    the run used, however the context's terms are named."""
    (example,) = [
        record for name, record in RECORDS.items() if name.startswith("specification-")
    ]
    record = copy.deepcopy(example)
    record["generated_by"]["environment"]["iri"] = iri
    assert error_pointers(validator("ProvenanceRecord"), record) == set()
    graph = as_rdf(record)
    named = {
        str(node) for node in graph.objects(None, PROV.used) if isinstance(node, URIRef)
    }
    assert named == {iri}
    assert (URIRef(iri), RDF.type, PROV.Entity) in graph


def test_classes_map_onto_prov():
    sv = SchemaView(str(SCHEMA))
    classes = [
        "ProvenanceRecord",
        "Generation",
        "RecordedInput",
        "Environment",
        "Runner",
    ]
    assert {c: sv.get_uri(c, expand=True) for c in classes} == {
        "ProvenanceRecord": str(PROV.Entity),
        "Generation": str(PROV.Activity),
        "RecordedInput": str(PROV.Entity),
        "Environment": str(PROV.Entity),
        "Runner": str(PROV.SoftwareAgent),
    }
