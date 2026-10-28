---
rfc: NNNN
title: Data inputs
status: Draft
authors:
  - Tom Charnock (@tomcharnock-lightcone)
created: 2026-10-28
tracking-issue: https://github.com/LightconeResearch/astra-spec/issues/86
superseded-by:
---

## Context

[RFC 0004](0004-composition.md) removed `type: analysis`, `ref`, `ref_version`, `use_outputs` and `from` from `Input`, since another analysis's elements are now read by address. That leaves an input with `id`, `label`, `description`, `type` and `source` ([#86](https://github.com/LightconeResearch/astra-spec/issues/86)).

`type` has one value left, `data`, so every input says the same thing.

`source` is described as "URI or path to the data source" and the spec calls it descriptive rather than prescriptive. In practice it is used as a path (`data/catalog_data.csv` in the spec), a loader (`sklearn.datasets.load_iris` in RFC 0004's iris example) or a URI (`s3://…` in the tests). A runner can't tell which of these it has been given, what a path is relative to or how to read it. `source` is also optional, so an input can name nothing to read at all.

Result provenance and layout ([#91](https://github.com/LightconeResearch/astra-spec/pull/91)) records the content hash of the file each input names, so every input has to name a file. [#58](https://github.com/LightconeResearch/astra-spec/pull/58) proposes the same rule for outputs' paths - relative to the folder of the `astra.yaml` and inside the workspace.

## Proposal

This RFC proposes that an input is a file committed with the analysis that declares it, named by its path. Data from anywhere else comes in through an output's recipe, which astra already has.

This RFC requires Result provenance and layout ([#91](https://github.com/LightconeResearch/astra-spec/pull/91)), which it refers to throughout: the record of each result holds the content hash of each input file it read and #91 leaves the files that inputs name out of an analysis's code.

The examples use RFC 0004's running example, whose root declares the input `data` that `subanalysis1.output1` reads as `root.data`.

### Modifications

#### 1. An input names a file

In the running example the root's input becomes

```yaml
# analysis/astra.yaml
inputs:
  - { id: data, path: data.csv }
```

where RFC 0004 had `{ id: data, type: data }`, and `Input` becomes

| Field         | Type   | Required | Meaning                                                  |
|---------------|--------|----------|----------------------------------------------------------|
| `id`          | string | Yes      | The local name outputs and recipes use                   |
| `label`       | string | No       | A short display name                                     |
| `description` | string | No       | What the data is                                         |
| `path`        | string | Yes      | The file's path relative to the folder of the `astra.yaml`     |

`path` replaces `source` and

- names one file. Data in many files is many inputs, or an output's recipe brings it in (section 3)
- stays inside the analysis's own folder and outside any analysis within it (a folder with an `astra.yaml` of its own). The data belongs with the analysis that uses it. Another analysis reads it by address as in RFC 0004, so `subanalysis1` reads `root.data` rather than declaring `../data.csv`
- names the file the analysis reads. What's committed is the file itself, or something standing in for it that tooling recognises - a git-annex link or a Git LFS pointer at the path, or a DVC file beside it. A large file therefore needn't be in git's history and how its bytes are kept is up to the tooling. Something standing in for the content isn't the content

No hash is declared in `astra.yaml`. A change to an input's file only stales the results that read it (#91, sections 3 and 4). An analysis's code (#91, section 3) also leaves out what stands in for an input's file, such as a DVC file beside it.

#### 2. `type` is removed

Its one value, `data`, says nothing about an input that every input doesn't already say.

#### 3. Data from outside the repository

Data that isn't committed with the analysis comes in through an output whose recipe gets it - a download, a loader, a query. The output is built once, or per universe when it depends on a decision such as which data release to use. If the root's data in the running example came from outside, `data` would be an output instead, here per universe since it depends on `a`

```yaml
# analysis/astra.yaml
outputs:
  - id: data
    type: data
    format: csv
    decisions: [a]
    recipe:
      command: python src/get_data.py --option {decisions.a} --out {output}
```

Nothing that reads `root.data` changes. Each of the output's results has a provenance record like any other result: the code that got the data and the content hash of what came back. Getting the data again and getting different bytes shows as a different hash. The spec names no way of getting data, so any tool can be used to get it.

### What validators check

| Rule | Severity |
|---|---|
| An input's `path` is relative and without `..` | error |
| An input's file isn't inside another analysis's folder | error |
| An input's `path` names a file (its content, or something standing in for it) | error |

`type` and `source` are no longer valid fields of `Input`. Only committed files are run (#91), so validators don't check whether an input's file is committed.

## Examples

### The iris pipeline

In RFC 0004's Example 2 the root of `iris_pipeline` declares its data as an input with a loader

```yaml
# iris_pipeline/astra.yaml
inputs:
  - { id: iris_data, type: data, source: sklearn.datasets.load_iris }
```

With this RFC the loader names no file, so the data becomes an output built once whose recipe loads it and writes it out

```yaml
# iris_pipeline/astra.yaml
outputs:
  - id: iris_data
    type: data
    format: csv
    recipe:
      command: python src/load.py --loader sklearn.datasets.load_iris --out {output}
```

An input and an output are read by address in the same way, so `split`'s `inputs: [iris_data]` and `feature_extraction`'s `inputs: [iris.iris_data]` don't change. The data is loaded once and its record holds the content hash of what the loader gave.

## Implementation implications & migration

*Compatibility:* breaking - `type` was required and `source` becomes a required `path` with a narrower meaning. Builds on RFC 0004 and the RFCs on Analyses in other repositories and Result provenance and layout.

*Migration steps:*

- remove `type: data`
- a `source` naming a file in the analysis's folder becomes `path`
- an input naming a file in another analysis's folder moves to that analysis and is read by address
- any other `source` (a loader, a URI, a dataset id), or none, becomes an output built once whose recipe gets the data. (If the id is kept the same all the rest of the analyses that use it don't change).

## Questions or objections

- **Credit for data from outside:** where data from outside the repository comes from (a DOI or a URL) is only held in the recipe and the description. Whether astra should say more is left open until attribution and trust are dealt with.

## Future possible RFCs

- **Fetching by content hash:** a project lists where the bytes of its inputs and results are kept (a git-annex remote, a bucket, a cache) and tooling fetches them from there by their content hash ([#66](https://github.com/LightconeResearch/astra-spec/issues/66)).
- **Very large data:** data read where it is rather than copied, on a cluster or in a bucket (#66).
- **Inputs of many files:** a dataset split over many files, or a format that is a folder such as Zarr.

## References

- [RFC 0004](0004-composition.md): declared analyses and addresses (reading an input from another analysis)
- Analyses in other repositories ([#89](https://github.com/LightconeResearch/astra-spec/pull/89)): which Result provenance and layout builds on
- Result provenance and layout ([#91](https://github.com/LightconeResearch/astra-spec/pull/91)): each result's record holds the content hash of every input file it read
- [#86](https://github.com/LightconeResearch/astra-spec/issues/86): the review of `Input`'s fields
- [#58](https://github.com/LightconeResearch/astra-spec/pull/58): `Output.target` and its rule for paths
- [#66](https://github.com/LightconeResearch/astra-spec/issues/66): sharing input and output files so an analysis can be run on another machine
