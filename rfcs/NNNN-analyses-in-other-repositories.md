---
rfc: NNNN
title: Analyses in other repositories
status: Draft
authors:
  - Tom Charnock (@tomcharnock-lightcone)
  - Francois Lanusse (@eiffl)
created: 2026-10-26
tracking-issue: https://github.com/LightconeResearch/astra-spec/issues/88
superseded-by:
---

## Context

[RFC 0004](0004-composition.md) made every analysis a directory with its own `astra.yaml`, declared by another analysis with `{ id, path }` and used through addresses (`<id>.<element>`). To keep that RFC short, a declared `path` had to be relative and inside the repository of a top-level analysis. Anything outside that repository was left for a later RFC building on [#55](https://github.com/LightconeResearch/astra-spec/issues/55).

Leaving out anything outside the top-level repository cuts new work off from the work it builds on, e.g.

- comparing earlier commits or releases of the same repository
- using the upstream repository of a fork
- reusing another astra analysis in a different repository altogether

With [Result provenance and layout](https://github.com/LightconeResearch/astra-spec/pull/91) each result has a record committed with its analysis. The record holds the result's content hash, its size and the commit its recipe ran from. Whether a result is unchanged can then be told without having to rematerialise it. With [Data inputs](https://github.com/LightconeResearch/astra-spec/pull/92) every input is a file committed with its analysis. One commit of an analysis's repository therefore fixes its code, its inputs and the records of its results.

So far, though, all of this only works for an analysis declared by `path`. An analysis in another repository has to be copied in or added as a git submodule. Either way the whole analysis is required even when only one of its results is read. `astra.yaml` can't say which repository and commit the analysis comes from either.

#55 asked to "refer to static, immutable artifacts when validating a new analysis, without the need to rerun previous analyses". It proposed putting the repository and its revision into each reference, first as `OWNER/REPO@REF.ARTIFACT` and then as `source@ref:subanalysis:output#universe` with the sources declared in their own `sources:` block. [#43](https://github.com/LightconeResearch/astra-spec/issues/43) similarly asks for one pointer to another analysis that fixes its revision.

## Proposal

This RFC proposes that a declaration names either a `path` or a `url` and may name a `commit`. A `path` names an analysis within the top-level analysis's repository as in RFC 0004 and a `url` names another repository (a remote), whose top-level analysis is the one declared. With a `commit` (required for `url`) the declaration names an analysis from a commit - the analysis as it was at that commit. An analysis from a commit is read from git at that commit and reading it doesn't need a checkout - only the `astra.yaml` files, the records of its results and the bytes that a recipe reads are required. Whilst this is enough for using results that other analyses have already materialised, it may also be desirable to *drive* an analysis from a commit, in which case the tool gets its files at that commit and it's driven like any other declared analysis (section 7).

This RFC requires *Result provenance and layout* ([#91](https://github.com/LightconeResearch/astra-spec/pull/91)) and *Data inputs* ([#92](https://github.com/LightconeResearch/astra-spec/pull/92)), which it refers to throughout: the results of an analysis from a commit are read through *Result provenance and layout*'s records and *Data inputs* makes every input a file committed with its analysis.

### Modifications

#### 1. Declaring an analysis from a commit

Imagine using RFC 0004's running example (Example 1) and committing it at the top level of a repository of its own, `https://github.com/owner/analysis` for example. A new analysis, `followup`, declares it and reads two of its results

```yaml
# followup/astra.yaml
analyses:
  - id: upstream
    url: https://github.com/owner/analysis
    commit: <full commit id>
outputs:
  - id: report
    ...
    inputs: [upstream.summary#u1, upstream.subanalysis3.output3]
```

where, beside its `id`, an `AnalysisDeclaration` has

| Field    | Type   | Required                           | Meaning                                                                                            |
|----------|--------|------------------------------------|----------------------------------------------------------------------------------------------------|
| `path`   | string | No - required if there's no `url`  | The directory of an analysis in the declaring analysis's repository, as in RFC 0004                |
| `url`    | string | No - required if there's no `path` | Where git can fetch another repository (a remote) from. Its top-level analysis is the one declared |
| `commit` | string | No - required with a `url`         | The full id of the commit the declared analysis is from                                            |

A declaration with a `path` and no `commit` means exactly what it means in RFC 0004. With a `url` the declared analysis is the analysis at the top level of the repository at that commit. If it has analyses of its own they are reached by address through it (`upstream.subanalysis3.output3`) as for any declared analysis.

With a `commit`

- the declaration is never part of a cycle, since a commit can only name earlier ones. Declarations by `path` alone can still form cycles as in RFC 0004
- only a full commit id is accepted (40 hexadecimal digits, or 64 in a SHA-256 repository). A branch moves. A tag can be moved or deleted and can name another commit in a fork or a mirror. A shortened id can become ambiguous as a repository grows

A `path` with a `commit` declares the analysis at that `path` as it was at that commit. The `path` is relative to the declaring analysis and inside the repository of the top-level analysis exactly as in RFC 0004, only read at that commit. The declaring analysis as it was at an earlier commit, for example, is

```yaml
# followup/astra.yaml
analyses:
  - id: previous
    path: .
    commit: <full commit id of an earlier commit>
```

and any other analysis in the repository can be declared at a commit in the same way. Such an analysis is read from the local repository. Where the declaring analysis is itself read from a remote, the commit is looked up in that remote's repository instead, at its URL. The commit SHOULD be an ancestor of the commit the declaration is in.

#### 2. Identity and reading at the commit

The commit id, with the `path` for an analysis of the declaring analysis's own repository, is the declared analysis's identity. Two declarations naming the same commit and `path` name the same analysis. A remote's URL only says where to get it - a fork or a mirror with the same commit gives the same analysis.

The declared analysis is read from git at the declared commit and git itself checks everything read against the commit id. Reading it runs none of its code. Only these are read

- the `astra.yaml` files of the declared analysis and of every analysis it declares
- the `astra.yaml` of a result's analysis at the commit its record names, to tell whether the result is unchanged (section 4)
- the record of each result that is read or cited and the records of all the results it was made from (section 4)
- which files there are at a commit and which differ between two commits (without their contents)
- the bytes of each result or input file that a recipe reads (section 5)

Where a tool keeps what it read is up to the tool. However, it is required that none of what is read becomes part of the declaring analysis's code (*Result provenance and layout*, section 3) and none of it is a change to the declaring analysis's repository that stops a runner from running. Validators and runners can work offline from what they kept of an earlier read.

#### 3. Using an analysis from a commit

Unless it's driven (section 7) none of the declared analysis's recipes run so it can only be used for

- its outputs in its own universes, with a pin (`upstream.summary#u1`)
- its outputs that are built once (`upstream.subanalysis3.output3`)
- its inputs (`upstream.data`)

Evidence can cite its results in the same way.

RFC 0004 already allows only these through a declaration that isn't driven - a decision or an output read without a pin has to go through a driven declaration.

#### 4. Results and their records

A result of the declared analysis is read through its record at the declared commit, in the analysis the result belongs to as in *Result provenance and layout*. The records of `followup`'s two reads from `https://github.com/owner/analysis` at `<full commit id>` are

```
upstream.summary#u1              =>    .astra/records/u1/summary.json
upstream.subanalysis3.output3    =>    subanalysis3/.astra/records/output3.json
```

Records are committed in the repository of the analysis they belong to. If `upstream` itself declared an analysis from a commit, that analysis's records would be read in its repository at the commit `upstream` names for it.

A result can only be read once its record is committed so the declaring analysis names the commit that added the records rather than the one the recipes ran from. If the recipes ran at `<commit A>`, their records name `<commit A>`. The records are then committed in a later commit, `<commit B>` which is the commit `followup` declares `upstream` at.

A result is unchanged if nothing *Result provenance and layout*'s section 4 compares has changed between `<commit A>` and `<commit B>`. *Result provenance and layout*'s section 3 keeps the commit a record names in the history of the commits that hold the record, so `<commit A>` can be got wherever `<commit B>` can.

A result is only unchanged if the results it was made from are unchanged too so their records are read as well. The content hash of each of those results is taken from its record and their bytes aren't needed.

An address is part of `astra.yaml` and so an address that doesn't exist in the declared analysis is an error in the declaring analysis. Anything with a valid address can be pointed to - whether it has been recorded and is unchanged is checked separately

- a result with no record at the declared commit is `missing`
- a result recorded at the declared commit is `stale` if something it was made from has changed since the commit its record names

#### 5. Getting the bytes

To build an output that reads a result of the declared analysis, the result's bytes have to be fetched and be the ones its record names. They come from what git holds at the result's location (*Result provenance and layout*, section 1) in the declared analysis's repository at the declared commit. Their content hash and size are checked against the record, which makes them `present`, `modified` or `absent` as in *Result provenance and layout*. When one of the declared analysis's inputs is read by address, its file is obtained in the same way from its `path` at the declared commit.

Where something stands in for the bytes, such as a git-annex link or a Git LFS pointer as in *Data inputs*, the tooling that recognises it gets them.

Where the bytes are kept is up to the tool and, like everything else read from a commit, they aren't part of the declaring analysis's code. Getting the actual bytes from anywhere else, such as a store that finds them by their content hash, is left to a later RFC.

#### 6. Validating an analysis from a commit and reaching a remote

The declared analysis, with everything it declares, must be valid at the declared commit. That can't change - a commit's files never change and each `astra.yaml` is read by the version it states. A validator can therefore either read every `astra.yaml` the declared analysis reaches or remember the answer for a commit it has already validated.

A published analysis SHOULD only declare remotes that its readers can fetch. This isn't a MUST because a remote may well be private whilst the analysis is being worked on. A remote that can't be fetched is an error in the declaring analysis that names its declaration.

#### 7. Driving an analysis from a commit

Whether an analysis from a commit is driven is up to the driver's universes as in RFC 0004. Driving it runs its recipes so the tool needs its files at the declared commit. The recipes MUST run on exactly those files. Where the tool puts them is up to the tool and, like everything else read from a commit, they aren't part of the declaring analysis's code and aren't a change that stops a runner from running. Which environment the recipes run in is up to the runner, as for any recipe - the driver's or one it builds for the driven analysis - and it's recorded in the driver's records as in *Result provenance and layout* (as a `uri` when it's built from the driven analysis's own files, since a `file` environment's path is read in the repository the record is committed in).

As in RFC 0004, reading one of the declared analysis's own universes whilst also driving it takes a second declaration

```yaml
# followup/astra.yaml
analyses:
  - id: upstream
    url: https://github.com/owner/analysis
    commit: <full commit id>
  - id: upstream_driven
    url: https://github.com/owner/analysis
    commit: <same full commit id>
outputs:
  - id: against_u1
    ...
    inputs: [upstream_driven.summary, upstream.summary#u1]
universes:
  - id: w1
    decisions:
      upstream_driven.a: a2
      upstream_driven.subanalysis1.b: b2
      upstream_driven.subsubanalysis1.d: d2
      upstream_driven.subanalysis2.c: c2
```

`upstream_driven.summary` is built in `w1` with every decision of `upstream_driven` set by `followup`'s universe. `upstream.summary#u1` is `upstream`'s own `u1`, read through its record.

Only what the driver's universes build is built. Those results belong to the driver as in RFC 0004 and so do their records

```
followup/results/w1/upstream_driven.summary.<format>
followup/.astra/records/w1/upstream_driven.summary.json
```

Those records name the driver's commit, as in *Result provenance and layout*, and the declaration at that commit says which commit the driven analysis is from - and, for a remote, where to get it.

The driven analysis's outputs built once aren't built - like the rest of its results they're read through their records at the declared commit (section 4).

RFC 0004 already allows a declared analysis to be a git submodule, which records a URL and a commit. That is still allowed. A submodule's URL and commit are only known to git and its checkout can drift from them. A `url` and a `commit` do the same job in `astra.yaml` so

- the declared analysis has the same identity whether it is read or driven
- what a driver runs is the declared commit, with no checkout to drift from it

### What validators check

| Rule | Severity |
|---|---|
| A declaration has exactly one of `path` and `url` | error |
| A declaration with a `url` has a `commit` | error |
| A `commit` is a full commit id | error |
| A `path` with a `commit` names a commit the declaring analysis's repository has | error |
| A `path` with a `commit` names an ancestor of the commit its declaration is in | warning |
| An analysis from a commit, with everything it declares, is valid at that commit | error |
| A remote can be fetched: its URL can be reached and has the commit | error |

Every other rule of RFC 0004 applies to analyses from commits as it is, with their files read at their commits.

### What's checked

| Rule | Checked by | Result |
|---|---|---|
| A result of an analysis from a commit that is read or cited is unchanged at the declared commit | check | `unchanged`, `stale` or `missing` |
| The bytes of a result of an analysis from a commit that a recipe reads are the ones its record names | check | `present`, `modified` or `absent` |
| An output that reads a result of an analysis from a commit when that result is missing or stale, or its bytes can't be got or aren't the recorded ones | runner | isn't built |

## Examples

### The iris pipeline from its own repository

Say that `examples/iris_pipeline` from RFC 0004 is committed at the top level of a repository of its own and that its results have been built and their records committed. A new analysis tries k-NN on three components and reports it beside the pipeline's own baseline

```yaml
# iris_rerun/astra.yaml
id: iris_rerun
version: "0.1.0"
name: The iris pipeline again with k-NN
analyses:
  - id: iris
    url: https://github.com/owner/iris-pipeline
    commit: <commit id that added its records>
  - id: iris_knn
    url: https://github.com/owner/iris-pipeline
    commit: <same commit id>
outputs:
  - id: against_baseline
    type: report
    format: json
    inputs: [iris_knn.summary, iris.summary#baseline]
    recipe:
      command: >-
        python src/report.py --ours {inputs.iris_knn.summary}
        --baseline {inputs.iris.summary#baseline} --out {output}
universes:
  - id: knn
    decisions:
      iris_knn.test_split: thirty_pct
      iris_knn.random_seed: seed_7
      iris_knn.feature_extraction.method: pca
      iris_knn.feature_extraction.n_components: three
      iris_knn.classification.classifier: knn
```

`iris.summary#baseline` is read through `.astra/records/baseline/summary.json` in the pipeline's repository at that commit. Its bytes are got from `results/baseline/summary.md` there (or by the tooling that holds them) and checked against that record. Nothing else of the pipeline is fetched to read it. `iris_knn` is driven by `knn` from the pipeline's files at that commit, wherever the tool puts them. Its results go in `iris_rerun/results/knn/`.

## Implementation implications & migration

*Compatibility:* additive on top of RFC 0004. Every existing declaration has a `path` without a `commit` and is unchanged. It requires *Result provenance and layout* and *Data inputs*.

*Migration steps:* none. An analysis moved from this repository into another one swaps its declaration's `path` for a `url` and a `commit`.

## References

- [RFC 0004](0004-composition.md): declared analyses, addresses, driving and pins, which this RFC extends to analyses in other repositories
- [RFC 0003](0003-cross-universe-artifact-references.md) ([#52](https://github.com/LightconeResearch/astra-spec/issues/52), [#65](https://github.com/LightconeResearch/astra-spec/pull/65), reduced to universes in [#83](https://github.com/LightconeResearch/astra-spec/pull/83)): in-file universes and pins
- [Result provenance and layout](https://github.com/LightconeResearch/astra-spec/pull/91) (tracked in [#90](https://github.com/LightconeResearch/astra-spec/issues/90)): the records a declared analysis's results are read through
- [Data inputs](https://github.com/LightconeResearch/astra-spec/pull/92) (tracked in [#86](https://github.com/LightconeResearch/astra-spec/issues/86)): an input names a file committed with its analysis, so the declared commit fixes it
- [#55](https://github.com/LightconeResearch/astra-spec/issues/55): cross-repository artifact references, which this RFC is based on
- [#43](https://github.com/LightconeResearch/astra-spec/issues/43): an identity layer for addressing and resolving content across analyses
- [#66](https://github.com/LightconeResearch/astra-spec/issues/66): re-running and extending an analysis on other machines
