---
rfc: 0002
title: Author analysis reports as MyST documents that reference ASTRA content
status: Draft # Draft | Active | Accepted | Rejected | Superseded
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

**Prior art.** The scientific-document problem is already solved by
[MyST Markdown](https://mystmd.org/): structured frontmatter (authors with
affiliation/ORCID, keywords, license), cross-references, citations and
bibliographies, figures and tables, and export to PDF/JATS. ASTRA's narrative
reinvents a thin, rigid slice of this *inward*; it even already carries an
anchor cross-reference grammar (`[text](#decisions.scaling)`) that gestures at
MyST-style referencing.

**Working prototype.** The mechanism proposed here is already demonstrated
end-to-end by [**MySTRA**](https://github.com/LightconeResearch/MySTRA) — a MyST
plugin that reads `astra.yaml` at build time and emits standard MyST AST — and a
full DESI DR1 BAO example project that renders on the stock `myst` engine and
themes. This RFC is grounded in something that works; its job is to decide *what
of this belongs in the ASTRA specification*, not to bless a particular tool.

## Proposal

In plain language: **an analysis's report stops being a fixed field inside
`astra.yaml` and becomes an ordinary MyST document in the project that
references the structured content ASTRA already holds.** The structured graph
remains the single source of truth; the report is prose over it and renders to a
real paper.

The proposal has three parts. The first two are the reviewable core of this RFC;
the third is deliberately left open (see *Questions or objections*).

### 1. Transition the narrative field to a plain `description`

**Remove the `Narrative` class entirely** — its five sections (`summary`,
`findings`, `methods`, `inputs`, `outputs`) and the conditional coverage
validation — and give `Analysis` a single optional **`description`**, the same
free-prose field every other content object already carries (`Input`, `Output`,
`Option`, and `Universe` all use `description`; `Decision` and `Insight` use the
semantically-specific `rationale` and `claim`/`notes`). This makes "every ASTRA
object has an optional `description`" a real, teachable rule, and removes a field
whose five sections merely *duplicated* the structured children they sat beside.
A short human description stays in the spec; everything richer moves to the MyST
report.

### 2. Make ASTRA elements addressable; let MyST reports reference them

The load-bearing spec commitment is **identity, not rendering**: every analysis
element — decisions, outputs, findings, prior insights, inputs, and
sub-analyses — is addressable by a stable **tree-path**, the same grammar the
narrative anchors already use, extended with a sub-analysis scope prefix:

```
<id>                      # element in the root analysis
<sub>.<id>                # element in a sub-analysis
<sub>.<subsub>.<id>       # nested
```

A report is one or more MyST pages in the project (`index.md`, conventionally a
page per sub-analysis). A build-time bridge resolves references against
`astra.yaml`, the selected universe, and the materialised results into standard
MyST output — figures/tables with provenance, finding/decision cards, and live
numbers interpolated from result products, so nothing is hand-typed.

This RFC proposes that ASTRA **normatively owns the addressing** (what is
referenceable, and by what path) and leaves **the MyST authoring vocabulary
as a companion convention** (the `astra:*` directives/roles, the live-value
addressing grammar, and the materialised-results path convention), with MySTRA
as the reference implementation — rather than baking a single rendering
toolchain into the schema. Where exactly to draw that line is the central open
question below.

### 3. Authoring metadata (authors)

An ASTRA analysis stands alone — it may never acquire a report — so it must record
its own attribution: **who did the analysis**. This cannot be delegated to a
report medium's frontmatter, because there may be no report. Today
`Analysis.authors` is a bare list of strings, too thin to carry author identity
(ORCID), affiliation, or contributor roles.

This RFC enriches `Analysis.authors` into a list of author objects that adopt
**MyST's `author` frontmatter field names verbatim**. Reusing the exact names
means the analysis is self-sufficient for attribution *and* — when a MyST report
is later added — the entries map one-to-one onto the report's author frontmatter
with no translation layer. The fields mirror MyST's author schema:

- `name` — required; the only mandatory field.
- `orcid` — the author's ORCID (a persistent identifier).
- `email`, `corresponding` — contact and corresponding-author flag.
- `affiliations` — list of affiliations.
- `roles` — CRediT contributor roles.
- `equal_contributor`, `deceased`, `note` — standard MyST author flags/notes.
- `url`, `github`, and the other social-link keys MyST defines (`bluesky`,
  `mastodon`, `linkedin`, …).

```yaml
# astra.yaml
authors:
  - name: Jane Doe
    orcid: 0000-0002-1825-0097
    email: jane@example.org
    corresponding: true
    affiliations:
      - Institute for Cosmic Surveys
    roles:
      - Conceptualization
      - Software
  - name: DESI Collaboration
```

These fields are inlined directly at the `authors` level — this RFC does **not**
introduce a dedicated reusable contributor/agent object. Factoring the same
fields into such an object (so it can also describe organisations, software
agents, or run attribution) is a natural later generalisation and is deliberately
out of scope here.

When a MyST report exists, its frontmatter carries the **document-level** concerns
the analysis graph does not — byline order on the page, publication keywords,
document license — while the author entries themselves align field-for-field with
these analysis authors. ASTRA `tags` remain analysis categorisation; publication
keywords are a report concern.

**Two levels of authorship, and how they relate.** The analysis authors and the
paper authors are distinct sets with a deliberate relationship, which falls into
two cases:

- *Written by the analysis authors (the common case).* The paper byline is a
  **superset** of the analysis authors — everyone who did the analysis, plus
  writing-only contributors who shaped the manuscript but touched no part of the
  analysis (a co-author who wrote the discussion, say). The analysis authors carry
  over field-for-field; the extra contributors appear only in the report
  frontmatter, and CRediT `roles` keep the distinction legible
  (`Software`/`Investigation` on an analysis author vs `Writing – original draft`
  on a writing-only one).
- *Reused by a third party (citation, not authorship).* If a *different* author
  imports a result from someone else's analysis — an `Input` of `type: analysis`
  referenced via `ref` — the imported analysis's authors are **not** added to the
  byline. The reused work is **cited**, carrying its own authorship with it.

The boundary is the analysis boundary: you may claim byline credit for the
analyses you authored, while work you import you cite. In short — **paper authors
⊇ the authors of the analyses you wrote (plus writing-only contributors); the
authors of analyses you import are cited, not credited.**

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
element); the report is a MyST page that references the analysis (excerpt from
the prototype's `index.md`):

```yaml
# astra.yaml
description: |
  Reproduction of the DESI DR1 configuration-space BAO measurement …
```

```markdown
<!-- index.md -->
---
title: Configuration-Space BAO Distances from DESI DR1
authors:
  - name: DESI Collaboration
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
`astra.yaml`, rerun the analysis, and the report updates itself. Plain MyST
cross-references work alongside the ASTRA ones (`[](#output-bao_fit_plot)`), and
sub-analysis pages use the scoped prefix (`reconstruction.algorithm`).

**Authors** — the analysis records who did the work; the report byline *extends*
that set rather than restating identities. The analysis authors (`astra.yaml`):

```yaml
# astra.yaml
authors:
  - name: Jane Doe
    orcid: 0000-0002-1825-0097
    roles: [Conceptualization, Software, Investigation]
  - name: Sam Lee
    orcid: 0000-0001-5109-3700
    roles: [Data curation, Formal analysis]
```

The report byline is a **superset** — the same two analysis authors, carried over
field-for-field, plus a writing-only contributor who never touched the analysis
(`index.md`):

```yaml
# index.md
authors:
  - name: Jane Doe          # carried over from astra.yaml
    orcid: 0000-0002-1825-0097
    roles: [Conceptualization, Software, Investigation, Writing – original draft]
  - name: Sam Lee
    orcid: 0000-0001-5109-3700
    roles: [Data curation, Formal analysis]
  - name: Pat Rivera        # writing only — not an author of the analysis
    orcid: 0000-0003-1419-2405
    roles: [Writing – review & editing]
```

## Implementation implications & migration

This change is **not confined to the spec repository** — it ripples through the
schema, both SDKs, and the companion renderer. Landing it requires coordinated
changes across the ASTRA repositories:

**`astra-spec` (this repo) — schema, datamodel, docs:**

- `src/astra/schema/analysis.yaml`: remove the `Narrative` class and the
  `narrative` slot; add an optional `description` slot to `Analysis`. Drop the
  conditional section-coverage rules. Enrich `Analysis.authors` from a list of
  strings into a list of author objects using MyST's author field names (part 3);
  this is breaking, with a migration that lifts each string into `name`.
- `src/astra/datamodel/`: regenerated from the schema via `just gen-python`.
- The published JSON Schema artifact (`astra-spec.org/<version>/schema/…`) shifts
  — both SDKs resolve the schema from there, so this is the propagation point.
- Docs: update `specification.md` (narrative section), `index.md`, `cli.md`, and
  `README.md`, and add an "authoring a report" page describing the MyST workflow
  and the addressing grammar. The auto-generated `docs/elements/` reference
  regenerates via `just gen-doc`.

**`astra-tools` (Python CLI + SDK):**

- The validator (`astra validate`) holds the section-coverage logic that must be
  dropped, and would gain any new reference-resolution checks (though those may
  belong to the renderer — see open questions).
- `astra init` scaffolding should emit a MyST report skeleton (`index.md`,
  `myst.yml`) alongside `astra.yaml`, not a narrative stub.
- The existing paper-management surface should be reviewed and aligned with (or
  superseded by) the MyST report workflow.

**`astra-typescript` (`@astra-spec/sdk`):**

- The TypeScript types and validation mirror the Python schema surface and must
  be regenerated/updated for the removed `Narrative` class and new `description`
  slot.
- This is load-bearing for the renderer: MySTRA's data-model types come directly
  from `@astra-spec/sdk`, so the prototype tracks this package — the SDK must be
  updated before (or with) the renderer.

**Companion renderer (MySTRA, separate repo):** rendering relies on a build-time
MyST bridge. This RFC documents the workflow and the addressing contract;
whether ASTRA ships or formally blesses a reference implementation is part of the
spec-vs-tooling open question.

**Compatibility / versioning:**

- Removing the `narrative` field is a **breaking** change — existing analyses
  that declare a `narrative` will no longer validate. Under the
  [versioning policy](https://astra-spec.org/about/) this is a **major** bump.
  Adding the optional `description` slot is itself additive.
- **Migration:** a documented path (and ideally a small helper) maps an existing
  five-section `narrative` into (a) a one-paragraph `description` and (b) a
  starter MyST report page, so no prose is lost.

## Questions or objections

These are the forks this draft intends to resolve through discussion; they are
recorded here as open, not decided.

- **Fate of the narrative field — resolved.** Earlier drafts weighed keeping a
  reduced `summary` section; the proposal now removes `Narrative` entirely in
  favour of a single optional `description`, consistent with every other element
  object. Recorded here so the rejected alternative (a bespoke `summary`) is not
  silently re-litigated.
- **Where is the spec ↔ tooling boundary? - resolved** The proposal has ASTRA own the
  *addressing* (tree-path identity of elements) and treat the MyST rendering
  vocabulary (`astra:*`, the `{astra:value}` grammar, the materialised-results
  path convention) as a documented companion convention. This grammar is left to particular rendering tools, and is outside of the scope of the astra spec itself. 
- **Authoring metadata — mostly resolved.** Work-level attribution lives on
  `Analysis.authors`, using MyST's author field names so a report's frontmatter
  aligns field-for-field; document-level concerns (byline order, publication
  keywords, page license) live only in the report. Open: the precise convention
  by which a report signals byline-only additions or overrides versus simply
  inheriting the analysis authors — and whether the inlined author fields should
  later be factored into a reusable contributor object.
- **Universe scoping.** A rendered report is pinned to a single universe; ASTRA
  analyses are multi-universe. Should the spec state that a report is
  universe-scoped, and can a report compare across universes, or is that out of
  scope for v0.1? -> This is out of scope for this PR which does not cover universes.
- **Artifact boundary.** When an analysis is published/archived, is
  the MyST report inside that artifact boundary or a separate publication layer?

## References

- [MyST Markdown](https://mystmd.org/) — the scientific authoring system this
  proposal builds on (frontmatter, cross-references, citations, figures, export).
- [MySTRA](https://github.com/LightconeResearch/MySTRA) — the reference
  prototype: a MyST plugin that renders ASTRA components from `astra.yaml`.
- [RFC-0001](0001-establish-the-rfc-process.md) — establishes the process this
  RFC follows; also modelled on the MyST/MEP lineage.
- Tracking issue: [#41](https://github.com/LightconeResearch/astra-spec/issues/41).
