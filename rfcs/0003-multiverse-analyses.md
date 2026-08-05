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
decision remains valid; the body of an existing `universes/` file is already a
valid entry, so migration is a move, not a rewrite.

The spec deliberately privileges no universe (see the design principle above),
but nothing stops a *convention*: authors who want a reference configuration
can simply name a declared universe `baseline` — the name is theirs, not the
spec's.

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
invisible to the reference grammar (see *Migration*; this is breaking).

Because `Analysis` is self-similar, `universes` (and `multiverses`, below) may
be declared on any analysis node, and their ids are **unique across the whole
analysis tree** — so a selector resolves tree-wide without qualification.
In-file universes also join the RFC-0002 tree-path addressing.

### 2. Add `multiverses` — named sets of universes, enumerated or generated

`Analysis` gains an optional **`multiverses`** slot. A `Multiverse` names a set
of universes so cross-universe steps can reference the set by a stable id and
readers can see, in one place, which decision space a summary quantifies over.
Membership is declared through two fields — at least one must be present, and
when both are, the membership is their **union**:

**(a) `universes` — selection.** A list whose entries are, in resolution
order:

1. an exact declared **universe id**;
2. an exact **multiverse id** — recursively including its members (direct or
   indirect membership cycles are invalid);
3. a **regular expression** over declared universe ids (full-string match,
   declared universes only — it never matches multiverse ids or generated
   members).

Universe and multiverse ids keep the existing grammar (`^[a-z][a-z0-9_-]*$`),
which contains no regex metacharacters — so an id-shaped entry is always an
exact reference (it must resolve; it is *not* reinterpreted as a regex when
missing), and anything else is a regex. Note the trade the regex form makes:
declaring a new matching universe changes the multiverse's membership in that
revision of the document.

**(b) `decisions` — generation.** A map from decision references to *option
selectors*: a single option id, a list of option ids, or `"*"` (every option
of that decision). Members are the Cartesian product of the selected option
sets; any decision *not* in the map is held at **`base`**, a declared universe
id — required whenever the map does not cover every decision in scope, so
nothing is pinned implicitly. Combinations excluded by `requires` /
`incompatible_with` are filtered out (unlike a declared universe, where an
invalid selection is an error). As a shorthand for the full space,
`decisions: "*"` (scalar) varies *every* active decision over all of its
options — no `base`, nothing held fixed.

A decision in a sub-analysis is referenced by its tree path
(`preprocessing.threshold`); an unqualified id is allowed when it resolves in
the current node or names exactly one decision in the subtree, and is an error
otherwise.

```yaml
multiverses:
  - id: model_stability
    description: Configurations for the model-choice stability comparison.
    universes: [rf_standard, svm_standard]      # (a) exact selection

  - id: all_sensitivity
    description: Every declared sensitivity configuration.
    universes: ["^sensitivity_.*$"]             # (a) regex selection

  - id: scaling_sweep
    description: Vary feature scaling; all else held at rf_standard.
    base: rf_standard                           # (b) generation: 3 universes
    decisions:
      scaling: "*"

  - id: seed_scaling_grid
    description: Scaling x seed grid around the SVM configuration.
    base: svm_standard                          # (b) generation: 2 x 2 grid
    decisions:
      scaling: [standard, minmax]
      random_seed: "*"

  - id: combined_robustness
    description: Named configurations plus the scaling sweep.
    universes: [model_stability, "^sensitivity_.*$"]   # multiverse + regex
    base: rf_standard
    decisions:
      scaling: "*"                              # union of (a) and (b)

  - id: full_multiverse
    description: The valid Cartesian product across all decisions.
    decisions: "*"                              # the whole valid space
```

`Multiverse.decisions` is `Universe.decisions` generalized from single options
to option selectors, and `base` is the same diff mechanism a `Universe` uses:
a generator is exactly the set of diff-universes
`{base: <base>, decisions: <point>}` for every valid point of the product. A
multiverse expanding to zero universes is invalid.

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
  a single namespace across the whole analysis tree, so a selector resolves
  without guessing; a collision — even between declarations in different
  nested nodes — is invalid.

`Multiverse` fields:

| Field | Type | Required | Meaning |
|---|---|---:|---|
| `id` | `string` | Yes | Multiverse identifier. |
| `description` | `string` | No | Human-readable explanation of what the set covers. |
| `universes` | list of (universe id \| multiverse id \| regex) | At least one of `universes`/`decisions` | Selected members; union with `decisions`. |
| `base` | `string` | With a partial `decisions` map | Declared universe holding the non-varied decisions. |
| `decisions` | map of `decision_ref:` option \| option list \| `"*"` — or scalar `"*"` | At least one of `universes`/`decisions` | Generated members; scalar `"*"` is the full valid space. |

