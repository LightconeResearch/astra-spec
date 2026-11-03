# ASTRA Spec - Development Notes

## Schema and specification

The ASTRA schema is written in LinkML, in four modules under `src/astra/schema/`:

- **`types.yaml`** — the named types: `id`, `address`, `reference`, `option_reference`, `condition`, `commit_id`, `content_hash`, `spec_version`, `timestamp`. The id grammar is written once, in `settings`, and the `structured_pattern`s are built from it.
- **`analysis.yaml`** — the analysis document, `astra.yaml` (`tree_root: Analysis`): inputs, outputs, recipes, decisions and options, universes, declarations of other analyses.
- **`insight.yaml`** — insights and evidence, with the W3C Web Annotation selectors.
- **`provenance.yaml`** — the provenance record of a result (`tree_root: ProvenanceRecord`), mapped onto PROV-O.

The LinkML descriptions are the normative definitions of the fields: the field reference (`docs/elements/`) is generated from them, and the specification links to it rather than restating fields. Write each description in one or two sentences, in the present tense, saying what the field is and what it takes.

**`docs/specification.md`** is the normative specification. It carries the concepts, the grammars and the rule catalogue (its §9: every rule, with a code, a layer, a level and a source). It changes whenever a rule or a concept does: a new or changed rule goes into the catalogue, and the section that explains it links to the code.

Schema conventions (the contract tests check the maps and the patterns):

- Every element referenced by id is an entry of a map keyed by its id. The class has a key slot, `id` with `key: true` and `range: id` (`DecisionSelection` is keyed by `decision`, an `address`), and the map is a `multivalued: true` + `inlined: true` slot. A list of objects is `multivalued: true` + `inlined_as_list: true`. Element ids are `key`s, never `identifier`s; `Environment.iri` is the only `identifier`.
- Patterns stay in the subset ECMA-262 and Python's `re` share: anchored patterns end in `$(?!\n)`, and they use explicit classes (`[0-9]`, `[^\x00-\x20\x7f]`, `[^\x00-\x1f\x7f]`) rather than `.`, `\s`, `\S`, `\d`, `\w` or `\b`. No lookbehind, named groups, `\A` or `\Z`.
- A named type in `types.yaml` exists only if more than one field uses it; a pattern used once is written on its field.
- Module headers keep the placeholder `version: 0.0.0` (see Release).

