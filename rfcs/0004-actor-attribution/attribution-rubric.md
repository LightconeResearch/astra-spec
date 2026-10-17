# The Attribution Rubric

*Non-normative guidance for the ASTRA actor-attribution proposal. It explains and
guides; it adds no requirements to the specification. You can apply it to your own
`astra.yaml` without contacting the authors.*

**What it answers:** when a decision is recorded in an `astra.yaml`, which actors get
named on it, in what role, and what counts as each role.

---

## 1. Which decisions get an actor at all

You attribute only decisions that are already in the record, and ASTRA records only
*consequential* ones. Apply the **conclusion-invariance test** as a two-part check:

1. **Could a competent peer defensibly have chosen otherwise?** (A real alternative
   exists — not a fixed constraint, not a cosmetic tooling choice.)
2. **Could that other choice move the numerical result or change the conclusion?**

Record — and attribute — the decision only if **both** are yes. If every defensible
option yields the same conclusion, the choice is inconsequential: leave it out and name
no one. (Operationally: hold this decision fixed, let a fresh analyst redo everything
else; if the conclusion survives across the *other* defensible options here, the choice
did not need recording.)

- **Attribute:** algorithmic choices, numeric thresholds, statistical methods,
  data-selection criteria, corrections/calibrations.
- **Do not attribute:** choices that produce identical numbers, fixed external
  constraints, final output selection.

## 2. Two axes, kept separate

Every actor named on a decision sits at a point on **two independent axes**. Do not
collapse them into a single "author."

- **Direction ↔ Execution** — who set the *intent* (what to do and why) vs. who *did the
  work* (ran it, wrote the code).
- **Proposer ↔ Resolver** — who *put an option on the table* vs. who *ruled on it*
  (accepted, rejected, corrected).

An actor can occupy a different position on each axis for the same decision.
*Example (Iris `drop_iqr`):* the agent is **proposer + execution** (it proposed dropping
outliers); the researcher is **resolver + direction** (ruled it out). Two actors, four
distinct facts — one "author" field would lose three of them.

## 3. Disposition vocabulary

How to *think* about what happened to a proposed option. Two of the five land on ASTRA
fields; the other three are history, which ASTRA does not record.

- **proposed** — offered as a defensible option; not yet ruled on. → `proposed_by`.
- **rejected** — considered and ruled out, with a reason. → `excluded: true` +
  `excluded_reason` (what was observed), with `excluded_by` naming who ruled it out,
  `excluded_at` when, and `exclusion_rationale` the judgment that made the evidence
  dispositive. Keep the last two apart from `excluded_reason`: an option can be ruled
  out on a principle while its measured numbers looked fine on their own.
- **accepted** — chosen as the option that stands (the selected `default`).
- **revised** — kept, but changed (e.g. a parameter retuned); the option evolved.
- **corrected** — a previously accepted choice found wrong and replaced; the superseded
  value is *retained*, not deleted.

The last three have **no ASTRA field**. ASTRA records the final *state*; how that state
was reached is history, and history lives in the capture layer (e.g. TRACE). A
correction is therefore recorded exactly like any other rejection — the mistaken option
carries `excluded` + `excluded_reason`, and `excluded_by` names who caught it. Do not
look for a `disposition:` field; there isn't one, deliberately.

## 4. Identity conventions

The test is that *"which actor, exactly?"* stays answerable years later.

- **Humans → a `name`, a `ResearcherId`, or both** — at least one of the two. ORCID
  (orcid.org) is the recommended identity and the one that survives a change of name or
  institution, but a person is referenceable through several schemes, so `ResearcherId`
  groups ORCID with arXiv, OpenAlex, Wikidata and Google Scholar ids. When no persistent
  id is at hand, a display `name` alone is the honest minimum — requiring an ORCID to
  record anything would mean most sessions record nothing.
- **Agents → model + harness + version.** The *harness* is the software wrapper running
  the model (e.g. `claude-code`); the *version* pins the release (e.g. `2026-07`). A bare
  model name is not enough.

**Never guess an identifier.** An ORCID names a real person, so an invented one is a
false attribution to someone who exists. If you do not know a collaborator's id, record
their name; if you do not know that either, leave the actor out. A sparse honest record
beats a dense fabricated one.

## 5. CRediT mapping

Each capturable role maps to a CRediT term (credit.niso.org). Where the work has no
CRediT home, use a **flagged extension role** rather than forcing the fit.

| Contribution on a decision | CRediT term |
|---|---|
| Frames the decision — sets what is at stake | Conceptualization |
| Proposes an option / designs the method | Methodology |
| Selects or vouches for the data | Data curation |
| Writes or maintains the recipe code | Software |
| Runs the analysis, computes the result | Formal analysis |
| Checks, rules out an option, catches an error | Validation |
| Oversees the work, final sign-off | Supervision |

**Proposed extension roles** (no CRediT equivalent — flag as an extension, do not
force into a CRediT term; a human or an agent may hold any of them):

- **planner** — decomposes the task and sequences sub-analyses.
- **executor** — runs code or tools and returns results.
- **researcher** — retrieves prior work and assembles evidence/context.

The seven CRediT roles ASTRA does not use are the ones that cannot attach to a
*single decision*. Five are analysis- or paper-level (Funding acquisition, Project
administration, Resources, Visualization, Writing – original draft). The other two
sit just outside the decision: **Investigation** (data generation / collection) is
upstream of the recorded analysis and, where it bears on a choice, is covered by
Data curation; and **Writing – review & editing** attributes editing the rationale
*prose*, not the decision itself.

## 6. The accountability boundary

*A stated position, offered to be argued with.*

- **Agents may hold execution-type roles.** An agent can be the **proposer**, and the
  **executor**, of work in any role *open to it* — Methodology, Data curation, Software,
  Formal analysis, Validation, plus all three extension roles.
- **Two roles stay human, and the schema enforces it.** `conceptualization` and
  `supervision` cannot be held by an agent: validation rejects
  `{actor: <agent>, role: conceptualization}` outright. So an agent's contribution to
  framing a decision is *not recordable as `conceptualization`* — in practice it is
  recorded as `methodology` (it proposed an option) or `researcher` (it surfaced prior
  work), and the human who owns the framing carries `conceptualization`.
- **Also human, but not schema-enforced:** **final responsibility for the published
  claim**. No attribution field names a responsible party, so this one rests on the
  convention below rather than on validation.
- **The load-bearing rule:** on any decision that survives into the record, a **human
  must be the resolver**, and a **human is the named party under final responsibility**.
  An agent is never the accountable resolver of the final conclusion.

This is just Axis B (§2) pinned to one actor type: agents propose, humans resolve.

---

**Worked example.** The *Examples* section of the RFC applies every section here: the
actor registry (§4); `proposed_by` / `excluded_by` with roles (§2, §5); and the
data-leakage catch — a **corrected** choice, recorded with the ordinary `excluded`
fields and attributed to `validation` (§3, §6). Its universe half shows
`selected_by` / `reviewed_by` recording an agent's pick and the human sign-off over it.

**Glossary.** *ASTRA* — the specification and its repository. *astra.yaml* — one
analysis's decision record. *Non-normative* — guides, adds no requirements. *Actor* — any
human or agent worth attributing on a decision. *Disposition* — what happened to a
proposed option. *CRediT* — Contributor Roles Taxonomy, credit.niso.org. *ORCID* —
persistent researcher id, orcid.org.
