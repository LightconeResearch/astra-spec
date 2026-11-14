# ASTRA Specification

**Agentic Schema for Transparent Research Analysis** — a declarative YAML format for scientific analyses that separates *what* you want to learn from *how* to compute it.

[![Build and test](https://github.com/astra-project/astra-spec/actions/workflows/main.yaml/badge.svg)](https://github.com/astra-project/astra-spec/actions/workflows/main.yaml)
[![Docs](https://img.shields.io/badge/docs-astra--spec.org-334155.svg)](https://astra-spec.org)
[![Schema license: CC BY 4.0](https://img.shields.io/badge/schema-CC_BY_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![Code license: BSD 3-Clause](https://img.shields.io/badge/code-BSD_3--Clause-blue.svg)](https://opensource.org/license/bsd-3-clause)

> [!WARNING]
> ASTRA is in **early alpha**. Expect breaking changes between minor versions, and pin the schema version in your analyses. Bug reports from real-analysis attempts and design challenges are exactly what the project needs at this stage — please open an [issue](https://github.com/astra-project/astra-spec/issues).

---

## What is ASTRA?

ASTRA is a structured format that captures every consequential choice in a scientific analysis — its inputs, outputs, decisions, and the evidence behind them — so the result is **reproducible**, **auditable**, and **composable**. An agent, a workflow runner, a notebook, or a human reads the spec and produces the results; ASTRA itself stays out of execution.

For the longer argument that motivates the project — per-result trust in the agentic-AI era and why an open substrate matters — see the [Lightcone Research position paper](https://github.com/LightconeResearch/astra-paper).

## Quick example

```yaml
# astra.yaml
spec_version: "0.1.0"
label: Iris Classification

outputs:
  iris_data:
    type: data
    format: csv
    description: Loaded from sklearn.datasets.load_iris
    recipe:
      command: python src/load.py --out {output}

  accuracy:
    type: metric
    format: json
    inputs: [iris_data]
    decisions: [scaling, model]
    recipe:
      command: >-
        python src/evaluate.py --data {inputs.iris_data}
        --scaling {decisions.scaling} --model {decisions.model} --out {output}

decisions:
  scaling:
    label: Feature Scaling
    options:
      none:     { label: No Scaling }
      standard: { label: StandardScaler }

  model:
    label: Classification Model
    options:
      random_forest: { label: Random Forest }
      svm:
        label: SVM
        requires: [scaling.standard]

universes:
  baseline:
    decisions: { scaling: standard, model: random_forest }
```

A *universe* picks one option per decision it uses (e.g. `{ scaling: standard, model: svm }`). The same analysis can carry many universes; each one yields one set of results.

## Install and try it

```bash
uv tool install astra-tools           # installs the `astra` CLI on your PATH
astra init my-analysis && cd my-analysis
astra validate
astra info
```

Full walk-through: **[Getting started →](https://astra-spec.org/latest/getting-started/)**

## Repository layout

This repository (`astra-spec`) holds the LinkML schema and the documentation site.

```
src/astra/
  schema/       # LinkML schema source (edit these)
  datamodel/    # Generated Python datamodel (do not edit directly)
docs/           # Documentation source (Zensical → astra-spec.org)
conformance/    # Conformance suite: analysis cases with their verdicts (documents: tests/data/)
project/        # Generated: JSON Schemas, JSON-LD context and rules.json (committed); TS, OWL, Java and more
tools/          # Generators and checks of the schema files and the docs
linkml-templates/  # Templates for the generated field reference and Pydantic models
```

The Python CLI and SDK (`astra-tools`) live in a separate repository: [`astra-project/astra-tools`](https://github.com/astra-project/astra-tools). Both packages share the `astra.*` Python namespace via [PEP 420](https://peps.python.org/pep-0420/). The `astra-spec` package ships the LinkML sources and the generated JSON Schemas, JSON-LD context and `rules.json` under `astra.schema` (read them through `importlib.resources`), and the generated Python datamodels under `astra.datamodel`.

The datamodels of the two documents are LinkML's dataclasses (`analysis`, `provenance`) and Pydantic models (`astra_pydantic`, `provenance_pydantic`). They are a typed view of a document the JSON Schema accepted, not a validator: they don't check the patterns of the named types, the class rules or the maps' keys.

```python
from astra.datamodel.astra_pydantic import Analysis

analysis = Analysis.model_validate(document)  # `document`: an astra.yaml the JSON Schema accepted
analysis.outputs["result"].id                # "result": each entry takes its key as its id
```

## Development

```bash
git clone https://github.com/astra-project/astra-spec.git
cd astra-spec
uv sync --dev
```

Requires Python 3.10+, [uv](https://docs.astral.sh/uv/), and [just](https://github.com/casey/just/).

```bash
just test         # Schema generation, Python datamodels, pytest, schema lint
just lint         # LinkML schema lint
just gen-schema   # Regenerate the JSON Schemas, JSON-LD context and rules.json
just gen-python   # Regenerate Python datamodels
just gen-doc      # Regenerate the field reference docs
just docs-serve   # Live-reload local preview of the docs site
just --list       # Everything else
```

The release recipe (`just release X.Y.Z`) regenerates the generated files with the version, updates `CITATION.cff`, commits both and creates an annotated tag. Pushing the tag triggers the `Deploy versioned docs on tag` workflow, which publishes the versioned docs to `gh-pages` via mike.

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [Community page](https://astra-spec.org/latest/community/) for the full contribution workflow.

## License

- **Schema** — [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **Code** — [BSD 3-Clause](LICENSE)

Both are permissive; commercial and academic use are unrestricted. Schema reuse requires attribution; code reuse requires the standard BSD-3 notice.

## Citing

If you use ASTRA, please cite the repository — the easiest way is the **"Cite this repository"** button on this page (it generates APA and BibTeX from [`CITATION.cff`](CITATION.cff)). Include the schema version you targeted; it is recorded in the `$id` and `$comment` of each generated JSON Schema.

For the broader context, the [Lightcone Research position paper](https://github.com/LightconeResearch/astra-paper) is a separate citation, not a replacement.

## Credits

Developed by [Lightcone Research](https://github.com/LightconeResearch). Built with [LinkML](https://linkml.io) using the [linkml-project-copier](https://github.com/dalito/linkml-project-copier) template.
