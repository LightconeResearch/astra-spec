---
rfc: 0004
title: Declared analyses and cross-analysis references
status: Active
authors:
  - Tom Charnock (@tomcharnock-lightcone)
created: 2026-10-20
tracking-issue: https://github.com/LightconeResearch/astra-spec/issues/84
superseded-by:
---

## Context

Currently, subanalyses are part of a single analysis tree, whether they are inline in the root (top-level) `astra.yaml` or defined in a file which is referenced in this `astra.yaml` by `path:`. Notably, these subanalyses are not analyses in their own right and cannot be validated or built out of the context of the root level `astra.yaml`. Furthermore, elements of these subanalyses can be related in multiple different ways, i.e.

- `path:` - to bring a subfolder into an analysis as a node in the root's tree
- `from:` - which has different meanings depending on what is referred to and from which element of the analysis (which slot it is defined in)
  - `../` - for subanalyses to get inputs and/or decisions from parents
  - `../sibling.artifact` - to alias an input from sibling subanalyses - requiring all subanalyses to be under the same root analysis (or at least common ancestor)
  - `child.artifact` - to re-export an artifact built by a subanalysis' output.

To reference different analyses there exists also `type: analysis` for `inputs:`, but this is just a record of an analysis which is currently not resolved in `astra-tools` and there is no mechanism to specify which universe's output is selected.

## Proposal

This RFC proposes to promote every subanalysis to its own standalone analysis in its own directory and with its own `astra.yaml`, where it can have its own decisions, universes and results. This means that any stage of analysis can be built and checked by itself and easily moved and reused by other analyses. The language for interaction between analyses is greatly simplified, reducing to one declaration and addressing. Furthermore, analyses can use each other by declaring each other and referring to elements by name, i.e. an analysis that declares another analysis can use that declared analysis' outputs and decisions or drive its decisions from its own universes.

### Glossary

This is just a short glossary of terms that seem somewhat abstract and are used throughout the proposal

| Term | Meaning |
|---|---|
| Analysis | A directory with its own `astra.yaml`, with its own decisions and universes, and its own results (section 1) |
| Root | The top-level analysis being validated or built - any analysis can be the root |
| Analysis stack | The root and every analysis it declares whether directly or via another declared analysis |
| Subanalysis | Any analysis in the analysis stack other than the root. Validated or built on its own that analysis becomes the root |
| Driver / driven | An analysis whose universes set the decisions of another analysis is its driver and that other analysis is driven (section 3, *Driving decisions*) |
| Consuming | Using an element of another analysis by address without driving it, whether one of its inputs, outputs or decisions (section 2) |

### Modifications

#### 1. Every analysis is a directory

An analysis is a directory with an `astra.yaml` defining its version, name and outputs (and optionally its own inputs, decisions, options and universes, and `results/` if there is something to build). Each analysis is independent and only depends on another analysis by declaring and referring to that other analysis. An analysis' recipes always run in its own directory.

`Analysis.analyses` becomes a list of declarations:

```yaml
# analysis/astra.yaml
analyses:
  - { id: subanalysis1, path: subanalysis1 }
  - { id: subanalysis2, path: subanalysis2 }
```

where

| Field   |  Type  | Required |                               Meaning                                                                        |
|---------|--------|----------|--------------------------------------------------------------------------------------------------------------|
| `id`    | string |      Yes | A unique name this analysis uses for a declared analysis                                                     |
| `path`  | string |      Yes | The directory holding the declared analysis' `astra.yaml` (relative to the declaring analysis' `astra.yaml`) |

Whilst in principle `path` could come from anywhere, we leave remote analyses for a later RFC. Here, for simplicity, we require `path` to be relative to the declaring analysis' `astra.yaml` and within the repository of the root analysis, i.e. the top-level analysis being validated or built. A subanalysis can be a git submodule with its own repository. If it declares something outside that repository, such as the root with `..`, it can only be validated and built from the root, otherwise it can also be validated and built on its own. Anything outside the root's repository is left to the later RFC.

