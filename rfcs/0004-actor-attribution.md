---
rfc: 0004
title: Optional actor attribution for decisions and universe selections
status: Draft # Draft | Active | Accepted | Rejected | Superseded
authors:
  - Oliver Charles Muellerklein (@Thru-Echoes)
  - Benjamin Navet (@BenjaminNavet)
  - Martin Legrand (@Fosowl)
created: 2026-07-30
tracking-issue: https://github.com/LightconeResearch/astra-spec/issues/53
superseded-by: # RFC number, once another RFC replaces this one
---

## Context

An `astra.yaml` records *what* was decided and *why* (options, `default`,
`rationale`), and its constraint model relates options to one another with
`requires` and `incompatible_with`. A universe (`universes/*.yaml`) records one
complete selection: for each decision, which option was chosen. Neither layer
records any of the *who*: no field names who put an option on the table, who ruled
it out, who selected an option for a universe, or who reviewed that pick.

That gap matters now that agents co-author analyses. When an agent proposes an
outlier rule and a human rejects it, when a human catches a data-leakage mistake an
agent introduced, or when an agent assembles a candidate universe that a human then
signs off on, the record keeps the surviving *state* but loses the *attribution* —
precisely the information a reader needs to judge accountability and to reproduce
the reasoning.

Looking outward before inventing inward, two established standards already
cover this ground and this proposal reuses them rather than reinventing:

- **CRediT** (Contributor Roles Taxonomy, credit.niso.org) — the 14-role
  vocabulary journals already use for contribution statements.
- **ORCID** (orcid.org) — the primary persistent researcher identifier. It is
  the *default* human id, but not everyone has one and a person is referenceable
  through several schemes; the schema therefore groups ORCID with sibling
  scholarly ids (arXiv, OpenAlex, Wikidata, Google Scholar) in a small
  `ResearcherId` record rather than pinning a single `orcid` scalar.

**This does not reopen RFC-0002.** That RFC decoupled analysis *reports* from
`astra.yaml` and dropped the analysis-level `authors:` list in the process. What it
removed was **document authorship** — who wrote the analysis up — which correctly
belongs in the decoupled report. What this RFC adds is **per-decision attribution**:
a value attached to a single `Option` or `DecisionSelection`, naming who proposed or
ruled on *that* choice. It cannot live in a decoupled report, because it is part of
the decision record itself — the same reason RFC-0002 left `papers/` author metadata
untouched as out of scope.

A companion non-normative document, the **Attribution Rubric**, tells a working
scientist how to apply these fields honestly; it travels with this RFC but adds
no requirements to the schema.

## Proposal

Add an **optional, additive** actor layer spanning both places where a "who" is
meaningful — the *options* of an analysis and the *selections* of a universe.
Nothing here is required; an `astra.yaml` (and its universes) with no actor fields
stays valid and unchanged in meaning.

**1. A top-level `actors:` registry.** A map of actor id to actor record.
Humans carry an optional display `name` and a **`ResearcherId`** — a small record
grouping one or more scholarly identifiers (`orcid`, `arxiv`, `openalex`, `wikidata`,
`google_scholar`; any subset), with ORCID the default; agents are identified by
`model` + `harness` + `version` (the harness is the software wrapper running the
model). The test is that *"which actor, exactly?"* stays answerable years later —
which is precisely why a person is not pinned to a single id scheme. The same registry
serves both the analysis-level and the universe-level attribution below.

A human actor must be identifiable by **at least one** of `name` or `identifiers`, not
by `identifiers` alone. ORCID remains the recommended identity and the one that
survives a change of name or institution; a bare `name` is the honest minimum when no
persistent id is at hand. Requiring an ORCID to record anything would mean most
sessions record nothing — losing the attribution as well as the id. A display `name`
also matters because CRediT statements are rendered by name, not by registry key.
Recording nothing is always preferable to recording a guess: an ORCID names a real
person, so tooling must never infer or invent one.

*Scope of a reference.* An actor reference resolves against the nearest enclosing
`actors:` registry, then upward through ancestor analyses. A sub-analysis reached by
`path:` is a standalone `Analysis` and carries its own registry — upward resolution is
unavailable when it is validated on its own. A universe carries no registry at all:
its `selected_by` / `reviewed_by` resolve against the registry of the analysis it
selects over.

**2. One attribution value, reused everywhere.** Every attribution field takes the
same value: *either* an actor id (shorthand) *or* an object `{actor, role}` whose
`role` is drawn from the role vocabulary of §5 (a CRediT-subset term or
a flagged agent extension). No field grows a parallel `*_role` slot — the role lives
as a sub-key inside the value.

