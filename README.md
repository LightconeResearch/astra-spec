# ASTRA Specification

**Agentic Schema for Transparent Research Analysis** — a declarative YAML format for scientific analyses that separates *what* you want to learn from *how* to compute it.

[![Build and test](https://github.com/LightconeResearch/astra-spec/actions/workflows/main.yaml/badge.svg)](https://github.com/LightconeResearch/astra-spec/actions/workflows/main.yaml)
[![Docs](https://img.shields.io/badge/docs-astra--spec.org-334155.svg)](https://astra-spec.org)
[![Schema license: CC BY 4.0](https://img.shields.io/badge/schema-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Code license: BSD 3-Clause](https://img.shields.io/badge/code-BSD_3--Clause-blue.svg)](https://opensource.org/license/bsd-3-clause)

> [!WARNING]
> ASTRA is in **early alpha**. Expect breaking changes between minor versions, and pin the schema version in your analyses. Bug reports from real-analysis attempts and design challenges are exactly what the project needs at this stage — please open an [issue](https://github.com/LightconeResearch/astra-spec/issues) or join the [Community](https://astra-spec.org/community/).

---

## What is ASTRA?

ASTRA is a structured format that captures every consequential choice in a scientific analysis — its inputs, outputs, decisions, and the evidence behind them — so the result is **reproducible**, **auditable**, and **composable**. An agent, a workflow runner, a notebook, or a human reads the spec and produces the results; ASTRA itself stays out of execution.

For the longer argument that motivates the project — per-result trust in the agentic-AI era and why an open substrate matters — see the [Lightcone Research position paper](https://github.com/LightconeResearch/astra-paper).

## Quick example

```yaml
# astra.yaml
version: "1.0"
name: Iris Classification

inputs:
  - id: iris_data
    type: data
    source: sklearn.datasets.load_iris

outputs:
  - id: accuracy
    type: metric
    decisions: [scaling, model]
    recipe:
      command: python src/evaluate.py

decisions:
  scaling:
    label: Feature Scaling
    default: standard
    options:
      none:     { label: No Scaling }
      standard: { label: StandardScaler }

  model:
    label: Classification Model
    default: random_forest
    options:
      random_forest: { label: Random Forest }
      svm:
        label: SVM
        requires: [scaling.standard]
```

A *universe* picks one option per decision (e.g. `{ scaling: standard, model: svm }`). The same analysis can carry many universes; each one yields one set of results.

## Install and try it

```bash
uv tool install astra-tools           # installs the `astra` CLI on your PATH
astra init my-analysis && cd my-analysis
astra validate astra.yaml
astra info
astra viz
```

Full walk-through: **[Getting started →](https://astra-spec.org/getting-started/)**

## Repository layout

This repository (`astra-spec`) holds the LinkML schema and the documentation site.

```
src/astra/
  schema/       # LinkML schema source (edit these)
  datamodel/    # Generated Python datamodel (do not edit directly)
docs/           # Documentation source (Zensical → astra-spec.org)
tests/data/    # Valid/invalid YAML fixtures
project/        # Multi-language bindings (Python, TS, JSON Schema, JSON-LD, OWL, Java)
```

The Python CLI and SDK (`astra-tools`) live in a separate repository: [`LightconeResearch/astra-tools`](https://github.com/LightconeResearch/astra-tools). Both packages share the `astra.*` Python namespace via [PEP 420](https://peps.python.org/pep-0420/).

## Development

```bash
git clone https://github.com/LightconeResearch/astra-spec.git
cd astra-spec
uv sync --dev
```

Requires Python 3.9+, [uv](https://docs.astral.sh/uv/), and [just](https://github.com/casey/just/).

```bash
just test         # Schema generation, Python datamodel, examples
just lint         # LinkML schema lint
just gen-python   # Regenerate Python datamodels
just gen-doc      # Regenerate the schema reference docs
just docs-serve   # Live-reload local preview of the docs site
just --list       # Everything else
```

The release recipe (`just release X.Y.Z`) updates `CITATION.cff` and creates an annotated tag; the version is injected into generated artifacts from the tag at build time. Pushing the tag triggers the `Deploy versioned docs on tag` workflow, which publishes the versioned docs to `gh-pages` via mike.

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [Community page](https://astra-spec.org/community/) for the full contribution workflow.

## License

- **Schema** — [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **Code** — [BSD 3-Clause](LICENSE)

Both are permissive; commercial and academic use are unrestricted. Schema reuse requires attribution; code reuse requires the standard BSD-3 notice.

## Citing

If you use ASTRA, please cite the repository — the easiest way is the **"Cite this repository"** button on this page (it generates APA and BibTeX from [`CITATION.cff`](CITATION.cff)). Include the schema version you targeted; it is recorded at the top of each LinkML source file and in every generated artefact.

For the broader context, the [Lightcone Research position paper](https://github.com/LightconeResearch/astra-paper) is a separate citation, not a replacement.

## Credits

Developed by [Lightcone Research](https://github.com/LightconeResearch). Built with [LinkML](https://linkml.io) using the [linkml-project-copier](https://github.com/dalito/linkml-project-copier) template.