The other docs pages (`docs/index.md`, `docs/getting-started.md`, `docs/cli.md`, `docs/llms.txt`) and `README.md` are to be kept consistent with the specification. `docs/llms.txt` is the agent-facing briefing served at `/latest/llms.txt` ([llms.txt convention](https://llmstxt.org/)), and is also shipped inside the wheel as `astra/docs/llms.txt` (hatch force-include in `pyproject.toml`) so that `astra guide` in astra-tools can print the copy matching the installed schema.

## The generated contract

The JSON Schemas generated from the LinkML sources are the contract: what validators in any language (astra-tools, typescript-astra, editors) check documents against. They live in **`src/astra/schema/generated/`** and are committed:

- `analysis.schema.json` — `astra.yaml`, closed
- `provenance.schema.json` — a record, closed
- `provenance.open.schema.json` — a record, open (for checkers reading records of a newer version)
- `analysis.context.jsonld`, `provenance.context.jsonld` — the JSON-LD contexts

After any change to a schema module, run `just gen-schema` and commit the regenerated `src/astra/schema/generated/` with the change. Never edit these files by hand. `just check-generated` regenerates into `tmp/` and fails on any difference from what is committed; it is part of `just test` and CI. The generators stamp the latest git tag's version into the files, so the drift check needs the tags fetched.

The JSON Schemas are built by **`tools/jsonschema_generator.py`**, a small extension of LinkML's `JsonSchemaGenerator` (dev-only, LinkML pinned in the dev group). It adds `propertyNames` with the key's pattern to every id-keyed map and allows one written form per map entry: an object without its key, or, for `Universe.decisions`, the compact `<decision>: <option>`. The JSON-LD contexts come from stock `gen-jsonld-context`.

The package ships only artefacts: the LinkML sources and `generated/`, as the namespace package `astra.schema` (plus `astra/docs/llms.txt`). There are no Python files under `src/astra/` and no runtime dependencies; build-time Python lives in `tools/`.

## Tests

`just test` runs the drift check (`check-generated`), pytest and `linkml-lint`. Everything is validated as a consumer would: a plain `jsonschema` Draft 2019-09 validator against the committed generated schemas, with YAML loaded as YAML 1.2 by ruamel.yaml's safe loader (never PyYAML, never LinkML's validators or Python models).

Fixtures are whole documents in `tests/data/valid/` and `tests/data/invalid/`, named `<Root>-<nnn>-<what>.yaml` with `<Root>` `Analysis` or `ProvenanceRecord`. Each invalid fixture is a minimal valid document with one thing broken, and starts with exactly two comment lines:

```yaml
# rule: <CODE>          a code from the specification's rule catalogue (§9)
# fails at: <location>  a JSON Pointer, `(root)` for the document, or `parse`
```

The test asserts that the validator reports an error at that location. Every schema-layer code in the catalogue has at least one invalid fixture. Fixtures with a duplicate key fail at parse and are excluded from pre-commit's `check-yaml`. Every `astra.yaml` under `examples/` must also validate.

## Documentation versioning (mike)

The whole docs site is versioned with [mike](https://github.com/squidfunk/mike) — specifically squidfunk's fork, which Zensical's versioning provider depends on. Each release deploys a full copy of the site to a subdirectory of the `gh-pages` branch (`/0.0.9/`, `/latest/`, etc.). Mike is enabled via `[project.extra.version] provider = "mike"` in `zensical.toml`; the version dropdown in the header is rendered natively.

Release flow:

1. `just release X.Y.Z` — regenerates the contract with the release version (`RELEASE_VERSION=X.Y.Z just gen-schema`), updates `CITATION.cff`, commits both (`src/astra/schema/generated/` and `CITATION.cff`), and creates an annotated tag. Does not push. Schema YAMLs are *not* mutated: they keep the placeholder `version: 0.0.0`, and the generators read a staged copy under `tmp/schema/` with the version injected, from `$RELEASE_VERSION` or else the latest git tag.
2. `git push && git push origin vX.Y.Z` — review then push. The `Deploy versioned docs on tag` GitHub Actions workflow runs `mike deploy --push --update-aliases X.Y.Z latest` automatically.

For a manual deploy (e.g. backfilling a tag), `just docs-deploy X.Y.Z` runs the same `mike deploy` locally.

First-time setup: after the first deploy, run `just docs-set-default latest` once so the bare site root redirects to `/latest/`.

Hosting: mike pushes to `gh-pages`. The hosting platform (Cloudflare Pages, GitHub Pages, etc.) must be configured to serve from `gh-pages`, not `main`. Without this, `mike deploy` runs successfully but the site doesn't pick up versioned URLs in production.

Schema artifacts (`docs/schema/*.{yaml,json,jsonld}`) are versioned along with the rest of the site: `just gen-doc` writes the merged LinkML model there and copies in the committed contract from `src/astra/schema/generated/`. Machine consumers should resolve them via the canonical `https://w3id.org/astra/...` URI (which redirects to a hosted location), or pin to `astra-spec.org/X.Y.Z/schema/...`.

## Key Commands

```bash
just test             # Drift check of the generated files, pytest, and linkml-lint
just gen-schema       # Regenerate the contract into src/astra/schema/generated/ (commit it)
just check-generated  # Fail if the committed generated files differ from a fresh generation
just lint             # Lint the schema (linkml-lint)
just gen-doc          # Generate the field reference (docs/elements/) and docs/schema/
just docs-serve       # Build and preview docs locally with live reload
just release X.Y.Z    # Regenerate the contract with the version, update CITATION.cff, commit and tag
```

## Repository Layout

- `src/astra/schema/` — LinkML schema sources: `types.yaml`, `analysis.yaml`, `insight.yaml`, `provenance.yaml` (edit these)
- `src/astra/schema/generated/` — The generated contract: JSON Schemas and JSON-LD contexts (regenerate with `just gen-schema`, commit, never edit)
- `tools/jsonschema_generator.py` — The JSON Schema generator extension
- `docs/` — Documentation source (rendered with [Zensical](https://zensical.org/); config in `zensical.toml`)
- `docs/specification.md` — The normative ASTRA specification
- `docs/index.md` — Landing page (clean, MCP-style with card grid nav)
- `docs/getting-started.md` — Install + scaffold + validate tutorial
- `docs/cli.md` — `astra` CLI reference (covers commands shipped by `astra-tools`)
- `docs/elements/` — Auto-generated schema reference (generated by `just gen-doc`, not committed)
- `docs/schema/` — Published schema artifacts (written by `just gen-doc`, not committed)
- `examples/` — Example ASTRA projects (iris, iris_pipeline)
- `tests/data/valid/`, `tests/data/invalid/` — Fixtures, validated through the committed JSON Schemas
- `tests/generator/` — Scratch schemas for the generator extension's and the named types' tests
- `rfcs/` — ASTRA RFCs, the record of significant changes to the specification
