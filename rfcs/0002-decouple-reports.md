---
rfc: 0002
title: Decouple analysis reports from astra.yaml
status: Accepted # Draft | Active | Accepted | Rejected | Superseded
authors:
  - Francois Lanusse (@eiffl)
created: 2026-06-20
tracking-issue: https://github.com/LightconeResearch/astra-spec/issues/41
superseded-by:
---

## Context

Writing up a completed ASTRA analysis today means filling in the **`narrative`
field** — a fixed five-section object (`summary`, `findings`, `methods`,
`inputs`, `outputs`) embedded as Markdown in `astra.yaml`. `astra validate`
applies *conditional coverage*: a section becomes **required** once the matching
structured data exists (e.g. `findings` prose is required once
`Analysis.findings` has entries). The design assumed the write-up would be a
prescribed, paper-like dashboard view.

In practice this is too rigid in one dimension and too weak in another:

- **Prescriptive structure.** It dictates *what* a write-up must contain and
  *how* it is sectioned, and enforces a coverage checklist. The paper-like view
  is genuinely nice for a finished analysis, but authors should have wide
  latitude over how they craft the narrative and what it says.
- **Not a real authoring surface.** It is plain Markdown in YAML: no first-class
  figures/tables, no citations or bibliography, no multi-page structure, no
  export to a PDF/paper. So authors re-type measured numbers and re-paste
  figures into the prose, where they immediately start to rot — a value goes
  stale, a figure is from an old run, a stated assumption no longer matches the
  spec. There is no single source of truth between the analysis and its
  write-up.

ASTRA already holds the *truth* of an analysis — every decision, the inputs and
outputs of each step, the findings, the prior insights, and (once run) the
materialised result products. The opportunity is to let the write-up
**reference** that structured content instead of restating it.

