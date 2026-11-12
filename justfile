# ============ Hint for for Windows Users ============

# On Windows the "sh" shell that comes with Git for Windows should be used.
# If it is not on path, provide the path to the executable in the following line.
#set windows-shell := ["C:/Program Files/Git/usr/bin/sh", "-cu"]

# ============ Variables used in recipes ============

# Load environment variables from config.public.mk or specified file
set dotenv-load := true
# set dotenv-filename := env_var_or_default("LINKML_ENVIRONMENT_FILENAME", "config.public.mk")
set dotenv-filename := x'${LINKML_ENVIRONMENT_FILENAME:-config.public.mk}'

# Set shebang line for cross-platform Python recipes (assumes presence of launcher on Windows)
shebang := if os() == 'windows' {
  'py'
} else {
  '/usr/bin/env python3'
}

# Environment variables with defaults
schema_name := env_var_or_default("LINKML_SCHEMA_NAME", "_no_schema_given_")
source_schema_dir := env_var_or_default("LINKML_SCHEMA_SOURCE_DIR", "")
gen_doc_args := env_var_or_default("LINKML_GENERATORS_DOC_ARGS", "")

# Directory variables
schema_source_file := env_var_or_default("LINKML_SCHEMA_SOURCE_FILE", schema_name)
source_schema_path := source_schema_dir / schema_source_file + ".yaml"
# Generators read from a staged copy under tmp/schema/ where the version is
# injected at build time. Source YAMLs keep a placeholder version, so running
# generators never produces a "fix version" diff in the working tree.
staged_schema_dir := "tmp/schema"
staged_schema_path := staged_schema_dir / schema_source_file + ".yaml"
docdir := "docs/elements"  # Directory for generated documentation
# Each JSON Schema's $id is this, the series of the version it is generated
# with (X.Y for a release X.Y.Z, a pre-release's whole version, or dev), `/`,
# then its file name
schema_namespace := "https://w3id.org/astra/"
distrib_schema_path := "docs/schema"  # Directory for publishing schema artifacts
# The site shows astra-tools' CLI reference and installation page, which live
# in astra-tools beside the code they describe (`_docs-tools`): taken from its
# branch or tag `tools_ref` (v0.1-rebuild, astra-tools' v0.1 work, until it
# reaches main), which ASTRA_TOOLS_REF overrides, or from the local folder
# ASTRA_TOOLS_DOCS names, such as ../astra-tools/docs
tools_ref := if env_var_or_default("ASTRA_TOOLS_REF", "") == "" { "v0.1-rebuild" } else { env_var("ASTRA_TOOLS_REF") }
tools_docs := env_var_or_default("ASTRA_TOOLS_DOCS", "")

# ============== Project recipes ==============

# List all commands as default command. The prefix "_" hides the command.
_default: _status
    @just --list

# Initialize a new project (use this for projects not yet under version control)
[group('project management')]
setup: _check-config _git-init install _git-add && _setup_part2
  git commit -m "Initialise git with minimal project" -a || true

_setup_part2: gen-doc
  @echo
  @echo '=== Setup completed! ==='

# Install project dependencies
[group('project management')]
install:
  uv sync --group dev

# Sync the docs dependency group (zensical)
[group('documentation')]
docs-install:
  uv sync --group docs

# Update the LinkML package
[group('project management')]
update: _update-linkml

