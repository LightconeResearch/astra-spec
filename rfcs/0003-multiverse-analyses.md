---
rfc: 0003
title: Multiverse analyses — in-file universes and cross-universe artifact references
status: Draft # Draft | Active | Accepted | Rejected | Superseded
authors:
  - Francois Lanusse (@eiffl)
created: 2026-07-30
tracking-issue: https://github.com/LightconeResearch/astra-spec/issues/52
superseded-by:
---

## Context

ASTRA can *describe* a multiverse but cannot *analyze* one. The schema records
decisions, options, and per-universe selections — yet the analyses that motivated
calling these things "universes" in the first place (Steegen et al. 2016) are
inexpressible, because no step can consume an artifact realized under a decision
configuration other than its own. Two gaps combine to cause this:

- **Universes live outside `astra.yaml`.** A universe is a standalone YAML file
  in the project's `universes/` directory (e.g. `universes/baseline.yaml`).
  Nothing inside `astra.yaml` can name, address, or quantify over a universe.
- **Artifact references are universe-implicit.** Every entry in `Output.inputs`
  resolves to an Input or sibling Output *in the current universe*: each
  dependency edge silently means "the version of this artifact materialized
  under the same decision selections as me."

The consequence is that a whole class of analyses cannot be declared:

- averaging or summarizing a metric across the decision space (multiverse
  analysis, Steegen et al. 2016),
- a specification-curve figure over the full decision grid (Simonsohn et
  al. 2020),
- a robustness comparison between two named configurations (`baseline` vs
  `svm_focused`).

The spec already gestures at the missing machinery: `Output.decisions`
documentation says runners use it to "determine the minimal universe set needed
to materialize the output" — but offers no syntax for an output whose inputs
*span* universes.