No matter which analysis is doing the declaration, the same directory is the same analysis. `subanalysis1` from `analysis` above would be equivalent to `sibling_analysis` from `subanalysis2` with this declaration:

```yaml
# analysis/subanalysis2/astra.yaml
analyses:
  - { id: sibling_analysis, path: ../subanalysis1 }
```

The subanalysis would be read once and built once per universe rather than for every time it is declared.

There is no problem in making cyclic declarations such as a declared subanalysis containing a declaration of its parent analysis

```yaml
# analysis/subanalysis1/astra.yaml
analyses:
  - { id: root, path: .. }
```

with the strong requirement that artifact dependencies cannot form cycles.

This modification replaces the functionality of inline subanalyses, `path:` from children and `type: analysis` from inputs and so they can be removed from the spec.

#### 2. Referencing anything from anywhere

An element of a declared analysis is addressed as `<id>.<element>` and elements of a subanalysis declared by a declared analysis can be referenced as `<id>.<sub>.<element>` *ad infinitum*. This form can be used as the `inputs` or `decisions` of `outputs`, in conditions and constraints (`when`, `requires` and `incompatible_with`) or as the `artifact` cited by `evidence`. For example, if the root analysis defined:

```yaml
# analysis/astra.yaml
inputs:
  - { id: data, type: data }
decisions:
  a: { options: { a1: ..., a2: ... } }
```

then an output can *consume* the root's `data` and `a` directly by address

```yaml
# analysis/subanalysis1/astra.yaml
outputs:
  - { id: output1, ..., inputs: [root.data], decisions: [root.a] }
```

A recipe names them as they are written, `{inputs.root.data}` and `{decisions.root.a}`. Conditions and constraints name another analysis' decision in the same way followed by one of its options, so `when: [root.a.a1]` would make an element exist only when the root's `a` is `a1`.

All addresses are considered local to the declaring analysis. This removes completely the need for `from:` in `Input`, `Output` and `Decision` since the other analysis' elements are accessed directly by address.

#### 3. Universes across analyses

A decision used by address (section 2) has the value chosen in the universe being built and so a decision address never takes a `#`. This means that the analysis the decision belongs to has to be built in that universe too, i.e. `output1` can only be built in the root's universes (or those of an analysis driving the root) since `subanalysis1` can't know the value of `a` on its own.

##### Driving decisions

Each analysis can have its own set of decisions and options, where decisions belonging to a particular analysis should be defined within that analysis

```yaml
# analysis/astra.yaml
decisions:
  a: { options: { a1: ..., a2: ... } }
```

```yaml
# analysis/subanalysis1/astra.yaml
decisions:
  b: { options: { b1: ..., b2: ... } } 
```

```yaml
# analysis/subanalysis2/astra.yaml
decisions:
  c: { options: { c1: ..., c2: ... } } 
```

An analysis is considered to be *driving* the analysis stack if it has universes that set **all** of the required decisions of the whole stack of analyses which are named in the universe (no default universes in subanalyses are considered in this RFC). Using the format of universes as detailed in RFC-0003, the decisions of subanalyses are set using flat keys, `<id>.<decision>`, like

```yaml
# analysis/astra.yaml
universes:
  - id: u1
    decisions:
      a: a1
      subanalysis1.b: b1
      subanalysis2.c: c1
```  

Since the decisions are defined in the analyses where they are relevant, we do not need to redefine those decisions in each driving analysis. All options are also defined in the relevant analysis and we can imagine a simple tooling to obtain the available options for decisions if desired. When an analysis is driving other analyses, universes existing in those other driven analyses are considered to not exist. There is just one driver for each universe being built.

Also following RFC-0003, we can use `derived_from` to partially define universes so we can change only whichever decision we wish:

```yaml
# analysis/astra.yaml
universes:
  - id: u1
    decisions:
      a: a1
      subanalysis1.b: b1
      subanalysis2.c: c1
  - id: u2
    derived_from: u1
    decisions:
      subanalysis1.b: b2
```