# Clean all generated files
[group('project management')]
clean:
  rm -rf tmp
  rm -rf {{docdir}}/*.md

# (Re-)Generate documentation locally
[group('model development')]
site: gen-doc

# Build docs site (output: site/)
[group('documentation')]
docs: _docs-prep
  uv run zensical build

# Deploy a versioned snapshot of the docs to gh-pages via mike, moving each
# alias named after the version to it: a release X.Y.Z moves X.Y and latest,
# a pre-release none. The tag workflow runs it after `just release`. It runs
# only at the commit tagged vX.Y.Z (`_at-tag`), before it builds anything: the
# site publishes the checkout's committed contract (`_add-artifacts`), and
# only the tagged commit holds the release's, while main holds `dev`.
[group('documentation')]
docs-deploy version *aliases: (_at-tag version) _docs-prep
  uv run mike deploy --push --update-aliases {{version}} {{aliases}}

[group('documentation')]
docs-set-default alias='latest':
  uv run mike set-default --push {{alias}}

[group('documentation')]
docs-versions:
  uv run mike list

[group('documentation')]
docs-delete-version version:
  uv run mike delete --push {{version}}

# Build docs in strict mode
[group('documentation')]
docs-strict: _docs-prep
  uv run zensical build --strict

# Serve docs with live reload at http://127.0.0.1:8000
[group('documentation')]
docs-serve: _docs-prep
  uv run zensical serve

[group('documentation')]
docs-clean:
  rm -rf site

# Prepare the docs: the field reference, the published schema files, and
# astra-tools' CLI reference and installation page (`_docs-tools`)
_docs-prep: gen-doc docs-install _docs-tools

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

# Run all tests: the generated files are current, pytest, and the schema lints clean
[group('model development')]
test: check-generated _pytest lint

# Generate the JSON Schemas of the analysis document and the provenance record
# (closed, and open for fields it doesn't know), the record's JSON-LD context
# (LinkML's, with every IRI in full and no term a prefix) and the rule
# catalogue, into `out`, from the staged (versioned) schema. Each
# JSON Schema's `$id` is the URI of its own file under its series (`{series}`,
# filled in by the generator: `0.1` for every 0.1.x, a pre-release's whole
# version, or `dev`), so the closed and open record schemas are distinct, and
# so are two minor versions. `rules.json` holds the rules extracted from the
# codes table of the specification's Rules section, and the code of each JSON
# Schema keyword that can fail. Last, the Pydantic models of the two documents,
# LinkML's `gen-pydantic` with the base model of `linkml-templates/pydantic/`,
# whose one validator gives each entry of a map keyed by `id` its key as its
# `id`: a typed view of a document the JSON Schema accepted, never a validator
[group('model development')]
gen-schema out="src/astra/schema/generated": _stage-versioned
  mkdir -p {{out}}
  uv run python tools/jsonschema_generator.py --id {{schema_namespace}}{series}/analysis.schema.json {{staged_schema_dir}}/analysis.yaml > {{out}}/analysis.schema.json
  uv run python tools/jsonschema_generator.py --id {{schema_namespace}}{series}/provenance.schema.json {{staged_schema_dir}}/provenance.yaml > {{out}}/provenance.schema.json
  uv run python tools/jsonschema_generator.py --not-closed --id {{schema_namespace}}{series}/provenance.open.schema.json {{staged_schema_dir}}/provenance.yaml > {{out}}/provenance.open.schema.json
  uv run python tools/jsonld_context.py {{staged_schema_dir}}/provenance.yaml > {{out}}/provenance.context.jsonld
  uv run python tools/rules.py docs/specification.md {{staged_schema_dir}}/analysis.yaml {{staged_schema_dir}}/provenance.yaml --schemas {{out}}/analysis.schema.json {{out}}/provenance.schema.json {{out}}/provenance.open.schema.json > {{out}}/rules.json
  uv run gen-pydantic --template-dir linkml-templates/pydantic {{staged_schema_dir}}/analysis.yaml > {{out}}/analysis.py
  uv run gen-pydantic --template-dir linkml-templates/pydantic {{staged_schema_dir}}/provenance.yaml > {{out}}/provenance.py

# Check that the committed generated files are what `gen-schema` makes now.
# The `__pycache__` Python writes on importing the Pydantic models (the tests
# do) is ignored by git, the wheel and this check
[group('model development')]
check-generated:
  rm -rf tmp/generated-check
  just gen-schema tmp/generated-check
  diff -r -x __pycache__ tmp/generated-check src/astra/schema/generated

# Run linting
[group('model development')]
lint:
  uv run linkml-lint {{source_schema_dir}}

# Tag a new release: regenerates the generated schema artefacts with the new
# version, updates CITATION.cff, commits both, and creates an annotated git
# tag; then regenerates them as `dev` and commits that, so that only the
# tagged commit holds the version. The version is X.Y.Z, or a pre-release:
# X.Y.Z followed by aN, bN or rcN (PEP 440's normal form, which the wheel
# takes from the tag). A patch release never changes what is valid, so when
# the version's minor already has a release (from 0.1 on), the regenerated
# files are compared with its greatest release (`tools/check_patch.py`) before
# anything is committed. Schema YAMLs are not mutated — generators inject the
# version from $RELEASE_VERSION at build time. After pushing the tag, the
# `Deploy versioned docs on tag` workflow will publish the docs automatically.
[group('model development')]
release version:
  #!/usr/bin/env bash
  set -euo pipefail
  if ! [[ "{{version}}" =~ ^([0-9]+)\.([0-9]+)\.[0-9]+((a|b|rc)[0-9]+)?$ ]]; then
    echo "Error: version must be X.Y.Z, or X.Y.Z followed by aN, bN or rcN (got '{{version}}')" >&2
    exit 1
  fi
  minor="${BASH_REMATCH[1]}.${BASH_REMATCH[2]}"
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "Error: working tree is not clean. Commit or stash changes first." >&2
    exit 1
  fi
  if git rev-parse "v{{version}}" >/dev/null 2>&1; then
    echo "Error: tag v{{version}} already exists." >&2
    exit 1
  fi
  if [[ ! -f CITATION.cff ]]; then
    echo "Error: CITATION.cff is missing." >&2
    exit 1
  fi
  RELEASE_VERSION="{{version}}" just gen-schema
  if [[ "${minor}" != "0.0" ]]; then
    previous=$(git tag --list "v${minor}.*" --sort=-version:refname | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | head -n 1 || true)
    if [[ -n "${previous}" ]] && ! uv run python tools/check_patch.py "${previous}"; then
      git checkout -- src/astra/schema/generated
      echo "Error: v{{version}} changes what is valid since ${previous}; that waits for the next minor version." >&2
      exit 1
    fi
  fi
  git add src/astra/schema/generated
  today=$(date -u +%Y-%m-%d)
  sed -i "s/^version: .*/version: \"{{version}}\"/" CITATION.cff
  sed -i "s/^date-released: .*/date-released: \"${today}\"/" CITATION.cff
  git add CITATION.cff
  git commit -m "Release v{{version}}"
  git tag -a "v{{version}}" -m "Release v{{version}}"
  RELEASE_VERSION=dev just gen-schema
  git add src/astra/schema/generated
  git commit -m "Back to dev after v{{version}}"
  echo
  echo "Created the tagged commit v{{version}}, then a commit back to dev. Next steps:"
  echo "  - git push --atomic origin HEAD v{{version}}"
  echo "  - the deploy-docs-on-tag workflow will publish the docs automatically"