**Prior art.** Multiverse analysis (Steegen, Tuerlinckx, Gelman & Vanpaemel
2016) and specification-curve analysis (Simonsohn, Simmons & Nelson 2020) are
established methodology; tooling such as [Boba](https://github.com/uwdata/boba)
(Liu et al. 2021) demonstrates a DSL for authoring and executing decision
multiverses. On the workflow side, Snakemake's `expand()` is the standard
pattern for fanning a rule's inputs over a parameter grid — the same fan-in
shape this RFC needs at the specification level.

**Working prototype.** The mechanism proposed here is demonstrated end-to-end by
[`astra-multiverse-example`](https://github.com/anthonyozerov/astra-multiverse-example)
(Anthony Ozerov), an independent reproduction of Figure 1 of Steegen et
al. 2016. Its `astra.yaml` declares the paper's five data-processing decisions;
option constraints (`incompatible_with`) cut the Cartesian product down to 210
valid universes, and a `when` condition on the Study 1 output reduces *its*
active set to 120. A single `multiverses` entry names the full valid decision
space, six metric outputs are referenced as `<output>@full_multiverse` by a
figure output, and a runner executes all universes and reproduces the paper's
published significance counts. As with RFC-0002, this RFC is grounded in
something that works; its job is to decide what of it belongs in the ASTRA
specification.

## Proposal

In plain language: **universes become addressable elements of the analysis
document, sets of universes get names, and an output's inputs may reference an
artifact *at* a universe or *across* a set of universes.** A plain reference
keeps today's meaning — same universe as the consumer — so existing analyses are
untouched. The proposal has three parts.

### 1. Bring `universes` definitions into `astra.yaml`

`Analysis` gains an optional **`universes`** slot holding the same `Universe`
objects that today live as standalone files in the `universes/` directory:

```yaml
universes:
  - id: baseline
    description: Default configuration using standard practices
    decisions:
      scaling: standard
      model: random_forest
  - id: svm_focused
    description: Configuration optimized for SVM (requires standard scaling)
    decisions:
      scaling: standard
      model: svm
```

The `Universe` class itself is unchanged; what changes is where universes can
live. In-file universes are addressable by the reference grammar below (and by
the RFC-0002 tree-path addressing); the `universes/` directory remains valid for
runner-selected configurations (see *Migration*).

### 2. Add `multiverses` — named sets of universes

`Analysis` gains an optional **`multiverses`** slot. A `Multiverse` names a set
of universes so cross-universe steps can reference the set by a stable id and
readers can see, in one place, which decision space a summary quantifies over:

```yaml
multiverses:
  - id: model_robustness
    description: Configurations relevant to the model-choice robustness check.
    universes: [baseline, svm_focused]

  - id: full_multiverse
    description: The valid Cartesian product across all decisions.
    universes: "*"
```

Membership takes one of two forms:

- **An enumerated list** of universe ids declared under `universes:`.
- **`"*"`** — every valid point of the decision space: the Cartesian product of
  all decisions' options, minus combinations excluded by `requires` /
  `incompatible_with` constraints. These grid-point universes are *implicit*:
  they need not (and in practice cannot, at 210 of them) be declared
  individually. Each receives a **derived id**, formed by joining the selected
  option ids in decision-declaration order with hyphens
  (e.g. `f5-nmo3-r2-ecl2-ec1`). Option ids are snake_case and may not contain
  hyphens, so the derivation is unambiguous and reversible.

Note the refinement relative to the tracking issue: there, `"*"` was sketched as
"all *declared* universes." The prototype clarified that the useful meaning is
the **full valid decision space** — multiverse analyses quantify over the
choices themselves, not over whichever configurations happen to be named. A set
of declared universes is expressed by enumerating them.

### 3. Extend the artifact reference grammar with `@`

Entries in `Output.inputs` may qualify an artifact reference with a universe or
multiverse scope:

| Reference | Meaning |
|---|---|
| `artifact` | Unchanged: the artifact in the *consumer's own* universe. |
| `artifact@<universe_id>` | The artifact materialized under one declared universe — a **pin**. |
| `artifact@<multiverse_id>` | The artifact under *each* universe in the set — a **fan-out**, resolving to a collection. |

Semantics:

- **Fan-outs respect activation.** `artifact@<multiverse_id>` resolves to the
  artifact's realizations in the universes of the set where the artifact is
  *active* — universes excluded by the output's `when` conditions contribute
  nothing. (In the prototype, `religiosity_study1_p@full_multiverse` yields 120
  artifacts while its siblings yield 210.)
- **Universe-invariant consumers.** An output whose inputs are all pinned or
  fanned-out does not itself vary with the current universe: it is materialized
  once per project, not once per universe — the right identity for a
  multiverse-level summary or figure. An output that mixes plain and qualified
  references remains universe-scoped and additionally pulls in the referenced
  cross-universe artifacts.
- **Recipe surface.** In recipe templates, `{inputs.<id>}` for a fan-out
  reference expands to the collection of materialized artifact paths; how the
  collection is surfaced (space-separated paths, a manifest file, a sidecar)
  remains the runner's choice, consistent with the existing recipe contract.
- **Materialization sharing.** Two universes that differ only in decisions *not*
  listed on the upstream output's `decisions` share a realization; runners
  already compute per-output cache keys this way. A fan-out delivers one entry
  per member universe, with shared realizations deduplicated at the cache, not
  in the collection (see *Questions*).

Bare `artifact@*` (option 2 in the tracking issue) is **not** proposed: a
fan-out must name a declared multiverse. This keeps every cross-universe edge
attached to a described, reusable set — one extra stanza in exchange for the
summary's domain being part of the record.

## Examples

**A real multiverse analysis** — trimmed from the prototype's reproduction of
Steegen et al. (2016) Figure 1. Five decisions with option constraints define
210 valid universes; each p-value output is computed per universe; the figure
consumes all of them:

```yaml
decisions:
  fertility_assessment:      # F1–F5
    ...
  next_menstrual_onset:      # NMO1–NMO3
    ...
  cycle_length_exclusion:
    options:
      ecl1: { label: ECL1 }
      ecl2:
        label: ECL2
        incompatible_with: [next_menstrual_onset.nmo2]
      ecl3:
        label: ECL3
        incompatible_with: [next_menstrual_onset.nmo1]
  ...

outputs:
  - id: religiosity_study1_p
    type: metric
    inputs: [study1_data]
    decisions: [fertility_assessment, next_menstrual_onset,
                relationship_status, cycle_length_exclusion,
                certainty_exclusion]
    when: ["~next_menstrual_onset.nmo3"]   # NMO3 unavailable in Study 1
    recipe:
      command: >-
        python src/analyze_universe.py --data {inputs.study1_data}
        --outcome religiosity ... --output {output}

  - id: fig1
    type: figure
    description: Six-panel histogram of interaction p-values across universes.
    inputs:
      - religiosity_study1_p@full_multiverse   # 120 artifacts
      - religiosity_study2_p@full_multiverse   # 210 artifacts
      - fiscal_attitudes_p@full_multiverse
      - social_attitudes_p@full_multiverse
      - voting_preference_p@full_multiverse
      - donation_preference_p@full_multiverse
    recipe:
      command: >-
        python src/plot_figure1.py --multiverse-results {inputs}
        --significance 0.05 --output {output}

multiverses:
  - id: full_multiverse
    description: >-
      The valid Cartesian product across all five decisions. Option
      constraints remove NMO1+ECL3 and NMO2+ECL2, leaving 210 universes.
    universes: "*"
```

**Named-universe comparison** — the iris example, extended with a robustness
check pinned to two declared configurations:

```yaml
outputs:
  - id: f1_score
    type: metric
    inputs: [trained_output]
    decisions: [scaling, model, test_size, random_seed]
    recipe:
      command: python src/evaluate.py

  - id: model_comparison
    type: metric
    description: Baseline vs SVM macro-F1 comparison.
    inputs:
      - f1_score@baseline
      - f1_score@svm_focused
    recipe:
      command: python src/compare.py

universes:
  - id: baseline
    decisions: { scaling: standard, model: random_forest,
                 test_size: small, random_seed: seed_42 }
  - id: svm_focused
    decisions: { scaling: standard, model: svm,
                 test_size: small, random_seed: seed_42 }
```

## Implementation implications & migration

**`astra-spec` (this repo) — schema, datamodel, docs:**

- `src/astra/schema/analysis.yaml`: add optional `universes` and `multiverses`
  slots to `Analysis` (the `universe` schema is already imported); extend the
  `Output.inputs` documentation and validation pattern to admit the `@`
  qualifier.
- `src/astra/schema/universe.yaml`: add a `Multiverse` class (`id`,
  `description`, `universes: list | "*"`). Revisit the `UniverseNode.universe`
  doc-string, which currently hard-codes the "sub-analysis's `universes/`
  directory."
- Generated artifacts: `just gen-python`, `just gen-doc`; the published JSON
  Schema at `astra-spec.org/<version>/schema/…` shifts, which is the propagation
  point for both SDKs.
- Docs: `specification.md` (the *Universes* section currently states universes
  are "stored separately from `astra.yaml`"; add the reference grammar and a
  *Multiverses* section), `index.md` at-a-glance example if touched, `cli.md`
  validation rules, `README.md`, and the `examples/` projects. A Steegen-style
  example project would exercise the full mechanism in-tree.

**`astra-tools` (Python CLI + SDK):**

- `astra validate` gains checks: every `@` target resolves to a declared
  universe or multiverse id; declared universes select valid options and honor
  `requires` / `incompatible_with`; enumerated multiverse members exist; a
  pinned reference targets an output that is active in the pinned universe.
- Runner semantics: cross-universe edges change scheduling — one output can now
  demand materialization of an upstream artifact under many universes — and the
  derived-id scheme for `"*"` grid points must match the spec so artifact paths
  are stable across runners.

**`astra-typescript` (`@astra-spec/sdk`):** regenerate types for the new slots
and the `Multiverse` class; the reference grammar change surfaces wherever the
SDK parses `Output.inputs`.

**Compatibility / versioning:**

- Plain references keep their exact current meaning, and both new slots are
  optional, so existing analyses validate unchanged: the schema change is
  **additive — a minor bump** under the versioning policy.
- The `universes/` directory remains supported as a place for runner-selected
  configurations; in-file `universes` are required only when a universe must be
  *referenced* from within the document. Whether the directory is eventually
  deprecated in favor of in-file definitions is left open (below); this RFC
  does not remove anything.

## Questions or objections

Recorded as open unless marked otherwise; discussion on the tracking issue and
the draft PR resolves them.

- **What does `"*"` quantify over? — resolved by the prototype.** The full
  valid decision space (constrained Cartesian product), not "all declared
  universes." The declared-universes reading is expressible by enumeration, and
  a multiverse analysis that silently depended on which configurations happened
  to be declared would be fragile. Recorded so the alternative is not silently
  re-litigated.
- **Should bare `artifact@*` be allowed in `inputs`? — resolved: no.** Every
  fan-out goes through a named, described `Multiverse`. The prototype adopted
  this voluntarily and the resulting record is better for it.
- **One collection entry per universe, or per distinct realization? — open.**
  When an upstream output ignores some decisions, several member universes share
  one realization. The proposal delivers one entry per universe (Steegen-style
  counts over universes need the multiplicity) with realizations shared in the
  cache; the alternative — collapsing to distinct realizations — is equivalent
  to fanning out over the projection of the multiverse onto the output's
  `decisions`, and could later be expressed explicitly if needed.
- **Derived universe ids — open.** The proposed scheme (option ids joined by
  hyphens in decision-declaration order) is simple and collision-free, but ties
  ids to declaration order and can get long for wide decision spaces. Is
  declaration-order dependence acceptable, or should the id embed decision ids
  (`fertility_assessment=f5,...`) at the cost of length?
- **Sub-analysis scoping — open.** The prototype is a flat analysis. How does
  the `@` grammar compose with sub-analyses — can a parent fan out over a
  child's decision space, and how do `UniverseNode` selections participate in
  `"*"` enumeration? A conservative first cut: `@` references and multiverse
  enumeration operate on the current scope's decisions only.
- **Combinatorial guardrails — open.** `"*"` can be astronomically large.
  Should validators warn (or runners require confirmation) above a universe
  count threshold, or is that purely a tooling concern outside the spec?
- **Intensional multiverses — deferred.** Defining a multiverse by constraint
  or sweep (e.g. vary one decision, hold the rest at a named universe) was part
  of the original sketch and remains attractive for sensitivity analyses, but
  enumerated-plus-`"*"` covers the motivating cases; a constraint language can
  be layered on later without breaking this design.
- **Report scoping (RFC-0002 tie-in) — noted.** RFC-0002 left "can a report
  compare across universes?" out of scope. Universe-invariant outputs give
  reports a natural way to present multiverse-level results without resolving
  that question in general.

## References

- Steegen, Tuerlinckx, Gelman & Vanpaemel (2016), *Increasing Transparency
  Through a Multiverse Analysis*,
  [10.1177/1745691616658637](https://doi.org/10.1177/1745691616658637) — the
  methodology, and the source of the prototype's reproduced figure.
- Simonsohn, Simmons & Nelson (2020), *Specification curve analysis*,
  [10.1038/s41562-020-0912-z](https://doi.org/10.1038/s41562-020-0912-z).
- Liu, Kale, Althoff & Heer (2021), *Boba: Authoring and Visualizing Multiverse
  Analyses*, [10.1109/TVCG.2020.3028985](https://doi.org/10.1109/TVCG.2020.3028985)
  — a DSL and runtime for decision multiverses.
- [Snakemake `expand()`](https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html#the-expand-function)
  — the workflow-level fan-in pattern over parameter grids.
- [`astra-multiverse-example`](https://github.com/anthonyozerov/astra-multiverse-example)
  (Anthony Ozerov) — the working prototype this RFC is grounded in.
- Tracking issue: [#52](https://github.com/LightconeResearch/astra-spec/issues/52).
- [RFC-0002](0002-decouple-reports.md) — establishes element addressing, which
  in-file universes and multiverses join as addressable elements.
