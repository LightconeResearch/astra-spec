---
rfc: NNNN
title: Switches in place of conditions
status: Draft
authors:
  - Tom Charnock (@tomcharnock-lightcone)
created: 2026-11-11
tracking-issue: https://github.com/LightconeResearch/astra-spec/issues/87
superseded-by:
---

## Context

`when` switches a decision or an output off in some universes. #87 found three places where the specification doesn't say what follows: a recipe that uses a decision switched off where its output is built, an output that reads an output switched off, and a condition or a constraint that tests a decision switched off. The draft *Using conditional elements* closed them by making whatever uses a switched-off element carry its `when`, so a condition spreads to every reader. This RFC, #93's outcome, replaces that draft. A reader chooses what it reads by a decision instead, and a decision needs an option only where something uses it.

## Proposal

- **`when` goes**: `Decision.when`, `Output.when` and the condition grammar. With them go `when` as a reason an output is built per universe (RFC 0003 §2) and the rules on switched-off elements: a universe setting a decision whose `when` fails, and an output read without a pin where it is switched off (RFC 0003 *What validators check*, RFC 0004's row on reads in the universe being built). `requires`, `incompatible_with` and `excluded` stay.
- **A switch** is an entry of `outputs` with a `switch`, a decision's address, and `cases`, from options of that decision to references: each names an input, an output or a switch, of the analysis or by address, pinned or not. It may have a `label`, a `description` and `tags`, and has no `type`, `format`, `inputs`, `decisions` or `recipe` (a new schema error, `INVALID_SWITCH`). It makes nothing: it has no result, record, name or place of its own. Every case counts, taken or not: its key is an option of the decision (`UNKNOWN_OPTION`), its reference resolves (`UNRESOLVED_ADDRESS`), and no output reads itself through `inputs` and `cases` (`OUTPUT_CYCLE`).
- **Taking.** In each universe a switch takes the case of the option its decision selects there, and reading it reads what that case names: `{inputs.s}` is the path of the input or result the case gives there. A pinned case is read in its pin's universe, and `s#u1` reads the switch as it is in `u1`. Options may share a case, and a case on an excluded option is never taken. Where the option selected has no case, the switch isn't built, nor is anything that reads it without a pin. There is no default case and no switch on several decisions: a case that names a switch nests the two, and by convention the switch on the decision that decides whether the other matters is the outer one.
- **Built.** An output other than a switch is built in a universe if everything it reads there without a pin is an input, an output built once, or built there; a switch is built there if its decision selects there an option with a case that names one of these or, pinned, something built in its pin's universe. Not being built passes to whatever reads it without a pin, and is no error. Whether an output is built never depends on driving. An output that reads a switch without a pin is built per universe; a switch itself is neither built per universe nor built once.
- **Planned** amends *Planned results*: the driving analysis plans from its own outputs other than switches that no case of its own names, its own switches that no `inputs` entry or case of its own names, and what its evidence cites. It plans their results where they are built, a switch's being those of the case it takes, and every result a planned result reads, through the case each switch takes. An output that a case names is so planned, as another analysis's output is, only where something planned reads it: one that is also a deliverable must be read or cited elsewhere to be built where that case isn't taken.
- **Reached.** The driving analysis reaches what it plans from, built or not: an output built once, and evidence citing one, once; other pinned evidence in its pin's universe; anything else in each of its universes. It reaches too whatever something reached reads, there or, pinned, in its pin's universe: each entry of an output, and only the case a switch takes.
- **Used.** A universe uses, with its own analysis as the driving analysis, each decision that a result planned in it lists or a switch reached in it switches on. It uses on some branch each decision listed or switched on by what its analysis would reach in it were every case of every switch followed, and each decision that a universe inheriting its key for it, without setting it, uses on some branch. Both are judged per decision, however its address is spelled.
- **What a universe sets** amends RFC 0003 §1 and *Driving, defined once*: an effective selection sets every decision its universe uses, of its analysis and of those its universes drive, and drops nothing it inherits. A universe's own key for a decision it doesn't use on any branch is an error (`UNUSED_DECISION`); for one it uses on some branch but doesn't use, a warning (`INACTIVE_DECISION`). Neither judges an inherited key. An analysis with no decisions of its own, or none that a universe of the driving analysis uses, has nothing to set, so a chain is driven through it without a key.
- **Constraints** are judged among the decisions **in play** in a universe: those it uses and, in a universe of an analysis other than the driving analysis, those that something reached through a pin uses there. A decision not in play counts as selecting nothing: a `requires` naming it fails, an `incompatible_with` naming it holds, and the constraints on the option selected for it aren't judged. Constraints never make a decision used, and `NOT_BUILT_IN_UNIVERSE` and `UNDRIVEN_DECLARATION` don't judge them.
- **Pins** amend RFC 0003 §2: every pinned output or switch is built in the universe it is pinned to (`PIN_NOT_BUILT`, in place of the error on a pin where an output is switched off). Where a reached pin names a universe of an analysis other than the driving analysis, that universe sets each decision, of its analysis or one its universes drive, that what is reached through the pin uses there (a second `PIN_NOT_BUILT` row). A pin its own file's universes don't name falls back to the universe of the analysis whose element the reference names.
- **Reads across analyses** amend RFC 0004's rows on the universe being built, which *Planned results* applies to planned results: in each universe they judge what the driving analysis reaches there, built or not. Reading another analysis's switch needs that analysis built where it is read and, in the file of the universe's analysis, a driven chain, as reading its output built per universe does, whatever case the switch takes. A switch uses the decision it switches on, even where it takes no case, and reads only the case it takes.
- **Evidence** may cite a switch each of whose cases names an output other than a switch, or a switch like it. Without a pin it cites, in each of the driving analysis's universes, the result of the case taken there: none means `missing`, several the worst status.
- **Staleness** amends RFC 0005 §4: a result is also made from, for each switch it reads through, the decision it switches on, the option selected for it where it is read and the case it takes. A change to any of them makes the result stale, even where two options share a case. Records don't change: an `inputs` entry is recorded as written.

## Examples

The draft's calibrated fit, with switches:

```yaml
inputs:
  raw: {path: data/raw.csv}
decisions:
  correction_mode: {options: {none: {}, calibrated: {}}}
  calibration_prior: {options: {weak: {}, informative: {}}}
outputs:
  calibrated_table:
    inputs: [raw]
    ...
  table:                         # calibrated_table, where the correction is calibrated
    switch: correction_mode
    cases: {calibrated: calibrated_table}
  fit_summary:
    inputs: [table]
    decisions: [calibration_prior]
    recipe:
      command: python src/fit.py --prior {decisions.calibration_prior} {inputs.table} {output}
    ...
  informative_only:              # where the prior isn't weak
    switch: calibration_prior
    cases: {informative: calibrated_table}
  check_input:                   # the guard, outermost
    switch: correction_mode
    cases: {calibrated: informative_only}
  prior_check:
    inputs: [check_input]
    ...
universes:
  baseline: {decisions: {correction_mode: none}}
  calibrated: {derived_from: baseline, decisions: {correction_mode: calibrated, calibration_prior: weak}}
  informative: {derived_from: calibrated, decisions: {calibration_prior: informative}}
```

- In `baseline`, `table` and `check_input` have no case for `none`, so neither `fit_summary` nor `prior_check` is built, and nothing uses `calibration_prior`: `baseline` doesn't set it. Setting it there would draw `INACTIVE_DECISION`, as `baseline` uses it on some branch, through `fit_summary`; a key for a decision that nothing lists or switches on breaks `UNUSED_DECISION`.
- In `calibrated`, `fit_summary` is built with the weak prior, and `calibrated_table`, which only cases name, is planned, once, because `fit_summary` reads it there. `check_input` takes `informative_only`, which has no case for `weak`, so `prior_check` isn't built.
- In `informative`, both are built. In `baseline`, `informative_only` is never reached, so nothing asks about `calibration_prior` there: the outer switch is the guard.

## Implementation implications & migration

- *Compatibility:* breaking, before v0.1's first release. Schema: `Decision.when`, `Output.when` and the `condition` type go; `Output.switch` and `Output.cases` come, and `type`, `format` and `recipe` are required only of an output that isn't a switch. Rules: `INPUT_NOT_BUILT` goes; `PIN_INACTIVE` becomes `PIN_NOT_BUILT`, with a second row; `UNUSED_DECISION` and `INVALID_SWITCH` are new; `INACTIVE_DECISION` becomes a warning with the meaning above; the wording of `MISSING_DECISION`, the two constraint rules and nine others follows. `rules.json` holds 64 rules.
- *Landed* on astra-spec's `v0.1-schema` and astra-tools' `v0.1-rebuild` in two steps: first `when` went, a universe setting every decision of its analysis and of those its universes drive, so that only a file with `when` changed verdict; then switches came.
- *Depends on* *Maps and ids*, *Universes from other analyses*, *Driving, defined once* and *Planned results*.
- *Tools:* astra-tools' plan notes say, per universe, which output a switch leaves unbuilt and for which option. The specification says nothing about a missing case.
- *Migration:*
  - an output's `when: [d.o]` becomes a switch `{switch: d, cases: {o: output}}`, and its readers read the switch; `~d.o` gives a case to every other option; a list of conditions nests switches, the guarding decision's outermost;
  - an output that only its `when` made built per universe is built once: its record and bytes go to places without `{universe}/`, and it is `missing` until built there;
  - a decision's `when` goes: the decision is used where something planned lists it, so an output that lists it goes behind a switch on what the `when` tested;
  - a universe's own key for a decision it uses on no branch goes;
  - a reader moved behind a switch is stale once, as its `inputs` entry and command change.
- *A real port:* unions-bmodes had two `when`s on the leakage-corrected catalog, `applied` in every one of its universes, so both went with no switch; and 38 keys of its sub-analyses' universes, which repeated every root decision, went as `UNUSED_DECISION`.

## Questions or objections

- **A missing case is silent.** An option added later with no case leaves the switch, and whatever reads it without a pin, unbuilt where it is selected, with no error. A `skip:` list, with an error for an option in neither (`MISSING_CASE`), was weighed: little work, but a field and a rule frozen into 0.1 for a slip the plan notes already show. It can come in 0.2, which would then make invalid a switch that leaves an option in neither.
- **A pin into another analysis's own universe** can read only what uses decisions that universe uses on some branch, as it may set no other. A file that pins something its target analysis never reaches, and needs a key for it there, has no valid form: drive that analysis from the pinning one, or make it reach what is pinned. Counting such pins as that universe's own would make its verdict depend on who declares it.
- **Forbidden combinations** stay errors where both decisions are in play, as in Steegen's multiverse (210 valid universes of 270). Reading a `requires` that names a decision not in play as met, rather than broken, can come in a later minor version without invalidating a file.
- **Not in v0.1:** `type` and `format` on a switch, a default case (a re-export by another name), a switch on several decisions, and switches in `decisions`.

## References

- [#93](https://github.com/LightconeResearch/astra-spec/issues/93), whose outcome this is; [#87](https://github.com/LightconeResearch/astra-spec/issues/87), the three holes; the draft *Using conditional elements*, which this replaces.
- RFC 0003 §1, §2, *What validators check*; RFC 0004 §2, §3, *What validators check*; RFC 0005 §4.
- The drafts *Driving, defined once* and *Planned results*; [#80](https://github.com/LightconeResearch/astra-spec/issues/80): a case on a planned option is never taken while the option can't be selected.
