---
rfc: NNNN
title: Analyses in other repositories
status: Draft
authors:
  - Tom Charnock (@tomcharnock-lightcone)
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

With [Result provenance and layout](https://github.com/LightconeResearch/astra-spec/pull/91) each result has a record committed with its analysis. The record holds the result's content hash, its size and the commit of the code that made it. Whether a result is still current can then be told without having to rematerialise it. With [Data inputs](https://github.com/LightconeResearch/astra-spec/pull/92) every input is a file committed with its analysis. One commit of an analysis's repository therefore fixes its code, its inputs and the records of its results.

So far, though, all of this only works for an analysis declared by `path`. An analysis in another repository has to be copied in or added as a git submodule. Either way the whole analysis is required even when only one of its results is read. `astra.yaml` can't say which repository and commit the analysis comes from either.

#55 asked to "refer to static, immutable artifacts when validating a new analysis, without the need to rerun previous analyses". It proposed putting the repository and its revision into each reference, first as `OWNER/REPO@REF.ARTIFACT` and then as `source@ref:subanalysis:output#universe` with the sources declared in their own `sources:` block. [#43](https://github.com/LightconeResearch/astra-spec/issues/43) similarly asks for one pointer to another analysis that fixes its revision.

## Proposal

This RFC proposes that a declaration names either a `path` or a `repository`. A `path` names an analysis within the top-level analysis's repository as in RFC 0004. A `repository` names an analysis from a commit, either of another repository (a remote) or of the declaring analysis's own repository. An analysis from a commit is read from git at that commit and reading it doesn't need a checkout - only the `astra.yaml` files, the records of its results and the bytes that a recipe reads are required. Whilst this is enough for using results that other analyses have already materialised, it may also be desirable to *drive* an analysis from a commit, in which case it's checked out at the declaration's `checkout` (section 7) and driven like any other declared analysis.

This RFC requires *Result provenance and layout* ([#91](https://github.com/LightconeResearch/astra-spec/pull/91)) and *Data inputs* ([#92](https://github.com/LightconeResearch/astra-spec/pull/92)), which it refers to throughout: the results of an analysis from a commit are read through *Result provenance and layout*'s records and *Data inputs* makes every input a file committed with its analysis.

### Modifications

#### 1. Declaring an analysis from a commit

Imagine using RFC 0004's running example (Example 1) and committing it at the top level of a repository of its own, `https://github.com/owner/analysis` for example. A new analysis, `followup`, declares it and reads two of its results

```yaml
# followup/astra.yaml
analyses:
  - id: upstream
    repository:
      url: https://github.com/owner/analysis
      commit: <full commit id>
outputs:
  - id: report
    ...
    inputs: [upstream.summary#u1, upstream.subanalysis3.output3]
```

where an `AnalysisDeclaration` has exactly one of

| Field        | Type         | Required                                 | Meaning                                                                                       |
|--------------|--------------|------------------------------------------|-----------------------------------------------------------------------------------------------|
| `path`       | string       | No - required if there's no `repository` | The directory of an analysis in the declaring analysis's repository, as in RFC 0004           |
| `repository` | `Repository` | No - required if there's no `path`       | An analysis from a commit of another repository or of the declaring analysis's own repository |

where `Repository` has

| Field      | Type   | Required | Meaning                                                                                                   |
|------------|--------|----------|-----------------------------------------------------------------------------------------------------------|
| `url`      | string | No       | Where git can fetch the repository from. Left out for a commit of the declaring analysis's own repository |
| `commit`   | string | Yes      | The full id of the commit                                                                                 |
| `checkout` | string | No       | Where the analysis is checked out to be driven (section 7)                                                |

A declaration with a `path` means exactly what it means in RFC 0004. With a `repository`

- the declared analysis is the analysis at the top level of its repository at that commit. If it has analyses of its own they are reached by address through it (`upstream.subanalysis3.output3`) as for any declared analysis
- declarations can form cycles within a repository as in RFC 0004 but not across repositories since a commit can only name a commit that existed before it
- only a full commit id is accepted (40 hexadecimal digits, or 64 in a SHA-256 repository). A branch moves. A tag can be moved or deleted and can name another commit in a fork or a mirror. A shortened id can become ambiguous as a repository grows

A commit of the declaring analysis's own repository is declared without a `url`

```yaml
# followup/astra.yaml
analyses:
  - id: previous
    repository:
      commit: <full commit id of an earlier commit>
```

Such an analysis is the repository's top-level analysis at that commit, read from the local repository. Where the declaring analysis is itself read from a remote, the commit is looked up in that remote's repository instead, at its URL. The commit SHOULD be an ancestor of the commit the declaration is in.

#### 2. Identity and reading at the commit

The commit id is the declared analysis's identity. Two declarations naming the same commit name the same analysis. The URL only says where to get it - a fork or a mirror with the same commit gives the same analysis.

The declared analysis is read from git at the declared commit and git itself checks everything read against the commit id. Reading it runs none of its code. Only these are read

- the `astra.yaml` files of the declared analysis and of every analysis it declares
- the `astra.yaml` of a result's analysis at the commit its record names, to tell whether the result is current (section 4)
- the record of each result that is read or cited and the records of all the results it was made from (section 4)
- which files there are at a commit and which differ between two commits (without their contents)
- the bytes of each result or input file that a recipe reads (section 5)

Where a tool keeps what it read is up to the tool. However, it is required that none of what is read becomes part of the declaring analysis's code (*Result provenance and layout*, section 3) and none of it is a change to the declaring analysis's repository that stops a runner from running. Validators and runners can work offline from what they kept of an earlier read.

#### 3. Using an analysis from a commit

None of the declared analysis's recipes can run without a checkout so the declared analysis can only be used for

- its outputs in its own universes, with a pin (`upstream.summary#u1`)
- its outputs that are built once (`upstream.subanalysis3.output3`)
- its inputs (`upstream.data`)

Evidence can cite its results in the same way.

RFC 0004 already allows only these through a declaration that isn't driven - a decision or an output read without a pin has to go through a driven declaration. The only new rule is that no universe drives an analysis from a commit without a `checkout`.

#### 4. Results and their records

A result of the declared analysis is read through its record at the declared commit, in the analysis the result belongs to as in *Result provenance and layout*. The records of `followup`'s two reads from `https://github.com/owner/analysis` at `<full commit id>` are

```
upstream.summary#u1              =>    .astra/records/u1/summary.json
upstream.subanalysis3.output3    =>    subanalysis3/.astra/records/output3.json
```

Records are committed in the repository of the analysis they belong to. If `upstream` itself declared an analysis by `repository`, that analysis's records would be in its own repository at the commit `upstream` names.

A result can only be read once its record is committed so the declaring analysis names the commit that added the records rather than the one the recipes ran from. If the recipes ran at `<commit A>`, the code in their records names `<commit A>`. The records are then committed in a later commit, `<commit B>` which is the commit `followup` declares `upstream` at.

In *Result provenance and layout*'s section 4, "now" for the declared analysis is the declared commit, `<commit B>`. The declared analysis's code, the output's declaration and the options of its decisions are compared at `<commit A>` and `<commit B>` to tell whether a result is current. The commit a record names SHOULD be an ancestor of the commit the record is added in so that `<commit A>` can be got wherever `<commit B>` can.

A result is only current if the results it was made from are current too so their records are read as well. The content hash of each of those results is taken from its record and their bytes aren't needed.

An address is part of `astra.yaml` and so an address that doesn't exist in the declared analysis is an error in the declaring analysis. Anything with a valid address can be pointed to - whether it has been recorded and is still current is checked separately

- a result with no record at the declared commit is `missing`
- a result whose record isn't current at the declared commit is `stale`

#### 5. Getting the bytes

To build an output that reads a result of the declared analysis, the result's bytes have to be fetched and be the ones its record names. They come from what git holds at the result's location (*Result provenance and layout*, section 1) in the declared analysis's repository at the declared commit. Their content hash and size are checked against the record, which makes them `present`, `modified` or `absent` as in *Result provenance and layout*. When one of the declared analysis's inputs is read by address, its file is obtained in the same way from its `path` at the declared commit.

Where something stands in for the bytes, such as a git-annex link or a Git LFS pointer as in *Data inputs*, the tooling that recognises it gets them.

Where the bytes are kept is up to the tool and, like everything else read from a commit, they aren't part of the declaring analysis's code. Getting the actual bytes from anywhere else, such as a store that finds them by their content hash, is left to a later RFC.

#### 6. Validating an analysis from a commit and reaching a remote

The declared analysis must be valid as the top-level analysis of its repository at the declared commit. That can't change - a commit's files never change and each `astra.yaml` is read by the version it states. A validator can therefore either read every `astra.yaml` the declared analysis reaches or remember the answer for a commit it has already validated.

A published analysis SHOULD only declare remotes that its readers can fetch. This isn't a MUST because a remote may well be private whilst the analysis is being worked on. A remote that can't be fetched is an error in the declaring analysis that names its declaration.

#### 7. Driving an analysis from a commit

Driving the declared analysis runs its recipes so it has to be checked out at the place the declaration's `checkout` names. By convention only an analysis that is driven is given a `checkout` since reading it doesn't need one.

As in RFC 0004, reading one of the declared analysis's own universes whilst also driving it takes a second declaration (and that one needs no `checkout`)

```yaml
# followup/astra.yaml
analyses:
  - id: upstream
    repository:
      url: https://github.com/owner/analysis
      commit: <full commit id>
  - id: upstream_driven
    repository:
      url: https://github.com/owner/analysis
      commit: <same full commit id>
      checkout: remotes/upstream
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

With a `checkout`

- the declared analysis is checked out at `checkout` at the declared commit and its recipes run there
- anything already at `checkout` must be at the declared commit with none of its committed files changed. Files added afterwards aren't part of the commit and so don't count as a change
- `checkout` is relative and stays inside the declaring analysis's repository
- declarations with the same `checkout` name the same commit

The results of the driven analysis belong to the driver as in RFC 0004 and so do their records

```
followup/results/w1/upstream_driven.summary.<format>
followup/.astra/records/w1/upstream_driven.summary.json
```

A record of a result made from a remote's code also names the remote's `url` in its `code`, beside the `commit` and `path` of *Result provenance and layout*.

RFC 0004 already allows a declared analysis to be a git submodule, which records a URL and a commit. That is still allowed. A submodule's URL and commit are only known to git and its checkout can drift from them. A `repository` with a `checkout` does the same job but puts the URL and commit in `astra.yaml` so

- the declared analysis has the same identity whether it is read or driven
- validators check that the checkout is at that commit

### What validators check

| Rule | Severity |
|---|---|
| A declaration has exactly one of `path` and `repository` | error |
| A `repository` has a `commit` that is a full commit id | error |
| A `repository` without a `url` names a commit the declaring analysis's repository has | error |
| A `repository` without a `url` names an ancestor of the commit its declaration is in | warning |
| An analysis from a commit is valid as the top-level analysis of its repository at that commit | error |
| A remote can be fetched: its URL can be reached and has the commit | error |
| A `checkout` is relative and stays inside the declaring analysis's repository | error |
| Declarations with the same `checkout` name the same `commit` | error |
| A checkout is at its commit with none of its committed files changed, or there is nothing there yet | error |
| No flat key names an analysis from a commit without a `checkout` | error |

Every other rule of RFC 0004 applies to analyses from commits as it is, with their files read at their commits.

### What's checked

| Rule | Checked by | Result |
|---|---|---|
| A result of an analysis from a commit that is read or cited has a current record at the declared commit | check | `current`, `stale` or `missing` |
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
    repository:
      url: https://github.com/owner/iris-pipeline
      commit: <commit id that added its records>
  - id: iris_knn
    repository:
      url: https://github.com/owner/iris-pipeline
      commit: <same commit id>
      checkout: remotes/iris
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

`iris.summary#baseline` is read through `.astra/records/baseline/summary.json` in the pipeline's repository at that commit. Its bytes are got from `results/baseline/summary.md` there (or by the tooling that holds them) and checked against that record. Nothing else of the pipeline is fetched to read it. `iris_knn` is checked out at `remotes/iris` and driven by `knn`. Its results go in `iris_rerun/results/knn/`.

## Implementation implications & migration

*Compatibility:* additive on top of RFC 0004. Every existing declaration has a `path` and is unchanged. It requires *Result provenance and layout* and *Data inputs*. It adds `url` to the `code` of *Result provenance and layout*'s records.

*Migration steps:* none. An analysis moved from this repository into another one swaps its declaration's `path` for a `repository`, with a `checkout` if it's driven.

## References

- [RFC 0004](0004-composition.md): declared analyses, addresses, driving and pins, which this RFC extends to analyses in other repositories
- [RFC 0003](0003-cross-universe-artifact-references.md) ([#52](https://github.com/LightconeResearch/astra-spec/issues/52), [#65](https://github.com/LightconeResearch/astra-spec/pull/65), reduced to universes in [#83](https://github.com/LightconeResearch/astra-spec/pull/83)): in-file universes and pins
- [Result provenance and layout](https://github.com/LightconeResearch/astra-spec/pull/91) (tracked in [#90](https://github.com/LightconeResearch/astra-spec/issues/90)): the records a declared analysis's results are read through, and the `code` this RFC adds `url` to
- [Data inputs](https://github.com/LightconeResearch/astra-spec/pull/92) (tracked in [#86](https://github.com/LightconeResearch/astra-spec/issues/86)): an input names a file committed with its analysis, so the declared commit fixes it
- [#55](https://github.com/LightconeResearch/astra-spec/issues/55): cross-repository artifact references, which this RFC is based on
- [#43](https://github.com/LightconeResearch/astra-spec/issues/43): an identity layer for addressing and resolving content across analyses
- [#66](https://github.com/LightconeResearch/astra-spec/issues/66): re-running and extending an analysis on other machines
