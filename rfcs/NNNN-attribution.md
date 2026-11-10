---
rfc: NNNN
title: Attribution
status: Draft
authors:
  - Tom Charnock (@tomcharnock-lightcone)
  - Oliver Charles Muellerklein (@Thru-Echoes)
  - Benjamin Navet (@BenjaminNavet)
  - Martin Legrand (@Fosowl)
created: 2026-11-10
tracking-issue: https://github.com/LightconeResearch/astra-spec/issues/53
superseded-by:
---

## Context

An `astra.yaml` says what was chosen and why - an option's `excluded` reason, a decision's `rationale`, the prior insights an option cites - but not who chose it. With software agents writing analyses alongside people, a reader can't tell an option a person put forward from one an agent did, or who ruled an option out, signed off a universe or stands behind a finding. git doesn't say either. It records who wrote a line and not who proposed or ruled on what the line says - a person writing up an option their agent suggested is the line's author.

[#53](https://github.com/LightconeResearch/astra-spec/issues/53) and its draft [#56](https://github.com/LightconeResearch/astra-spec/pull/56) proposed attributing options and universe selections. This RFC takes that idea onto the v0.1 schema and keeps it small. It attributes single choices and claims.

## Proposal

An analysis can say who proposed and who reviewed each of its decisions, options, universes and insights, naming people and the agents working for them.

- **People**: `people`, a map keyed by id. A person has an optional `label` and an optional `orcid`, written bare as a `doi` is, such as `0000-0002-1825-0097`.
- **Agents**: `agents`, a map keyed by id. An agent has
  - `on_behalf_of`, the id of the one person it works for (required)
  - `model`, as its provider names it (required)
  - `harness`, the software running the model, as `{id, version}` like a record's `runner`
  - an optional `label` and `description`

  When its model or harness version changes an agent gets a new entry - what it did before keeps naming what it was then.
- **Attribution**: `proposed_by` and `reviewed_by`, optional lists of ids of people or agents, on decisions, options, universes and insights.
  - `proposed_by` is who put it forward. For a prior insight that's who took it from its source, not the source's authors
  - `reviewed_by` is who ruled on it: on an excluded option who excluded it, on an option that isn't who accepted it, on a decision, universe or insight who signed it off
  - on a universe they attribute the whole universe, not each selection. Like everything but the selection they aren't inherited through `derived_from`. An import has neither
- **Results**: attribution never makes a result stale since none of its fields is something a result is made from.
- **Rules**:
  - `AMBIGUOUS_ID` (MUST, validator) gains: no person and agent of one analysis share an id
  - new, `UNKNOWN_ATTRIBUTION` (MUST, validator): every id in `proposed_by` and `reviewed_by` names a person or agent of its analysis and every `on_behalf_of` names a person
  - the schema rows gain
    - `MISSING_FIELD`: an agent's `on_behalf_of` and `model`, a harness's `id` and `version`
    - `INVALID_VALUE`: the form of `orcid`
    - `INVALID_IMPORT`: attribution on an import
  - lists of ids are non-empty and hold no id twice, as every list of strings is

## Examples

```yaml
people:
  author: {orcid: 0000-0000-0000-0000}
agents:
  agent:
    on_behalf_of: author
    model: example-model-1
    harness: {id: example-harness, version: 0.0.0}
decisions:
  decision1:
    proposed_by: [agent]
    reviewed_by: [author]
    options:
      method1: {proposed_by: [author]}
      method2: {proposed_by: [agent]}
      method3:
        proposed_by: [agent]
        reviewed_by: [author]
        excluded: It needs data this analysis doesn't have.
universes:
  u1:
    proposed_by: [author]
    decisions: {decision1: method1}
  u2:
    proposed_by: [agent]
    reviewed_by: [author]
    derived_from: u1
    decisions: {decision1: method2}
findings:
  finding1:
    claim: method2 gives a higher output1 than method1.
    evidence: [{artifact: output1#u1}, {artifact: output1#u2}]
    proposed_by: [agent, author]
    reviewed_by: [author]
```

The agent raised `decision1` and proposed `method2` and `method3`. The author excluded `method3`, signed off the agent's universe `u2` and stands behind `finding1` with the agent. Without any of these fields the file means what it did before.

## Implementation implications & migration

- Compatibility: additive. Every field is optional and no file changes.
- Depends on: *Settling the schema for v0.1* (maps keyed by id, `excluded` holding its reason, the rules table).
- Schema: classes `Person`, `Agent` and `Harness`, with `people` and `agents` on `Analysis`. `proposed_by` and `reviewed_by` (multivalued `id`s) on `Decision`, `Option`, `Universe` and `Insight`, with one `INVALID_IMPORT` rule each. `orcid` has the pattern `^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$`. `Person`, `Agent` and `on_behalf_of` map to PROV-O's `prov:Person`, `prov:SoftwareAgent` and `prov:actedOnBehalfOf`.
- Tooling: filling in `people` and `agents` is left to tools - from a person's own settings and from an agent's harness, say.
- Migration: none.

## Differences from #53

- One pair of fields, `proposed_by` and `reviewed_by`, on decisions, options, universes and insights, in place of `proposed_by` and `excluded_by` on options and `selected_by` and `reviewed_by` on selections. `reviewed_by` on an excluded option is who excluded it.
- Lists of ids in place of an id or `{actor, role}` - several people and agents can contribute. No roles: the field already says what was done and a `role` can be added later.
- The whole universe in place of each selection, keeping `<decision>: <option>`. An object form beside it can be added later.
- `people` and `agents` in place of one `actors` map with a `type` - no rule depends on a type. Merging the two later would break files.
- Only `orcid`, written bare as a `doi` is, in place of five schemes - it lasts, as a DOI does. Other schemes can be added later as fields but writing ORCID as a URL would break files.
- `on_behalf_of`, one person, in place of roles only people can hold: every agent leads back to a person who answers for it. A list would break files.
- No `excluded_at` (git has the time) and no second exclusion text (`excluded` holds the reason). Either can be added later.

## Questions or objections

## References

[#53](https://github.com/LightconeResearch/astra-spec/issues/53), [#56](https://github.com/LightconeResearch/astra-spec/pull/56); [ORCID](https://orcid.org); [CRediT](https://credit.niso.org); [W3C PROV-O](https://www.w3.org/TR/prov-o/); RFC 0002, RFC 0004, RFC 0005, RFC 0007.