If subanalyses of a subanalysis existed, we could simply use the same addressing scheme proposed in section 2 to reach in and drive the subsubanalysis

```yaml
# analysis/subanalysis1/subsubanalysis1/astra.yaml
decisions:
  d: { options: { d1: ..., d2: ... } }
outputs:
  - id: output1
    ...
    decisions: [d]
```
  
```yaml
# analysis/subanalysis1/astra.yaml
analyses:
  - { id: subsubanalysis1, path: subsubanalysis1 }
```

```yaml
# analysis/astra.yaml
universes:
  - id: u1
    decisions:
      a: a1
      subanalysis1.b: b1
      subanalysis1.subsubanalysis1.d: d1
      subanalysis2.c: c1
```

or equivalently if the driving analysis `astra.yaml` declared the subsubanalysis directly it could define  

```yaml
# analysis/astra.yaml
analyses:
  - { id: subanalysis1, path: subanalysis1 }
  - { id: subanalysis2, path: subanalysis2 }
  - { id: subsubanalysis1, path: subanalysis1/subsubanalysis1 }
inputs:
  - { id: data, type: data }
decisions:
  a: { options: { a1: ..., a2: ... } }
universes:
  - id: u1
    decisions:
      a: a1
      subanalysis1.b: b1
      subsubanalysis1.d: d1
      subanalysis2.c: c1
  - id: u2
    derived_from: u1
    decisions:
      subanalysis1.b: b2
```

Whether the decision is defined via the whole address or a top-level declaration doesn't matter since the same directory is always the same analysis. Technically both `subanalysis1.subsubanalysis1.d` and `subsubanalysis1.d` could be set in the universe and as long as the values are the same it doesn't make any difference - there would only be an error on disagreement (and maybe a warning on repeated setting of the same decision via multiple addresses if we wanted).

An analysis with no decisions, whose outputs only read things that don't change between universes (like the root's `data`), has nothing for a driver to set. Its results are built once and belong to the analysis itself:

```yaml
# analysis/subanalysis3/astra.yaml
analyses:
  - { id: root, path: .. }
outputs:
  - id: output3
    ...
    inputs: [root.data]
```

```yaml
# analysis/astra.yaml
analyses:
  - { id: subanalysis3, path: subanalysis3 }
```

`output3` only reads the root's external input `data`, so it is the same in every universe and is built once, as `analysis/subanalysis3/results/output3.<format>`.

This method of interacting with analyses in `universes` using flat keys means we can remove `Universe.analyses` and `UniverseNode`. 

A decision should be driven if it only matters to one analysis and should be consumed by address if it is shared by several analyses (like the seed of a whole analysis stack) - although this is just convention rather than enforced. Driving leaves an analysis able to stand alone whilst consuming a decision ties the outputs that use it to the analysis the decision belongs to.

#### 4. Which universe a reference reads

As in RFC-0003, a universe can be pinned using `#<universe_id>`.

```yaml
# analysis/subanalysis1/astra.yaml
outputs:
  - id: output1
    ...
    inputs: [root.data]
    decisions: [root.a, b]
```

```yaml
# analysis/astra.yaml
outputs:
  - id: summary1_u1
    ...
    inputs: [subanalysis1.output1#u1]
```

This is fine if we want to pin specific universes, but most of the time an analysis wants another analysis' output in whichever universe is being built. As within one analysis in RFC-0003, a reference without a pin means exactly that.

```yaml
# analysis/subanalysis2/astra.yaml
outputs:
  - id: output2
    ...
    inputs: [sibling_analysis.output1]
    decisions: [c]
```

The above example means that the input to `output2` is the `output1` from `sibling_analysis` built in whichever universe is currently building `output2`. The universe being built is defined by analysis and id, not by its id alone (the same id could be used in several analyses) and so is only relevant in an analysis which is defining the universe or an analysis driven by that driving analysis.

Because the universe being built is pushed through every analysis the root drives, we can define something like

```yaml
# analysis/astra.yaml
outputs:
  - id: summary
    ...
    inputs: [subanalysis2.output2]
```

