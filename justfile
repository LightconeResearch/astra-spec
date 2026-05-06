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
config_yaml := if env_var_or_default("LINKML_GENERATORS_CONFIG_YAML", "") != "" {
  "--config-file " + env_var_or_default("LINKML_GENERATORS_CONFIG_YAML", "")
} else {
  ""
}
gen_doc_args := env_var_or_default("LINKML_GENERATORS_DOC_ARGS", "")
gen_java_args := env_var_or_default("LINKML_GENERATORS_JAVA_ARGS", "")
gen_owl_args := env_var_or_default("LINKML_GENERATORS_OWL_ARGS", "")
gen_pydantic_args := env_var_or_default("LINKML_GENERATORS_PYDANTIC_ARGS", "")
gen_ts_args := env_var_or_default("LINKML_GENERATORS_TYPESCRIPT_ARGS", "")

# Directory variables
src := "src"
dest := "project"
pymodel := src / schema_name / "datamodel"
schema_source_file := env_var_or_default("LINKML_SCHEMA_SOURCE_FILE", schema_name)
source_schema_path := source_schema_dir / schema_source_file + ".yaml"
docdir := "docs/specification/draft/elements"  # Directory for the generated draft schema reference
distrib_schema_path := "docs/schema/draft"  # Directory for the draft machine-readable schema artifacts

# ============== Project recipes ==============

# List all commands as default command. The prefix "_" hides the command.
_default: _status
    @just --list

# Initialize a new project (use this for projects not yet under version control)
[group('project management')]
setup: _check-config _git-init install _git-add && _setup_part2
  git commit -m "Initialise git with minimal project" -a || true

_setup_part2: gen-project gen-doc
  @echo
  @echo '=== Setup completed! ==='
  @echo 'Various model representations have been created under directory "project". By default'
  @echo 'they are ignored by git. You decide whether you want to add them to git tracking or'
  @echo 'continue to git-ignore them as they can be regenerated if needed.'
  @echo 'For tracking specific subfolders, add !project/[foldername]/* line(s) to ".gitignore".'

# Install project dependencies
[group('project management')]
install:
  uv sync --group dev

# Sync the docs dependency group (zensical)
[group('documentation')]
docs-install:
  uv sync --group docs

# Updates project template and LinkML package
[group('project management')]
update: _update-template _update-linkml

