---
rfc: 0003
title: Multiverse analyses — in-file universes and cross-universe artifact references
status: Active # Draft | Active | Accepted | Rejected | Superseded
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
decision remains valid. Nothing stops the *convention* of naming a reference
configuration `baseline` — the name carries no spec meaning.

`Universe` fields after this change:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | `string` | Yes | Universe identifier. |
| `description` | `string` | No | Human-readable explanation. |
| `base` | `string` | No | Declared universe whose effective selection is inherited. |
| `decisions` | map of `decision_id: option_id` | No | Overrides relative to `base`; must be complete when `base` is absent. |
| `analyses` | map of `UniverseNode` | No | Nested selections mirroring sub-analyses; inheritance applies recursively. |

**The `universes/` directory is removed.** `astra.yaml` becomes the single
source of truth: keeping the directory as an alternative would demand
precedence rules and invite silent divergence, and external files remain
invisible to the reference grammar (breaking — see *Implementation
implications & migration*).

Because `Analysis` is self-similar, `universes` may
be declared on any analysis node, and their ids are **unique across the whole
analysis tree** — so a selector resolves tree-wide without qualification.
In-file universes also join the RFC-0002 tree-path addressing.

### 2. Extend the artifact reference grammar with `#`

Entries in `Output.inputs` may qualify an artifact reference with a universe
selector:

```
input-reference ::= artifact-id [ "#" universe-id ]     ; declared ids only
```

The sigil is `#`, not `@`: `#` conventionally selects a view *within* a
resource, while `@` pins a *revision* and is left free for a future sources
RFC to address external analyses, so the two axes compose
(`…output@rev#universe`; rationale recorded in *Questions*). One YAML caveat:
`#` mid-token is literal (`score#full_grid` needs no quotes), but a stray
space turns the selector into a comment and the reference into a valid plain
`score` — validators should flag an input whose line-comment looks like a
selector.

`artifact-id` keeps its existing grammar (an Input or sibling Output id,
resolving through `from:` chains, with `.` as the hierarchy separator
unchanged); `#` cannot appear in element ids, so the extension is unambiguous.
The selector is only valid on references that resolve to an *Output*: an
external `Input` does not vary by universe, so qualifying it is an error.

| Reference | Meaning |
|---|---|
| `artifact` | Unchanged: the artifact realized under the *same universe as the consumer* (late-bound; see below). |
| `artifact#<universe_id>` | The artifact realized under one declared universe — a **pin**. |

Semantics:

- **Pins respect activation.** A pin to a universe where the artifact is
  inactive is an error.
- **Universe scoping is inferred, and `#` cuts it.** An output is
  *universe-scoped* if it declares `decisions`, or if any unqualified input
  reference resolves to a universe-scoped artifact. Qualified references never
  propagate scope — the qualifier fixes the universe(s) — and external
  `Input`s carry none. An output that comes out universe-invariant is
  materialized once per project, not once per universe: the right identity for
  a multiverse-level summary or figure. Its recipe consequently has no
  "current universe," so `{decisions.<id>}` placeholders are invalid there;
  and since qualifying a reference to a universe-invariant artifact selects
  nothing, validators should flag it as redundant.

## Examples

**Declared universes, diffs, and a comparison** — the iris example, extended
with a pinned stability comparison. `svm_standard` is a one-line diff of
`rf_standard` (a relationship, not a hierarchy — neither is privileged):

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
      - f1_score#rf_standard
      - f1_score#svm_standard
    recipe:
      command: python src/compare.py

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
```

## Implementation implications & migration

**Compatibility:** this is a **breaking** change — a major bump under the
versioning policy. Universe declarations move into `astra.yaml` and the
`universes/` directory is dropped as a supported location; migration is
mechanical (each file's body is already a valid in-file entry). Unqualified
references, the `.` hierarchy separator, and all other existing grammar keep
their exact meaning; the `#` selector itself is additive.

## Questions or objections

Recorded as open unless marked otherwise; discussion on the tracking issue and
the draft PR resolves them.

- **Should decision defaults define an implicit `baseline` universe? —
  resolved: no.** An earlier draft derived an implicit, spec-reserved
  `baseline` universe from `Decision.default` and made it the default base for
  diffs and generators. Rejected: privileging one specification is contrary to
  the premise of multiverse analysis and to the stability principle of the PCS
  framework (Yu & Kumbier 2020) — every defensible universe has equal standing,
  and a spec-blessed default invites treating one path as *the* analysis with
  the rest as robustness garnish. Consequently: no reserved universe ids;
  partial universes require an explicit `base`; `Decision.default` stays a
  presentational hint. Authors who want a reference configuration may *name* a
  universe `baseline` by convention — the spec attaches no meaning to the
  name. (A contemporaneous alternative draft on the tracking issue completes
  omitted decisions from defaults; this RFC deliberately does not.) Recorded
  so the convenience argument is not silently re-litigated.
- **Selector sigil: `#` over `@` — resolved.** Earlier drafts used `@`.
  Adopted `#` following the alternative draft on the tracking issue and
  ecosystem convention: `#` selects a view *within* a resource (URL fragments,
  CSS `#id`), `@` pins a *revision* (`actions/checkout@v4`, `pkg@1.2.3`), and
  `@` stays free for a future sources RFC addressing external analyses at
  repository revisions, so the axes compose. Cost accepted: the YAML
  stray-space comment footgun, mitigated by a validator lint.

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
- Tracking issue: [#52](https://github.com/LightconeResearch/astra-spec/issues/52).
- [RFC-0002](0002-decouple-reports.md) — establishes element addressing, which
  in-file universes join as addressable elements.