which would allow us to build `summary` for whichever universe we want to build by asking a runner for `summary` pinned at that universe which would push through that universe to `subanalysis2.output2`.

Even an analysis without any decisions depends on the universe when it reads an output that is built per universe without a pin

```yaml
# analysis/subanalysis3/astra.yaml
analyses:
  - { id: subanalysis2, path: ../subanalysis2 }
outputs:
  - id: output3_per_universe
    ...
    inputs: [subanalysis2.output2]
```

so `output3_per_universe` is built in each of the root's universes (which is driving) and those results belong to the root, whilst `output3` (from earlier) is still built once and belongs to `subanalysis3`.

If a driven analysis also has universes of its own, reaching one of them needs a second declaration of that analysis which isn't driven.

```yaml
# analysis/subanalysis1/subsubanalysis1/astra.yaml
universes:
  - id: v1
    decisions:
      d: d2
```

```yaml
# analysis/astra.yaml
analyses:
  - { id: subanalysis1, path: subanalysis1 }
  - { id: subanalysis2, path: subanalysis2 }
  - { id: subanalysis3, path: subanalysis3 }
  - { id: subsubanalysis1, path: subanalysis1/subsubanalysis1 }
  - { id: subsubanalysis1_undriven, path: subanalysis1/subsubanalysis1 }
outputs:
  - id: subsummary1_u1
    ...
    inputs: [subsubanalysis1.output1#u1]
  - id: subsummary1_v1
    ...
    inputs: [subsubanalysis1_undriven.output1#v1]
```

Both declarations for the analysis `subanalysis1/subsubanalysis1` are the same directory but only `subsubanalysis1` is named in the root's universes (`subsubanalysis1.d: d1`) and therefore only `subsubanalysis1` is driven and the universe from `subsubanalysis1_undriven` is free to be referenced directly.

As with RFC-0003, external inputs and outputs that are built once are the same in every universe and so take no pin.

Evidence cites an artifact in the same way, so a finding can name the result of another analysis in the universe that supports it

```yaml
# analysis/astra.yaml
findings:
  finding1:
    ...
    evidence:
      - artifact: subanalysis1.output1#u1
```

Evidence isn't built in a universe, so when it cites an output that is built per universe it should carry a pin. A finding about results that a driver builds therefore belongs in the driver's `astra.yaml`.

The grammar of `Output.inputs` and `Evidence.artifact` from RFC-0003 becomes

```
reference ::= address [ "#" universe-id ]
```

A pin `#<universe_id>` names the driver's universe through a driven declaration or otherwise the analysis' own universe. Without a pin, an input is read in the universe being built.

#### 5. Results live with the universe that produced them

Any results which are produced from a driving analysis belong with the universe which sets the decisions. This includes the results of driven analyses. Whilst in this RFC we don't strictly enforce the location on disk of these results, they *belong* to the driver, which, for example, could be at `analysis/results/{universe_id}/{subanalysis_id}.{artifact_id}.{format}`. A recipe always runs in its own analysis' directory, but the runner tells it where to write its result (`{output}`), so a driven analysis' recipes write into the driver's results.

Any results built in an analysis' own universes (when it isn't driven) belong to that analysis, which could be `analysis/subanalysis1/results/{universe_id}/{artifact_id}.{format}` for example.

For elements that don't vary with choice of universe they would also exist within the analysis that defines them, i.e. `{path-to-analysis}/results/{artifact_id}.{format}`.

Building the analyses used throughout the descriptions in 1-4 we would end up with

```
analysis/
  results/
    summary1_u1.<format>
    subsummary1_u1.<format>
    subsummary1_v1.<format>
    u1/
      summary.<format>
      subanalysis1.output1.<format>
      subanalysis2.output2.<format>
      subanalysis3.output3_per_universe.<format>
      subsubanalysis1.output1.<format>
    u2/
      summary.<format>
      subanalysis1.output1.<format>
      subanalysis2.output2.<format>
      subanalysis3.output3_per_universe.<format>
      subsubanalysis1.output1.<format>
  subanalysis1/
    subsubanalysis1/
      results/
        v1/
          output1.<format>
  subanalysis3/
    results/
      output3.<format>
```