**3. Four optional fields on the `Option` object** — two carrying attribution, two
completing the exclusion record that attribution plugs into:

| Field | Value | Meaning |
|-------|-------|---------|
| `proposed_by` | actor id, or `{actor, role}` | Who put this option on the table. |
| `excluded_by` | actor id, or `{actor, role}` | Who ruled this option out. |
| `excluded_at` | date (ISO-8601 `YYYY-MM-DD`) | When it was ruled out. |
| `exclusion_rationale` | string | Why the decider found the evidence dispositive. |

Together with the **existing** `excluded` / `excluded_reason`, an exclusion becomes a
complete record: *that* it was ruled out, **what** was measured (`excluded_reason`),
**who** ruled it out, **when**, and on **what judgment**. The last two are not
attribution — they name no actor — but an exclusion attributed to a person without a
date or a stated judgment is only half a record.

`excluded_reason` and `exclusion_rationale` are deliberately distinct: the first
reports what was *observed*, the second the *judgment* that made it dispositive. An
option can be ruled out on a stated principle — "changes two variables at once, so the
effect is confounded" — while its measured numbers, on their own, looked acceptable.
Collapsing the two would flatten the evidence into the verdict and make the exclusion
unauditable.

All three of `excluded_by`, `excluded_at` and `exclusion_rationale` are only
meaningful on an option that was actually ruled out, so validation requires
`excluded: true` alongside any of them. Without that pairing a record can name who
excluded — or when — an option that is still live, a self-contradiction nothing else
would catch.

**4. Two optional attribution fields on the `DecisionSelection` object** (the
per-decision choice inside a universe):

| Field | Value | Meaning |
|-------|-------|---------|
| `selected_by` | actor id, or `{actor, role}` | Who chose this option for this universe. |
| `reviewed_by` | actor id, or `{actor, role}` | Who reviewed the selection — typically a human signing off on an agent's pick. |

To carry these on a selection without breaking existing universes, the universe
`decisions:` map accepts **either** form:

- the existing **shorthand** — `decision_id: option_id` (no attribution), or
- an **object** — the existing `option_id:` slot plus the optional `selected_by` /
  `reviewed_by` fields.

**5. A role vocabulary, constrained by actor type.** The `role` sub-key draws on a
curated subset of CRediT terms that can attach to a single decision or selection,
plus explicitly **flagged extension roles** where CRediT has no home. The vocabulary
is **one closed enum**; what varies by actor type is which of its values an actor may
hold. That constraint encodes the rubric's accountability boundary as a validation
rule rather than leaving it to guidance, and reads as two lists:

| A **human** actor may hold | An **agent** actor may hold |
|---|---|
| `conceptualization` *(human-owned)* | — |
| `methodology` | `methodology` |
| `data_curation` | `data_curation` |
| `software` | `software` |
| `formal_analysis` | `formal_analysis` |
| `validation` | `validation` |
| `supervision` *(human-owned)* | — |
| `planner` *(extension)* | `planner` *(extension)* |
| `executor` *(extension)* | `executor` *(extension)* |
| `researcher` *(extension)* | `researcher` *(extension)* |

The split has a single constraint: `conceptualization` and `supervision` are
**human-only** (a human frames the decision and signs off — and, per the boundary,
is always the *resolver*). Every other role is **open to both** actor types — the
five shared CRediT terms and all three extensions (`planner`, `executor`,
`researcher`), the last three naming work CRediT has no term for. So the agent list is
exactly the human list minus those two human-only terms. Validation MUST reject a
`{actor, role}` whose `role` is not allowed for that actor's `type` — in
practice, an agent tagged `conceptualization` or `supervision`. The full definitions
live in the rubric. The vocabulary is a single **closed enum** (resolved — see "Roles"
under *Questions or objections* below), and the two lists above are **not** two enums:
they are views on one per-role allow-table, because a slot's legal range cannot depend
on another object's `type`. The enum lives in the schema; the table is enforced by
`astra-tools`. A prototype implementation of both lives on `main` of the `Fosowl`
forks: the enum in `astra-spec` (`src/astra/schema/actor.yaml`), the table in
`astra-tools` (`src/astra/validation/semantic.py`).

**Corrections need no new structure.** A mistake that was caught and replaced is
recorded the way ASTRA already records a discarded option: the mistaken option carries
`excluded: true` + `excluded_reason`, with `excluded_by: {actor: <human>, role:
validation}` naming *who caught it*, `excluded_at` *when*, and
`exclusion_rationale` the judgment. This RFC deliberately proposes **no**
`corrections:` object, **no** revision log, and **no** new option-to-option relation
beyond the existing `requires` / `incompatible_with`.

