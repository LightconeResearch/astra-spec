# Getting started

This walk-through gets you from zero to a validated ASTRA analysis in about ten minutes. You will install the CLI, scaffold a project, edit the analysis, and validate it.

If you'd rather see the schema first, jump to the [specification](specification/draft/format.md).

## Install

We recommend installing with [**uv**](https://docs.astral.sh/uv/) — Astral's fast Python package and project manager. If you don't have uv yet, follow the [official installation instructions](https://docs.astral.sh/uv/getting-started/installation/) (one-line install on macOS, Linux, and Windows).

=== "uv (recommended)"

    ```bash
    uv tool install astra-tools
    ```

=== "pip"

    ```bash
    pip install astra-tools
    ```

=== "From source"

    ```bash
    git clone https://github.com/LightconeResearch/ASTRA.git
    cd ASTRA
    uv pip install -e ".[dev]"
    ```

Verify the install:

```bash
astra --version
astra --help
```

## Scaffold a project

Use [`astra init`](cli.md#astra-init) to create a minimal project layout:

```bash
astra init my-analysis
cd my-analysis
```

This produces:

```
my-analysis/
├── astra.yaml              # Analysis specification (source of truth)
├── .gitignore
├── src/                    # Your analysis code
└── universes/
    └── baseline.yaml       # Default decision selection
```

The scaffolded `astra.yaml` is a complete, valid analysis with `TODO:` markers in the prose. It includes a `narrative` block, a `container:` default (`python:3.12-slim`), one example decision (`example_method` with options `option_a` and `option_b`), and two outputs (`main_result` chained into a `conclusion` report). It compiles as-is — you can edit incrementally rather than rewriting from scratch.

!!! tip "Skip git initialisation"
    By default `astra init` runs `git init` in the new directory and makes an initial commit. Pass `--no-git` to skip both.

## Edit the analysis

The scaffold gives you a working starting point; what follows is a boiled-down view of the structure you'll be editing. Every analysis declares three top-level sections — **`inputs:`**, **`outputs:`**, **`decisions:`** — plus optional metadata (`name`, `version`, `narrative`, `tags`, `authors`, `container`).

```yaml
version: "1.0"
name: My Analysis
container: python:3.12-slim       # default for all recipes; per-output override allowed

narrative:                        # structured prose; sections are anchorable
  summary: |
    One paragraph describing the analysis.
  methods: |
    Reference decisions inline: the [example method](#decisions.example_method).

inputs:
  - id: primary_data
    type: data                    # "data" or "analysis"
    description: "Source dataset"

outputs:
  - id: main_result
    type: metric                  # metric | figure | table | data | report
    description: "Primary output"
    decisions: [example_method]   # contract: only these decisions are visible to the recipe
    recipe:
      command: python src/main.py --method {decisions.example_method} --out {output}

decisions:
  example_method:
    label: "Example Method"
    default: option_a             # used when generating a baseline universe
    options:
      option_a: { label: "Option A" }
      option_b: { label: "Option B" }
```

A few things worth noting:

- **Decisions parameterize outputs.** `Output.decisions` declares the contract — only the listed decisions resolve inside `recipe.command`. The validator rejects `{decisions.foo}` if `foo` isn't in the list.
- **Recipe placeholders.** Four forms are legal: `{inputs}` (all declared inputs, space-separated), `{inputs.<id>}` (one declared input), `{decisions.<id>}` (one declared decision), and `{output}` (where to write). `{{` and `}}` are literal braces.
- **The narrative is structured.** Five sections — `summary`, `findings`, `methods`, `inputs`, `outputs` — exist so renderers can navigate them reliably. The validator makes a section *required* when its structured counterpart exists: declare `decisions:` and you owe `methods:` prose; declare `outputs:` and you owe `outputs:` prose. See [Narrative](specification/draft/format.md#narrative).
- **Constraints between options.** `requires:` and `incompatible_with:` (format: `decision.option`) gate which option combinations are valid. They are checked when you validate a universe.

## Validate

Run [`astra validate`](cli.md#astra-validate) to check the file:

```bash
astra validate astra.yaml
```

Validation runs in four stages, each gating the next:

1. **Schema validation** — Pydantic models (generated from the LinkML schema) check types, required fields, and format patterns (ID pattern, version pattern, DOI pattern, …).
2. **Semantic validation** — duplicate IDs, default options exist, `from:` paths resolve and respect direction rules, recipe template placeholders match `Output.inputs` / `Output.decisions`, output dependency graph has no cycles, constraint references resolve.
3. **Narrative validation** — Markdown anchors (`[text](#decisions.foo)`) point at real elements; the conditionally-required sections are present; coverage warnings flag declared elements that nothing in the narrative mentions.
4. **Evidence verification** (opt-in, `--verify-evidence`) — quoted text in `prior_insights` and `findings` actually appears in the cached source PDFs.

A clean run prints:

```text
Validating astra.yaml...
✓ Schema validation passed
✓ Semantic validation passed
✓ Narrative anchors resolved
✓ Narrative sections present
✓ Narrative coverage complete

Validation successful!
```

When something is wrong, errors print as `[ERROR_CODE] path: message`:

```text
Semantic validation errors:
  • [UNDECLARED_TEMPLATE_REF] outputs.accuracy.recipe.command:
    Command placeholder '{decisions.foo}' references undeclared decision
    'foo' (add it to Output.decisions)
  • [DUPLICATE_OUTPUT] outputs.main_result:
    Duplicate output ID: main_result
```

Coverage warnings (e.g. "Decision 'foo' is declared but not mentioned in any narrative section") are non-blocking; the validator returns success but flags them in yellow so authors can round-trip the prose.

## Inspect

[`astra info`](cli.md#astra-info) prints a Rich-rendered summary: the analysis name, version, each populated narrative section as a labelled paragraph, and tables for inputs, outputs, and decisions. By default everything renders; pass `--decisions`, `--inputs`, or `--outputs` to focus.

```bash
astra info
astra info --decisions
```

[`astra viz`](cli.md#astra-viz) draws the decision space. The default ASCII tree groups options under each decision, marks the default with `[default]`, and renders `incompatible_with` / `requires` constraints as glyphs (`✗` and `→`):

```text
└── My Analysis
    └── example_method
        ├── option_a: Option A [default]
        └── option_b: Option B
```

Sub-analyses, if any, nest under their parent. Pass `--format mermaid` to emit a Mermaid graph that can be pasted directly into a Markdown document:

```bash
astra viz --format mermaid
```

## Define universes

A *universe* is one complete set of decision selections — one option per decision in the analysis tree. Each universe yields one set of results; the same analysis can carry many of them.

Generate the baseline from your `default:` values:

```bash
astra universe generate --name baseline
```

This writes `universes/baseline.yaml`:

```yaml
id: baseline
description: Default configuration using standard practices

decisions:
  example_method: option_a
```

Add a second universe by hand to flex an alternative path:

```yaml
# universes/alt.yaml
id: alt
description: Alternative method choice

decisions:
  example_method: option_b
```

Validate either way:

```bash
astra validate universes/alt.yaml          # full validation against the analysis
astra universe check universes/alt.yaml    # universe-only checks (faster on iteration)
```

Universe validation enforces three rules: every decision in the analysis tree has a selection; each selection names an option that exists on its decision; and no `requires:` / `incompatible_with:` constraint is violated. If the analysis says `model.svm requires scaling.standard`, a universe selecting `svm` must also select `standard` — the validator points to the offending pair.

For nested analyses, the universe mirrors the tree:

```yaml
id: baseline
decisions:
  random_seed: seed_42       # root decision
analyses:
  feature_extraction:
    decisions:
      method: pca            # selection inside a sub-analysis
```

## Add evidence (optional)

ASTRA decisions can cite literature. You author the citation in `astra.yaml` — a `prior_insight` with a claim, the source DOI, and the quoted text that supports it — and link the insight to the decision option it justifies:

```yaml
prior_insights:
  attention_scales:
    claim: "Self-attention scales better than recurrence."
    created_at: "2026-04-15T10:00:00Z"
    evidence:
      - id: ev_paper
        doi: "10.48550/arXiv.1706.03762"
        version: 7
        quote:
          exact: "Attention is all you need"

decisions:
  architecture:
    label: "Architecture"
    default: transformer
    options:
      transformer:
        label: "Transformer"
        insights: [attention_scales]   # link the option to the insight
      rnn:
        label: "RNN"
```

The chain *option → insight → evidence → DOI* is what gives a decision an auditable trail back to the literature.

When you re-validate with verification turned on, the validator reads each `prior_insights[].evidence[]` entry, looks up the cached PDF for that DOI, and fuzzy-matches the `quote.exact` against the extracted text:

```bash
astra validate astra.yaml --verify-evidence
```

Papers are kept in a content-addressed cache under `~/.cache/astra/papers/`. The cache is populated by the agent or pipeline that authored the citation — they have the paper in hand at write time, so nothing extra is asked of the reader. The CLI exposes lower-level commands ([`astra paper add`](cli.md#astra-paper), `list`, `verify-quote`, …) for manual cache management, troubleshooting, and CI integration, but the day-to-day flow doesn't require them.

Artifact-backed evidence (typical for `findings:` whose output artifacts haven't been materialised yet) is reported as `SKIPPED` rather than failing the validation.

## What ASTRA doesn't run

The CLI validates and inspects analyses; it does **not** execute recipes. Each `recipe.command` is a POSIX shell command that an executor — an agent, a workflow runner, a notebook, or you on the command line — reads and invokes. The executor materialises the declared inputs (giving each one a concrete on-disk path), picks an output path, expands the `{inputs.<id>}` / `{inputs}` / `{decisions.<id>}` / `{output}` placeholders against the active universe, and runs the resulting command.

This separation is intentional: the spec stays stable as the agent and execution layer evolves. ASTRA's job is to make every analytical choice explicit, traceable, and verifiable; the choice of *runner* is yours.

