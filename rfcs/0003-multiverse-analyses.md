---
rfc: 0003
title: Multiverse analyses — in-file universes and cross-universe artifact references
status: Draft # Draft | Active | Accepted | Rejected | Superseded
authors:
  - Francois Lanusse (@eiffl)
  - Anthony Ozerov (@anthonyozerov)
  - Jacopo Teneggi (@JacopoTeneggi)
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
- a stability comparison between two named configurations (a random-forest vs
  an SVM specification of the same pipeline).

## Proposal

In plain language: **universes become addressable elements of the analysis
document, declared in full or as diffs of one another; sets of universes get
names and constructors; and an output's inputs may reference an artifact *at*
a universe or *across* a set of universes.** A plain reference keeps today's
meaning — same universe as the consumer — so existing analyses are untouched.
The proposal has three parts.

One design principle runs through all three: **no universe is privileged by the
spec.** The premise of multiverse analysis — and of the stability principle in
the PCS framework (Yu & Kumbier 2020) — is that every defensible specification
has equal standing; a spec-blessed "default" or "baseline" universe would
invite reading one path as *the* analysis and the rest as robustness garnish.
ASTRA therefore defines no implicit universe and reserves no universe id:
every universe and every relationship between universes is declared by the
author. (`Decision.default` remains a presentational hint for scaffolding and
editors; it plays no role in universe construction.)

### 1. Bring `universes` into `astra.yaml` — in full or as diffs of one another

`Analysis` gains an optional **`universes`** slot holding `Universe` objects,
and `Universe` gains one construction rule:

- **Universes may be declared as diffs.** `Universe.decisions` may be
  **partial** when a new optional **`base`** slot names another declared
  universe: unspecified decisions inherit their selection from the base.
  Without `base`, `decisions` must be complete, exactly as today. `base` chains
  resolve transitively; cycles are invalid. `base` expresses a *relationship
  between two declared universes*, chosen by the author — it does not anoint
  the base as special. (The existing `from` idiom is deliberately *not* reused:
  on `Input`/`Output`, `from` is a pure re-export alias that forbids local
  overrides, whereas `base` is inherit-*and*-override — a different operation
  deserving a different word.)

```yaml
universes:
  - id: rf_standard
    description: Random forest with standard scaling.
    decisions:
      scaling: standard
      model: random_forest
      test_size: small
      random_seed: seed_42

  - id: svm_standard
    base: rf_standard       # same specification, one decision changed
    decisions:
      model: svm

  - id: svm_large_test
    base: svm_standard      # diffs chain
    decisions:
      test_size: large
```

A universe's **effective selection** is its base's effective selection with the
local `decisions` applied on top. The diff form is not just brevity — it is
record quality: it states *how two specifications relate*, which is exactly the
datum a stability comparison rests on. A universe that spells out every
decision remains valid, so today's complete `universes/` files carry over
unchanged.

`Universe` fields after this change:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | `string` | Yes | Universe identifier. |
| `description` | `string` | No | Human-readable explanation. |
| `base` | `string` | No | Declared universe whose effective selection is inherited. |
| `decisions` | map of `decision_id: option_id` | No | Overrides relative to `base`; must be complete when `base` is absent. |
| `analyses` | map of `UniverseNode` | No | Nested selections mirroring sub-analyses; inheritance applies recursively. |

Only in-file universes are addressable: `base` (on universes and on multiverse
generators), enumerations, and `@` scopes resolve against the document's
`universes` — never against `universes/` directory files, which remain valid
for runner-selected configurations (see *Migration*). In-file universes also
join the RFC-0002 tree-path addressing.

### 2. Add `multiverses` — named sets of universes, enumerated or generated

`Analysis` gains an optional **`multiverses`** slot. A `Multiverse` names a set
of universes so cross-universe steps can reference the set by a stable id and
readers can see, in one place, which decision space a summary quantifies over.
Membership takes one of three forms:

- **(a) Enumeration** — `universes:` lists declared universe ids.
- **(b) Generator** — `vary:` maps each swept decision to `"*"` (all of its
  options) or to an explicit option list; the members are the Cartesian product
  of the swept option sets. Any decision *not* listed in `vary` is held at
  **`base`**, a declared universe id — required whenever `vary` does not cover
  every decision, so nothing is pinned implicitly. Points excluded by
  `requires` / `incompatible_with` constraints are dropped.
- **(c) The full space** — `universes: "*"`: every valid point of the decision
  space. Sugar for a generator that varies *every* decision over all of its
  options (no `base` — nothing is held fixed).

```yaml
multiverses:
  - id: model_stability
    description: Configurations for the model-choice stability comparison.
    universes: [rf_standard, svm_standard]      # (a) enumeration

  - id: scaling_sweep
    description: Vary feature scaling; all else held at rf_standard.
    base: rf_standard                           # (b) generator: 3 universes
    vary:
      scaling: "*"

  - id: seed_scaling_grid
    description: Scaling x seed grid around the SVM configuration.
    base: svm_standard                          # (b) generator: 2 x 2 grid
    vary:
      scaling: [standard, minmax]
      random_seed: "*"

  - id: full_multiverse
    description: The valid Cartesian product across all decisions.
    universes: "*"                              # (c) the whole valid space
```

