# Code generated from the linkML model

This directory holds the output generated with [LinkML generators](https://linkml.io/linkml/generators/index.html)
from the model in `src/astra/schema/`, whose two roots are `analysis.yaml` and `provenance.yaml`.
Generators transform a linkml schema into another datamodel such as SQL or RDF, or into other artefacts,
such as JSON-Schema, a visualisation, or markdown documentation.

Three folders are ASTRA's contract, written by `just gen-schema` with its own generators (`tools/`), committed, and
shipped in the wheel under `astra/schema/`:

- `jsonschema/`: the JSON Schemas of `astra.yaml` (`analysis.schema.json`) and of the provenance record
  (`provenance.schema.json`, and `provenance.open.schema.json` for fields it doesn't define), and those of the three
  documents tools exchange, from `documents.yaml` (`validation-report.schema.json`, `resolved-analysis.schema.json`,
  `check-report.schema.json`);
- `jsonld/`: the record's JSON-LD context (`provenance.context.jsonld`);
- `rules/`: the rule catalogue (`rules.json`).

The other folders, from `just gen-project`, are ignored by git.
