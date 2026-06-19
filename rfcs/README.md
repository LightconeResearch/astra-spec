# ASTRA RFCs

This directory holds **ASTRA Requests for Comments (RFCs)** — the written,
citable record of significant changes to the ASTRA specification, its tooling
conventions, and its governance.

Small, low-risk changes (typo fixes, doc tweaks, a tightened error message, an
obviously-missing enum value) do **not** need an RFC — open an issue or a pull
request directly. An RFC is for changes that are significant, contested, or
worth recording the rationale for: new schema concepts, breaking changes,
versioning and compatibility rules, publishing and identifier conventions, and
process or governance changes.

The full lifecycle, decision rights, and acceptance criteria are documented on
the site:

- **[RFC process](https://astra-spec.org/rfc-process/)** — how a proposal moves from idea to accepted.
- **[Governance](https://astra-spec.org/governance/)** — who decides, and how that evolves toward v0.1.

> **ASTRA is in alpha.** The process below is published as a *full-featured
> draft*. Until ASTRA reaches **v0.1**, decisions rest with the maintainer
> (François Lanusse) with discussion in issues and pull requests; the formal
> review window and multi-approver acceptance bar become binding at v0.1.

## How to propose an RFC

1. **Open an issue** describing the idea, so others can react before you invest
   in a full draft. Use the *RFC proposal* issue template.
2. **Open a pull request** that adds `rfcs/NNNN-short-slug.md`, copied from
   [`0000-template.md`](0000-template.md), where `NNNN` is the next free number.
3. **Discuss and iterate** in the pull request until the proposal stabilizes.
4. When ready, the proposal moves to **Active** review and is **Accepted** or
   **Rejected** per the [RFC process](https://astra-spec.org/rfc-process/).
   Both accepted *and* rejected RFCs are merged, so the record is complete.

## Status legend

| Status | Meaning |
|---|---|
| **Draft** | Under active drafting and discussion; not yet up for a decision. |
| **Active** | Stabilized; in the time-boxed final review window. |
| **Accepted** | Approved. Implementation may begin (or has begun). |
| **Rejected** | Declined, but merged for the record with the rationale intact. |
| **Superseded** | Replaced by a later RFC (see its `superseded-by` field). |

## Index

| RFC | Title | Status |
|---|---|---|
| [0001](0001-establish-the-rfc-process.md) | Establish the ASTRA RFC process and interim governance | Accepted |