**Prior art.** The scientific-document problem is already solved by mature
authoring systems. [MyST Markdown](https://mystmd.org/), for example, offers
structured frontmatter (authors with affiliation/ORCID, keywords, license),
cross-references, citations and bibliographies, figures and tables, and export
to PDF/JATS. ASTRA's narrative reinvents a thin, rigid slice of this *inward*;
it even already carries an anchor cross-reference grammar
(`[text](#decisions.scaling)`) that gestures at the same kind of referencing.
The point is not to adopt one such system into the spec, but to stop
reinventing one inside it.

**Working prototype.** The mechanism proposed here is already demonstrated
end-to-end by one example implementation,
[**MySTRA**](https://github.com/LightconeResearch/MySTRA) — a MyST plugin that
reads `astra.yaml` at build time and emits standard MyST AST — together with a
full DESI DR1 BAO example project that renders on the stock `myst` engine and
themes. This RFC is grounded in something that works; its job is to decide *what
of this belongs in the ASTRA specification*, not to bless a particular tool or
authoring framework.

## Proposal

In plain language: **an analysis's report stops being a fixed field inside
`astra.yaml` and becomes an ordinary document in the project that references the
structured content ASTRA already holds.** The structured graph remains the
single source of truth; the report is prose over it and renders to a real paper.
Crucially, **ASTRA is not prescriptive about how the report is authored or
rendered** — that is left to external toolchains. MyST is the example used
throughout this RFC because a working prototype exists, but it is only an
example: any comparable authoring framework could consume the same addressing
contract, and others may well emerge.

The proposal has two parts.

### 1. Transition the narrative field to a plain `description`

**Remove the `Narrative` class entirely** — its five sections (`summary`,
`findings`, `methods`, `inputs`, `outputs`) and the conditional coverage
validation — and give `Analysis` a single optional **`description`**, the same
free-prose field every other content object already carries (`Input`, `Output`,
`Option`, and `Universe` all use `description`; `Decision` and `Insight` use the
semantically-specific `rationale` and `claim`/`notes`). This makes "every ASTRA
object has an optional `description`" a real, teachable rule, and removes a field
whose five sections merely *duplicated* the structured children they sat beside.
A short human description stays in the spec; everything richer moves to the
external report.

### 2. Make ASTRA elements addressable; let reports reference them

The load-bearing spec commitment is **identity, not rendering**: every analysis
element — decisions, outputs, findings, prior insights, inputs, and
sub-analyses — is addressable by a stable **tree-path**, the same grammar the
narrative anchors already use, extended with a sub-analysis scope prefix:

```
<id>                      # element in the root analysis
<sub>.<id>                # element in a sub-analysis
<sub>.<subsub>.<id>       # nested
```

A report is one or more authoring-framework pages in the project (e.g.
`index.md`, conventionally a page per sub-analysis). A build-time bridge
resolves references against `astra.yaml`, the selected universe, and the
materialised results into rendered output — figures/tables with provenance,
finding/decision cards, and live numbers interpolated from result products, so
nothing is hand-typed.

This RFC proposes that ASTRA **normatively owns the addressing** (what is
referenceable, and by what path) and leaves the **authoring vocabulary that sits
on top of it as a companion convention of the rendering toolchain** (in the MyST
example: the `astra:*` directives/roles, the live-value addressing grammar, and
the materialised-results path convention), with MySTRA as one reference
implementation — rather than baking a single rendering toolchain into the
schema.

## Examples

**Before** — the write-up lives in `astra.yaml` as the five-section `narrative`,
restating the analysis and hand-typing numbers:

```yaml
narrative:
  summary: |
    Reproduction of the DESI DR1 configuration-space BAO measurement …
  methods: |
    The pipeline runs in three stages: reconstruction produces shifted
    catalogs, clustering measures correlation functions, and a template-fitting
    stage turns each into posterior constraints on the BAO scale …
  # findings / inputs / outputs sections, each required once the
  # corresponding structured data exists
```

**After** — `astra.yaml` keeps a single optional `description` (like every other
element); the report is an external page that references the analysis. The
excerpt below uses MyST as the example authoring framework (from the prototype's
`index.md`):

```yaml
# astra.yaml
description: |
  Reproduction of the DESI DR1 configuration-space BAO measurement …
```

```markdown
<!-- index.md -->
---
title: Configuration-Space BAO Distances from DESI DR1
exports:
  - format: pdf
---

The combined LRG3+ELG1 bin reaches $D_V/r_d =$
{astra:value}`bao_distance_table tracer=lrg3_elg1 col=DV_over_rd pm`,
consistent with the {astra:finding}`bao_detected_post_recon` detection.

The pipeline runs in three stages: {astra:analysis}`reconstruction` produces
shifted catalogs, {astra:analysis}`clustering` measures correlation functions,
and a template-fitting stage turns each into posterior constraints.

:::{astra:output} bao_fit_plot
:::
```

The value is read live from the result product, the finding renders as a card
with its record, and the figure is pulled in with its provenance. Edit
`astra.yaml`, rerun the analysis, and the report updates itself. The framework's
native cross-references work alongside the ASTRA ones (in MyST,
`[](#output-bao_fit_plot)`), and sub-analysis pages use the scoped prefix
(`reconstruction.algorithm`). The directive/role spelling shown here is
MyST-specific; a different toolchain would expose the same addressing through
its own vocabulary.

## Implementation implications & migration

This change is **not confined to the spec repository** — it ripples through the
schema, both SDKs, and the companion renderer. Landing it requires coordinated
changes across the ASTRA repositories:

**`astra-spec` (this repo) — schema, datamodel, docs:**

- `src/astra/schema/analysis.yaml`: remove the `Narrative` class and the
  `narrative` slot; add an optional `description` slot to `Analysis`. Drop the
  conditional section-coverage rules. Remove the `Analysis.authors` slot (see
  *Authorship deferred* below); this is breaking.
- `src/astra/datamodel/`: regenerated from the schema via `just gen-python`.
- The published JSON Schema artifact (`astra-spec.org/<version>/schema/…`) shifts
  — both SDKs resolve the schema from there, so this is the propagation point.
- Docs: update `specification.md` (narrative section), `index.md`, `cli.md`, and
  `README.md`, and add an "authoring a report" page describing the external
  report workflow and the addressing grammar (using MyST as the worked example).
  The auto-generated `docs/elements/` reference regenerates via `just gen-doc`.

**`astra-tools` (Python CLI + SDK):**

- The validator (`astra validate`) holds the section-coverage logic that must be
  dropped, and would gain any new reference-resolution checks (though those may
  belong to the renderer — see open questions).
- `astra init` scaffolding should emit a report skeleton (for the MyST example,
  `index.md` + `myst.yml`) alongside `astra.yaml`, not a narrative stub.
- The existing paper-management surface should be reviewed and aligned with (or
  superseded by) the external report workflow.

**`astra-typescript` (`@astra-spec/sdk`):**

- The TypeScript types and validation mirror the Python schema surface and must
  be regenerated/updated for the removed `Narrative` class, the removed `authors`
  slot, and the new `description` slot.
- This is load-bearing for the renderer: MySTRA's data-model types come directly
  from `@astra-spec/sdk`, so the prototype tracks this package — the SDK must be
  updated before (or with) the renderer.

**Companion renderer (MySTRA, separate repo):** rendering relies on a build-time
bridge. This RFC documents the workflow and the addressing contract; whether
ASTRA ships or formally blesses a reference implementation is part of the
spec-vs-tooling open question.

**Compatibility / versioning:**

- Removing the `narrative` and `authors` fields is a **breaking** change —
  existing analyses that declare either will no longer validate. Under the
  [versioning policy](https://astra-spec.org/about/) this is a **major** bump.
  Adding the optional `description` slot is itself additive.
- **Migration:** a documented path (and ideally a small helper) maps an existing
  five-section `narrative` into (a) a one-paragraph `description` and (b) a
  starter report page, so no prose is lost. Existing `authors` strings have no
  schema home after this change; the migration should surface them so they can be
  carried into the report medium's own frontmatter.

## Questions or objections

These are the forks this draft intends to resolve through discussion; they are
recorded here as open, not decided.

- **Fate of the narrative field — resolved.** Earlier drafts weighed keeping a
  reduced `summary` section; the proposal now removes `Narrative` entirely in
  favour of a single optional `description`, consistent with every other element
  object. Recorded here so the rejected alternative (a bespoke `summary`) is not
  silently re-litigated.
- **Where is the spec ↔ tooling boundary? — resolved.** The proposal has ASTRA own
  the *addressing* (tree-path identity of elements) and treats the authoring/
  rendering vocabulary (in the MyST example, `astra:*`, the `{astra:value}`
  grammar, the materialised-results path convention) as a documented companion
  convention of whatever toolchain renders the report. That vocabulary is left to
  particular rendering tools and is outside the scope of the ASTRA spec itself.
- **Authorship — deferred (removed for now).** ASTRA no longer carries any notion
  of authorship: the `Analysis.authors` field is removed. The reason is that
  authorship cannot be applied coherently until ASTRA defines **identity, reuse,
  and citation semantics for individual elements**. If you extend a prior ASTRA
  analysis, it is undefined whether you add yourself to the author list, drop the
  originals, or keep them — none of which is meaningful without a notion of
  element identity and a way to *cite* rather than absorb reused work. Rather than
  ship an attribution model we cannot yet use correctly, we remove it. The
  tree-path addressing introduced in part 2 is a first step toward per-element
  identity; once elements have stable, citable identity we can layer
  citation/forking of ASTRA components on top and revisit attribution then. In the
  meantime, attribution of a write-up lives where it is already well-defined: the
  report medium's own frontmatter (e.g. MyST's author frontmatter), outside ASTRA.
- **Universe scoping.** A rendered report is pinned to a single universe; ASTRA
  analyses are multi-universe. Should the spec state that a report is
  universe-scoped, and can a report compare across universes, or is that out of
  scope for v0.1? → Out of scope for this PR, which does not cover universes.
- **Artifact boundary.** When an analysis is published/archived, is the report
  inside that artifact boundary or a separate publication layer? → Probably the
  report is not part of the research object on its own.

## References

- [MyST Markdown](https://mystmd.org/) — an example scientific authoring system
  this proposal can build on (frontmatter, cross-references, citations, figures,
  export); used throughout this RFC as an illustration, not a requirement.
- [MySTRA](https://github.com/LightconeResearch/MySTRA) — one reference
  prototype: a MyST plugin that renders ASTRA components from `astra.yaml`.
- [RFC-0001](0001-establish-the-rfc-process.md) — establishes the process this
  RFC follows; also modelled on the MyST/MEP lineage.
- Tracking issue: [#41](https://github.com/LightconeResearch/astra-spec/issues/41).
