# RFC process

The **Request for Comments (RFC)** process is how significant changes to ASTRA
are proposed, discussed, and decided in the open. It exists to keep major
decisions transparent, to invite participation without requiring deep prior
context, and to leave a durable, citable record of *what* changed and *why* —
the same values ASTRA asks of the analyses it describes.

!!! warning "Draft process — alpha"
    ASTRA is in **alpha**, and this process is published as a *full-featured
    draft*. Until ASTRA reaches **v0.1**, decisions rest with the **Lightcone
    Research core team**, with all discussion in public issues and pull requests.
    The time-boxed review window and multi-approver acceptance bar described
    below become **binding at v0.1**, when the [Steering Council](governance.md)
    expands beyond the core team. See [Governance](governance.md).

The process is modeled on [MyST Enhancement Proposals](https://mep.mystmd.org),
and the PEP/Jupyter lineage behind it.

## When you need an RFC

You **do not** need an RFC for low-risk changes — typo and documentation fixes,
tightened error messages, an obviously-missing enum value. Open an
[issue](https://github.com/LightconeResearch/astra-spec/issues) or a pull
request directly.

You **do** want an RFC when a change is significant, contested, or worth
recording the rationale for:

- new schema concepts or breaking changes to existing ones,
- versioning and compatibility rules,
- publishing, identifier, and metadata conventions,
- changes to the process or governance itself.

### What an RFC is — and is not

An ASTRA RFC **is** a written proposal for a significant change, scoped narrowly
enough to review and implement in a reasonable timeframe, and grounded in real
or anticipated use. It **is not** a full system design, a comprehensive
ontology, a guarantee of permanence, or a substitute for implementation. RFCs
are working agreements that may be revised or superseded as ASTRA matures.

## Lifecycle

RFCs live in the [`rfcs/`](https://github.com/LightconeResearch/astra-spec/tree/main/rfcs)
directory of the `astra-spec` repository, as numbered Markdown files. The process
leans on GitHub's native pull-request signals rather than a custom set of labels:
**a draft PR means the RFC is being worked on; marking it ready for review opens
the decision window.** Each RFC's own `status:` frontmatter field is the durable
record of where it ended up.

1. **Open an issue.** Describe the idea using the *RFC proposal* issue template
   (which carries the `rfc` label), so others can react and you get an early
   signal before investing in a full draft.
2. **Open a draft pull request.** Add `rfcs/NNNN-short-slug.md`, copied from
   [`0000-template.md`](https://github.com/LightconeResearch/astra-spec/blob/main/rfcs/0000-template.md),
   with `status: Draft`, and open the PR as a **GitHub draft**. The template's
   sections are **Context · Proposal · Examples · Implementation implications &
   migration · Questions or objections · References**.
3. **Discuss and iterate.** While the PR is a draft, invite discussion, incorporate
   feedback, and record objections and their responses in the RFC. Treat revisions
   as success, not failure.
4. **Open the decision window.** When the proposal has stabilized and the author
   wants to move forward, **mark the PR ready for review** and set the RFC to
   `status: Active`. The ready-for-review timestamp starts the review clock.
5. **Decide.** The RFC is **Accepted** or **Rejected**, recorded by setting
   `status:` accordingly in the frontmatter. *Both* outcomes are **merged**: an
   accepted RFC records the agreement, a rejected RFC records the reasoning so the
   question is not silently re-litigated. An author may instead **close the PR**
   to withdraw a proposal.
6. **Implement.** Accepted RFCs move into implementation following the project's
   normal development practices (schema change + regenerated artifacts + docs in
   one reviewed pull request).

## Statuses

A status lives in each RFC's `status:` frontmatter field; the table below maps it
to the corresponding pull-request state, so the two never need separate labels to
stay in sync.

| `status:` | Meaning | Pull-request state |
|---|---|---|
| **Draft** | Under active drafting and discussion; not yet up for a decision. | Draft PR |
| **Active** | Stabilized; in the open review window. | Ready for review |
| **Accepted** | Approved. Implementation may begin (or has begun). | Merged |
| **Rejected** | Declined, but merged for the record with the rationale intact. | Merged |
| **Superseded** | Replaced by a later RFC (recorded in its `superseded-by` field). | (set later) |

## Acceptance criteria

!!! note "Becomes binding at v0.1"
    During alpha, the Lightcone Research core team accepts or rejects an RFC
    after open discussion; there is no fixed quorum. From **v0.1**, an RFC may be accepted
    when **all** of the following hold:

    - it has been **Active** for a minimum open review window (proposed: at
      least five weekdays),
    - it has the required **Steering Council approvals** (proposed: at least
      two), and
    - there are **no outstanding requests for changes** from a Steering Council
      member.

    If a blocking objection is raised, the author may revise and restart the
    decision once the objection is addressed. The exact numbers are themselves
    subject to refinement by RFC as the Steering Council grows.

## Relationship to versioning

When an accepted RFC changes the schema, its **Implementation implications &
migration** section should state whether the change is a minor or major bump under ASTRA's
[versioning policy](about.md) and what migration (if any) existing analyses
need. The mechanics of versioned schema hosting — per-version docs and
machine-fetchable schemas at stable URLs — are already in place; see the
[About](about.md) page and the canonical `https://w3id.org/astra/` namespace.
