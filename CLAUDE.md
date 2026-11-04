# ASTRA Spec - Development Notes

## Schema and specification

The ASTRA schema is written in LinkML, in four modules under `src/astra/schema/`:

- **`types.yaml`** — the named types: `id`, `address`, `reference`, `option_reference`, `condition`, `commit_id`, `content_hash`, `spec_version`, `timestamp`. The id grammar is written once, in `settings`, and the `structured_pattern`s are built from it.
- **`analysis.yaml`** — the analysis document, `astra.yaml` (`tree_root: Analysis`): inputs, outputs, recipes, decisions and options, universes, declarations of other analyses.
- **`insight.yaml`** — insights and evidence, with the W3C Web Annotation selectors.
- **`provenance.yaml`** — the provenance record of a result (`tree_root: ProvenanceRecord`), mapped onto PROV-O.

The LinkML descriptions are the normative definitions of the fields: the field reference (`docs/elements/`) is generated from them, and the specification links to it rather than restating fields. Write each description in one or two sentences, in the present tense, saying what the field is and what it takes. Descriptions carry no history: no "no longer", "was" or "replaces".

**`docs/specification.md`** is the normative specification. It carries the concepts, the grammars and the rule catalogue (its §9: every rule, with a code, a layer, a level and a source). It changes whenever a rule or a concept does: a new or changed rule goes into the catalogue, and the section that explains it links to the code. §9 stays hand-written, and its four rule tables are also data: `generated/rules.json` is extracted from them (see below), so keep their headings and columns as they are.

Schema conventions (the contract tests check the maps and the patterns):

- Every element referenced by id is an entry of a map keyed by its id. The class has a key slot, `id` with `key: true` and `range: id` (`DecisionSelection` is keyed by `decision`, an `address`), and the map is a `multivalued: true` + `inlined: true` slot. A list of objects is `multivalued: true` + `inlined_as_list: true`. Element ids are `key`s, never `identifier`s; `Environment.iri` is the only `identifier`.
- Patterns stay in the subset ECMA-262 and Python's `re` share: every `$` outside a lookahead is written `$(?!\n)`, and every anchored pattern ends in one; patterns use explicit classes (`[0-9]`, `[^\x00-\x20\x7f]`, `[^\x00-\x1f\x7f]`) rather than `.`, `\s`, `\S`, `\d`, `\w` or `\b`. No lookbehind, named groups, `\A` or `\Z`.
- A named type in `types.yaml` exists only if more than one field uses it; a pattern used once is written on its field.
- Module headers keep the placeholder `version: 0.0.0` (see Release).