# Generate md documentation for the schema and add artifacts: both roots, the
# analysis document and the provenance record, in one run (`--include`), so
# that the slots the two share get one page each, rather than one run
# overwriting the other's. The index, type and slot pages use the templates in
# linkml-templates/. `tools/docgen.py` is `gen-doc` with each description in a
# table cut at the end of its first sentence, or of its last word before 80
# characters, each range linked to its type, each `<` and `&` of a
# description shown as written, and a `-slot` suffix on a slot's page whose
# name differs from another page's only in case. The pages of an
# earlier build are removed first, so that none is left under an old name. Each
# Regex Pattern cell is then written as HTML, every character but an ASCII
# letter or digit as a character reference, so that the site shows the pattern
# exactly (`tools/pattern_cells.py`)
[group('model development')]
gen-doc: _stage-versioned _gen-yaml && _add-artifacts
  rm -f {{docdir}}/*.md
  uv run python tools/docgen.py {{gen_doc_args}} --template-directory linkml-templates --include {{staged_schema_dir}}/provenance.yaml -d {{docdir}} {{staged_schema_path}}
  uv run python tools/pattern_cells.py {{docdir}}

# ============== Hidden internal recipes ==============

# Show current project status
_status: _check-config
  @echo "Project: {{schema_name}}"
  @echo "Source: {{source_schema_path}}"

# Check project configuration
_check-config:
    #!{{shebang}}
    import os
    schema_name = os.getenv('LINKML_SCHEMA_NAME')
    if not schema_name:
        print('**Project not configured**:\n - See \'.env.public\'')
        exit(1)
    print('Project-status: Ok')

# Update LinkML to latest version
_update-linkml:
  uv add linkml --upgrade-package linkml

# Run Python unit tests with pytest
_pytest:
  uv run python -m pytest

# Stage a versioned copy of every schema YAML under tmp/schema/. The version
# is injected at build time so source files keep a stable placeholder and are
# never mutated by `gen-doc`. Uses $RELEASE_VERSION when set, otherwise the
# tag at HEAD without its `v`, otherwise `dev`: between releases, and in a
# clone without tags, the files are stamped `dev`. It must be X.Y.Z, X.Y.Z
# followed by aN, bN or rcN, or dev. The directory is cleared first, so a
# module that no longer exists isn't staged.
_stage-versioned:
  #!/usr/bin/env bash
  set -euo pipefail
  if [[ -n "${RELEASE_VERSION:-}" ]]; then
    VERSION="${RELEASE_VERSION}"
  elif TAG=$(git describe --tags --exact-match --match 'v[0-9]*' 2>/dev/null); then
    VERSION=${TAG#v}
  else
    VERSION=dev
  fi
  if ! [[ "${VERSION}" =~ ^([0-9]+\.[0-9]+\.[0-9]+((a|b|rc)[0-9]+)?|dev)$ ]]; then
    echo "Error: the version must be X.Y.Z, X.Y.Z followed by aN, bN or rcN, or dev (got '${VERSION}')" >&2
    exit 1
  fi
  rm -rf {{staged_schema_dir}}
  mkdir -p {{staged_schema_dir}}
  for f in {{source_schema_dir}}/*.yaml; do
    base=$(basename "$f")
    if grep -q '^version:' "$f"; then
      sed "s/^version: .*/version: ${VERSION}/" "$f" > "{{staged_schema_dir}}/${base}"
    else
      cp "$f" "{{staged_schema_dir}}/${base}"
    fi
  done

