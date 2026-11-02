---
rfc: NNNN
title: Schema tidy-up
status: Draft
authors:
  - Tom Charnock (@tomcharnock-lightcone)
created: 2026-10-30
tracking-issue: https://github.com/LightconeResearch/astra-spec/issues/94
superseded-by:
---

## Context

A few parts of the schema are unused, inconsistent or say less than tooling enforces. None of them is big but each is something a reader (or someone writing a new tool) has to work out for themselves.

1. **Two fields on evidence that nothing reads.** `Evidence.snapshot` ("Path to immutable copy of the artifact") and `Evidence.source_commit` ("Git commit that produced the original artifact") are optional and nothing we know of reads either of them. Nothing says what the path is relative to, what keeps the copy immutable or what happens when the commit and the cited output disagree.
2. **A required time that nothing reads.** Every insight must have a `created_at` and nothing we know of reads it. It isn't clear what it is the creation of - a finding's time is really its result's and a prior insight's is its paper's - and git already records when each line was written. Most of the documentation's examples write a padded midnight (`2026-05-11T00:00:00Z`). Keeping it would mean settling how times are written ([#54](https://github.com/LightconeResearch/astra-spec/issues/54)) for a field nobody uses.
3. **A flag that nothing reads.** `Insight.derived` is "True if synthesized/inferred from multiple sources" in the schema and "Whether the claim was produced by this analysis" in the specification - which being in `findings` already says. Nothing we know of reads it, and a flag can't say what a claim is drawn from.
4. **Two ways to give a page.** Evidence's `location` takes a `value` (`page=8`) and a `page` (`8`). Nothing we know of reads `value` since tooling reads `page`. The class says it is a W3C FragmentSelector, whose form is `value`, though `page` isn't part of it.
5. **Two classes that nothing uses.** No field has `KeyValuePair` or `InsightCollection` as its range so no `astra.yaml` can contain either. `KeyValuePair` held Docker build arguments and was left behind when [#10](https://github.com/LightconeResearch/astra-spec/pull/10) folded `container_build` into `container`. `InsightCollection` describes a standalone file of insights that no tooling loads - an analysis keeps its insights in `prior_insights` and `findings`. Both still appear in the generated models. `InsightCollection` is also listed in the specification's table of schema files.
6. **`label` is optional in some places, required in others and missing on universes.** `Input`, `Output` and `Insight` have an optional `label` and tooling falls back to the id when there isn't one. `Decision` and `Option` require one, so an option whose id already says it all has to say it twice, as in RFC-0004's own example

   ```yaml
   random_seed:
     label: Random seed
     options: { seed_42: { label: "42" }, seed_7: { label: "7" } }
   ```

   A universe has no label at all, though it is what a reader sees most - in results, comparisons and pins.
7. **Tags on only some elements.** `Analysis`, `Decision` and `Insight` have an optional `tags` list for grouping and classifying them. Inputs, outputs, options and universes can't be tagged.
8. **Two fields for one fact.** An excluded option is marked `excluded: true` and gives its reason in `excluded_reason`. The schema and the specification say the reason is optional. `astra validate` requires one when `excluded` is true and rejects one otherwise, so a file that follows the specification can still fail. The rule can't be written into the schema either, since LinkML can't put a condition on a boolean's value into the JSON Schema it generates.
9. **A rule only the description states.** `Evidence`'s description says "Exactly one of doi or artifact must be set" but nothing checks it, so evidence with neither or both is valid.

RFC-0003 and RFC-0004 already change every `astra.yaml` (universes move into the file and `from:` goes) so this is the cheapest moment to remove and tighten fields - analyses migrate once rather than twice.

## Proposal

This RFC proposes nine small changes to the schema. Each is independent of the others so any one can be dropped without touching the rest.

### Modifications

#### 1. `Evidence.snapshot` and `Evidence.source_commit` are removed

Evidence names the output it cites by its id or address. When the output is built per universe the evidence pins it to the universe the claim is about (`fit_params#robust`), as RFC-0003 introduced. That is enough to say which result a claim rests on. Which commit made that result and which bytes it is belong to the result rather than to every finding that cites it - [#91](https://github.com/LightconeResearch/astra-spec/pull/91) proposes a record per result that holds its commit and content hash.

#### 2. `Insight.created_at` is removed

Insights no longer carry a time. When a finding's result was made belongs to the result (#91's record holds it) and when a line of `astra.yaml` was written is in git. With `created_at` gone `astra.yaml` holds no times at all, so how to write them no longer arises there.

#### 3. `Insight.derived` is removed

Being in `findings` already says a claim comes from this analysis. What a claim is drawn from would be said by citing it, which a flag can't do.

#### 4. `FragmentSelector.value` is removed

A location is given by its `page` alone, the form tooling reads. The class no longer claims to be a W3C FragmentSelector.

#### 5. `KeyValuePair` and `InsightCollection` are removed

Both classes go from the schema and so from the generated models. `InsightCollection` also leaves the specification's table of schema files. No file is affected.

#### 6. `label` is optional everywhere

`Decision.label` and `Option.label` become optional, as `Input.label`, `Output.label` and `Insight.label` already are, and `Universe` gets an optional `label` of its own. Tooling shows the id wherever there's no label. An option with nothing to say beyond its id is an empty map

```yaml
random_seed:
  options: { seed_42: {}, seed_7: {} }
```

A universe's label isn't inherited through `derived_from`, since it names that universe and not the one it starts from.

#### 7. `tags` on inputs, outputs, options and universes

`Input`, `Output`, `Option` and `Universe` get an optional `tags` list, as `Analysis`, `Decision` and `Insight` already have. Tags are free strings. A universe's tags, like its label, aren't inherited through `derived_from`. A declaration gets none since the analysis it names has its own.

#### 8. `excluded` holds the reason

`excluded` becomes a string, the reason the option was rejected, and `excluded_reason` is removed. An option is excluded exactly when it has one and the reason can't be empty, which the schema checks with a pattern. One field can't disagree with itself so there is nothing left for a separate rule to enforce.

```yaml
quadratic_fit:
  label: Quadratic relation
  excluded: Pilot residuals did not justify adding curvature.
```

As before, no universe may select an excluded option.

#### 9. Evidence has exactly one of `doi` and `artifact`

The rule moves from `Evidence`'s description into the schema, as two rules on which of the two fields is present. LinkML can carry a rule on presence. Evidence with neither or both, which the description already ruled out, becomes invalid.

## Implementation implications & migration

*Compatibility:* breaking. Changes 1, 2, 3, 4 and 8 can make a file invalid. Change 9 only invalidates a file the description already ruled out. Change 5 affects no file, only code that imports the generated classes. Changes 6 and 7 are additive.

*Migration steps:*
- remove `snapshot` and `source_commit` from evidence. Evidence citing an output built per universe pins it to the universe the claim is about
- remove `created_at` from every prior insight and finding
- remove `derived` from every prior insight and finding
- remove `value` from evidence's `location`, writing its page as `page` where there isn't one
- replace `excluded: true` and `excluded_reason: <reason>` with `excluded: <reason>`. An option with `excluded: false` drops it
- give evidence that has neither or both of `doi` and `artifact` exactly one

## Questions or objections

- **Should `Analysis.name` become `label`, to match everything else?** Inputs, outputs, decisions, options, insights and universes are named by an optional `label` and an analysis by `name`. A rename would make them consistent but would break every file. RFC-0004 also requires `name` on every analysis. This RFC leaves it as is.

## References

- [RFC-0003](0003-cross-universe-artifact-references.md): pins, which evidence uses to name the result it cites
- [RFC-0004](0004-composition.md): `name` required on every analysis and the example in *Context*
- [#91](https://github.com/LightconeResearch/astra-spec/pull/91): a record per result, with the commit it was made from and when it was made
- [#54](https://github.com/LightconeResearch/astra-spec/issues/54): how times are written, which no longer arises in `astra.yaml`
- [#10](https://github.com/LightconeResearch/astra-spec/pull/10): `container_build` folded into `container`, leaving `KeyValuePair` unused
- [#80](https://github.com/LightconeResearch/astra-spec/issues/80): planned options and what `excluded` means. This RFC changes how `excluded` is written, not what it means