**Why a date is state, not history.** ASTRA records final **state**; the *history* of
how that state was reached stays in the capture layer (e.g. TRACE). `excluded_at` does
not breach that line. History is a *sequence* — proposed → accepted → revised →
excluded, every transition retained; that is what TRACE keeps. `excluded_at` is a
single scalar attribute of the one exclusion that stands, and the record says nothing
about how many times the option changed hands before it did. What the date carries is
**the dating of the evidence**: an option ruled out before a later result landed was
judged on different evidence than one ruled out after. Without it a reader cannot tell
whether an exclusion is still well-founded given what was learned since — which makes
it a property of the conclusion's warrant, not a log entry. Day granularity is
deliberate for the same reason: enough to date the evidence, not enough to invite
reconstructing a timeline.

Plain-language summary: *let an analysis optionally say who proposed and who
excluded each option — and, for an exclusion, when and on what judgment — and let a
universe optionally say who selected and who reviewed each choice, with, if wanted,
the role of each contribution (a CRediT term or a flagged agent extension), without
changing anything about how decisions or selections themselves are recorded.*

## Examples

**Analysis level** — the registry plus attributions that exercise all three role
classes: a human *framing* a decision (`conceptualization`, human-only), an agent
*proposing* an option it retrieved (`researcher`, an extension open to both), and a
rejected proposal the human ruled out (`methodology` / `validation`, shared). Each
attribution is a single `{actor, role}` value:

```yaml
actors:                              # NEW top-level key (optional)
  jane:
    type: human
    name: "Jane Doe"                 # NEW: display name — what a CRediT statement shows
    identifiers:                     # NEW: ResearcherId — grouped scholarly ids, not a lone orcid
      orcid: "0009-0000-0000-0000"   # any subset; `name` alone is also valid
  assistant:
    type: agent
    name: "Claude Opus 5 (claude-code)"   # NEW
    model: claude-opus-5
    harness: claude-code
    version: "2026-07"

decisions:
  outlier_handling:
    label: "Outlier handling"
    rationale: "Whether flagged extreme rows stay in the training data."
    default: keep_all
    options:
      keep_all:
        label: "Keep all 150 rows"
        proposed_by: {actor: jane, role: conceptualization}  # NEW: human-only role — framing the "trust the curated data" stance
      drop_iqr:
        label: "Drop the 12 rows flagged by the 1.5 IQR rule"
        proposed_by: {actor: assistant, role: methodology}         # NEW
        excluded: true                                         # existing field
        excluded_reason: >-                                    # existing field
          The rows are real biological variation, not measurement error.
        excluded_by: {actor: jane, role: validation}     # NEW
  model:
    label: "Classifier"
    default: random_forest
    options:
      random_forest:
        label: "Random forest"
        proposed_by: {actor: jane, role: methodology}    # NEW
      svm:
        label: "SVM (RBF kernel)"
        proposed_by: {actor: assistant, role: researcher}          # NEW: `researcher` extension (open to both) — agent surfaced it from prior Iris baselines
```

The shorthand stays valid for anyone who does not want roles:

```yaml
        proposed_by: assistant  # bare actor id — the origin form, still accepted
```

A **corrected mistake** with no new machinery — the data-leakage catch is just an
excluded option whose exclusion is attributed to a `validation` contribution:

```yaml
  scaling:
    label: "Feature scaling"
    default: standard_after_split
    options:
      standard_after_split:
        label: "StandardScaler, fit on the training split only"
        proposed_by: {actor: jane, role: methodology}    # NEW
      standard_before_split:
        label: "StandardScaler, fit on the FULL dataset before the split"
        proposed_by: {actor: assistant, role: methodology}   # NEW
        excluded: true                                       # existing field
        excluded_reason: >-                                  # existing field — what was OBSERVED
          Held-out accuracy fell from 0.97 to 0.94 after refitting the scaler
          on the training split alone.
        excluded_by: {actor: jane, role: validation}         # NEW — who caught it
        excluded_at: 2026-07-28                              # NEW — when
        exclusion_rationale: >-                              # NEW — the JUDGMENT
          Data leakage. Fitting before the train/test split let test-set
          statistics contaminate the training features, so the higher number was
          never a real gain — the option is unusable regardless of how it scores.
```

That block is why `excluded_reason` and `exclusion_rationale` are separate slots.
Read alone, the observation says the option scored *better* (0.97 vs 0.94); it is the
judgment that explains why the better number is the disqualifying one. Flattened into
a single field, a later reader sees an option discarded for outperforming its
replacement.

**Universe level** — a selection where an agent picked the model and a human
signed off, alongside a plain-shorthand selection that carries no attribution.
The `{actor, role}` value and the `actors:` registry are the same as above:

