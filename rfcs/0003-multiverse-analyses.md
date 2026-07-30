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
document, declared as diffs against a baseline; sets of universes get names and
constructors; and an output's inputs may reference an artifact *at* a universe
or *across* a set of universes.** A plain reference keeps today's meaning —
same universe as the consumer — so existing analyses are untouched. The
proposal has three parts.

### 1. Bring `universes` into `astra.yaml` — as diffs against a baseline

`Analysis` gains an optional **`universes`** slot holding `Universe` objects,
and `Universe` gains construction semantics built on two rules:

- **The baseline.** Every decision already carries a `default` option — whose
  doc-string reads "Default option ID for baseline universes." This RFC makes
  that normative: the all-defaults selection is the **implicit baseline
  universe**, addressable under the reserved id **`baseline`** without being
  declared. Declaring a universe with id `baseline` explicitly shadows the
  implicit one (to describe it, or to pin a different reference configuration).
- **Universes are diffs.** `Universe.decisions` may be **partial**: unspecified
  decisions inherit their selection from the universe's *base*. The base is
  named by a new optional **`from`** slot — the same inheritance idiom
  `Input`/`Output` already use — and defaults to `baseline`. `from` chains
  resolve transitively; cycles are invalid.

```yaml
decisions:
  scaling:     { default: standard, options: { none: …, standard: …, minmax: … } }
  model:       { default: random_forest, options: { svm: …, random_forest: …, logistic: … } }
  test_size:   { default: small, options: { small: …, large: … } }
  random_seed: { default: seed_42, options: { seed_42: …, seed_123: … } }

universes:
  # `baseline` needs no declaration: it is the all-defaults selection.

  - id: svm_focused
    description: Switch the model to SVM; everything else at baseline.
    decisions:
      model: svm            # a one-line diff against `baseline`

  - id: svm_large_test
    from: svm_focused       # diff against another declared universe
    decisions:
      test_size: large
```

A universe's **effective selection** is its base's effective selection with the
local `decisions` applied on top. The diff form is not just brevity — it is
record quality: the reader sees exactly what a configuration *deviates from*,
and adding a new decision later does not invalidate every declared universe
(each picks up the new default through its base). A universe that spells out
every decision remains valid, so today's complete `universes/` files carry over
unchanged.

`Universe` fields after this change:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | `string` | Yes | Universe identifier. |
| `description` | `string` | No | Human-readable explanation. |
| `from` | `string` | No | Base universe whose effective selection is inherited. Defaults to `baseline`. |
| `decisions` | map of `decision_id: option_id` | No | Overrides relative to the base; may be complete. |
| `analyses` | map of `UniverseNode` | No | Nested selections mirroring sub-analyses; inheritance applies recursively. |

In-file universes are addressable by the reference grammar below (and by the
RFC-0002 tree-path addressing); the `universes/` directory remains valid for
runner-selected configurations (see *Migration*).

### 2. Add `multiverses` — named sets of universes, enumerated or generated

`Analysis` gains an optional **`multiverses`** slot. A `Multiverse` names a set
of universes so cross-universe steps can reference the set by a stable id and
readers can see, in one place, which decision space a summary quantifies over.
Membership takes one of three forms:

- **(a) Enumeration** — `universes:` lists declared universe ids.
- **(b) Generator** — `vary:` maps each swept decision to `"*"` (all of its
  options) or to an explicit option list; the members are the Cartesian product
  of the swept option sets, with every *other* decision held at **`base`** (a
  universe id, defaulting to `baseline`). Points excluded by `requires` /
  `incompatible_with` constraints are dropped.
- **(c) The full space** — `universes: "*"`: every valid point of the decision
  space. Sugar for a generator that varies *every* decision over all of its
  options (`base` is then irrelevant).

```yaml
multiverses:
  - id: model_robustness
    description: Configurations relevant to the model-choice robustness check.
    universes: [baseline, svm_focused]          # (a) enumeration

  - id: scaling_sweep
    description: Sensitivity to feature scaling, all else held at baseline.
    vary:                                       # (b) generator: 3 universes
      scaling: "*"

  - id: seed_scaling_grid
    description: Scaling x seed grid around the SVM configuration.
    base: svm_focused                           # (b) generator: 2 x 2 grid
    vary:
      scaling: [standard, minmax]
      random_seed: "*"

  - id: full_multiverse
    description: The valid Cartesian product across all decisions.
    universes: "*"                              # (c) the whole valid space
```

Exactly one of `universes` or `vary` must be present; `base` is only meaningful
alongside `vary`.

**Identity of generated universes.** A generated member is identified by its
*effective selection* — the grid point itself, not the multiverse that produced
it. Its **derived id** joins the selected option ids in decision-declaration
order with hyphens (e.g. `f5-nmo3-r2-ecl2-ec1`; option ids are snake_case and
may not contain hyphens, so the derivation is unambiguous and reversible). The
same point reached through different multiverses — or coinciding with a
declared universe — is *one* universe: realizations and cache keys attach to
the selection, not to the name. Derived ids are valid pin targets
(`f1_score@none-svm-small-seed_42`), though declared names read better.

`Multiverse` fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | `string` | Yes | Multiverse identifier. |
| `description` | `string` | No | Human-readable explanation of what the set covers. |
| `universes` | list of universe ids, or `"*"` | One of `universes`/`vary` | Enumerated members, or the full valid decision space. |
| `base` | `string` | No | Generator form: universe holding the non-varied decisions. Defaults to `baseline`. |
| `vary` | map of `decision_id: "*"` \| option list | One of `universes`/`vary` | Generator form: swept decisions and their option sets. |

