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

[RFC-0004](0004-composition.md) made every analysis a directory with its own `astra.yaml`, declared by another analysis with `{ id, path }` and used through addresses (`<id>.<element>`). To keep that RFC short, a declared `path` had to be relative and inside the repository of a top-level analysis. Anything outside that repository was left for a later RFC building on [#55](https://github.com/LightconeResearch/astra-spec/issues/55).

Omitting anything outside the top-level repository makes building on existing work disconnected from the existing work itself, e.g.

- comparing earlier commits or releases of the same repository
- using the upstream repository of a fork
- reusing another astra analysis in a different repository altogether

It is technically possible to perform the above points by copying the analysis in or adding it as a git submodule. However, astra cannot say that a declared analysis comes from another repository at a commit. With a submodule git knows the URL and the commit while `astra.yaml` doesn't which prevents giving the remote analysis an identity independent of the declaring analysis.

#55 proposed putting the repository and its revision into each reference, first as `OWNER/REPO@REF.ARTIFACT` and then as `source@ref:subanalysis:output#universe` with the sources declared in their own `sources:` block. [#43](https://github.com/LightconeResearch/astra-spec/issues/43) similarly asks for one pointer to another analysis that fixes its revision.

## Proposal

This RFC proposes that a declaration can name a repository and a commit to get an analysis from. In this short RFC, the analysis is checked out at the declaration's `path` and from then on it is an analysis like any other - addresses, pins and driving from RFC-0004 apply unchanged and references don't change at all.

RFC-0004 already allows a declared analysis to be a git submodule, which records a URL and a commit. Declaring a remote can therefore look like extra machinery for the same thing. However, having the URL and commit in `astra.yaml` declares an identity for the remote. The motivation for the simplicity of this RFC is that later RFCs could record that identity as the provenance of the code behind each result and use it to address a remote's artefacts without pulling the analysis at all.

### Modifications

#### 1. Declaring a remote

Imagine using RFC-0004's running example (Example 1) and committing it at the top level of a repository of its own, `https://github.com/owner/analysis` for example. A new analysis, `followup`, declares it

```yaml
# followup/astra.yaml
analyses:
  - id: upstream
    path: remotes/upstream
    repository:
      url: https://github.com/owner/analysis
      commit: <full commit id>
```

where `AnalysisDeclaration` gains one optional field

| Field        | Type         | Required | Meaning                                                      |
|--------------|--------------|----------|--------------------------------------------------------------|
| `repository` | `Repository` | No       | The repository and commit the declared analysis comes from   |

with

| Field    | Type   | Required | Meaning                                                    |
|----------|--------|----------|------------------------------------------------------------|
| `url`    | string | Yes      | Where git can fetch the repository from                    |
| `commit` | string | Yes      | The full id of the commit                                  |

Without a `repository` a declaration means exactly what it means in RFC-0004. With `repository`

- `path` is where the remote is checked out and where its recipes run. It stays relative and inside the declarer's repository as in RFC-0004
- declarations checked out at the same path must name the same commit
- the remote is the analysis at the top level of its repository at that commit and must be valid as that repository's top-level analysis, so nothing it declares by `path` points outside it. If that analysis has subanalyses they can be reached by address through it (`upstream.subanalysis3.output3`) as for any declared analysis
- declarations can form cycles within a repository as in RFC-0004, but not across repositories since a commit can only name a commit that existed before it
- only a full commit id is accepted (40 hexadecimal digits, or 64 in a SHA-256 repository). A branch or a tag moves and a shortened id can become ambiguous as a repository grows

An earlier commit of the declarer's own repository is declared in just the same way, by the repository's URL, which means that commit has to be available there

```yaml
# followup/astra.yaml
analyses:
  - id: previous
    path: remotes/previous
    repository:
      url: https://github.com/owner/followup
      commit: <full commit id of previous commit>
```

#### 2. Identity and where to get it

The commit id is the remote's identity. Two declarations naming the same commit name the same analysis. The URL only says where to get it - a fork or a mirror with the same commit gives the same analysis.

If there is nothing at `path` the commit is fetched from the URL and checked out there. If there is something already there it must be that commit with none of the files committed in it changed. Files added afterwards, such as results built in the checkout, aren't part of the commit and so validators could still see the commit at that path. Tooling could also update a checkout when the declared commit is changed. 

#### 3. Using a remote

Once it is checked out a remote is used exactly as RFC-0004 describes. `followup` can read the remote's result in one of the remote's own universes with a pin (or just by address if the result is not built in a universe)

```yaml
# followup/astra.yaml
outputs:
  - id: report
    ...
    inputs: [upstream.summary#u1, upstream.subanalysis3.output3]
```

In the form proposed in this RFC (where remote analyses are checked out as subanalyses), an analysis can also drive the remote from its own universes. As in RFC-0004, reading one of the remote's own universes whilst also driving it takes a second declaration. Both declarations can be checked out at the same path since two ids at one path are one analysis

```yaml
# followup/astra.yaml
analyses:
  - id: upstream
    path: remotes/upstream
    repository:
      url: https://github.com/owner/analysis
      commit: <full commit id>
  - id: upstream_driven
    path: remotes/upstream
    repository:
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

`upstream_driven.summary` is read in `w1`, with every decision of the remote set by `followup`'s universe, whilst `upstream.summary#u1` is the remote's own `u1`.

#### 4. Results

Results belong to the universe that produced them, as in RFC-0004. A checked-out remote is a declared analysis like any other, so its results follow the same rules

- Results of a driven remote belong to the driver, e.g. `followup/results/w1/upstream_driven.summary.<format>`
- Results in the remote's own universes and its outputs built once belong to the remote, e.g. `followup/remotes/upstream/results/u1/summary.<format>`. They are fixed by its commit
- Results that the remote has committed come with the checkout

As in RFC-0004 where results go on disk isn't enforced and is left to [#72](https://github.com/LightconeResearch/astra-spec/issues/72).

Driving a remote will still need its checkout, since its recipes have to run. Driving falls out naturally from the proposition here.

#### 5. Reaching a remote

A published analysis SHOULD only declare remotes that its readers can fetch. This is a SHOULD rather than a MUST because a remote may well be private whilst the analysis is being worked on.

A remote that can't be fetched is an error that names its declaration. If a copy of the remote is already at `path`, validators and runners can be run offline without fetching anything.

### What validators check

| Rule | Severity |
|---|---|
| A `repository` has a `url` and a `commit` that is a full commit id | error |
| A declaration's `path` is relative, stays inside the root's repository and holds an `astra.yaml` which is determined once checked out for a remote | error |
| A remote is valid as the top-level analysis of its own repository, so nothing it declares by `path` points outside that repository | error |
| Declarations checked out at the same `path` name the same `commit` | error |
| A remote is available and correct: an analysis at `path` is at the correct commit with none of its committed files changed, or there is nothing at `path` and the URL can be reached and has the commit | error |

The second row extends RFC-0004's row for a declaration's `path` to remotes. Every other rule of RFC-0004 applies to remotes as it is.

## Examples

### The iris pipeline from its own repository

Say that `examples/iris_pipeline` from RFC-0004 is committed at the top level of a repository of its own. This is then used by a new analysis that tries k-NN on three components and reports it beside the pipeline's own baseline

```yaml
# iris_rerun/astra.yaml
id: iris_rerun
version: "0.1.0"
name: The iris pipeline again with k-NN
analyses:
  - id: iris
    path: remotes/iris
    repository:
      url: https://github.com/owner/iris-pipeline
      commit: <git commit id>
  - id: iris_knn
    path: remotes/iris
    repository:
      url: https://github.com/owner/iris-pipeline
      commit: <same git commit id>
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

`iris_knn` is driven by `knn` and its results go in `iris_rerun/results/knn/`. `iris` is the same checkout but is not driven and whose own universes are reference (and so the artefacts go into the checkout).

## Implementation implications & migration

*Compatibility:* additive on top of RFC-0004. Declarations without a `repository` are unchanged, which covers every existing analysis.

*Migration steps:* none. Moving an analysis from this repository into another one only adds a `repository` to its declaration and keeps its `path`.

## Other RFCs that could spawn out of this RFC

- **Results without re-running:** a remote's results in its own universes are fixed by its commit. They could be fetched rather than rebuilt once results are recorded and stored somewhere they can be found ([#72](https://github.com/LightconeResearch/astra-spec/issues/72)).
- **Remotes without a checkout:** once results can be fetched an analysis that only reads a remote's results wouldn't need its files at all. `path` could then be left out. Driving a remote would still need a checkout as in this RFC, so remotes would have two uses - driven from a checkout, or read by address without one.
- **A hash of the content:** for copies got from outside git, such as an archive or a store, where there is no commit to check.
- **References in prose and patterns:** citing a remote's element in a rationale, or many outputs at once (`source:output_*` in #55). These would be features of addresses in general.

## References

- [RFC-0004](0004-composition.md): declared analyses, addresses, driving and pins, which this RFC extends to analyses in other repositories
- [RFC-0003](0003-cross-universe-artifact-references.md) ([#52](https://github.com/LightconeResearch/astra-spec/issues/52), [#65](https://github.com/LightconeResearch/astra-spec/pull/65), reduced to universes in [#83](https://github.com/LightconeResearch/astra-spec/pull/83)): in-file universes and pins
- [#55](https://github.com/LightconeResearch/astra-spec/issues/55): cross-repository artifact references, which this RFC is based on
- [#43](https://github.com/LightconeResearch/astra-spec/issues/43): an identity layer for addressing and resolving content across analyses
- [#66](https://github.com/LightconeResearch/astra-spec/issues/66): re-running and extending an analysis on other machines
- [#72](https://github.com/LightconeResearch/astra-spec/issues/72): a canonical location for materialised outputs