```yaml
id: baseline
description: Default configuration using standard practices.
decisions:
  scaling:                                              # object form (NEW)
    option_id: standard_after_split
    selected_by: {actor: jane, role: methodology} # NEW
  model:
    option_id: random_forest
    selected_by: {actor: assistant, role: methodology}      # NEW: the agent proposed the pick ...
    reviewed_by: {actor: jane, role: validation}  # NEW: ... and a human signed off
  outlier_handling: keep_all                            # shorthand still valid (no attribution)
```

Before/after for a reader: today the option blocks lose *who proposed* / *who
excluded* and the universe selections are bare `decision: option`; after, those
facts (and their roles) are recoverable, every other field is byte-for-byte
unchanged, and any selection can keep the untouched shorthand.

Every `role` above is legal for its actor's `type` — `agent` with `methodology`,
`researcher` with `validation`, and so on. The type split is what makes the
following *invalid*, caught by validation rather than by convention:

```yaml
proposed_by: {actor: assistant, role: conceptualization}  # REJECTED — conceptualization is human-only
reviewed_by: {actor: assistant, role: supervision}         # REJECTED — supervision is human-only
proposed_by: {actor: assistant, role: executor}            # OK — executor is open to both types
```

## Implementation implications & migration

- **`src/astra/schema/`** (LinkML, schema id `https://w3id.org/astra/analysis`):
  add an optional `actors` map to the `Analysis` class; add an `Actor` class (with
  `human` / `agent` variants, expressed via `type`-keyed validation rules rather
  than subclassing) and a small `Attribution` class `{actor, role}` — both live in a
  **new `actor.yaml` module** imported by `analysis.yaml` *and* `universe.yaml`,
  because `Attribution` is shared by `Option` and `DecisionSelection` and
  `universe.yaml` cannot import `analysis.yaml` without a cycle (see “Concrete schema
  changes (per file)” below) —
  `{actor, role}` stays the shape used at every attribution point; the change below
  is only *which* `role` values are legal.
  - The `human` variant carries a `ResearcherId` class (slots `orcid`, `arxiv`,
    `openalex`, `wikidata`, `google_scholar` — each optional, with a rule requiring
    at least one) instead of a bare `orcid` scalar; the `agent` variant keeps
    `model` + `harness` + `version`. Each id slot may pin its own `pattern` — note
    that the ORCID pattern checks the *shape* only (`0000-0000-0000-000X`); the
    ISO 7064 MOD 11-2 check digit is not expressible as a regex, so verifying it is
    astra-tools' job if it is wanted at all.
  - On the `Option` class, add optional slots `proposed_by` and `excluded_by`, each
    with range `union(string, Attribution)` (the string is the actor-id shorthand),
    plus `excluded_at` (`range: date`) and `exclusion_rationale` (a string) completing
    the exclusion record alongside the existing `excluded` / `excluded_reason`.
  - On the `DecisionSelection` class, add optional slots `selected_by` and
    `reviewed_by` with the same `union(string, Attribution)` range, and change **both**
    universe `decisions` slots — on `Universe` and on `UniverseNode` — to a union that
    accepts a scalar `option_id` (shorthand) or a `DecisionSelection` object.
  - **No parallel `*_role` slots** anywhere — the role lives inside the value.
  - Define **one** closed role enum, `Role`, holding all ten terms. The type split is
    *not* expressed in LinkML: a slot's legal range cannot depend on another object's
    `type`, so `Attribution.role` simply ranges over `Role`. astra-tools then validates
    the pair against a single per-role allow-table — `conceptualization` and
    `supervision` allow `human` only; every other role — the five shared CRediT terms
    plus all three extensions (`planner`, `executor`, `researcher`) — allows both.
    Two enums would express no constraint that one does not, since the agent list is a
    strict subset of the human list.
  - A **prototype implementation** of the role vocabulary — a closed `Role` enum, a
    single `ROLE_ALLOWED_TYPES` table as the one source of truth (both per-type lists
    and every exclusion are *derived* from it), and consistency guardrails as
    tests — lives on `main` of the `Fosowl` forks
    (`astra-tools`, `src/astra/validation/semantic.py`). It is the normative
    shape for the astra-tools side: deriving the two per-type lists from one table,
    rather than hand-maintaining them, is what stops them from drifting apart.
