---
rfc: 0003
title: In-file universes and cross-universe artifact references
status: Active # Draft | Active | Accepted | Rejected | Superseded
authors:
  - Francois Lanusse (@eiffl)
  - Anthony Ozerov (@anthonyozerov)
  - Jacopo Teneggi (@JacopoTeneggi)
  - Tom Charnock (@tomcharnock-lightcone)
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

This RFC makes the last of these expressible: universes are declared in
`astra.yaml`, and an output's input can be pinned to a named universe. The
first two also need sets of universes, sweeps over a decision, and fan-out over
a set; those come in a later RFC (see *Questions or objections*).

## Proposal

In plain language: **universes become addressable elements of the analysis
document, declared in full or as diffs of one another, and an output's inputs
may reference an artifact *at* a universe.** A plain reference keeps today's
meaning — same universe as the consumer — so existing references read
unchanged. The proposal has three parts.

One design principle runs through all three: **no universe is privileged by the
spec.** The premise of multiverse analysis — and of the stability principle in
the PCS framework (Yu & Kumbier 2020) — is that every defensible specification
has equal standing; a spec-blessed "default" or "baseline" universe would
invite reading one path as *the* analysis and the rest as robustness garnish.
ASTRA therefore defines no implicit universe and reserves no universe id:
every universe and every relationship between universes is declared by the
author. **`Decision.default` is removed:** a decision lists its options and
none is singled out; which option is used is chosen by each universe. The other
job a default did — saying which option a reported result was produced with —
is done by a pin on the evidence (§3), where it belongs to the claim rather
than to the decision.

An analysis with no decisions needs no universe: everything it builds is built
once (§2). An analysis that declares decisions but no universes is valid, but
nothing that depends on those decisions can be built; validators should warn
about it.

### 1. Bring `universes` into `astra.yaml` — in full or as diffs of one another

`Analysis` gains an optional **`universes`** slot holding `Universe` objects,
and `Universe` gains one construction rule:

- **Universes may be declared as diffs.** `Universe.decisions` may be
  **partial** when a new optional **`derived_from`** slot names another
  universe declared in the same analysis: unspecified decisions inherit their
  selection from it. Without `derived_from`, `decisions` must be complete,
  exactly as today. `derived_from` chains resolve transitively; cycles are
  invalid. `derived_from` expresses a *relationship between two declared
  universes*, chosen by the author — it does not anoint the universe it names
  as special. (This is not the existing `from` idiom: on `Input`/`Output`,
  `from` is a pure re-export alias that forbids local overrides, whereas
  `derived_from` is inherit-*and*-override — a different operation.)

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
    derived_from: rf_standard   # same specification, one decision changed
    decisions:
      model: svm

  - id: svm_large_test
    derived_from: svm_standard  # diffs chain
    decisions:
      test_size: large
```

A universe's **effective selection** is the effective selection of the universe
it is derived from, with the local `decisions` applied on top. The diff form is
not just brevity — it is record quality: it states *how two specifications
relate*, which is exactly the datum a stability comparison rests on. A universe
that spells out every decision remains valid. Nothing stops the *convention* of
naming a reference configuration `baseline` — the name carries no spec meaning.

Two rules complete the effective selection:

- **`analyses` entries are inherited per sub-analysis.** An entry's
  `decisions` are written over the inherited ones, and nested `analyses` merge
  the same way. If either the entry or the inherited one names a `universe`,
  the entry replaces the inherited one.
- **An inherited selection for a decision that is no longer active is
  dropped,** so a diff that switches a decision off (through its `when`) does
  not have to undo what it inherited for it. A selection the universe makes
  itself is checked as today: setting an inactive decision directly is an
  error, and a diff that switches a decision on must set it.

The effective selection is then validated exactly like a universe written in
full: every active decision selected, every selection an existing option, and
no `requires` or `incompatible_with` broken.

`Universe` fields after this change:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | `string` | Yes | Universe identifier. |
| `description` | `string` | No | Human-readable explanation. |
| `derived_from` | `universe_id` | No | Another universe of the same analysis whose effective selection is inherited. |
| `decisions` | map of `decision_id: option_id` | No | Overrides relative to `derived_from`; must be complete when `derived_from` is absent. |
| `analyses` | map of `UniverseNode` | No | Nested selections mirroring sub-analyses; inheritance applies recursively. |

**The `universes/` directory is removed.** `astra.yaml` becomes the single
source of truth: keeping the directory as an alternative would demand
precedence rules and invite silent divergence, and external files remain
invisible to the reference grammar (breaking — see *Implementation
implications & migration*).

Because `Analysis` is self-similar, `universes` may be declared on any analysis
node, and their ids are **unique within their analysis**. Only the root
analysis's universes are built. A sub-analysis's universes are presets: a
universe of the root can pick one by name, and they are built only when the
sub-analysis's file is used on its own. In-file universes also join the
RFC-0002 tree-path addressing.

A universe of the root sets a sub-analysis's decisions through
`Universe.analyses`, as today. Each entry does one of two things: it lists the
sub-analysis's `decisions`, or it picks one of the sub-analysis's own universes
by id (`universe: <id>`). That id used to name a file in the sub-analysis's
`universes/` directory; it now names an entry in its `universes` list.

This RFC changes sub-analyses only as far as moving universes into the file
requires. Inline sub-analyses, `from:` aliases and `Universe.analyses`
otherwise stay as they are; a later RFC on composing analyses revisits them.

### 2. Extend the artifact reference grammar with `#`