(`"*"` never means "all declared universes" — as an option selector it means
"every option of this decision," and as `decisions: "*"` it means the full
valid decision space; see *Questions* for the record.)

### 3. Extend the artifact reference grammar with `#`

Entries in `Output.inputs` may qualify an artifact reference with a universe or
multiverse selector:

```
input-reference ::= artifact-id [ "#" selector-id ]
selector-id     ::= universe-id | multiverse-id     ; declared ids only
```

The sigil is `#`, not `@`, following ecosystem convention: `#` selects a
fragment or view *within* a resource (URL fragments, CSS `#id`), while `@`
conventionally pins a *revision* (`actions/checkout@v4`, `pkg@1.2.3`) — and
`@` is deliberately left free for a future sources RFC to address external
analyses at repository revisions, so the two axes compose
(`…output@rev#universe`). One YAML caveat: `#` mid-token is literal
(`score#full_grid` needs no quotes), but a stray space turns the selector into
a comment and the reference into a valid plain `score` — validators should
flag an input whose line-comment looks like a selector.

`artifact-id` keeps its existing grammar (an Input or sibling Output id,
resolving through `from:` chains, with `.` as the hierarchy separator
unchanged); `#` cannot appear in element ids, so the extension is unambiguous.
The selector is only valid on references that resolve to an *Output*: an
external `Input` does not vary by universe, so qualifying it is an error.
Whether the selector names a universe or a multiverse is not visible in the
syntax; resolution in the shared namespace determines the cardinality.

| Reference | Meaning |
|---|---|
| `artifact` | Unchanged: the artifact realized under the *same universe as the consumer* (late-bound; see below). |
| `artifact#<universe_id>` | The artifact realized under one declared universe — a **pin**. |
| `artifact#<multiverse_id>` | The artifact under *each* universe in the set — a **fan-out**, resolving to a collection. |

Semantics:

- **Fan-outs respect activation.** `artifact#<multiverse_id>` resolves to the
  artifact's realizations in the universes of the set where the artifact is
  *active* — universes excluded by the output's `when` conditions contribute
  nothing (the multiverse keeps those members; only this artifact's projection
  is smaller). A *pin* to a universe where the artifact is inactive is an
  error. (In the prototype, `religiosity_study1_p#full_multiverse` yields 120
  artifacts while its siblings yield 210.)
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
- **Recipe surface.** In recipe templates, `{inputs.<id>}` for a fan-out
  reference expands to the collection of materialized artifact paths; how the
  collection is surfaced (space-separated paths, a manifest file, a sidecar)
  remains the runner's choice, consistent with the existing recipe contract.
  The resolved collection must preserve each member's complete effective
  selection, so an anonymous generated universe stays scientifically
  identifiable without a human-facing id.
- **Materialization sharing.** Two universes that differ only in decisions *not*
  listed on the upstream output's `decisions` share a realization; runners
  already compute per-output cache keys this way. A fan-out delivers one entry
  per member universe, with shared realizations deduplicated at the cache, not
  in the collection (see *Questions*).

Bare `artifact#*` (option 2 in the tracking issue) is **not** proposed: a
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
      - religiosity_study1_p#full_multiverse   # 120 artifacts
      - religiosity_study2_p#full_multiverse   # 210 artifacts
      - fiscal_attitudes_p#full_multiverse
      - social_attitudes_p#full_multiverse
      - voting_preference_p#full_multiverse
      - donation_preference_p#full_multiverse
    recipe:
      command: >-
        python src/plot_figure1.py --multiverse-results {inputs}
        --significance 0.05 --output {output}

multiverses:
  - id: full_multiverse
    description: >-
      The valid Cartesian product across all five decisions. Option
      constraints remove NMO1+ECL3 and NMO2+ECL2, leaving 210 universes.
    decisions: "*"
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
      - f1_score#rf_standard
      - f1_score#svm_standard
    recipe:
      command: python src/compare.py

  - id: scaling_sensitivity
    type: metric
    description: Macro-F1 as a function of feature scaling, all else at rf_standard.
    inputs:
      - f1_score#scaling_sweep   # fan-out: one artifact per scaling option
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
    decisions:
      scaling: "*"