Note the refinement relative to the tracking issue: there, `"*"` was sketched as
"all *declared* universes." The prototype clarified that the useful meaning is
the **full valid decision space** — multiverse analyses quantify over the
choices themselves, not over whichever configurations happen to be named. A set
of declared universes is expressed by enumerating them.

### 3. Extend the artifact reference grammar with `@`

Entries in `Output.inputs` may qualify an artifact reference with a universe or
multiverse scope:

```
input-reference ::= artifact-id [ "@" scope-id ]
scope-id        ::= universe-id | multiverse-id
universe-id     ::= declared universe id | implicit "baseline" | derived grid-point id
```

`artifact-id` keeps its existing grammar (an Input or sibling Output id,
resolving through `from:` chains); `@` cannot appear in element ids today, so
the extension is unambiguous.

| Reference | Meaning |
|---|---|
| `artifact` | Unchanged: the artifact in the *consumer's own* universe. |
| `artifact@<universe_id>` | The artifact materialized under one specific universe — a **pin**. |
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

**Baseline, diffs, and a sweep** — the iris example, extended with a pinned
robustness comparison and a one-decision sensitivity sweep. Note that
`baseline` is never declared (it is the all-defaults selection), `svm_focused`
is a one-line diff, and the sweep's domain is a named, described set:

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
      - f1_score@baseline        # implicit all-defaults universe
      - f1_score@svm_focused
    recipe:
      command: python src/compare.py

  - id: scaling_sensitivity
    type: metric
    description: Macro-F1 as a function of feature scaling, all else at baseline.
    inputs:
      - f1_score@scaling_sweep   # fan-out: one artifact per scaling option
    recipe:
      command: python src/scaling_sensitivity.py

universes:
  - id: svm_focused
    description: Switch the model to SVM; everything else at baseline.
    decisions:
      model: svm

multiverses:
  - id: scaling_sweep
    description: Sensitivity to feature scaling, all else held at baseline.
    vary:
      scaling: "*"
```

## Implementation implications & migration

**`astra-spec` (this repo) — schema, datamodel, docs:**

- `src/astra/schema/analysis.yaml`: add optional `universes` and `multiverses`
  slots to `Analysis` (the `universe` schema is already imported); extend the
  `Output.inputs` documentation and validation pattern to admit the `@`
  qualifier; update the `Decision.default` doc-string to its normative role as
  the baseline selection.
- `src/astra/schema/universe.yaml`: add the `from` slot to `Universe` and
  document `decisions` as overrides relative to the base; add a `Multiverse`
  class (`id`, `description`, `universes`, `base`, `vary`) with a rule making
  `universes` and `vary` mutually exclusive. Revisit the
  `UniverseNode.universe` doc-string, which currently hard-codes the
  "sub-analysis's `universes/` directory."
- Generated artifacts: `just gen-python`, `just gen-doc`; the published JSON
  Schema at `astra-spec.org/<version>/schema/…` shifts, which is the propagation
  point for both SDKs.
- Docs: `specification.md` (the *Universes* section currently states universes
  are "stored separately from `astra.yaml`"; add the reference grammar and a
  *Multiverses* section), `index.md` at-a-glance example if touched, `cli.md`
  validation rules, `README.md`, and the `examples/` projects. A Steegen-style
  example project would exercise the full mechanism in-tree.

**`astra-tools` (Python CLI + SDK):**

- `astra validate` gains checks: every `@` target resolves to a universe
  (declared, `baseline`, or derived) or multiverse id; `from` chains resolve
  and are acyclic; a universe relying on baseline completion errors if some
  decision lacks a `default`; effective selections select valid options and
  honor `requires` / `incompatible_with`; `vary` names existing decisions and
  options; enumerated multiverse members exist; a pinned reference targets an
  output that is active in the pinned universe.
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
  **additive — a minor bump** under the versioning policy. Allowing partial
  `Universe.decisions` is a loosening: complete universe files stay valid as-is
  (an empty diff), and partial ones only become *newly* valid.
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
- **Is reserving `baseline` acceptable? — open.** The implicit baseline makes
  the common case free but claims an id and silently changes meaning if a
  project declares its own `baseline` with non-default selections. Alternatives:
  require an explicit declaration to enable `@baseline`, or a distinct spelling
  (`@~` or `@default`) for the all-defaults universe. The proposal leans on the
  reserved id because `Decision.default`'s own doc-string already promises it.
- **Are diffs too implicit? — open.** With `from:` chains, a universe's full
  selection is no longer visible at its declaration site. The record arguably
  *improves* (deviation-from-baseline is the scientifically meaningful datum,
  and new decisions propagate through defaults instead of invalidating every
  universe), but tooling should make the effective selection one command away
  (e.g. `astra universe show <id>`).
- **Sub-analysis scoping — open.** The prototype is a flat analysis. How does
  the `@` grammar compose with sub-analyses — can a parent fan out over a
  child's decision space, and how do `UniverseNode` selections participate in
  `"*"` enumeration? A conservative first cut: `@` references and multiverse
  enumeration operate on the current scope's decisions only.
- **Combinatorial guardrails — open.** `"*"` can be astronomically large.
  Should validators warn (or runners require confirmation) above a universe
  count threshold, or is that purely a tooling concern outside the spec?
- **Intensional multiverses — partially resolved.** The `base`/`vary` generator
  covers the sweep and grid cases from the original sketch (vary some decisions,
  hold the rest at a named universe). A general *constraint* language — "all
  valid universes where `scaling` is not `none`" — is still deferred; it can be
  layered on later (e.g. a `where:` clause) without breaking this design.
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
