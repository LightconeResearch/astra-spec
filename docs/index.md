# ASTRA

**Agentic Schema for Transparent Research Analysis** is an open YAML specification for describing the scientific structure of an analysis: the inputs it consumes, the outputs it claims to produce, the methodological decisions that shape those outputs, and the evidence that supports the choices being made.

ASTRA exists because AI-assisted science needs a record that is both machine-readable and scientifically legible. Code is executable but often hides intent. Papers are readable but usually compress away the decision trail. An `astra.yaml` file sits between them: it gives humans and agents a shared map of what the analysis is supposed to establish, which choices matter, and how each result can be traced back to data, code, and decisions.

[:lucide-rocket: **Get started**](getting-started.md){ .md-button .md-button--primary }
[:lucide-book-open: Specification explained](specification.md){ .md-button }

!!! warning "Alpha development"
    ASTRA is in **early alpha**. The schema, CLI, and tooling are still moving, so expect breaking changes between minor versions and pin the schema version in your analyses. Bug reports, design challenges, and examples the current schema does not yet cover are especially useful at this stage; please open an issue on the [GitHub repo](https://github.com/LightconeResearch/astra-spec/issues) or join the [Community](community.md) tab.

## Why ASTRA?

Scientific results rest on chains of choices: which dataset to include, which preprocessing step to apply, which model to fit, which prior to adopt, which diagnostic to trust, and which alternatives were considered but rejected. Those choices are often scattered across code, notebooks, comments, commit history, lab notes, and the final paper. That is tolerable when analyses move slowly and reviewers can reconstruct the missing context by hand. It becomes fragile when AI systems can generate plausible-looking results faster than people can inspect them.

ASTRA makes the decision structure explicit. It does not replace code, papers, notebooks, workflow engines, or git. Instead, it records the scientific contract that those artifacts should satisfy. A reader should be able to open `astra.yaml` and answer: What is being analyzed? What goes in? What comes out? Which choices control each output? Which alternatives were considered? Which results depend on which choices? What evidence backs the claims?

This gives ASTRA three jobs:

1. **Provenance certification.** Every plot, number, table, and claim can be tied back to the inputs, recipes, and decisions that produced it.
2. **Observability.** Consequential assumptions are declared where reviewers, collaborators, and agents can inspect them.
3. **Scientific legibility.** The record is organized around the concepts scientists actually argue about: inputs, outputs, decisions, options, constraints, evidence, and findings.

## The mental model

An ASTRA project starts with one analysis document, usually called `astra.yaml`. Read it as a structured research design:

```yaml
version: "1.0"
name: Iris Classification Study

narrative:
  summary: |
    Train and evaluate a classifier for the Iris dataset.
  methods: |
    The analysis compares feature [scaling](#decisions.scaling)
    choices and [model](#decisions.model) choices.
  inputs: |
    The [iris_data](#inputs.iris_data) input provides the measurements.
  outputs: |
    The [accuracy](#outputs.accuracy) metric reports held-out performance.

inputs:
  - id: iris_data
    type: data
    source: sklearn.datasets.load_iris
    description: Fisher's classic 150-sample, 3-class dataset.

outputs:
  - id: accuracy
    type: metric
    description: Classification accuracy on a held-out test set.
    inputs: [iris_data]
    decisions: [scaling, model]
    recipe:
      command: >-
        python src/evaluate.py
        --data {inputs.iris_data}
        --scaling {decisions.scaling}
        --model {decisions.model}
        --out {output}

decisions:
  scaling:
    label: Feature scaling
    rationale: Scaling changes the geometry seen by distance-based models.
    default: standard
    options:
      none: { label: No scaling }
      standard: { label: StandardScaler }

  model:
    label: Classification model
    rationale: The algorithm determines the hypothesis class being tested.
    default: random_forest
    options:
      random_forest: { label: Random forest }
      svm:
        label: Support vector machine
        requires: [scaling.standard]
```

The point of the file is not that it contains the whole analysis. The point is that it names the parts of the analysis that must remain stable enough for humans and tools to reason about them. The Python script still does the computation. A runner still chooses how to execute it. The paper still explains the result. ASTRA supplies the ledger that keeps the scientific intent, decision space, and provenance links visible.

## How to read the documentation

The pages in this documentation are ordered from practical to formal:

- [Getting started](getting-started.md) walks through installing the CLI, scaffolding a project, validating `astra.yaml`, and defining universes.
- [Specification explained](specification.md) introduces the file format one concept at a time, then gives a compact reference for each field.
- [CLI reference](cli.md) describes the commands available today.
- [Schema reference](elements/index.md) is the generated LinkML reference for readers who need the exact datamodel.

A useful first pass is to read the [minimal ASTRA document](specification.md#minimal-astra-document), then the sections on [inputs](specification.md#inputs), [outputs](specification.md#outputs), and [decisions](specification.md#decisions). Those three objects are the core of the format.

## What ASTRA is, and is not

ASTRA is a specification layer. It is intentionally narrow. It records scientific structure; it does not try to become the runtime, repository, manuscript, or platform.

| ASTRA records | ASTRA does not replace |
|---|---|
| Scientific intent and narrative | Papers and long-form explanation |
| Inputs and outputs | Data stores or artifact registries |
| Decisions, options, constraints, and excluded alternatives | Git history or issue trackers |
| Recipes attached to outputs | Workflow engines and schedulers |
| Evidence-backed findings | Peer review or scientific judgement |
| Validation rules for the record | Re-running every computation |

That boundary is deliberate. The specification should remain stable while agents, runners, execution platforms, and review tools evolve around it.