# Fail unless HEAD is the commit tagged v<version>.
_at-tag version:
  #!/usr/bin/env bash
  set -euo pipefail
  if [[ "$(git rev-parse -q --verify "refs/tags/v{{version}}^{commit}")" != "$(git rev-parse HEAD)" ]]; then
    echo "Error: HEAD is not at the tag v{{version}}. Deploy from a checkout of it: git checkout v{{version}}" >&2
    exit 1
  fi

# Add the merged models to docs/schema, one for each tree root: the analysis
# document's (`astra.yaml`) and the provenance record's (`provenance.yaml`).
# A LinkML schema should have at most one tree root (the metamodel's note on
# `tree_root`), so one model can't hold both.
_gen-yaml:
  -mkdir -p {{distrib_schema_path}}
  uv run gen-yaml {{staged_schema_path}} > {{distrib_schema_path}}/{{schema_name}}.yaml
  uv run gen-yaml {{staged_schema_dir}}/provenance.yaml > {{distrib_schema_path}}/provenance.yaml

# Publish the committed contract, the JSON Schemas, the record's JSON-LD
# context and `rules.json` of `gen-schema`, beside the merged model. Copied,
# not regenerated: stock `gen-json-schema` would publish a second, weaker
# schema. Any other .json or .jsonld there is removed, so only the contract is
# published; the Pydantic models ship in the wheel, not on the site.
_add-artifacts:
  rm -f {{distrib_schema_path}}/*.json {{distrib_schema_path}}/*.jsonld
  cp {{source_schema_dir}}/generated/*.json {{source_schema_dir}}/generated/*.jsonld {{distrib_schema_path}}/

# Initialize git repository
_git-init:
  git init

# Add files to git
_git-add:
  git add .

# Commit files to git
_git-commit:
  git commit -m 'chore: just setup was run' -a

# Show git status
_git-status:
  git status
