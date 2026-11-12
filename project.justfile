## Add your own just recipes here. This is imported by the main justfile.

# Overriding recipes from the root justfile by adding a recipe with the same
# name in this file is not possible until a known issue in just is fixed,
# https://github.com/casey/just/issues/2540

# ============== ASTRA ==============

# Each JSON Schema's $id is this, the series of the version it is generated
# with (X.Y for a release X.Y.Z, a pre-release's whole version, or dev), `/`,
# then its file name
schema_namespace := "https://w3id.org/astra/"
# The site shows astra-tools' CLI reference and installation page, which live
# in astra-tools beside the code they describe (`_docs-tools`): taken from its
# branch or tag `tools_ref` (v0.1-rebuild, astra-tools' v0.1 work, until it
# reaches main), which ASTRA_TOOLS_REF overrides, or from the local folder
# ASTRA_TOOLS_DOCS names, such as ../astra-tools/docs
tools_ref := if env_var_or_default("ASTRA_TOOLS_REF", "") == "" { "v0.1-rebuild" } else { env_var("ASTRA_TOOLS_REF") }
tools_docs := env_var_or_default("ASTRA_TOOLS_DOCS", "")
# Every generated file that is committed, which `release` regenerates and
# commits: the contract (`gen-schema`) and the Python datamodels
# (`gen-python`; their folder's `__init__.py` is written by hand)
generated_files := dest / "jsonschema" + " " + dest / "jsonld" + " " + dest / "rules" + " " + pymodel

# Generate the contract from the staged (versioned) schema, each file in the
# folder of its LinkML generator under `dest` (project/): the JSON Schemas of
# the analysis document and the provenance record (closed, and open for fields
# it doesn't know) in jsonschema/, the record's JSON-LD context (LinkML's, with
# every IRI in full and no term a prefix) in jsonld/, and the rule catalogue
# in rules/. Each JSON Schema's `$id` is the URI of its own file under its
# series (`{series}`, filled in by the generator: `0.1` for every 0.1.x, a
# pre-release's whole version, or `dev`), so the closed and open record
# schemas are distinct, and so are two minor versions. `rules.json` holds the
# rules extracted from the codes table of the specification's Rules section,
# and the code of each JSON Schema keyword that can fail.
[group('model development')]
gen-schema: _stage-versioned
  mkdir -p {{dest}}/jsonschema {{dest}}/jsonld {{dest}}/rules
  uv run python tools/jsonschema_generator.py --id {{schema_namespace}}{series}/analysis.schema.json {{staged_schema_dir}}/analysis.yaml > {{dest}}/jsonschema/analysis.schema.json
  uv run python tools/jsonschema_generator.py --id {{schema_namespace}}{series}/provenance.schema.json {{staged_schema_dir}}/provenance.yaml > {{dest}}/jsonschema/provenance.schema.json
  uv run python tools/jsonschema_generator.py --not-closed --id {{schema_namespace}}{series}/provenance.open.schema.json {{staged_schema_dir}}/provenance.yaml > {{dest}}/jsonschema/provenance.open.schema.json
  uv run python tools/jsonld_context.py {{staged_schema_dir}}/provenance.yaml > {{dest}}/jsonld/provenance.context.jsonld
  uv run python tools/rules.py docs/specification.md {{staged_schema_dir}}/analysis.yaml {{staged_schema_dir}}/provenance.yaml --schemas {{dest}}/jsonschema/analysis.schema.json {{dest}}/jsonschema/provenance.schema.json {{dest}}/jsonschema/provenance.open.schema.json > {{dest}}/rules/rules.json

# Check that the committed generated files, the contract (`gen-schema`) and the
# Python datamodels (`gen-python`), are what the two make now: both run again
# into tmp/generated-check/, and each file is compared with its committed
# copy. The `__pycache__` Python writes on importing the datamodels (the tests
# do) is ignored by git, the wheel and this check.
[group('model development')]
check-generated:
  rm -rf tmp/generated-check
  just dest=tmp/generated-check/project pymodel=tmp/generated-check/datamodel gen-schema gen-python
  diff -r tmp/generated-check/project/jsonschema {{dest}}/jsonschema
  diff -r tmp/generated-check/project/jsonld {{dest}}/jsonld
  diff -r tmp/generated-check/project/rules {{dest}}/rules
  diff -r -x __pycache__ -x __init__.py tmp/generated-check/datamodel {{pymodel}}

# Fail unless HEAD is the commit tagged v<version>.
_at-tag version:
  #!/usr/bin/env bash
  set -euo pipefail
  if [[ "$(git rev-parse -q --verify "refs/tags/v{{version}}^{commit}")" != "$(git rev-parse HEAD)" ]]; then
    echo "Error: HEAD is not at the tag v{{version}}. Deploy from a checkout of it: git checkout v{{version}}" >&2
    exit 1
  fi

# Copy astra-tools' docs/cli.md and docs/installation.md into docs/: from
# astra-tools at `tools_ref`, or from the folder ASTRA_TOOLS_DOCS names
_docs-tools:
  #!/usr/bin/env bash
  set -euo pipefail
  from="{{tools_docs}}"
  if [[ -z "${from}" ]]; then
    rm -rf tmp/astra-tools
    git clone --quiet --depth 1 --branch "{{tools_ref}}" https://github.com/LightconeResearch/astra-tools.git tmp/astra-tools
    from=tmp/astra-tools/docs
  fi
  cp "${from}/cli.md" "${from}/installation.md" docs/
