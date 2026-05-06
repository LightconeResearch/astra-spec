# Getting started

This walk-through gets you from zero to a validated ASTRA analysis in about ten minutes. You will install the CLI, scaffold a project, edit the analysis, and validate it.

If you'd rather see the schema first, jump to the [specification](specification.md).

## Install

ASTRA's tooling ships as the [`astra-tools`](https://pypi.org/project/astra-tools/) package, which depends on [`astra-spec`](https://pypi.org/project/astra-spec/) for the schema. Python 3.11 or newer is required.

=== "pip"

    ```bash
    pip install astra-tools
    ```

=== "uv"

    ```bash
    uv pip install astra-tools
    # or, in a uv-managed project:
    uv add astra-tools
    ```

=== "From source"

    ```bash
    git clone https://github.com/LightconeResearch/ASTRA.git
    cd ASTRA
    pip install -e ".[dev]"
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

The scaffolded `astra.yaml` contains a single example decision and `TODO:` markers in the narrative and inputs/outputs that you fill in as you author the analysis.

!!! tip "Skip git initialisation"
    Pass `--no-git` if you don't want `astra init` to run `git init` and create an initial commit.

## Edit the analysis

Open `astra.yaml`. The minimum required structure is:

```yaml
version: "1.0"
name: My Analysis

inputs:
  - id: primary_data
    type: data
    description: "Source dataset"

outputs:
  - id: main_result
    type: metric
    description: "Primary output metric"
    decisions: [example_method]
    recipe:
      command: python src/main.py --method {decisions.example_method} --out {output}

decisions:
  example_method:
    label: "Example Method"
    default: option_a
    options:
      option_a: { label: "Option A" }
      option_b: { label: "Option B" }
```

A few things worth noting:

- **Decisions parameterize outputs.** `Output.decisions` declares the contract — only the listed decisions are visible inside `recipe.command`.
- **Recipe templates use local IDs.** `{inputs.<id>}` and `{decisions.<id>}` resolve against what the output declared.
- **The narrative is structured prose.** Five sections (`summary`, `findings`, `methods`, `inputs`, `outputs`) give renderers reliable anchors for navigation. See [Narrative](specification.md#narrative).

## Validate

Run [`astra validate`](cli.md#astra-validate) to check structure, cross-references, and narrative coverage:

```bash
astra validate astra.yaml
```

You should see:

```text
Validating astra.yaml...
✓ Schema validation passed
✓ Semantic validation passed
✓ Narrative anchors resolved
✓ Narrative sections present
✓ Narrative coverage complete

Validation successful!
```

If validation fails, the CLI prints a list of issues with the offending field. Fix them and re-run.

## Inspect

[`astra info`](cli.md#astra-info) prints the analysis summary; [`astra viz`](cli.md#astra-viz) draws the decision space.

```bash
astra info
astra info --decisions     # decisions only
astra viz                  # ASCII tree
astra viz --format mermaid # Mermaid for embedding
```

## Define a universe

A *universe* is a complete set of decision selections — one option per decision. Generate the baseline from your defaults:

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

Validate it:

```bash
astra validate universes/baseline.yaml
```

Universe validation enforces that every decision is selected, that every selected option exists, and that no `incompatible_with` / `requires` constraint is violated.

## Add evidence (optional)

ASTRA decisions can cite literature evidence. Add a paper to your local cache and the validator can check that quoted text actually appears in the source PDF.

```bash
# Cache the paper
astra paper add 10.48550/arXiv.1706.03762 --version 7

# Reference it as a prior insight in astra.yaml:
#   prior_insights:
#     attention_is_all_you_need:
#       claim: "Self-attention scales better than recurrence."
#       evidence:
#         - id: ev_paper
#           doi: "10.48550/arXiv.1706.03762"
#           version: 7
#           quote:
#             exact: "Attention is all you need"

# Verify quoted text exists in the cached PDF
astra validate astra.yaml --verify-evidence
```

See [`astra paper`](cli.md#astra-paper) for the full paper-management surface.

## Where to next

<div class="grid cards" markdown>

-   :lucide-file-text: __Read the specification__

    ---

    Every field, constraint, and validation rule of the ASTRA format.

    [:lucide-arrow-right: Specification](specification.md)

-   :lucide-terminal: __Browse the CLI__

    ---

    Reference for every `astra` command and the Python SDK helpers.

    [:lucide-arrow-right: CLI reference](cli.md)

-   :lucide-list-tree: __Schema reference__

    ---

    Auto-generated docs for every class and slot in the LinkML schema.

    [:lucide-arrow-right: Schema reference](elements/index.md)

-   :lucide-folder: __Examples__

    ---

    Two complete worked examples — `iris/` (flat) and `iris_pipeline/` (nested sub-analyses).

    [:lucide-arrow-right: Examples on GitHub](https://github.com/LightconeResearch/astra-spec/tree/main/examples)

</div>