Exactly one of `universes` or `vary` must be present; `base` accompanies `vary`
and is required unless `vary` covers every decision in scope.

**Identity of generated universes.** A generated member is identified by its
*effective selection* — the grid point itself, not the multiverse that produced
it. The same point reached through different multiverses — or coinciding with
a declared universe — is *one* universe: realizations and cache keys attach to
the selection, not to any name. Generated universes are deliberately
**anonymous**: they carry no spec-defined id and are not individually
addressable. To pin or enumerate a specific grid point, *declare* it — with
`base` that is a three-line diff — which also puts a name and a description in
the record. How runners spell per-universe storage paths is a tooling
convention, not spec surface: an option-id join (the prototype's
`f5-nmo3-r2-ecl2-ec1`) reads well for narrow spaces, a digest of the canonical
selection stays bounded for wide ones; either is faithful because identity
rests on the selection.

Three resolution rules keep this well-defined:

- **Multiverses are sets.** Members with identical effective selections
  collapse to one — whether listed twice in an enumeration or reached twice by
  a generator.
- **The decision space is a tree, not a grid.** A `when` condition can
  deactivate a decision under some selections; enumeration recurses over
  *active* decisions only, and an inactive decision is omitted from the
  effective selection. Points that differ only in inactive decisions are the
  same universe.
- **One namespace, no ambiguity.** Declared universe and multiverse ids share
  a namespace, so a `scope-id` resolves without guessing; a collision between
  them is invalid.

`Multiverse` fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | `string` | Yes | Multiverse identifier. |
| `description` | `string` | No | Human-readable explanation of what the set covers. |
| `universes` | list of declared universe ids, or `"*"` | One of `universes`/`vary` | Enumerated members, or the full valid decision space. |
| `base` | `string` | With partial `vary` | Generator form: declared universe holding the non-varied decisions. |
| `vary` | map of `decision_id: "*"` \| option list | One of `universes`/`vary` | Generator form: swept decisions and their option sets. |

