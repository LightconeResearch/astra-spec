---
rfc: NNNN
title: Using conditional elements
status: Draft
authors:
  - Tom Charnock (@tomcharnock-lightcone)
created: 2026-10-28
tracking-issue: https://github.com/LightconeResearch/astra-spec/issues/87
superseded-by:
---

## Context

`when` switches a decision or an output off in some universes. The specification says what that means for the element that is switched off but not for anything that uses it. Its own example in *Conditional elements* has two elements that only exist when `correction_mode` is `calibrated`

```yaml
decisions:
  correction_mode:
    options: { none: ..., calibrated: ... }
  calibration_prior:
    when: [correction_mode.calibrated]
    options: { weak: ..., informative: ... }

outputs:
  - id: calibrated_table
    when: [correction_mode.calibrated]
    ...
```

In a universe with `correction_mode: none` there is no `calibration_prior` and no `calibrated_table`. Other elements can still use them though. There are three places where the specification doesn't say what happens then.

1. **A recipe uses a switched-off decision's value**

   ```yaml
     - id: fit_summary
       decisions: [correction_mode, calibration_prior]
       recipe:
         command: python src/fit.py --prior {decisions.calibration_prior} --out {output}
   ```

   In a `none` universe there is no prior and the command has a hole in it, `--prior ???`. Validators accept this since the decision is listed on the output and it only fails when the command is built.

2. **An output reads a switched-off output**

   ```yaml
     - id: report
       inputs: [calibrated_table]
   ```

   `calibrated_table` is never built in a `none` universe. RFC-0003 makes a pin to a universe where an output isn't built an error and RFC-0004 does the same for a read without a pin across analyses. Nothing says what happens within one analysis - is `report` quietly not built or is it an error?

3. **A condition tests a switched-off decision.** `when: [~calibration_prior.weak]` means "the prior isn't weak". In a `none` universe there is no prior. Does the condition hold, never hold or is it an error? Tooling currently treats it as holding. Constraints ask the same question - does `requires: [calibration_prior.informative]` or `incompatible_with: [calibration_prior.weak]` hold when there is no prior?

Each answer changes what existing files mean so the rules should be tightened up to prevent ambiguity.

## Proposal

This RFC proposes one principle: nothing can use, read or test an element where that element is switched off. Whatever would do so has to carry the same switch so that it stays visible wherever the element is used.

### Modifications

#### 1. What an output uses exists wherever it's built

Every decision an output lists and every output it reads without a pin must exist in each universe the output is built in. Otherwise it's an error and the fix is to give the output the same `when`

```yaml
  - id: fit_summary
    when: [correction_mode.calibrated]
    decisions: [correction_mode, calibration_prior]
    ...
  - id: report
    when: [correction_mode.calibrated]
    inputs: [calibrated_table]
```

Listing a decision is enough to need the `when` even if the command doesn't name it. The decisions an output depends on are then the same in every universe it's built in.

#### 2. Conditions

A condition that names a decision switched off in a universe can't be evaluated there. In a `none` universe this holds for `calibration_prior.weak` and `~calibration_prior.weak` alike, in an output's `when` or a decision's. It is an error unless the condition is guarded - by another condition of the same `when` that fails in that universe

```yaml
  - id: prior_check
    when: [correction_mode.calibrated, ~calibration_prior.weak]
```

In a `none` universe `correction_mode.calibrated` fails so `prior_check` isn't built and `~calibration_prior.weak` is never tested. The order of the conditions doesn't matter and `when` stays an AND. The switched-off decision's own `when` always works as the guard.

#### 3. Constraints

A constraint is only checked in a universe that selects the option it's written on, so that option is its guard. A constraint that names a decision switched off in that universe is an error.

- `requires` naming a switched-off decision was already broken since the option it requires can't be selected. Only the reason is new
- `incompatible_with` works both ways round so it is written on the option of the decision that can be switched off, where it's only checked if that decision exists

```yaml
  calibration_prior:
    when: [correction_mode.calibrated]
    options:
      weak:
        incompatible_with: [fit_method.robust_linear]
      informative: ...
```

Written on `fit_method.robust_linear` instead, it would be an error in every `none` universe that picks the robust fit.

#### 4. Checked in each universe being built