# Clean all generated files
[group('project management')]
clean: _clean_project
  rm -rf tmp
  rm -rf {{docdir}}/*.md

# (Re-)Generate project and documentation locally
[group('model development')]
site: gen-project gen-doc

# Build docs site (output: site/)
[group('documentation')]
docs: _docs-prep
  uv run zensical build

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

_docs-prep: gen-doc docs-install

# Run all tests
[group('model development')]
test: _test-schema _test-python _test-examples

# Run linting
[group('model development')]
lint:
  uv run linkml-lint {{source_schema_dir}}

# Tag a new release: stamps the version into the schema, snapshots draft/ into
# a frozen X.Y.Z/ directory under docs/specification and docs/schema, updates
# CITATION.cff, commits, and creates an annotated git tag.
[group('model development')]
release version:
  #!/usr/bin/env bash
  set -euo pipefail
  if ! [[ "{{version}}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Error: version must be X.Y.Z (got '{{version}}')" >&2
    exit 1
  fi
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "Error: working tree is not clean. Commit or stash changes first." >&2
    exit 1
  fi
  if git rev-parse "v{{version}}" >/dev/null 2>&1; then
    echo "Error: tag v{{version}} already exists." >&2
    exit 1
  fi
  if [[ -e "docs/specification/{{version}}" || -e "docs/schema/{{version}}" ]]; then
    echo "Error: a snapshot for {{version}} already exists." >&2
    exit 1
  fi
  export LINKML_FORCE_VERSION={{version}}
  just gen-doc
  just snapshot-version {{version}}
  if [[ -f CITATION.cff ]]; then
    today=$(date -u +%Y-%m-%d)
    sed -i "s/^version: .*/version: \"{{version}}\"/" CITATION.cff
    sed -i "s/^date-released: .*/date-released: \"${today}\"/" CITATION.cff
  fi
  git add {{source_schema_dir}}/*.yaml CITATION.cff docs/specification docs/schema
  git commit -m "Release v{{version}}"
  git tag -a "v{{version}}" -m "Release v{{version}}"
  echo
  echo "Created snapshot, commit, and tag v{{version}}."
  echo "Push with: git push && git push origin v{{version}}"

# Snapshot the current draft/ tree into a frozen X.Y.Z/ tree. Called by `release`,
# but usable standalone to backfill a snapshot if the destination doesn't exist.
[group('model development')]
snapshot-version version: && _regen-spec-hub
  #!/usr/bin/env python3
  import re, shutil, sys
  from pathlib import Path

  v = "{{version}}"
  if not re.match(r"^\d+\.\d+\.\d+$", v):
      sys.exit(f"Error: version must be X.Y.Z (got '{v}')")
  spec_dst = Path(f"docs/specification/{v}")
  schema_dst = Path(f"docs/schema/{v}")
  if spec_dst.exists() or schema_dst.exists():
      sys.exit(f"Error: snapshot for {v} already exists.")

  shutil.copytree("docs/specification/draft", spec_dst)
  shutil.copytree("docs/schema/draft", schema_dst)

  index = spec_dst / "index.md"
  text = index.read_text().replace("**Version**: draft", f"**Version**: {v}")
  banner = (
      f'!!! note "Version {v}"\n'
      f'    This is a frozen release of the ASTRA specification. '
      f'See the [specification index](../) for other versions or the '
      f'latest [draft](../draft/).\n\n'
  )
  index.write_text(banner + text)

# Generate md documentation for the schema and add artifacts
[group('model development')]
gen-doc: _set-version _gen-yaml && _add-artifacts
  uv run gen-doc {{gen_doc_args}} -d {{docdir}} {{source_schema_path}}

# Generate the Python data models (dataclasses & pydantic)
gen-python: _set-version
  uv run gen-project -d  {{pymodel}} -I python {{source_schema_path}}
  just _fix-python-keywords
  uv run gen-pydantic {{gen_pydantic_args}} {{source_schema_path}} > {{pymodel}}/{{schema_name}}_pydantic.py

# Generate project files including Python data model
[group('model development')]
gen-project: _set-version
  uv run gen-project {{config_yaml}} -d {{dest}} {{source_schema_path}}
  mv {{dest}}/*.py {{pymodel}}
  just _fix-python-keywords
  uv run gen-pydantic {{gen_pydantic_args}} {{source_schema_path}} > {{pymodel}}/{{schema_name}}_pydantic.py

  @# Some generators ignore config_yaml or cannot create directories, so we run them separately.
  uv run gen-java {{gen_java_args}} --output-directory {{dest}}/java/ {{source_schema_path}}

  @if [ ! -d "{{dest}}/typescript" ]; then \
    mkdir -p {{dest}}/typescript ; \
  fi
  uv run gen-typescript {{gen_ts_args}} {{source_schema_path}} > {{dest}}/typescript/{{schema_name}}.ts

  @if [ ! -d "{{dest}}/owl" ]; then \
    mkdir -p {{dest}}/owl ; \
  fi
  uv run gen-owl {{gen_owl_args}} {{source_schema_path}} > "{{dest}}/owl/{{schema_name}}.owl.ttl"

# ============== Migrations recipes for Copier ==============

# Hidden command to adjust the directory layout on upgrading a project
# created with linkml-project-copier v0.1.x to v0.2.0 or newer.
# Use with care! - It may not work for customized projects.
_post_upgrade_v020: && _post_upgrade_v020py
  mv docs/*.md docs/elements

_post_upgrade_v020py:
    #!{{shebang}}
    import subprocess
    from pathlib import Path
    # Git move files from folder src to folder dest
    tasks = [
        (Path("src/docs/files"), Path("docs")),
        (Path("src/docs/templates"), Path("docs/templates-linkml")),
        (Path("src/data/examples"), Path("tests/data/")),
    ]
    for src, dest in tasks:
        for path_obj in src.rglob("*"):
            if not path_obj.is_file():
                continue
            file_dest = dest / path_obj.relative_to(src)
            if not file_dest.parent.exists():
                file_dest.parent.mkdir(parents=True)
            print(f"Moving {path_obj} --> {file_dest}")
            subprocess.run(["git", "mv", str(path_obj), str(file_dest)])
    print(
        "Migration to v0.2.x completed! Check the changes carefully before committing."
    )

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

# Update project template
_update-template:
  copier update --trust --skip-answered

# Update LinkML to latest version
_update-linkml:
  uv add linkml --upgrade-package linkml

# Fix Python keywords in generated dataclass model (gen-project/pythongen
# does not handle reserved words; the pydantic generator does this itself).
_fix-python-keywords:
  uv run python -c "\
  import re, pathlib; \
  p = pathlib.Path('{{pymodel}}/analysis.py'); \
  s = p.read_text(); \
  s = re.sub(r'^(\s+)from:', r'\1from_:', s, flags=re.MULTILINE); \
  s = re.sub(r'\bself\.from\b', 'self.from_', s); \
  s = re.sub(r'\bslots\.from\b', 'slots.from_', s); \
  s = re.sub(r'ASTRA\.from\b', \"ASTRA['from']\", s); \
  p.write_text(s)"

# Test schema generation
_test-schema:
  uv run gen-project {{config_yaml}} -d tmp {{source_schema_path}} 2>/dev/null

# Run Python unit tests with pytest
_test-python: gen-python
  uv run python -m pytest

# Run example tests
# NOTE: linkml-run-examples has known issues:
# 1. "simple dict" detection bug for classes with an identifier + exactly
#    one required field (e.g. Option).
# 2. The 'from' slot generates invalid Python (keyword conflict) when
#    pythongen compiles the module on the fly.
# Allow this step to fail until the upstream issues are resolved.
_test-examples: _ensure_examples_output
  -uv run linkml-run-examples \
    --input-formats json \
    --input-formats yaml \
    --output-formats json \
    --output-formats yaml \
    --counter-example-input-directory tests/data/invalid \
    --input-directory tests/data/valid \
    --output-directory examples/output \
    --schema {{source_schema_path}} > examples/output/README.md

# Inject a version into all schema YAML files. Uses LINKML_FORCE_VERSION if
# set (the `release` recipe relies on this to stamp X.Y.Z before its tag
# exists); otherwise falls back to the latest git tag.
_set-version:
  #!/usr/bin/env bash
  if [[ -n "${LINKML_FORCE_VERSION:-}" ]]; then
    VERSION="${LINKML_FORCE_VERSION}"
  else
    TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
    VERSION=${TAG#v}
  fi
  for f in {{source_schema_dir}}/*.yaml; do
    grep -q '^version:' "$f" && sed -i "s/^version: .*/version: ${VERSION}/" "$f"
  done