(`"*"` deliberately means the full valid decision space, not "all declared
universes" as sketched in the tracking issue — see *Questions* for the record.)

### 3. Extend the artifact reference grammar with `@`

Entries in `Output.inputs` may qualify an artifact reference with a universe or
multiverse scope:

```
input-reference ::= artifact-id [ "@" scope-id ]
scope-id        ::= universe-id | multiverse-id     ; declared ids only
```

`artifact-id` keeps its existing grammar (an Input or sibling Output id,
resolving through `from:` chains); `@` cannot appear in element ids today, so
the extension is unambiguous. The qualifier is only valid on references that
resolve to an *Output*: an external `Input` does not vary by universe, so
qualifying it is an error.

| Reference | Meaning |
|---|---|
| `artifact` | Unchanged: the artifact realized under the *same universe as the consumer* (late-bound; see below). |
| `artifact@<universe_id>` | The artifact realized under one declared universe — a **pin**. |
| `artifact@<multiverse_id>` | The artifact under *each* universe in the set — a **fan-out**, resolving to a collection. |

**Evaluation model.** No output ever names its own universe — the document
stays generic, exactly as today. A universe-scoped output denotes a *family*
of realizations indexed by universe; the index is bound at run time by
whatever demands the artifact (a runner materializing a chosen universe, or a
pin/fan-out demanding specific members). A plain reference is a *bound
variable*: "whatever universe this realization is being built under, consume
the upstream artifact under the same one." A qualifier replaces that bound
variable with a constant (pin) or quantifies it over a set (fan-out). A
universe-invariant output has no index to bind, which is exactly why all of
its references must be qualified or universe-invariant themselves.

Semantics:

- **Fan-outs respect activation.** `artifact@<multiverse_id>` resolves to the
  artifact's realizations in the universes of the set where the artifact is
  *active* — universes excluded by the output's `when` conditions contribute
  nothing. (In the prototype, `religiosity_study1_p@full_multiverse` yields 120
  artifacts while its siblings yield 210.)
- **Universe scoping is inferred, and `@` cuts it.** An output is
  *universe-scoped* if it declares `decisions`, or if any unqualified input
  reference resolves to a universe-scoped artifact. Qualified references never
  propagate scope — the qualifier fixes the universe(s) — and external
  `Input`s carry none. An output that comes out universe-invariant is
  materialized once per project, not once per universe: the right identity for
  a multiverse-level summary or figure. Its recipe consequently has no
  "current universe," so `{decisions.<id>}` placeholders are invalid there;
  and since qualifying a reference to a universe-invariant artifact selects
  nothing, validators should flag it as redundant.
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

**Declared universes, diffs, and a sweep** — the iris example, extended with a
pinned stability comparison and a one-decision sweep. `svm_standard` is a
one-line diff of `rf_standard` (a relationship, not a hierarchy — neither is
privileged), and every set an output quantifies over is named and described:

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
    description: Macro-F1 under the random-forest vs the SVM specification.
    inputs:
      - f1_score@rf_standard
      - f1_score@svm_standard
    recipe:
      command: python src/compare.py

  - id: scaling_sensitivity
    type: metric
    description: Macro-F1 as a function of feature scaling, all else at rf_standard.
    inputs:
      - f1_score@scaling_sweep   # fan-out: one artifact per scaling option
    recipe:
      command: python src/scaling_sensitivity.py

universes:
  - id: rf_standard
    description: Random forest with standard scaling.
    decisions: { scaling: standard, model: random_forest,
                 test_size: small, random_seed: seed_42 }

  - id: svm_standard
    description: Same specification with the model switched to SVM.
    base: rf_standard
    decisions:
      model: svm

multiverses:
  - id: scaling_sweep
    description: Vary feature scaling; all else held at rf_standard.
    base: rf_standard
    vary:
      scaling: "*"
```

## Implementation implications & migration

**`astra-spec` (this repo) — schema, datamodel, docs:**

- `src/astra/schema/analysis.yaml`: add optional `universes` and `multiverses`
  slots to `Analysis` (the `universe` schema is already imported); extend the
  `Output.inputs` documentation and validation pattern to admit the `@`
  qualifier; clarify in the `Decision.default` doc-string that the default is a
  presentational/scaffolding hint with no role in universe construction (its
  current "for baseline universes" wording suggests otherwise).
- `src/astra/schema/universe.yaml`: add the `base` slot to `Universe` and
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

- `astra validate` gains checks: universe and multiverse ids are unique in
  their shared namespace; every `@` target resolves to a declared universe or
  multiverse and qualifies a reference to an Output; `base`
  chains resolve and are acyclic; a universe without `base` selects an option
  for every *active* decision; effective selections select valid options and
  honor `requires` / `incompatible_with`; `vary` names existing decisions and
  options, `base` is present whenever `vary` is partial, and a generator with
  no valid members is an error; enumerated multiverse members exist; a pinned
  reference targets an output that is active in the pinned universe; a
  universe-invariant output's recipe uses no `{decisions.<id>}` placeholders.
- Runner semantics: cross-universe edges change scheduling — one output can now
  demand materialization of an upstream artifact under many universes. Runners
  key storage and caching on canonical effective selections; the path spelling
  (option join vs. selection digest) is a runner convention, recorded in its
  run manifest.

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
- **Should generated universes have addressable derived ids? — resolved: no.**
  An earlier draft gave every grid point a spec-defined id (option ids joined
  in decision-declaration order) usable in pins and enumerations. Rejected:
  for a `"*"` over a wide decision space the join grows unboundedly (dozens of
  decisions → ids of hundreds of characters, leaking into every artifact
  path), it depends on declaration order, and making the spelling addressable
  forced extra rules (declared-vs-derived collisions, shadowing). Instead,
  identity attaches to the *effective selection*; generated universes are
  anonymous; addressing a specific point means declaring it (a three-line
  `base` diff, which also names and describes it in the record); and storage
  spelling — join for narrow spaces, digest for wide — is a runner convention.
- **Should decision defaults define an implicit `baseline` universe? —
  resolved: no.** An earlier draft derived an implicit, spec-reserved
  `baseline` universe from `Decision.default` and made it the default base for
  diffs and generators. Rejected: privileging one specification is contrary to
  the premise of multiverse analysis and to the stability principle of the PCS
  framework (Yu & Kumbier 2020) — every defensible universe has equal standing,
  and a spec-blessed default invites treating one path as *the* analysis with
  the rest as robustness garnish. Consequently: no reserved universe ids;
  partial universes require an explicit `base`; generators require an explicit
  `base` when `vary` is partial; `Decision.default` stays a presentational
  hint. Recorded so the convenience argument is not silently re-litigated.
- **Are diffs too implicit? — open.** With `base` chains, a universe's full
  selection is no longer visible at its declaration site. The record arguably
  *improves* — the relationship between specifications is the datum a stability
  comparison rests on — but tooling should make the effective selection one
  command away (e.g. `astra universe show <id>`).
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
- Yu & Kumbier (2020), *Veridical data science*,
  [10.1073/pnas.1901326117](https://doi.org/10.1073/pnas.1901326117) — the PCS
  framework; its stability principle motivates treating all defensible
  specifications symmetrically, which is why this RFC privileges no universe.
- [Snakemake `expand()`](https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html#the-expand-function)
  — the workflow-level fan-in pattern over parameter grids.
- [`astra-multiverse-example`](https://github.com/anthonyozerov/astra-multiverse-example)
  (Anthony Ozerov) — the working prototype this RFC is grounded in.
- Tracking issue: [#52](https://github.com/LightconeResearch/astra-spec/issues/52).
- [RFC-0002](0002-decouple-reports.md) — establishes element addressing, which
  in-file universes and multiverses join as addressable elements.
