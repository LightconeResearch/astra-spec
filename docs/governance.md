# Governance

ASTRA is developed in the open and is intended to evolve towards a community-owned
standard. This page documents who makes decisions today, how those decisions are
made, and how that structure is expected to evolve. It is the companion to the
[RFC process](rfc-process.md), which is the mechanism through which most
decisions are actually made and recorded.

!!! warning "Draft governance — alpha"
    ASTRA is in **alpha**. This page describes the governance model as a
    *full-featured draft*: the structure below is what the project commits to at
    **v0.1**. Until then, ASTRA is stewarded by **Lightcone Research**, and
    decisions rest with the **Lightcone Research core team**, with all discussion
    in public issues and pull requests. There is no formal voting process during
    alpha — the [RFC acceptance bar](rfc-process.md#acceptance-criteria) becomes
    binding at v0.1.

## Stewardship

ASTRA is currently stewarded by [**Lightcone Research**](https://github.com/LightconeResearch),
which writes most of the code and documentation today. This stewardship is a *starting point, not the
long-term home*: as ASTRA stabilizes beyond alpha, the project will move into a
community-governed structure.

## Roles

**Steering Council.** Provides high-level technical and strategic direction,
safeguards the project's principles, oversees the RFC process, and acts as final
approver for RFCs. During alpha this role is held by the **Lightcone Research
core team**; it is expected to **expand at v0.1** into a dedicated council as
outside contributors join, drawing on the models used by the Python Software
Foundation and Project Jupyter.

**Maintainers.** Actively design, implement, and maintain the schema, tooling,
and documentation; review and approve pull requests. Maintainer status emerges
through sustained contribution rather than appointment, and may span
organizations and tool ecosystems.

**Contributors and community.** Anyone may open an issue, propose an RFC, or
submit code and documentation, provided they follow the
[Code of Conduct](#code-of-conduct). The governance structure exists to enable
progress and stewardship — not to restrict contribution. In alpha, the most
valuable contributions are real-analysis attempts, adversarial schema review,
and downstream tooling experiments; see the [Community](community.md) page.

## How decisions are made

Significant or contested changes go through the [RFC process](rfc-process.md). Decisions and their rationale 
are recorded durably as accepted (and rejected) RFCs, so the project's evolution stays auditable.

## Code of Conduct

All participation in ASTRA's spaces — issues, pull requests, and discussions —
is governed by the organization-wide
[**Contributor Covenant 3.0 Code of Conduct**](https://github.com/LightconeResearch/.github/blob/master/CODE_OF_CONDUCT.md).
Conduct concerns can be raised privately with the project leads at the addresses
listed there. Treat other contributors the way you would want to be treated;
assume good faith; disagree with the idea, not the person.

## Changing this document

Governance and process changes are themselves made by RFC. The procedural
baseline was established in
[RFC 0001](https://github.com/LightconeResearch/astra-spec/blob/main/rfcs/0001-establish-the-rfc-process.md);
amendments — including the composition of the Steering Council and the exact
acceptance thresholds — follow the same path.
