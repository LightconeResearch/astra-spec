---
rfc: 0001
title: Establish the ASTRA RFC process and interim governance
status: Accepted
authors:
  - Francois Lanusse (@eiffl)
created: 2026-06-19
tracking-issue:
superseded-by:
---

## Context

ASTRA is moving from an internally-developed schema toward a public, community
-shaped standard. The [About page](https://astra-spec.org/about/) already commits
the project to "open governance, eventually" — a steering group, a public RFC
process, and a version-decision protocol — with Lightcone Research as interim
steward. This RFC makes good on the first part of that commitment: it
establishes *how* changes are proposed, discussed, and decided, so external
contributors have a defined channel before the specification stabilizes.

It is intentionally **procedural rather than technical**. It does not change the
schema. Subsequent RFCs introduce and evolve specific schema concepts; this one
sets expectations for how we work together first.

The design borrows directly from processes that already work in this ecosystem:
[MyST Enhancement Proposals (MEP)](https://mep.mystmd.org) and the
PEP/Jupyter lineage behind it.

## Proposal

Adopt the process and governance documented canonically at:

- [`docs/rfc-process.md`](../docs/rfc-process.md) → <https://astra-spec.org/rfc-process/>
- [`docs/governance.md`](../docs/governance.md) → <https://astra-spec.org/governance/>

In summary:

- **RFCs live in-repo** under [`rfcs/`](./), as numbered Markdown files authored
  from [`0000-template.md`](0000-template.md). Keeping them beside the schema
  they motivate matches ASTRA's existing "schema + docs in one PR" workflow.
- **Lifecycle:** issue → draft PR → discuss & iterate → mark ready for review
  (opens the decision window) → accepted or rejected → implement. The process
  uses GitHub's native draft / ready-for-review / merged states rather than
  status labels (the only label is `rfc`, on the tracking issue); each RFC's
  `status:` frontmatter is the durable record. Both accepted and rejected RFCs
  are merged, preserving the rationale — fitting for a project whose whole thesis
  is a durable, reproducible record.
- **Template fields:** Context · Proposal · Examples · Implementation
  implications & migration · Questions or objections · References.
- **Interim governance:** until ASTRA reaches **v0.1**, the project is in alpha
  and decisions rest with the Lightcone Research core team, with all discussion
  in public issues and pull requests. The formal review window and
  multi-approver acceptance bar described in the process document become binding
  at v0.1, when the Steering Council expands beyond the core team.

**Alternatives considered.** A separate `astra-rfcs` repository was set aside:
ASTRA is a single-spec repository, and an in-repo directory keeps an RFC next to
the schema change it motivates. A GitHub-Discussions-only process was set aside
because it produces no durable, numbered, citable record and no PR-based review
gate — both of which matter for a reproducibility-focused standard.

## Examples

This RFC is its own first example: it was proposed as a pull request adding the
`rfcs/` directory, the template, and the two governance documents, and merged
under the very rules it defines.

## Implementation implications & migration

- Adds `rfcs/` (template, index, this RFC).
- Adds `docs/rfc-process.md` and `docs/governance.md`, wired into the site nav.
- Adds an *RFC proposal* GitHub issue template.
- Updates `CONTRIBUTING.md` and the [Community page](../docs/community.md) to
  point at the RFC process, and fixes the `CODE_OF_CONDUCT.md` reference to the
  organization-level [Contributor Covenant 3.0](https://github.com/LightconeResearch/.github/blob/master/CODE_OF_CONDUCT.md).
- No schema or generated-artifact changes; no migration required.

## Questions or objections

- **Is a single-maintainer "council" really governance?** For alpha, yes — it is
  honest about where decisions currently sit while publishing the full process
  the project commits to at v0.1. The draft status of the governance document
  makes the trajectory explicit rather than implied.
- **Why number RFCs with four digits?** Matches the sibling MEP convention
  and leaves room without renumbering.

## References

- [MyST Enhancement Proposals (MEP)](https://mep.mystmd.org) — the process and
  template this RFC is modeled on.
- [PEP 1](https://peps.python.org/pep-0001/) and
  [PEP 13](https://peps.python.org/pep-0013/) — the Python Enhancement Proposal
  workflow and steering-council governance behind the MEP lineage.