```

## Implementation implications & migration

**Schema (`src/astra/schema/`):** `analysis.yaml` gains inlined `universes`
and `multiverses` slots on `Analysis` (available at every node by
self-similarity) and the `#selector` extension to the `Output.inputs`
reference grammar; `Decision.default`'s doc-string is corrected to a
presentational hint. `universe.yaml` gains `Universe.base`, the `Multiverse`
class (`id`, `description`, `universes` selectors, `base`, `decisions` option
selectors), and an updated `UniverseNode.universe` that points at in-file
universes. Regenerate with `just gen-python` / `just gen-doc`; the published
JSON Schema propagates to both SDKs; docs (`specification.md` *Universes*
section, `elements/`, examples, README) update alongside per the repo's
schema-change ritual.

**Validation (`astra-tools`):** ids unique in the tree-wide shared namespace;
`base` chains and multiverse membership acyclic; a universe without `base` is
complete over active decisions; effective selections honor `requires` /
`incompatible_with`; regex members are valid full-match patterns over declared
universe ids; every multiverse expands to at least one universe; `#` selectors
resolve and qualify Output references; a pin targets an output active in that
universe; universe-invariant recipes use no `{decisions.<id>}` placeholders;
lint for the YAML `#`-comment footgun. Runner scheduling, cache keys, and
collection serialization are implementation concerns outside this RFC
(identity keys on effective selections).

**Compatibility:** this is a **breaking** change — a major bump under the
versioning policy. Universe declarations move into `astra.yaml` and the
`universes/` directory is dropped as a supported location; migration is
mechanical (each file's body is already a valid in-file entry). Unqualified
references, the `.` hierarchy separator, and all other existing grammar keep
their exact meaning; the `#` selector itself is additive.

## Questions or objections

Recorded as open unless marked otherwise; discussion on the tracking issue and
the draft PR resolves them.

- **What does `"*"` quantify over? — resolved by the prototype.** The full
  valid decision space (constrained Cartesian product), not "all declared
  universes." The declared-universes reading is expressible by enumeration, and
  a multiverse analysis that silently depended on which configurations happened
  to be declared would be fragile. Recorded so the alternative is not silently
  re-litigated.
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
  `base` when their `decisions` map is partial; `Decision.default` stays a
  presentational hint. Authors who want a reference configuration may *name* a
  universe `baseline` by convention — the spec attaches no meaning to the
  name. (A contemporaneous alternative draft on the tracking issue completes
  omitted decisions from defaults; this RFC deliberately does not.) Recorded
  so the convenience argument is not silently re-litigated.
- **Combinatorial guardrails — open.** `"*"` can be astronomically large.
  Should validators warn (or runners require confirmation) above a universe
  count threshold, or is that purely a tooling concern outside the spec?
- **Selector sigil: `#` over `@` — resolved.** Earlier drafts used `@`.
  Adopted `#` following the alternative draft on the tracking issue and
  ecosystem convention: `#` selects a view *within* a resource (URL fragments,
  CSS `#id`), `@` pins a *revision* (`actions/checkout@v4`, `pkg@1.2.3`), and
  `@` stays free for a future sources RFC addressing external analyses at
  repository revisions, so the axes compose. Cost accepted: the YAML
  stray-space comment footgun, mitigated by a validator lint.
- **Change the hierarchy separator from `.` to `:`? — rejected.** The
  alternative draft proposes colon-delimited artifact paths to reserve `.`
  for a future artifact-regex RFC. Rejected here: RFC-0002's accepted
  tree-path addressing already uses `.`, and breaking every existing
  hierarchical reference for a hypothetical future grammar is cost without
  present benefit — a future RFC can choose regex delimiters that coexist
  with `.` paths.

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
  (Anthony Ozerov) — the working prototype this RFC is grounded in; see also
  [`astra-multiverse-example-steegen-2`](https://github.com/anthonyozerov/astra-multiverse-example-steegen-2),
  the cross-version specification-search demonstration.
- [Alternative draft](https://github.com/LightconeResearch/astra-spec/issues/52#issuecomment-5145724722)
  on the tracking issue — source of the `#` selector, regex membership,
  nested multiverses, union membership, and the tree-wide namespace adopted
  here; diverges on defaults completion and the `:` separator (see
  *Questions*).
- Tracking issue: [#52](https://github.com/LightconeResearch/astra-spec/issues/52).
- [RFC-0002](0002-decouple-reports.md) — establishes element addressing, which
  in-file universes and multiverses join as addressable elements.