- **Generated datamodels**: regenerate from the schema; all new slots optional.
  Tooling must parse both universe forms (scalar shorthand and object). Two changes
  are load-bearing, both verified against astra-tools 0.2.11:
  1. The map key must be injected as `decision_id` when a selection uses the object
     form. The generated model already does this for the compact form; without it,
     `DecisionSelection(option_id=...)` fails because the identifier is absent.
  2. `_validate_universe_node` in `astra/validation/semantic.py` assumes the map value
     is a scalar option id and raises `TypeError: unhashable type: 'dict'` on the
     object form — an unhandled traceback, not a validation error. It must normalize
     the value shape before its membership checks.
- **`astra-tools` / validation**: accept both the scalar and object forms; validate
  that the actor id (scalar, or the object's `actor`) references an id in `actors:`,
  and that any `role` is legal for that actor's `type` — looked up in the per-role
  allow-table, which admits `conceptualization` and `supervision` for humans only.
  Two further checks the schema states but cannot enforce: a human actor carries at
  least one of `name` or `identifiers` (and, if `identifiers` is present, at least one
  id within it); and `excluded_by`, `excluded_at` and `exclusion_rationale` each appear
  only on an option that also carries `excluded: true`. Both are expressed here rather
  than in LinkML — the first is a disjunction, the second a boolean equality this schema
  has no idiom for. Absence of any actor field is valid.
- **Reserved ids**: `actors` joins the reserved set in the shared id pattern, beside
  `inputs` / `outputs` / `decisions` / `findings` / `prior_insights` / `analyses` /
  `options` / `content`, so no entity can shadow the new top-level category. This
  edits the one pattern applied to every entity id — `Input`, `Output`, `Option`,
  `Decision`, `Analysis`, `Insight`, `Evidence` — and to `Actor.id` itself.
- **Docs**: add the actor fields to the Option, Analysis, and DecisionSelection
  field references; ship the Attribution Rubric as non-normative guidance.
- **Compatibility & bump**: backward compatible — every existing `astra.yaml` and
  universe file remains valid and unchanged in meaning, and no existing field
  changes shape (the universe `decisions` slot *gains* an accepted object form
  without dropping the scalar). Under the versioning policy this is a **minor** bump
  *provided* the union is implemented; requiring the object form instead would make
  it a **major** bump, which the union is designed to avoid. No migration is required.

### Concrete schema changes (per file)

The exact LinkML for the bullets above. The actor layer lives in its **own module**
(`actor.yaml`) because `Attribution` is used by both `Option` (`analysis.yaml`) and
`DecisionSelection` (`universe.yaml`), and `universe.yaml` cannot import
`analysis.yaml` without a cycle — `analysis` already imports `universe`. Resulting
import DAG: `actor ← universe ← analysis` and `actor ← analysis`.

`Actor` is one flat class rather than two subclasses: a `type`-keyed rule pair
enforces "if `human` then `identifiers`, no `model`/`harness`/`version`; if `agent`
then `model`, no `identifiers`." `Attribution.role` ranges over the single closed
`Role` enum; which of its values are legal depends on another object (the referenced
actor's `type`), which no `range` can express, so that narrowing is left to
`astra-tools`.

**New `actor.yaml`** (`https://w3id.org/astra/actor`):

```yaml
id: https://w3id.org/astra/actor
name: actor
description: |-
  Contributors — human researchers and software agents — and the roles
  they hold on a decision or a universe selection.
license: https://creativecommons.org/licenses/by/4.0/
# Placeholder version. The real version is injected at build time from the
# latest git tag (or RELEASE_VERSION) — see `_stage-versioned` in the justfile.
version: 0.0.0

prefixes:
  astra: https://w3id.org/astra/
  linkml: https://w3id.org/linkml/
default_prefix: astra
default_range: string

imports:
  - linkml:types

enums:
  ActorType:
    description: Whether a contributor is a human researcher or a software agent
    permissible_values:
      human: {description: A human researcher}
      agent: {description: A software agent (a model running inside a harness)}

  Role:
    description: >-
      Contribution roles that can attach to a single decision or selection —
      a CRediT subset plus three flagged extensions. Which values a given actor
      may hold depends on its type; astra-tools enforces that (see Attribution.role).
    permissible_values:
      conceptualization:
        description: Frames the decision, sets what is at stake — human-only
      methodology:
        description: Proposes an option or designs the method
      data_curation:
        description: Selects or vouches for the data
      software:
        description: Writes or maintains the recipe code
      formal_analysis:
        description: Runs the analysis, computes the result
      validation:
        description: Checks, rules out an option, catches an error
      supervision:
        description: Oversees the work, final sign-off — human-only
      planner:
        description: Extension — decomposes the task and sequences sub-analyses
      executor:
        description: Extension — runs code or tools, returns results
      researcher:
        description: Extension — retrieves prior work, assembles context

classes:
  ResearcherId:
    description: >-
      One or more scholarly identifiers for a human actor. If the record is
      present at all, at least one id is present; ORCID is the default. An actor
      may instead be identified by `name` alone — see Actor's rules.
    attributes:
      orcid:
        pattern: "^\\d{4}-\\d{4}-\\d{4}-\\d{3}[0-9X]$"
        description: ORCID iD (https://orcid.org)
      arxiv:          {description: arXiv author id (https://arxiv.org/a)}
      openalex:       {description: OpenAlex id (https://openalex.org)}
      wikidata:       {description: Wikidata entity id}
      google_scholar: {description: Google Scholar profile id}
    any_of:   # at least one identifier present. DOCUMENTATION ONLY — a
              # class-level boolean expression does not survive into the
              # generated datamodel, so astra-tools enforces this (see
              # validation below). Nor can `rules:` express it: "at least
              # one of five" is a disjunction, not a precondition rule.
      - slot_conditions: {orcid:          {value_presence: PRESENT}}
      - slot_conditions: {arxiv:          {value_presence: PRESENT}}
      - slot_conditions: {openalex:       {value_presence: PRESENT}}
      - slot_conditions: {wikidata:       {value_presence: PRESENT}}
      - slot_conditions: {google_scholar: {value_presence: PRESENT}}

  Actor:
    description: A contributor — a human researcher or a software agent. Keyed by id in the actors registry
    attributes:
      id:
        identifier: true
        pattern: "^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|actors)$)[a-z][a-z0-9_]*$"
        description: Unique identifier (the key in the actors map)
      type:
        range: ActorType
        required: true
      name:
        description: >-
          Human-readable display name — "Jane Doe", or an agent's presentation
          name. What a rendered CRediT statement shows instead of the registry key.
      description:
        description: Free-prose description of this actor
      identifiers:
        range: ResearcherId
        inlined: true
        description: Scholarly identifiers (human actors)
      model:   {description: Model name and version, e.g. claude-opus-5 (agent actors)}
      harness: {description: Software wrapper running the model, e.g. claude-code (agent actors)}
      version: {description: Version or date stamp of the agent configuration (agent actors)}
    rules:
      - title: human_carries_identity_not_agent_fields
        preconditions:  {slot_conditions: {type: {equals_string: human}}}
        postconditions:
          any_of:   # at least one of name / identifiers. DOCUMENTATION ONLY,
                    # as in ResearcherId above — astra-tools enforces it.
            - slot_conditions: {name:        {value_presence: PRESENT}}
            - slot_conditions: {identifiers: {value_presence: PRESENT}}
          slot_conditions:
            model:   {value_presence: ABSENT}
            harness: {value_presence: ABSENT}
            version: {value_presence: ABSENT}
      - title: agent_carries_model_not_identifiers
        preconditions:  {slot_conditions: {type: {equals_string: agent}}}
        postconditions:
          slot_conditions:
            model:       {required: true}
            identifiers: {value_presence: ABSENT}

  Attribution:
    description: >-
      An actor together with the role they played. The shorthand form of an
      attribution slot is a bare actor id instead of this object.
    attributes:
      actor:
        required: true
        description: Actor id (a key in the analysis `actors` registry)
      role:
        range: Role
        description: >-
          Contribution role. astra-tools rejects a role not allowed for the
          referenced actor's type — conceptualization and supervision are
          human-only — because a `range` alone cannot express a dependency
          on another object's field.
```

**`analysis.yaml`** — add `- actor` to `imports`; add to `Analysis.attributes`:

```yaml
actors:
  range: Actor
  multivalued: true
  inlined: true
  description: Registry of contributors (humans and agents), keyed by actor id.
```

and to `Option.attributes` (alongside the **existing** `excluded` / `excluded_reason`):

```yaml
proposed_by:
  description: Who put this option on the table — an actor id, or an {actor, role} object.
  any_of: [{range: string}, {range: Attribution}]
  inlined: true
excluded_by:
  description: Who ruled this option out — an actor id, or an {actor, role} object. Pairs with the existing excluded / excluded_reason.
  any_of: [{range: string}, {range: Attribution}]
  inlined: true
excluded_at:
  range: date
  description: >-
    Calendar date on which the option was ruled out (ISO-8601, YYYY-MM-DD).
    Completes the exclusion record: excluded_by says who, excluded_at says when.
    Ordering matters when reading a decision space back — an option ruled out
    before a later result landed was judged on different evidence than one ruled
    out after. Only legal on an option marked excluded.
exclusion_rationale:
  description: >-
    Why the decider found the evidence dispositive — the judgment, as distinct
    from excluded_reason, which records what was measured or observed. An option
    can be excluded on a stated principle ("changes two variables at once, so the
    effect is confounded") while its excluded_reason reports numbers that on their
    own looked acceptable. Separating the two keeps the evidence auditable without
    flattening it into the judgment. Only legal on an option marked excluded.
```

`excluded_at` takes `range: date` rather than `datetime`: day granularity is enough to
date the evidence an exclusion rested on, and a timestamp would invite reconstructing a
chronology — which is history, and belongs in the capture layer.

No `rules:` block is added to `Option`. The pairing — `excluded_by`, `excluded_at` and
`exclusion_rationale` are each legal only on an option carrying `excluded: true` — is
checked by astra-tools instead: `excluded` is a boolean, and this schema has no
established idiom for asserting a boolean's *value* in a postcondition, its existing
rules all asserting presence or absence.

**`universe.yaml`** — add `- actor` to `imports`; add to `DecisionSelection.attributes`:

```yaml
selected_by:
  description: Who chose this option for this universe — an actor id, or an {actor, role} object.
  any_of: [{range: string}, {range: Attribution}]
  inlined: true
reviewed_by:
  description: Who reviewed the selection — an actor id, or an {actor, role} object.
  any_of: [{range: string}, {range: Attribution}]
  inlined: true
```

The same union applies to **`UniverseNode.decisions`**, not only `Universe.decisions`:
both carry `range: DecisionSelection, multivalued: true, inlined: true`, and
`UniverseNode` is how a universe records selections for **sub-analyses**. Patching only
the root slot would leave attribution silently unavailable one level down.

Keeping the `decision_id: option_id` shorthand once `DecisionSelection` carries more
than one non-identifier slot is exactly the "Union vs. required object" open question
below: LinkML's compact inlined-dict form assumes a single non-identifier slot, so the
shorthand is preserved by making the universe `decisions` slot a
`union(string, DecisionSelection)` rather than relying on compact-dict behaviour.

The object form's value slot keeps its existing name, **`option_id`**. Renaming it to
`option` would change the shape of a shipped, required slot on `DecisionSelection`,
breaking every universe file — which would contradict this RFC's own backward-
compatibility claim and turn a minor bump into a major one. The name is therefore
fixed by the compatibility argument, not chosen by taste.

**`insight.yaml`** — unchanged.

## Questions or objections

- **Union vs. required object for universe selections.** Keeping the scalar
  shorthand avoids churn in every existing universe, but two shapes for one field
  cost tooling complexity. Worth it? *(Resolved — **keep the union**. Requiring the
  object form would rewrite every existing universe file and make this a major bump,
  which the union exists to avoid. The tooling cost is real but bounded and now
  measured: against astra-tools 0.2.11 the object form fails in exactly two places —
  the generated model rejects a `DecisionSelection` whose `decision_id` was not
  injected from the map key, and `_validate_universe_node` raises
  `TypeError: unhashable type: 'dict'` because it assumes a scalar value. Both are
  named under "Generated datamodels" above.)*
- **Does `reviewed_by` presuppose an agent `selected_by`?** Human review is most
  meaningful over an agent's pick, but a human reviewing another human's pick is
  also valid. Should the schema constrain this, or leave it to the rubric? *(Open.)*
- **Roles: closed enum or free string?** A closed CRediT-subset enum is safer for
  tooling; a free string is more flexible for domains with unusual contributions.
  *(Resolved — **closed enum**. Validation rejects any role outside the referenced
  actor-type's list. A prototype implementation — closed `Role` enum,
  a single `ROLE_ALLOWED_TYPES` table from which both per-type lists and all
  exclusions are derived, and consistency guardrails as tests — lives on `main` of
  the `Fosowl` forks.)*
- **`ResearcherId`: named slots or a scheme/value list?** Named slots (`orcid`,
  `arxiv`, `openalex`, `wikidata`, `google_scholar`) are self-documenting and let each id carry its own
  validation `pattern`, but adding a new scheme means a schema edit. A generic
  `identifiers: [{scheme, value}]` list (scheme drawn from an enum) is open-ended
  and linked-data-native, at the cost of weaker per-scheme validation. The RFC
  currently proposes named slots. *(Open.)*
- **Extension roles in-spec or rubric-only?** `planner` / `executor` / `researcher`
  have no CRediT equivalent. *(Resolved — in-spec: enumerated as extension roles and
  open to both actor types; the two role lists are closed enums, per "Roles" above.)*
- **How does the `actors:` registry get populated?** The agent half is automatic — a
  harness knows its own `model`, `harness`, and `version` and can fill its entry with
  no user involvement. The human half cannot be inferred, and reciting an ORCID
  mid-session is unnatural, so this is where the actor layer either gets adopted or
  gets skipped. Two mechanisms, not exclusive:
  1. **A user-level config.** `astra config set actor.name / actor.orcid …`, written
     once and copied into the registry at authoring time. This is git's model: the
     commit embeds name and email permanently rather than referencing `~/.gitconfig`,
     which is why the record stays self-contained and readable years later. The
     registry must stay in the `astra.yaml` for exactly that reason — a record that
     points at a machine-local file fails the *"which actor, exactly?"* test the moment
     someone else clones it.
  2. **Validation as a prompt for the next turn.** When an actor entry is missing its
     identity, `astra validate` emits an error naming the missing field and stating
     that the value must be **asked of the user**, not invented. An agent that runs
     validation as a hook then has an actionable instruction on its next turn. This
     suits ASTRA's agent-facing design — `astra spec` already exists to be
     agent-consumable — and it keeps the human in the loop precisely where the record
     needs a human fact.
  Whichever is chosen, tooling must never infer or invent an identifier: an ORCID names
  a real person, and a guessed one is a false attribution. Deliberately **not specified
  here** — this is tooling, not schema, and astra-tools has no config surface today.
  *(Open.)*
- **Accountability boundary.** The rubric holds that agents may *propose* and
  *execute* any role but a human must be the *resolver* and hold final
  responsibility. *(Partly resolved — the schema now enforces the one hard type
  constraint: `conceptualization` and `supervision` are human-only. Still open, and
  left to the rubric: the "resolver is human" rule itself, which the `{actor, role}`
  shape does not encode — no attribution field currently names a resolver.)*

## Appendix — CRediT coverage

ASTRA's role vocabulary (Proposal §5) is a deliberate *subset* of CRediT: it keeps
only the terms that attach to a **single decision**, and adds three extension roles
for work CRediT has no term for. This table records the full mapping so the subset is
auditable — including the roles intentionally left out. "May be held by" repeats the
actor-type split from §5.

| CRediT role | In ASTRA? | ASTRA `role` | May be held by | Kept / not — why |
|---|:--:|---|---|---|
| Conceptualization | ✓ | `conceptualization` | human | frames the decision — human-owned |
| Data curation | ✓ | `data_curation` | human, agent | selects or vouches for the data |
| Formal analysis | ✓ | `formal_analysis` | human, agent | runs the analysis, computes the result |
| Funding acquisition | — | — | — | analysis-level; never attaches to a single decision |
| Investigation | — | — | — | data generation/collection is upstream; at decision level it collapses into `data_curation` |
| Methodology | ✓ | `methodology` | human, agent | proposes an option / designs the method |
| Project administration | — | — | — | analysis-level coordination, not a decision |
| Resources | — | — | — | provisioning compute/materials, not a decision |
| Software | ✓ | `software` | human, agent | writes or maintains the recipe code |
| Supervision | ✓ | `supervision` | human | oversees the work, final sign-off — human-owned |
| Validation | ✓ | `validation` | human, agent | checks, rules out an option, catches an error |
| Visualization | — | — | — | output-level, not a decision |
| Writing – original draft | — | — | — | paper-level, not a decision |
| Writing – review & editing | — | — | — | edits the rationale prose, not the decision itself |

Three **extension roles** have no CRediT term (flagged as extensions); all three are
open to both actor types:

| ASTRA `role` | May be held by | Meaning |
|---|---|---|
| `planner` | human, agent | decomposes the task, sequences sub-analyses |
| `executor` | human, agent | runs code or tools, returns results |
| `researcher` | human, agent | retrieves prior work, assembles evidence / context |

**Coverage: 7 of CRediT's 14 roles are used** (2 human-only, 5 shared), plus 3
extension roles, all open to both actor types. The other 7 CRediT roles do not attach
to a single decision and are intentionally not used. The rubric's §5 mapping now uses
the same 7-role subset.

## References

- CRediT — Contributor Roles Taxonomy, https://credit.niso.org
- ORCID — https://orcid.org
- Sibling researcher identifiers grouped by `ResearcherId` — arXiv author id
  (https://arxiv.org/a), OpenAlex (https://openalex.org), Wikidata (https://www.wikidata.org),
  Google Scholar profiles (https://scholar.google.com/citations)
- The Attribution Rubric (`attribution_rubric_draft.md`) — non-normative companion
- Worked example (`demo/astra-proposed-full.yaml`) and the current-schema baseline
  (`demo/astra.yaml`), a before/after pair on the same Iris analysis
- ASTRA `Option`, `Universe`, and `DecisionSelection` field references
- TRACE — the decision-capture layer that retains correction/revision history