### What validators check

| Rule | Severity |
|---|---|
| Declaration ids are unique within an analysis | error |
| A declaration's `path` is relative, inside the repository of the root (the top-level analysis being validated or built), and holds an `astra.yaml` | error |
| Every analysis has `version`, `name` and `outputs` | error |
| An address resolves through the declarations to an element of the right kind: an input or output in `Output.inputs`, a decision (without a `#`) in `Output.decisions`, a decision and one of its options in `when`, `requires` and `incompatible_with`, an output in `Evidence.artifact` | error |
| Outputs don't depend on each other in a cycle | error |
| A flat key names a declaration path, one of the decisions that analysis defines and one of its options | error |
| A driven analysis has each of the active decisions it defines set in every one of the driver's universes | error |
| A declaration is driven by all of the driver's universes or by none | error |
| Two spellings of the same decision select the same option | error |
| Another analysis' output read without a pin, and another analysis' decision, are only used where the analysis they belong to is built in the universe being built | error |
| In the file of the analysis whose universe is being built, another analysis' output read without a pin and another analysis' decision go through a declaration that analysis drives (`subsubanalysis1_undriven.output1` has no match) | error |
| An output read without a pin exists in the universe being built (its `when` holds there) | error |
| A pin, in `Output.inputs` or evidence, names a universe of the driver through a driven declaration and of the declared analysis if not driven | error |
| Evidence citing an output that is built per universe without a pin | warning |
| Decisions declared, or outputs built per universe, but no universes, unless the analysis is driven or consumes a decision | warning |

## Examples

### Example 1: the running example

For clarity, the analyses built up throughout the proposal are shown here in their final state. Note that `...` has been used to stand in for whatever else is needed to make the file valid (label, type, etc.) and the output results are the same as in section 5 of the Proposal. 

```yaml
# analysis/astra.yaml
inputs:
  - { id: data, type: data }
analyses:
  - { id: subanalysis1, path: subanalysis1 }
  - { id: subanalysis2, path: subanalysis2 }
  - { id: subanalysis3, path: subanalysis3 }
  - { id: subsubanalysis1, path: subanalysis1/subsubanalysis1 }
  - { id: subsubanalysis1_undriven, path: subanalysis1/subsubanalysis1 }
decisions:
  a: { options: { a1: ..., a2: ... } }
outputs:
  - id: summary1_u1
    ...
    inputs: [subanalysis1.output1#u1]
  - id: summary
    ...
    inputs: [subanalysis2.output2]
  - id: subsummary1_u1
    ...
    inputs: [subsubanalysis1.output1#u1]
  - id: subsummary1_v1
    ...
    inputs: [subsubanalysis1_undriven.output1#v1]
findings:
  finding1:
    ...
    evidence:
      - artifact: subanalysis1.output1#u1
universes:
  - id: u1
    decisions:
      a: a1
      subanalysis1.b: b1
      subsubanalysis1.d: d1
      subanalysis2.c: c1
  - id: u2
    derived_from: u1
    decisions:
      subanalysis1.b: b2
```

```yaml
# analysis/subanalysis1/astra.yaml
analyses:
  - { id: root, path: .. }
  - { id: subsubanalysis1, path: subsubanalysis1 }
decisions:
  b: { options: { b1: ..., b2: ... } }
outputs:
  - id: output1
    ...
    inputs: [root.data]
    decisions: [root.a, b]
```

```yaml
# analysis/subanalysis1/subsubanalysis1/astra.yaml
decisions:
  d: { options: { d1: ..., d2: ... } }
outputs:
  - id: output1
    ...
    decisions: [d]
universes:
  - id: v1
    decisions:
      d: d2
```

