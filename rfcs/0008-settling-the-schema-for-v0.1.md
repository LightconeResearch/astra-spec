---
rfc: 0008
title: Settling the schema for v0.1
status: Accepted
authors:
  - Tom Charnock (@tomcharnock-lightcone)
created: 2026-11-07
tracking-issue: https://github.com/astra-project/astra-spec/issues/94
superseded-by:
---

## Context

RFCs 0003 to 0007 set out how ASTRA works: universes live in `astra.yaml`
(0003), an analysis declares and drives others (0004), every result has a
record of how it was made (0005), data comes in as inputs (0006), and a
declared analysis can come from another commit or repository (0007).

Building v0.1 on them shows a few holes worth closing before a version that
analyses will rely on:

- Inputs, outputs, universes and declarations are lists of `{id: …}`, while
  decisions, options and insights are maps. A list can repeat an id, so
  RFCs 0003 and 0004 each add a rule that ids are unique.
- A driven analysis's own universes "are considered to not exist" (RFC 0004
  §3). Reading one needs a second, undriven declaration of the same folder,
  and what a pin names depends on whether its reference goes through a
  driven declaration.
- Some fields are read by nothing, or say twice what another field says,
  some elements can't take a label or tags that their neighbours take, and a
  few fields are named differently from the same thing elsewhere.

This RFC closes those holes, and gives a few fields the names that match the
rest, so that analyses migrate once. Smaller changes in v0.1, such as its list
of rules and how the YAML file is read, aren't covered here, since they don't
change ASTRA as a model.

## Proposal

### Maps keyed by id

`inputs`, `outputs`, `universes` and `analyses` become maps keyed by id, as
`decisions`, `options` and insights already are. An entry's id is its key, not
an `id` field. A map can't repeat a key, so the uniqueness rules of RFCs 0003
and 0004 go, and every collection is written one way.

```yaml
# before
inputs:
  - {id: input1, path: data/input1.csv}
universes:
  - id: u1
    decisions: {decision1: b}

# after
inputs:
  input1: {path: data/input1.csv}
universes:
  u1:
    decisions: {decision1: b}
```

### A pin is read in the file it is written in

Under RFC 0004 a pin `#u` names the driving analysis's `u` when its reference
goes through a driven declaration, and the declared analysis's own `u`
otherwise, so the same line can mean different universes depending on what
drives the file. Now `#u` names the `universes` entry `u` of the file it is
written in or, where that file has none, the declared analysis's own universe
`u`. A pin that names neither is an error.

```yaml
# analysis/astra.yaml has a universe u1 but no v1;
# stage has universes u1 and v1 of its own
outputs:
  output2:
    inputs:
      - stage.output3#u1   # this file's u1
      - stage.output3#v1   # no v1 here: stage's own v1
```

### Imports

An entry of `universes` can instead name another analysis's own universe,
under an id of the file's choosing: `{analysis: <address>, universe: <id>}`,
where the address is a declared analysis's, such as `stage` or `stage.inner`.
It is needed where the file's own ids hide the other analysis's, or to reach a
universe of an analysis other than the one whose output is read. An import
selects and drives nothing, and what is built in it belongs to that analysis.

```yaml
universes:
  u1:
    decisions: {stage.decision2: b}
  stage_u1: {analysis: stage, universe: u1}   # stage's own u1
outputs:
  output5:
    inputs:
      - stage.output3#u1         # built in this file's u1, which drives stage
      - stage.output3#stage_u1   # built in stage's own u1
```

### One declaration both drives and reads

Together, the two changes above let one declaration do what took two. A
declared analysis that the file's universes drive can still have its own
universes read through the same declaration. Its own universes exist and must
be valid, but set none of its decisions in the universes that drive it.

```yaml
# before: a second declaration of stage's folder, to read its own universes
analyses:
  - {id: stage, path: stage}
  - {id: stage_undriven, path: stage}
outputs:
  - id: output1
    inputs: [stage.output3#u1, stage_undriven.output3#u1, stage_undriven.output3#v1]

# after
analyses:
  stage: {path: stage}
universes:
  stage_u1: {analysis: stage, universe: u1}
outputs:
  output1:
    inputs: [stage.output3#u1, stage.output3#stage_u1, stage.output3#v1]
```

### Labels everywhere, and on universes

Every `label` becomes optional, so a decision or an option no longer needs
one, as inputs, outputs and insights already don't. Universes and imports can
take one too.

```yaml
decisions:
  decision1:
    options: {a: {}, b: {}}
universes:
  u1:
    label: Fast method
    decisions: {decision1: a}
```