The other docs pages (`docs/index.md`, `docs/getting-started.md`, `docs/cli.md`, `docs/llms.txt`) and `README.md` are to be kept consistent with the specification. `docs/llms.txt` is the agent-facing briefing served at `/latest/llms.txt` ([llms.txt convention](https://llmstxt.org/)), and is also shipped inside the wheel as `astra/docs/llms.txt` (hatch force-include in `pyproject.toml`) so that `astra guide` in astra-tools can print the copy matching the installed schema.

## The generated contract

The JSON Schemas generated from the LinkML sources are the contract: what validators in any language (astra-tools, astra-typescript, editors) check documents against. They live in **`src/astra/schema/generated/`** and are committed:

- `analysis.schema.json` — `astra.yaml`, closed
- `provenance.schema.json` — a record, closed
- `provenance.open.schema.json` — a record, open (for checkers reading records of a newer version)
- `provenance.context.jsonld` — the record's JSON-LD context, mapping its terms onto PROV-O. There is no context for `astra.yaml`: LinkML's flat context would give its id-keyed maps a wrong RDF reading
- `rules.json` — the rule catalogue (design D13): `rules`, every rule of the specification's §9 in order (`code`, `layer`, `level`, `statement`, `source`, and `status` in the check layer), and `errors`, the code of every keyword of the three JSON Schemas that can report an error, keyed by its absolute keyword location (`<$id>#<JSON Pointer>`). The tests check fixtures through it, as astra-tools and astra-typescript do

After any change to a schema module, run `just gen-schema` and commit the regenerated `src/astra/schema/generated/` with the change. Never edit these files by hand. `just check-generated` regenerates into `tmp/` and fails on any difference from what is committed; it is part of `just test` and CI. The generators stamp the latest git tag's version into each JSON Schema's `$comment`, so the drift check needs the tags fetched.

The JSON Schemas are built by **`tools/jsonschema_generator.py`**, a small extension of LinkML's `JsonSchemaGenerator` (dev-only, LinkML pinned in the dev group). It adds `propertyNames` with the key's pattern to every id-keyed map and allows one written form per map entry: an object without its key, or, for a keyed class with exactly one other slot, the compact form, that slot's value (in this schema only `DecisionSelection`, so `Universe.decisions` is `<decision>: <option>`). It also adds `uniqueItems` to every list of strings, drops every `$defs` entry the root can't reach, and keeps only standard JSON Schema keywords at the top level: LinkML's `metamodel_version` goes, and the schema version moves into `$comment`. Last, it moves each class-level check (the `oneOf` of an `exactly_one_of`, then each class rule's `if`/`then`) into its own member of `allOf`, guarded by an `if` that the value is an object and each field the check reads has its JSON type: a check is skipped only where a `type` keyword already fails, so no verdict changes and a value of the wrong type is `WRONG_TYPE` alone. Each `required` in a check has its fields in a `properties` beside it, inside a `not` too, so that Ajv compiles the schemas under `strict: true`: `just check-ajv` checks it, with the Ajv pinned in `tools/ajv/`, and CI runs it. The record's JSON-LD context comes from stock `gen-jsonld-context`.

`rules.json` is built by **`tools/rules.py`**, from the specification and the generated JSON Schemas with their LinkML sources; never edit it, and never write §9 from it. Its extractor reads §9 with `markdown-it-py` (dev-only, never regular expressions), as CommonMark with GFM tables, and is strict, enforcing what §9's "The catalogue as data" paragraph says: no `## 9. Conformance` heading or more than one, a subsection other than the four, a missing or repeated one or one out of their order, a rule table (one with a Code column) outside them or a subsection without exactly one, a missing, unknown or repeated column, a row that doesn't write one cell per column (counted on its source line, blockquote markers aside), an empty cell, a malformed or repeated code, an unknown layer or level, a rule whose RFC 2119 keyword contradicts its level (in its text, in a code span, or as the cell reads once rendered), a Source cell that isn't plain text or holds a token other than an RFC number with an optional `§n`, `tidy-up`, `main`, `#n` or `§n` (separated by `, `), a cell holding anything but text, code spans, emphasis, links and inline HTML, or a cell whose Markdown can't be rebuilt from its tokens fails `just gen-schema`. The error map walks each JSON Schema and fails on any keyword it can't give a code, on any code that isn't a schema-layer rule of §9, and on any `rule` annotation that gives no keyword its code.

**Codes on constraints.** Each constraint in the LinkML sources names the rule it enforces with one annotation key, `rule`: `annotations: {rule: INVALID_COMMIT}`. It goes where the constraint is defined:

- on a type, for its pattern (`commit_id` → `INVALID_COMMIT`);
- on a slot, for the pattern the slot writes itself (`Input.path` → `INVALID_PATH`). A slot that writes its own pattern must have one; a slot that takes its type's pattern may have one, which then wins over the type's (`DecisionSelection.decision`, a map key: a bad key is `INVALID_ID` whatever its type);
- on a class rule (`rules:` entry), for the `if` and the `then` of its `allOf` member;
- on each branch of an `exactly_one_of`, the same code on every branch (its `allOf` member's `if`, `oneOf` and branches take it): LinkML 1.12.1 can't annotate the `exactly_one_of` list itself.

Every `rule` annotation must give some keyword its code: one on a class, an enum, a type no slot uses, or a slot with no pattern fails the build. Keywords whose code never varies take a default instead: `required` outside a rule (`MISSING_FIELD`); `additionalProperties: false` (`UNKNOWN_FIELD`); `type` (`WRONG_TYPE`), except on a map key, which takes the key's code; `minProperties`/`minItems` of 1 (`EMPTY_COLLECTION`; any other minimum has no code and fails the build); `uniqueItems` (`DUPLICATE_ENTRY`); `enum`/`minimum` (`INVALID_VALUE`). The annotations don't reach the JSON Schemas.

**To add or change a rule:** edit its row in §9 of `docs/specification.md`; for a schema-layer rule, annotate the constraint that enforces it (above); then run `just gen-schema` and commit `generated/rules.json` with the change. A new schema-layer code also needs an invalid fixture.

The package ships only artefacts: the LinkML sources and `generated/`, as the namespace package `astra.schema` (plus `astra/docs/llms.txt`). There are no Python files under `src/astra/` and no runtime dependencies; build-time Python lives in `tools/`.

## Tests

`just test` runs the drift check (`check-generated`), pytest and `linkml-lint`; `just check-ajv` (in CI, and wherever node is installed) compiles the three JSON Schemas with the pinned Ajv under `strict: true`. Everything is validated as a consumer would: a plain `jsonschema` Draft 2019-09 validator against the committed generated schemas, with YAML loaded as YAML 1.2.2 under the core schema only, by ruamel.yaml's safe loader restricted in `tests/conftest.py` (never PyYAML, never LinkML's validators or Python models). The loader allows no timestamps or merge keys, no tags beyond the core schema's and no `%YAML` but 1.2; it reads a scalar tagged `!` as a string; it takes two keys of a map to be the same when they are equal YAML nodes, with the same tag and canonical form; and it refuses the ill-formed text ruamel.yaml would read (a comment glued to a token, a line of a flow collection or a quoted scalar not indented past its block, `[-]`, `!<!>`, a `\U` escape beyond U+10FFFF), raising a `YAMLError`. `tests/test_loader.py` checks it against the error cases of [yaml-test-suite](https://github.com/yaml/yaml-test-suite), vendored in `tests/yaml-test-suite/` from the release `data-2022-01-17`.

Fixtures are whole documents in `tests/data/valid/` and `tests/data/invalid/`, named `<Root>-<nnn>-<what>.yaml` with `<Root>` `Analysis` or `ProvenanceRecord` (it picks the schema) and `<nnn>` numbering from `001` for valid fixtures, from `101` for invalid `Analysis` fixtures and from `201` for invalid `ProvenanceRecord` fixtures. Each invalid fixture is a minimal valid document with one thing broken, and starts with two comment lines (and a third, `# also:`, where its one break brings a second error; see below):

```yaml
# rule: <CODE>          a code from the specification's rule catalogue (§9)
# fails at: <location>  a JSON Pointer, `(root)` for the document, or `parse`
```

The test (`check_invalid_fixture` in `tests/test_fixtures.py`) asserts that the fixture fails for the right reason: the validator reports errors at that location and nowhere else, and `rules.json` gives those errors the fixture's rule, through each error's absolute keyword location (`absolute_keyword_location` in `tests/conftest.py`: the JSON Pointer of `error.schema`, found in the schema by identity, then `/` and `error.validator`, since `jsonschema`'s `schema_path` runs through `$ref`s; spec §10 gives the same method for Ajv). A `parse` fixture's loader error must give exactly its code (`parse_code`: `DUPLICATE_KEY` for a repeated key, `INVALID_SYNTAX` for any other loader error). Where the one break also brings an error somewhere else, the fixture declares it in a third comment line, `# also: <CODE> at <pointer>`: the errors at that pointer must then be reported, and `rules.json` must give them that schema-layer code; no other second error is allowed, and a `parse` fixture has no `# also:` line. `jsonschema` reports each kind of error here:

| What fails | Location |
|---|---|
| missing field, unknown field, `exactly_one_of`, class rule | the object |
| bad map key, empty map | the map |
| empty list, repeated entry | the list |
| wrong value or wrong type | the value |

Every parse- and schema-layer code in the catalogue has at least one invalid fixture. Fixtures that fail at parse (a duplicate key, malformed YAML, a `%YAML` directive other than 1.2) are kept out of the repository's YAML linters, through lists kept by hand: add each new one to `check-yaml`'s `exclude` in `.pre-commit-config.yaml` and to `ignore` in `.yamllint.yaml`. `tests/yaml-test-suite/` is kept out of them too, and out of the whitespace hooks, so that its cases stay as vendored. Every `astra.yaml` under `examples/` must also validate, and the specification's example blocks are checked, each by its kind: whole documents validated, marked fragments validated over a stub, the `rules.json` excerpt a subset of the generated file, and §4's ABNF matching the named types' patterns (`tests/test_grammar.py`). A YAML or JSON block of the specification that isn't a whole document (one with `spec_version`) is marked by an HTML comment on the line before it: `<!-- fragment: Analysis -->` for a piece of an `astra.yaml`, `<!-- excerpt: rules.json -->` for the abridged `rules.json`.

The site renders §9 with Python-Markdown, not CommonMark, so `tests/test_site.py` reads the built page (`site/specification/index.html`) and checks that each cell of its rule tables shows the same text as the matching `rules.json` field rendered by markdown-it. CI's docs build (`test_pages_build.yaml`) runs it after `zensical build`; it is skipped wherever there is no `site/`.

## Documentation versioning (mike)

The whole docs site is versioned with [mike](https://github.com/squidfunk/mike) — specifically squidfunk's fork, which Zensical's versioning provider depends on. Each release deploys a full copy of the site to a subdirectory of the `gh-pages` branch (`/0.0.9/`, `/latest/`, etc.). Mike is enabled via `[project.extra.version] provider = "mike"` in `zensical.toml`; the version dropdown in the header is rendered natively.

Release flow:

1. `just release X.Y.Z` — regenerates the contract with the release version (`RELEASE_VERSION=X.Y.Z just gen-schema`), updates `CITATION.cff`, commits both (`src/astra/schema/generated/` and `CITATION.cff`), and creates an annotated tag. Does not push. Schema YAMLs are *not* mutated: they keep the placeholder `version: 0.0.0`, and the generators read a staged copy under `tmp/schema/` with the version injected, from `$RELEASE_VERSION` or else the latest git tag.
2. `git push --atomic origin HEAD vX.Y.Z` — review, then push the commit and the tag together. The `Deploy versioned docs on tag` GitHub Actions workflow runs `mike deploy --push --update-aliases X.Y.Z latest` automatically.

For a manual deploy (e.g. backfilling a tag), `just docs-deploy X.Y.Z` runs the same `mike deploy` locally.

First-time setup: after the first deploy, run `just docs-set-default latest` once so the bare site root redirects to `/latest/`.

Hosting: mike pushes to `gh-pages`. The hosting platform (Cloudflare Pages, GitHub Pages, etc.) must be configured to serve from `gh-pages`, not `main`. Without this, `mike deploy` runs successfully but the site doesn't pick up versioned URLs in production.

Schema artifacts (`docs/schema/*.{yaml,json,jsonld}`) are versioned along with the rest of the site: `just gen-doc` writes the merged LinkML model there and copies in the committed contract from `src/astra/schema/generated/`. Machine consumers should resolve them via the canonical `https://w3id.org/astra/...` URI (which redirects to a hosted location), or pin to `astra-spec.org/X.Y.Z/schema/...`.

## Key Commands

```bash
just test             # Drift check of the generated files, pytest, and linkml-lint
just gen-schema       # Regenerate the contract into src/astra/schema/generated/ (commit it)
just check-generated  # Fail if the committed generated files differ from a fresh generation
just check-ajv        # Compile the three JSON Schemas with the pinned Ajv under strict: true (needs node)
just lint             # Lint the schema (linkml-lint)
just gen-doc          # Generate the field reference (docs/elements/) and docs/schema/
just docs-serve       # Build and preview docs locally with live reload
just release X.Y.Z    # Regenerate the contract with the version, update CITATION.cff, commit and tag
```

## Repository Layout

- `src/astra/schema/` — LinkML schema sources: `types.yaml`, `analysis.yaml`, `insight.yaml`, `provenance.yaml` (edit these)
- `src/astra/schema/generated/` — The generated contract: the JSON Schemas, the record's JSON-LD context and `rules.json` (regenerate with `just gen-schema`, commit, never edit)
- `tools/jsonschema_generator.py` — The JSON Schema generator extension
- `tools/rules.py` — Builds `rules.json`: the §9 extractor and the error map
- `tools/ajv/` — A pinned Ajv (`package.json`, `package-lock.json`) and `check.mjs`, for `just check-ajv`
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