Entries in `Output.inputs` may pin an artifact reference to a universe:

```
input-reference ::= artifact-id [ "#" universe-id ]     ; declared ids only
```

The sigil is `#`: it conventionally selects a view *within* a resource
(rationale recorded in *Questions*). One YAML caveat: `#` mid-token is literal
(`f1_score#rf_standard` needs no quotes), but a stray space turns the pin into
a comment and the reference into a valid plain `f1_score` — validators should
flag an input whose line-comment looks like a pin.

`artifact-id` keeps its existing grammar (an Input or sibling Output id,
resolving through `from:` chains, with `.` as the hierarchy separator
unchanged); `#` cannot appear in element ids, so the extension is unambiguous.
A pin is only valid on references that resolve to an *Output*: an external
`Input` does not vary by universe, so pinning it is an error. A pin names a
universe declared on the **root** analysis, also when it is written inside a
sub-analysis (a known limitation; see *Questions*).

| Reference | Meaning |
|---|---|
| `artifact` | Unchanged: the artifact realized under the *same universe as the consumer* (late-bound; see below). |
| `artifact#<universe_id>` | The artifact realized under one declared universe — a **pin**. |

Semantics:

- **Pins respect activation.** A pin to a universe where the artifact is
  inactive is an error.
- **Universe scoping is inferred, and `#` cuts it.** An output is *built per
  universe* if it declares `decisions`, has a `when` (whether it exists
  depends on the universe), or if any unpinned input reference resolves to an
  artifact built per universe; a `from:` alias or a re-exported output is
  whatever it points at. Pinned references never propagate scope — the pin
  fixes the universe — and external `Input`s carry none. Any other output is
  *built once*: materialised once per project, not once per universe, the
  right identity for a comparison between named universes. Its recipe
  consequently has no "current universe," so `{decisions.<id>}` placeholders
  are invalid there, and it **must declare its `format`**, so that its file is
  told apart from the per-universe results (where results are stored is left
  to [#72](https://github.com/LightconeResearch/astra-spec/issues/72); for
  other outputs `format` stays recommended until 0.1.0). Since pinning a
  reference to an output built once selects nothing, validators should flag it
  as redundant.
- **Recipe placeholders name the entry exactly as written.** With two pins of
  one artifact, `{inputs.f1_score}` would be ambiguous, so the placeholder is
  the whole entry: `{inputs.f1_score#rf_standard}`. The same holds for dotted
  entries (`{inputs.classification.accuracy}`).

### 3. Pin evidence to a universe

A finding's evidence may pin the artifact it cites, written as in an output's
`inputs` (`artifact: f1_score#svm_standard`), so that it says which universe
the cited result comes from. The pin must name a declared universe. Validators
should warn when evidence cites an output built per universe without a pin:
the quoted value is only true of one universe's file.

### What validators check

| Rule | Severity |
|---|---|
| Universe ids are unique within their analysis | error |
| `derived_from` names a universe of the same analysis, and chains do not loop | error |
| An effective selection sets every active decision | error |
| An effective selection names only declared decisions and their options | error |
| A universe does not itself set a decision whose `when` fails | error |
| An effective selection breaks no `requires` or `incompatible_with` | error |
| An `analyses` entry sets `decisions` or `universe` (not both), and a named `universe` exists on that sub-analysis | error |
| A pin names a universe declared on the root | error |
| A pin is on an output, not an external input (following `from:` to its source) | error |
| A pinned output is built in that universe (its `when` holds there) | error |
| A placeholder names an `inputs` entry exactly as written | error |
| An output built once declares `format` | error |
| A pin on an output built once | warning |
| Evidence citing an output built per universe without a pin | warning |
| Decisions declared but no universes | warning |
| An `inputs` entry whose line-comment looks like a pin | warning (recommended) |

A sub-analysis's universes can depend on its parent's choices (a `when`, or a
`requires` on a `from:` alias), so they are judged where a universe of the root
picks one, with the parent's selections known. On their own they get only the
checks that do not need the parent (ids and `derived_from`).

## Examples

**Declared universes, diffs, and a comparison** — the iris example, extended
with a pinned stability comparison. `svm_standard` is a one-line diff of
`rf_standard` (a relationship, not a hierarchy — neither is privileged):

```yaml
outputs:
  - id: f1_score
    type: metric
    format: json
    inputs: [trained_output]
    decisions: [scaling, model, test_size, random_seed]
    recipe:
      command: python src/evaluate.py

  - id: model_comparison
    type: metric
    format: json
    description: Macro-F1 under the random-forest vs the SVM specification.
    inputs:
      - f1_score#rf_standard
      - f1_score#svm_standard
    recipe:
      command: >-
        python src/compare.py --a {inputs.f1_score#rf_standard}
        --b {inputs.f1_score#svm_standard} --out {output}

universes:
  - id: rf_standard
    description: Random forest with standard scaling.
    decisions: { scaling: standard, model: random_forest,
                 test_size: small, random_seed: seed_42 }

  - id: svm_standard
    description: Same specification with the model switched to SVM.
    derived_from: rf_standard
    decisions:
      model: svm
```

`f1_score` is built in each universe, and `model_comparison` once, from both.

**A finding that says which universe its evidence comes from:**

```yaml
findings:
  svm_scores_higher:
    claim: The SVM specification scores higher than the random forest.
    created_at: "2026-10-16T00:00:00Z"
    evidence:
      - id: ev_comparison
        artifact: model_comparison
      - id: ev_svm_f1
        artifact: f1_score#svm_standard
```

**A diff that switches a decision off** — `gpu_optimization` only exists when
`backend` is `gpu`:

```yaml
universes:
  - id: gpu_advanced
    decisions: { mode: advanced, backend: gpu, gpu_optimization: tensor_cores }
  - id: cpu_from_gpu
    derived_from: gpu_advanced
    decisions: { backend: cpu }   # the inherited gpu_optimization is dropped
```

**A sub-analysis's universe picked by name, and inherited by a diff:**

```yaml
analyses:
  stage:
    decisions:
      method: { options: { pca: ..., mlp: ... } }
    universes:
      - id: fast
        decisions: { method: pca }
    ...

universes:
  - id: baseline
    decisions: { test_split: twenty_pct }
    analyses:
      stage: { universe: fast }
  - id: deeper
    derived_from: baseline
    analyses:
      stage: { decisions: { method: mlp } }   # replaces the inherited entry
```

## Implementation implications & migration

**Compatibility:** this is a **breaking** change. Universe declarations move
into `astra.yaml`, the `universes/` directory is dropped as a supported
location, and `Decision.default` is removed; migration is mechanical (below).
Plain references, the `.` hierarchy separator, and all other existing grammar
keep their exact meaning; the `#` pin itself is additive.

**Migration of an existing analysis:**

1. Move each `universes/<id>.yaml` into `astra.yaml` under `universes` — the
   file's content is already a valid entry — and delete the folder. An
   `analyses` entry that names a `universe` keeps its id, which now names the
   entry moved into the sub-analysis's `universes` list.
2. Remove `default:` from decisions. If a universe was generated from
   defaults, keep it as a declared universe.
3. Give every output built once a `format`.
4. Pin evidence that cites an output built per universe.

## Questions or objections

Recorded as open unless marked otherwise; discussion on the tracking issue and
the draft PR resolves them.

- **Why are multiverses not in this RFC? — resolved.** Earlier drafts also
  proposed multiverses: named sets of universes, listed or generated from the
  decision space (`"*"`), and fan-out over a set (`artifact#multiverse`). They
  were taken out at this stage to reduce the scope, so that universes — which
  other work builds on — can be agreed, merged, and implemented first, and
  because how a set's members are stored depends on where results are stored
  at all ([#72](https://github.com/LightconeResearch/astra-spec/issues/72)).
  Sets, sweeps, and fan-out come in a later RFC. The multiverse design is
  carried forward in
  [#82](https://github.com/LightconeResearch/astra-spec/issues/82), which
  links the original text.
- **Should decision defaults define an implicit `baseline` universe? —
  resolved: no.** An earlier draft derived an implicit, spec-reserved
  `baseline` universe from `Decision.default` and made it the default base for
  diffs and generators. Rejected: privileging one specification is contrary to
  the premise of multiverse analysis and to the stability principle of the PCS
  framework (Yu & Kumbier 2020) — every defensible universe has equal standing,
  and a spec-blessed default invites treating one path as *the* analysis with
  the rest as robustness garnish. Consequently: no reserved universe ids;
  partial universes require an explicit `derived_from`; `Decision.default` is
  removed (next question). Authors who want a reference configuration may
  *name* a universe `baseline` by convention — the spec attaches no meaning to
  the name. (A contemporaneous alternative draft on the tracking issue
  completes omitted decisions from defaults; this RFC deliberately does not.)
  Recorded so the convenience argument is not silently re-litigated.
- **Why remove `Decision.default`? — resolved.** An earlier draft kept it as a
  presentational hint. It still marks one option per decision as the expected
  one — the privileging this RFC sets out to avoid — and tooling built a
  baseline universe from it. What a default used to say about a result is
  said by pinning the evidence (§3).
- **Why does `when` count for scoping? — resolved.** An
  earlier draft scoped an output by its `decisions` and unpinned inputs only.
  An output whose only link to a decision is a `when` was then built once, and
  an output built once has no current universe to evaluate its `when` in. The
  specification's own *Conditional elements* example (`calibrated_table`) is
  such an output. An output whose existence depends on a decision is built per
  universe.
- **Why must only outputs built once declare `format`? — open.** Their files
  sit next to the per-universe results, and `format` tells them apart.
  `format` is already scheduled to become required everywhere at 0.1.0; this
  RFC does not move that date.
- **Where are outputs built once stored? — open, for
  [#72](https://github.com/LightconeResearch/astra-spec/issues/72).** They
  could sit directly in `results/`, or in a fixed folder that cannot be a
  universe id (`results/_/`).
- **Pins name the root's universes — a known limitation.** A sub-analysis that
  is also used on its own names its own universes when used alone and the
  root's when included, so its pins only work in both if the ids line up. A
  later RFC on composing analyses, in which every analysis has its own
  universes, lifts this.
- **Pin sigil: `#` — resolved.** Earlier drafts used `@`. Adopted `#`
  following the alternative draft on the tracking issue and ecosystem
  convention: `#` selects a view *within* a resource (URL fragments, CSS
  `#id`). Cost accepted: the YAML stray-space comment footgun, mitigated by a
  validator lint.

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
- [`astra-multiverse-example`](https://github.com/anthonyozerov/astra-multiverse-example)
  (Anthony Ozerov) — the working prototype this RFC is grounded in; see also
  [`astra-multiverse-example-steegen-2`](https://github.com/anthonyozerov/astra-multiverse-example-steegen-2),
  the cross-version specification-search demonstration.
- [#72](https://github.com/LightconeResearch/astra-spec/issues/72) — where
  results are stored.
- Tracking issue: [#52](https://github.com/LightconeResearch/astra-spec/issues/52).
- [RFC-0002](0002-decouple-reports.md) — establishes element addressing, which
  in-file universes join as addressable elements.
