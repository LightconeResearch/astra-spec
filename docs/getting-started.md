# Getting started

A self-contained tour of the ASTRA format: scaffold a project, edit the analysis, validate it, inspect it, define universes, and attach evidence. It assumes the `astra` CLI is already installed — see [installation](installation.md).

If you'd rather see the schema first, jump to the [specification](specification.md).

## Scaffold a project

Use [`astra init`](cli.md#astra-init) to create a minimal project layout:

```bash
astra init my-analysis
cd my-analysis
```

This produces:

```
my-analysis/
└── astra.yaml              # Analysis specification (source of truth)
```

The scaffolded `astra.yaml` is a complete, valid analysis: a `spec_version` and one output, `result`, a JSON metric made by `python src/result.py '{output}'`. It validates as-is — you can edit incrementally rather than rewriting from scratch.

> **Tip:** Where no git repository holds the new directory, `astra init` runs `git init` in it. It makes no commit.

`astra init` never overwrites existing files, so it is safe to run in a directory that already has content; where the directory already has an `astra.yaml`, it stops with an error and leaves it untouched.

## Edit the analysis

The scaffold gives you a working starting point; what follows is a boiled-down view of the structure you'll be editing. Every analysis states its **`spec_version`** and declares its **`outputs:`**, usually with **`inputs:`** and **`decisions:`** — plus optional metadata (`label`, `description`, `tags`).

```yaml
spec_version: "0.1.0"
label: My Analysis

description: |                    # short free-prose orientation
  One paragraph describing the analysis.

inputs:
  primary_data:
    path: data/primary.csv        # a file tracked in git with the analysis
    description: "Source dataset"

outputs:
  main_result:
    type: metric                  # metric | figure | table | data | report
    format: json                  # file extension, no dot; required from 0.1.0
    description: "Primary output"
    decisions: [example_method]   # contract: only these decisions are visible to the recipe
    recipe:
      command: python src/main.py --method {decisions.example_method} --out {output}

decisions:
  example_method:
    label: "Example Method"
    options:
      option_a: { label: "Option A" }
      option_b: { label: "Option B" }
```

A few things worth noting:

- **Decisions parameterize outputs.** `Output.decisions` declares the contract — only the listed decisions resolve inside `recipe.command`. The validator rejects `{decisions.foo}` if `foo` isn't in the list.
- **Recipe placeholders.** Four forms are legal: `{inputs}` (all declared inputs, space-separated), `{inputs.<id>}` (one declared input), `{decisions.<id>}` (one declared decision), and `{output}` (where to write). `{{` and `}}` are literal braces.
- **Rich reports live alongside `astra.yaml`.** The spec keeps a single optional `description`; a fuller write-up — figures, citations, multi-page structure — is built next to the analysis and references its elements rather than restating them. [MySTRA](https://github.com/LightconeResearch/MySTRA) is one framework that does this.
- **Constraints between options.** `requires:` and `incompatible_with:` (format: `decision.option`) gate which option combinations are valid. They are checked against each universe when you validate the analysis.

## Validate

Run [`astra validate`](cli.md#astra-validate) on the analysis's folder:

```bash
astra validate .
```

Validation runs in three stages, each gating the next:

1. **Parsing** — the file is YAML 1.2 whose content is a map, with no key twice.
2. **Schema validation** — the JSON Schema (generated from the LinkML schema) checks types, required fields, and format patterns (ID pattern, version pattern, DOI pattern, …).
3. **Semantic validation** — duplicate IDs, input files exist and are tracked in git, declared analyses and addresses resolve, recipe template placeholders match `Output.inputs` / `Output.decisions`, output dependency graph has no cycles, constraint references resolve, universes are complete and consistent.

A clean run prints:

```text
astra.yaml: valid, 0 error(s), 0 warning(s)
```

When something is wrong, errors print by file, as `line:col level CODE message`:

```text
astra.yaml
  20:16 error UNDECLARED_TEMPLATE_REF `{decisions.foo}` isn't a placeholder of this output: it takes `{inputs}`, `{output}`, and `{inputs.<entry>}` and `{decisions.<entry>}` for an entry of its `inputs` or `decisions` as written; `{{` and `}}` are literal braces
astra.yaml: invalid, 1 error(s), 0 warning(s)
```

Non-blocking warnings print in yellow: the validator still returns success but surfaces them so authors can clean the record up.

## Inspect

[`astra info`](cli.md#astra-info) prints a Rich-rendered summary: the analysis label, and its declarations, inputs, outputs, decisions and universes, followed by the same for each analysis it declares, if any.

```bash
astra info
```

```text
astra.yaml  My Analysis
  inputs    primary_data: data/primary.csv
  outputs   main_result: metric, json
  decisions example_method: option_a, option_b
```

Once the analysis has universes (next section), [`astra universe list`](cli.md#astra-universe) and `astra universe show` name them and give each one's selection, and [`astra plan`](cli.md#astra-plan) lists the results they plan, with where each goes and its command.

## Define universes

A *universe* is one complete set of decision selections — one option per decision it uses, of the analysis and of the analyses it drives. Each universe yields one set of results; the same analysis can carry many of them.

Universes are written in `astra.yaml`, under `universes:`: there is no default universe or option ([Elements](specification.md#elements)).

```yaml
universes:
  baseline:
    description: Baseline configuration using standard practices
    decisions:
      example_method: option_a
```

Add a second universe by hand, next to `baseline`, to flex an alternative path:

```yaml
universes:
  alt:
    description: Alternative method choice
    decisions:
      example_method: option_b
```

Validate, and inspect the universes:

```bash
astra validate .              # full validation, universes included
astra universe show alt       # the selection alt makes
astra plan                    # the planned results and their commands
```

Universe validation enforces three rules, among others: every decision the universe uses, of the analysis and of the analyses it drives, has a selection; each selection names an option that exists on its decision; and no `requires:` / `incompatible_with:` constraint among the decisions it uses is violated. If the analysis says `model.svm requires scaling.standard`, a universe selecting `svm` must also select `standard` — the validator points to the offending pair.

For declared analyses, the universe sets their decisions by address ([Elements](specification.md#elements)):

```yaml
analyses:
  feature_extraction:
    path: feature_extraction
universes:
  baseline:
    decisions:
      random_seed: seed_42              # root decision
      feature_extraction.method: pca    # selection inside a sub-analysis
```

## Add evidence (optional)

ASTRA decisions can cite literature. You author the citation in `astra.yaml` — a `prior_insight` with a claim, the source DOI, and the quoted text that supports it — and link the insight to the decision option it justifies:

```yaml
prior_insights:
  attention_scales:
    claim: "Self-attention scales better than recurrence."
    evidence:
      - doi: "10.48550/arXiv.1706.03762"
        version: 7
        quote:
          exact: "Attention Is All You Need"

decisions:
  architecture:
    label: "Architecture"
    options:
      transformer:
        label: "Transformer"
        insights: [attention_scales]   # link the option to the insight
      rnn:
        label: "RNN"
```

The chain *option → insight → evidence → DOI* is what gives a decision an auditable trail back to the literature.

[`astra paper verify`](cli.md#astra-paper) reads each evidence entry that cites a DOI, looks up the cached PDF for that DOI, and fuzzy-matches the `quote.exact` against the extracted text:

```bash
astra paper verify .
```

Papers are kept in a cache under `~/.cache/astra/papers/`. `astra paper add` puts one there, and `astra paper list` shows which cited papers the cache holds. A paper missing from the cache, or a quote not found, is a warning, never an error.

Artifact-backed evidence (typical for `findings:`) cites an output's results rather than a paper: `astra paper verify` leaves it alone, and [`astra check`](cli.md#astra-check) gives it the status of the results it cites.

## What ASTRA doesn't run

The CLI validates and inspects analyses, and checks results against their records; it does **not** execute recipes. Each `recipe.command` is a POSIX shell command that a runner, such as lightcone-cli, reads and invokes ([Results](specification.md#results)). The runner materialises the declared inputs (giving each one a concrete on-disk path), picks an output path, expands the `{inputs.<id>}` / `{inputs}` / `{decisions.<id>}` / `{output}` placeholders against the universe being built, runs the resulting command, and writes the result with a record of the run, which [`astra check`](cli.md#astra-check) later compares with the analysis.

This separation is intentional: the spec stays stable as the agent and execution layer evolves. ASTRA's job is to make every analytical choice explicit, traceable, and verifiable; the choice of *runner* is yours.