Every rule above is checked in each universe being built as RFC-0003's pins and RFC-0004's reads already are - not for every selection the file allows. No logic is needed between `when`s and so `~correction_mode.none` guards as well as `correction_mode.calibrated` does. The rules are the same within one analysis and across analyses. By address the guard is written by address too, e.g. `when: [root.correction_mode.calibrated, ~root.calibration_prior.weak]`.

### What validators check

| Rule | Severity |
|---|---|
| The decisions an output lists and the outputs it reads without a pin exist in each universe it's built in (their `when` holds there) | error |
| A `when` names only decisions that exist in the universe being built, unless another of its conditions fails there | error |
| The constraints of a selected option name only decisions that exist in the universe being built | error |

The first row widens RFC-0004's "An output read without a pin exists in the universe being built" to the decisions an output lists and to reads within one analysis.

## Examples

### A calibrated line fit

This example illuminates each of the three problems that can occur and how it is resolved in this proposal

```yaml
decisions:
  correction_mode:
    options: { none: ..., calibrated: ... }
  calibration_prior:
    when: [correction_mode.calibrated]
    options:
      weak: { incompatible_with: [fit_method.robust_linear] }
      informative: ...
  prior_width:
    when: [correction_mode.calibrated, calibration_prior.informative]
    options: { narrow: ..., wide: ... }
  fit_method:
    options:
      ordinary_least_squares: ...
      robust_linear: ...
      bayesian: { requires: [calibration_prior.informative] }

outputs:
  - id: fit_params
    decisions: [fit_method]
  - id: calibrated_table
    when: [correction_mode.calibrated]
  - id: calibrated_fit
    when: [correction_mode.calibrated]
    inputs: [calibrated_table]
    decisions: [calibration_prior, fit_method]
  - id: prior_check
    when: [correction_mode.calibrated, ~calibration_prior.weak]
    decisions: [prior_width]

universes:
  - id: baseline
    decisions: { correction_mode: none, fit_method: ordinary_least_squares }
  - id: robust
    derived_from: baseline
    decisions: { fit_method: robust_linear }
  - id: calibrated
    derived_from: baseline
    decisions: { correction_mode: calibrated, calibration_prior: weak }
  - id: bayesian
    derived_from: calibrated
    decisions: { calibration_prior: informative, prior_width: narrow, fit_method: bayesian }
  - id: back_to_none
    derived_from: bayesian
    decisions: { correction_mode: none, fit_method: ordinary_least_squares }
```

| Universe | Builds |
|---|---|
| `baseline` | `fit_params` |
| `robust` | `fit_params` - there's no prior so the weak prior's constraint isn't checked |
| `calibrated` | `fit_params`, `calibrated_table` and `calibrated_fit` with the weak prior |
| `bayesian` | the three above with the informative prior and `prior_check` with the narrow width |
| `back_to_none` | `fit_params` - the prior and width it inherits from `bayesian` are dropped |

`prior_check` tests "not weak" whilst `prior_width` exists for "informative". They're written differently but hold in the same universes - the width is there wherever the check is built.

## Implementation implications & migration

*Compatibility:* breaking, with no change to the schema. A file that uses an element where it's switched off becomes invalid. Requires RFC-0003 (and RFC-0004 for addresses).

*Migration steps:*
- an output that lists or reads an element where it's switched off gets that element's `when`
- a condition on a decision that can be switched off gets that decision's `when` as a guard
- an `incompatible_with` naming a decision that can be switched off moves onto that decision's option

## Questions or objections

- **Constraints that can't be moved.** When both decisions are switched by different conditions, or the other decision belongs to an analysis that can't be changed, there's no side to write an `incompatible_with` on. A guard inside a constraint entry would fix this, as would reading a switched-off decision as "nothing selected" for constraints. Both relax the rules so either can come later without making any file invalid.

## References

- [#87](https://github.com/LightconeResearch/astra-spec/issues/87): the three holes which this RFC closes
- [RFC-0003](0003-cross-universe-artifact-references.md): in-file universes and pins, and a pin to a universe where the output isn't built
- [RFC-0004](0004-composition.md): addresses, and reads without a pin in the universe being built
- [#80](https://github.com/LightconeResearch/astra-spec/issues/80): planned options, which asks a similar question of the outputs that depend on them