### Tags on more elements

Inputs, outputs, options and universes take `tags`, as analyses, decisions and
insights already do, for grouping and finding them.

```yaml
inputs:
  input1: {path: data/input1.csv, tags: [raw]}
```

### A location's page

A location could give one page two ways, `page: 8` and `value: page=8`. `page`
goes, and `value` is the one way: a fragment identifier, as in a W3C
FragmentSelector.

```yaml
location: {page: 8}         # before
location: {value: page=8}   # after
```

### The syntax of a location

An evidence `location` can say, with `conforms_to`, which fragment syntax its
`value` uses, so evidence can point into a CSV, for example, and not only a PDF.
Without it, `value` is a PDF fragment.

```yaml
evidence:
  - artifact: output2
    location:
      value: row=5-7
      conforms_to: http://tools.ietf.org/rfc/rfc7111
```

### Fields nothing reads

These fields go:

- `Evidence.snapshot` and `Evidence.source_commit`: a result's record already
  holds the commit it was made from.
- `Insight.created_at`: when a result was made is in its record, and when a
  line was written is in git.
- `Insight.derived`: an insight in `findings` already says it comes from the
  analysis.
- `Analysis.id`: since RFC 0004, a folder at a commit is an analysis's
  identity (RFC 0007 §2).
- `Evidence.id`: nothing refers to one item of an insight's evidence.

```yaml
# before
findings:
  insight1:
    claim: The two universes give different results.
    created_at: <time>
    derived: true
    evidence:
      - id: evidence1
        artifact: output2
        source_commit: <commit id>

# after
findings:
  insight1:
    claim: The two universes give different results.
    evidence:
      - artifact: output2
```

### The reason an option is excluded

`excluded` holds the reason in place of `true`, and `excluded_reason` goes. An
option with a reason is excluded. The two fields recorded one fact and could
disagree: the schema and the specification made the reason optional, but
`astra validate` required it whenever `excluded` was true, and the schema had
no way to express that condition, so a file that followed the specification
could still fail. One field holding the reason can't disagree with itself.

```yaml
# before
c: {excluded: true, excluded_reason: It needs data this analysis doesn't have.}

# after
c: {excluded: It needs data this analysis doesn't have.}
```

### Names that match

Four fields are renamed, so that one thing has one name across ASTRA:

- `Analysis.name` becomes `label`, as every other element is named, and is
  optional like every label.
- `Analysis.version` becomes `spec_version`: it is the specification's
  version, where every other `version`, such as a cited work's, is a thing's
  own.
- A record's `version` becomes `spec_version`, as in an analysis.
- `Insight.notes` becomes `description`, as every other element calls its
  free prose; a decision's `rationale` stays.

```yaml
# before
name: Example analysis
version: "0.0.14"
findings:
  insight1:
    notes: Seen in both universes.

# after
label: Example analysis
spec_version: "0.1.0"
findings:
  insight1:
    description: Seen in both universes.
```

## Implementation implications & migration

*Compatibility:* breaking. Every `astra.yaml` changes, and some pins change
meaning. Optional labels, `tags` and `conforms_to` break no file.

*Migration steps:*

- write `inputs`, `outputs`, `universes` and `analyses` as maps: `- id: x`
  with its fields becomes `x:` with the same fields
- remove `snapshot`, `source_commit` and `id` from evidence, `created_at` and
  `derived` from insights, and `id` from the analysis
- remove a location's `page`, writing `value: page=<n>` where it has no
  `value`
- replace `excluded: true` and `excluded_reason: <reason>` with
  `excluded: <reason>`, and drop `excluded: false`
- rename `name` to `label` and `version` to `spec_version` in every analysis,
  writing it with three parts (`"0.1.0"`), and `version` to `spec_version` in
  every record
- rename `notes` to `description` in every insight
- where a pin `#u` named a universe the new rule doesn't, add an import of
  that universe and pin the import's id; a second declaration kept only to
  read a driven analysis's own universes can go

## Questions or objections

## References

- RFC 0003 §1; RFC 0004 §1, §3, §4, §5; RFC 0005 §2; RFC 0006 §1; RFC 0007 §1, §2, §7.
- Tracking issue: [#94](https://github.com/astra-project/astra-spec/issues/94).
- [W3C Web Annotation](https://www.w3.org/TR/annotation-model/)
  (`FragmentSelector`, `conformsTo`), [RFC 8118](https://www.rfc-editor.org/rfc/rfc8118)
  (PDF fragments) and [RFC 7111](https://www.rfc-editor.org/rfc/rfc7111) (CSV
  fragments).