```yaml
# analysis/subanalysis2/astra.yaml
analyses:
  - { id: sibling_analysis, path: ../subanalysis1 }
decisions:
  c: { options: { c1: ..., c2: ... } }
outputs:
  - id: output2
    ...
    inputs: [sibling_analysis.output1]
    decisions: [c]
```

```yaml
# analysis/subanalysis3/astra.yaml
analyses:
  - { id: root, path: .. }
  - { id: subanalysis2, path: ../subanalysis2 }
outputs:
  - id: output3
    ...
    inputs: [root.data]
  - id: output3_per_universe
    ...
    inputs: [subanalysis2.output2]
```

### Example 2: `iris_pipeline`

`examples/iris_pipeline` becomes three analyses. The root holds the data and the decisions the stages share and drives the decisions each stage defines for itself:

```yaml
# iris_pipeline/astra.yaml
id: iris_pipeline
version: "0.0.14"
name: Iris two-stage pipeline
inputs:
  - { id: iris_data, type: data, source: sklearn.datasets.load_iris }
analyses:
  - { id: feature_extraction, path: feature_extraction }
  - { id: classification, path: classification }
decisions:
  test_split:
    label: Test set proportion
    options: { twenty_pct: { label: "20%" }, thirty_pct: { label: "30%" } }
  random_seed:
    label: Random seed
    options: { seed_42: { label: "42" }, seed_7: { label: "7" } }
outputs:
  - id: split
    type: data
    format: json
    inputs: [iris_data]
    decisions: [test_split, random_seed]
    recipe:
      command: >-
        python src/split.py --data {inputs.iris_data}
        --test {decisions.test_split} --seed {decisions.random_seed} --out {output}
  - id: summary
    type: report
    format: md
    inputs: [classification.accuracy]
    recipe:
      command: python src/summary.py --accuracy {inputs.classification.accuracy} --out {output}
  - id: comparison
    type: metric
    format: json
    inputs: [classification.accuracy#baseline, classification.accuracy#mlp_svm]
    recipe:
      command: >-
        python src/compare.py --a {inputs.classification.accuracy#baseline}
        --b {inputs.classification.accuracy#mlp_svm} --out {output}
universes:
  - id: baseline
    decisions:
      test_split: twenty_pct
      random_seed: seed_42
      feature_extraction.method: pca
      feature_extraction.n_components: two
      classification.classifier: logistic
  - id: mlp_svm
    derived_from: baseline
    decisions:
      feature_extraction.method: mlp_encoder
      classification.classifier: svm
```

The feature extraction stage defines its own method and number of components and consumes the root's seed by address:

```yaml
# iris_pipeline/feature_extraction/astra.yaml
id: feature_extraction
version: "0.0.14"
name: Feature extraction
analyses:
  - { id: iris, path: .. }
decisions:
  method:
    label: Extraction method
    options:
      pca: { label: PCA }
      mlp_encoder: { label: MLP encoder, incompatible_with: [n_components.three] }
  n_components:
    label: Number of components
    options: { two: { label: "2" }, three: { label: "3" } }
outputs:
  - id: features
    type: data
    format: npy
    inputs: [iris.iris_data]
    decisions: [method, n_components, iris.random_seed]
    recipe:
      command: >-
        python src/extract.py --data {inputs.iris.iris_data} --method {decisions.method}
        --components {decisions.n_components} --seed {decisions.iris.random_seed} --out {output}
  - id: feature_plot
    type: figure
    format: png
    inputs: [features]
    decisions: [method, n_components]
    recipe:
      command: python src/plot.py --features {inputs.features} --out {output}
```

The classification stage declares its sibling by path and reads both the sibling's features and the root's split in the universe being built:

```yaml
# iris_pipeline/classification/astra.yaml
id: classification
version: "0.0.14"
name: Classification
analyses:
  - { id: iris, path: .. }
  - { id: feature_extraction, path: ../feature_extraction }
decisions:
  classifier:
    label: Classifier
    options: { logistic: { label: Logistic regression }, svm: { label: SVM }, knn: { label: k-NN } }
outputs:
  - id: predictions
    type: data
    format: csv
    inputs: [feature_extraction.features, iris.split]
    decisions: [classifier]
    recipe:
      command: >-
        python src/classify.py --features {inputs.feature_extraction.features}
        --split {inputs.iris.split} --classifier {decisions.classifier} --out {output}
  - id: accuracy
    type: metric
    format: json
    inputs: [predictions]
    decisions: [classifier]
    recipe:
      command: python src/evaluate.py --predictions {inputs.predictions} --out {output}
```