# Regenerate the version list inside the markers in docs/specification/index.md
_regen-spec-hub:
  #!/usr/bin/env python3
  import re
  from pathlib import Path

  spec_dir = Path("docs/specification")
  versions = sorted(
      (d.name for d in spec_dir.iterdir()
       if d.is_dir() and d.name != "draft"
       and re.match(r"^\d+\.\d+\.\d+$", d.name)),
      key=lambda v: tuple(int(x) for x in v.split(".")),
      reverse=True,
  )

  lines = []
  if versions:
      lines.append(f"- **[{versions[0]}]({versions[0]}/)** — current release")
      for v in versions[1:]:
          lines.append(f"- [{v}]({v}/)")
  lines.append("- [draft](draft/) — work in progress")

  hub = spec_dir / "index.md"
  text = hub.read_text()
  pattern = r"<!-- VERSIONS:START -->.*?<!-- VERSIONS:END -->"
  replacement = "<!-- VERSIONS:START -->\n" + "\n".join(lines) + "\n<!-- VERSIONS:END -->"
  hub.write_text(re.sub(pattern, replacement, text, flags=re.DOTALL))

# Add the merged model to docs/schema.
_gen-yaml:
  -mkdir -p {{distrib_schema_path}}
  uv run gen-yaml {{source_schema_path}} > {{distrib_schema_path}}/{{schema_name}}.yaml

# Generate JSON Schema and JSON-LD context into the distribution schema path
_add-artifacts:
  uv run gen-json-schema {{source_schema_path}} > {{distrib_schema_path}}/{{schema_name}}.schema.json
  uv run gen-jsonld-context {{source_schema_path}} > {{distrib_schema_path}}/{{schema_name}}.context.jsonld

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

_clean_project:
    #!{{shebang}}
    import shutil, pathlib
    # remove the generated project files
    for d in pathlib.Path("{{dest}}").iterdir():
        if d.is_dir():
            print(f'removing "{d}"')
            shutil.rmtree(d, ignore_errors=True)
    # remove the generated python data model
    for d in pathlib.Path("{{pymodel}}").iterdir():
        if d.name == "__init__.py":
            continue
        print(f'removing "{d}"')
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
        else:
            d.unlink()

_ensure_examples_output:  # Ensure a clean examples/output directory exists
  -mkdir -p examples/output
  -rm -rf examples/output/*.*

# ============== Include project-specific recipes ==============

import "project.justfile"

# ====== Override recipes from above with custom versions =======

# Uncomment the following line to allow duplicate recipe names
#set allow-duplicate-recipes

# Overriding recipes from the root justfile by adding a recipe with the same
# name in an imported file is not possible until a known issue in just is fixed,
# https://github.com/casey/just/issues/2540 - So we need to override them here.