The stages declare the root with `..` and the root declares them, which is a cycle of declarations but not of artifacts. Everything the stages build is driven, so all of the results belong to the root:

```
iris_pipeline/
  results/
    comparison.json
    baseline/
      split.json
      summary.md
      feature_extraction.features.npy
      feature_extraction.feature_plot.png
      classification.predictions.csv
      classification.accuracy.json
    mlp_svm/
      split.json
      summary.md
      feature_extraction.features.npy
      feature_extraction.feature_plot.png
      classification.predictions.csv
      classification.accuracy.json
```

## Implementation implications & migration

*Compatibility:* breaking and requires RFC-0003. A large swath of inline analyses has been removed and all subanalyses have to be promoted to full analyses in their own right. Report addresses from RFC-0002 (`<sub>.<id>`) keep their grammar, but `<sub>` is now the id of a declaration, so existing references keep working where the declaration ids match the old subanalysis keys.

*Migration steps:*
- each subanalysis gets its own directory and `astra.yaml` (version, name, outputs)
- these subanalyses are then declared in `analyses:`
- all `from: ../x` becomes a declaration of the parent (`{id: root, path: ..}`) and `root.x`
- a decision taken with `from:` is removed and wherever it was used the decision is named by address instead (`decisions: [root.a]`, `{decisions.root.a}`, `when: [root.a.a1]`)
- all re-exports become direct reads, and evidence that cited a re-exported output cites the subanalysis' output by address
- `Universe.analyses` and presets become flat keys covering every decision
- `type: analysis` inputs become declarations

## Questions or objections

- **Should setting the same decision under two spellings give a warning?** When one analysis is reached by two driven paths, its decisions can be set under either (`subanalysis1.subsubanalysis1.d` or `subsubanalysis1.d`). Two different options is an error but setting the same option under both is allowed. I'd say that whether that repetition should give at least a warning is open.

## Other RFCs that could spawn out of this RFC
- **Remote analyses:** A `path` is local and inside the repository. Analyses in other repositories, with their revisions and fetching, would build on [#55](https://github.com/LightconeResearch/astra-spec/issues/55) and should now be relatively simple.
- **Presets:** A driver sets every decision of the analyses it drives. Starting a driving universe from one of a driven analysis' own universes would need presets (like the `universe:` of a `Universe.analyses` entry in RFC-0003).
- **Derived analyses:** Reusing an analysis you don't own with some of its inputs or its environment replaced.

## References

- [RFC-0002](0002-decouple-reports.md): the `<sub>.<id>` addressing grammar, which addresses keep, with `<sub>` now the id of a declaration
- RFC-0003 ([#52](https://github.com/LightconeResearch/astra-spec/issues/52), [#65](https://github.com/LightconeResearch/astra-spec/pull/65), reduced to universes in [#83](https://github.com/LightconeResearch/astra-spec/pull/83)): in-file universes, `derived_from` and pins, which this RFC extends across analyses
- [#82](https://github.com/LightconeResearch/astra-spec/issues/82): multiverses, deferred from RFC-0003, which this RFC doesn't depend on
- [#43](https://github.com/LightconeResearch/astra-spec/issues/43): an identity layer for addressing and resolving content across analyses
- [#55](https://github.com/LightconeResearch/astra-spec/issues/55): cross-repository artifact references, which remote analyses would build on
- [#72](https://github.com/LightconeResearch/astra-spec/issues/72): a canonical location for materialised outputs, which would settle the layout in 5
- [#57](https://github.com/LightconeResearch/astra-spec/issues/57) (closed): validation not recursing into sub-analyses
