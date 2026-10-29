---
rfc: NNNN
title: Result provenance and layout
status: Draft
authors:
  - Tom Charnock (@tomcharnock-lightcone)
  - Francois Lanusse (@eiffl)
created: 2026-10-26
tracking-issue: https://github.com/LightconeResearch/astra-spec/issues/90
superseded-by:
---

## Context

[RFC 0004](0004-composition.md) says which analysis a result belongs to, but not where the result is or what made it. Currently a result is a file wherever a runner puts it, which leaves

- [#72](https://github.com/LightconeResearch/astra-spec/issues/72): no canonical location, so runners aren't interchangeable and evidence citing a result can't be checked mechanically
- [#43](https://github.com/LightconeResearch/astra-spec/issues/43) (its fourth point): no recorded provenance - nothing says what went into a result or which bytes came out
- [#66](https://github.com/LightconeResearch/astra-spec/issues/66): no way to share results across machines

A path alone says a file exists but not what the file looks like or what made it. This RFC gives every result a record of its provenance and a default place for its actual bytes, so that results can be checked without running anything.

## Proposal

A result is what a recipe made for one output in one universe (or once for an output built once). Whatever runs the recipes - the runner - writes a provenance record for each result it makes: what the result is and the run that made it. The record is stored in git, its location calculated from the result's address. The result's file is written to a default location worked out the same way and how it is stored from there is up to the tooling.

### Modifications

#### 1. Where results and their records go

A result belongs to an analysis as in RFC 0004 - it belongs to the analysis whose universe it was built in (or the analysis that declares it if it is built once). That analysis addresses a result by its *name* - the output's id, e.g. `output1` (which could be chained through declared analyses, e.g. `subanalysis1.output1`) and if it belongs to a particular universe also pinned to that universe (`subanalysis1.output1#u1`).

In the analysis it belongs to

- the record MUST be at `.astra/records/{universe}/{name}.json`, or `.astra/records/{name}.json` for an output built once
- the bytes SHOULD be at `results/{universe}/{name}.{format}`, or `results/{name}.{format}` for an output built once

Both paths are worked out from the address and a record is only the record of the result it names.

Records are tracked in git with the analysis, as its `astra.yaml` is, so they can be read whether or not the results' bytes are there. The records themselves are contained in a (hidden) store `.astra/` whilst tools are free to present the results in whatever views they like. By this we mean that although a runner writes each result to its default place (as above), the bytes needn't stay there. For example, imagine using git-annex or Git LFS to store results
- git-annex moves the results into its own store, `.git/annex/objects/...`, under a key made from the content hash and size (`SHA256E-s<size>--<SHA-256 hash>.<ext>`) and leaves a link at the default location
- Git LFS keeps the results in `.git/lfs/objects/...`, named by their content hash and commits a pointer file at the default location (`oid sha256:<SHA-256 hash>`, `size`)

Here we see that the default `results/` becomes a view of the actual bytes of the results. Of course the runner still needs to write to the default location, but the bytes aren't destined to survive there. It is for this reason the records must record the results' content hash and size. 

Keeping the bytes in a store, asked by content hash, is for a later RFC. The default place would then become a view of the store - links into it - rather than moving, and moving it would itself take an RFC since runners and checkers rely on it.

For RFC 0004's running example

```
analysis/
  .astra/records/
    summary1_u1.json
    subsummary1_u1.json
    subsummary1_v1.json
    u1/
      summary.json
      subanalysis1.output1.json
      subanalysis2.output2.json
      subanalysis3.output3_per_universe.json
      subsubanalysis1.output1.json
    u2/
      summary.json
      subanalysis1.output1.json
      subanalysis2.output2.json
      subanalysis3.output3_per_universe.json
      subsubanalysis1.output1.json
  results/
    <as in RFC 0004 section 5>
  subanalysis1/
    subsubanalysis1/
      .astra/records/v1/output1.json
      results/v1/output1.<format>
  subanalysis3/
    .astra/records/output3.json
    results/output3.<format>
```

**What's checked**

| Rule | Checked by | Result |
|---|---|---|
| A record names the result whose record is kept where it is | check | `missing` |
| A result's bytes are at its default place and match its record | check | `present`, `modified` or `absent` |

#### 2. What a record holds

Records have a schema of their own `provenance.yaml` beside `analysis.yaml`, which maps them onto W3C PROV-O.

`analysis/.astra/records/u1/subanalysis1.output1.json`:

```json
{
  "version": "0.1.0",
  "address": "subanalysis1.output1#u1",
  "content_hash": "sha256:<SHA-256 hash>",
  "size": <size>,
  "generated_by": {
    "commit": "<git commit id>",
    "inputs": [
      { "entry": "root.data", "content_hash": "sha256:<SHA-256 hash>", "size": <size> }
    ],
    "environment": {
      "kind": "file",
      "value": "envs/sandbox/uv.lock",
      "content_hash": "sha256:<SHA-256 hash>"
    },
    "runner": { "id": "example-runner", "version": "1.2.0" },
    "started": "2026-10-26T14:00:00Z",
    "finished": "2026-10-26T14:00:02Z"
  }
}
```

- `version`: *required* - the version of the astra specification the record follows
- `address`: *required* - the result as the analysis it belongs to addresses it - its name and `#` with its universe if it was built in a universe
- `content_hash`: *required* - the SHA-256 of the result's bytes
- `size`: *required* - their size in bytes
- `generated_by`: *required* - the run of the recipe that made the result
  - `commit`: *required* - the full id of the git commit the recipe ran from (it pins every file of the code and every `astra.yaml` - an analysis in a submodule through the commit the submodule is pinned at)
  - `inputs`: *required if the output lists any* - for each input the output lists, its `entry` as listed in the `astra.yaml` and the `content_hash` and `size` of what the recipe read - another output's result or the file an external input names.
  - `environment`: *required* - what the recipe ran in (section 3)
    - `kind`: `file` or `uri`
    - `value`: for `file` the file's path from the top level of the repository the record is committed in, for `uri` a URI naming the environment
    - `content_hash`: *required for `file`* - the file's SHA-256
  - `runner`: *required* - the runner that ran the recipe
    - `id`: *required* - its name, ideally unique (a URI, say)
    - `version`: *required* - its version
  - `started`, `finished`: when the recipe started and finished, in UTC ending in `Z`

Beyond its `version`, a record holds only what the commit it names can't give. The output's declaration, the options of its decisions and its format are all in the `astra.yaml` files at that commit. We can imagine tooling that can reconstruct all supplementary information given the commit.

Every hash names its algorithm (`sha256:<SHA-256 hash>`).

Converted to RDF through the schema, a record is PROV-O.

The information in or lacking from these records will start to allow us to build the level of reproducibility of a result. Without running anything, the record tells us whether a result is unchanged (section 4) and whether the bytes at hand correspond to what was produced. Two records of the same result with the same commit, inputs and environment (from another machine, say) show whether a result reproduces when their `content_hash` is the same. How well a result can be made again rests on its runner, which section 3 holds to recreating its environment. A record doesn't say whether its runner enforced the rules of section 3.

A record holds only these fields, and the order they're written in carries no meaning: two records with the same keys and values are the same record.

**What's checked**

| Rule | Checked by | Result |
|---|---|---|
| A record matches the record schema: its required fields, a full commit id, hashes that name their algorithm, a `file` environment's hash, times in UTC ending in `Z` | check | `missing` |

#### 3. What a runner does

A runner

- writes a record for each result it makes in the analysis the result belongs to
- only runs committed code: while the repository has changes other than the results and records it writes itself the runner refuses to run
- records the environment each recipe ran in, enough for the runner, at the version it records, to recreate that environment and make the result again. The same `kind` and `value` in `environment` always name the same environment
- SHOULD let someone see what an environment it recorded holds

A record names the commit its recipe ran from so it has to be committed in a later commit. Records and results aren't *code* so that later commit doesn't make them stale. The commit a record names has to stay in the history of the commits that hold the record, so branches with records should be merged rather than squashed or rebased.

An analysis's *code* is the files in its directory (see [Questions or objections](#questions-or-objections)) other than

- its `astra.yaml`
- the files its inputs name
- its results and records
- any directory inside it with an `astra.yaml` of its own - another analysis, declared or not, with its own code

Its recipes

- MUST use no other code. Anything else they use is an input or part of the environment, so a recipe that needs a subanalysis's work reads one of its outputs
- MUST read the files the analysis's inputs name only through the inputs their output lists

A runner MAY enforce both rules, and a checker MAY ignore files that can't change a result, such as git's own configuration files.

In the running example, with scripts in `analysis/src/` and `analysis/subanalysis1/src/`, the root's code would be `analysis/src/` and `subanalysis1`'s is `analysis/subanalysis1/src/`. A `README` beside either would also be considered code too.

**What's checked**

| Rule | Checked by | Result |
|---|---|---|
| Only committed code is run | runner | refuses to run |
| A result's code has no uncommitted changes | check | `stale` |
| Recipes use no other code, and read the files inputs name only through their output's inputs | runner (MAY, with a sandbox say) | the recipe fails |
| A runner can recreate the environment it recorded, at its version, and make the result again | running the record again with that runner | the same `content_hash` |

#### 4. When a result is unchanged

A record guarantees what its result was made from at the commit it names, and nothing beyond that commit. The commit never holds its own record, which comes in a later commit (section 3).

At a later commit, a result is *unchanged* if, since the commit in its record, nothing has changed in

- its output's declaration: its recipe's command, inputs, decisions and format
- the options of its decisions
- the content of its inputs
- its environment's file, for an environment of kind `file`
- the code of the analysis that declares its output

Unchanged suggests, but doesn't guarantee, that the recipe would make the same result again. Otherwise the result is stale. This means a result can become stale when

- its output's declaration has changed
  - the order of its inputs counts, since `{inputs}` passes them to the recipe in that order
  - the order of its decisions doesn't, since each reaches the recipe by name
- an option of one of its decisions has changed
- an input file it reads has changed
- its environment's file has changed
- a script of the analysis that declares its output has changed
- a result it reads is stale. Once that result is rebuilt, this one is unchanged again if the rebuilt bytes are the same

Nothing else counts: editing a finding, a description or another output leaves a result unchanged, and an environment named by a URI is recorded but not compared.

In the running example

- editing `finding1` leaves every result unchanged
- setting `u2`'s `subanalysis1.b` to `b1` makes `subanalysis1.output1#u2` stale, and with it `subanalysis2.output2#u2`, `subanalysis3.output3_per_universe#u2` and `summary#u2`
- changing a script in `analysis/subanalysis1/src/` makes `subanalysis1.output1` stale in both universes, and with it `subanalysis2.output2`, `subanalysis3.output3_per_universe` and `summary` in both. Once `subanalysis1.output1` is rebuilt in a universe, those three are unchanged again there if its bytes are the same
- `subsubanalysis1`'s results stay unchanged throughout

How a checker finds this out is up to the tooling.

**What's checked**

| Rule | Checked by | Result |
|---|---|---|
| Each planned result is unchanged | check | `unchanged`, `stale` (saying what changed) or `missing` (no record, or a file breaking a rule of section 1 or 2) |

#### 5. Evidence

Evidence citing a result is checked through the record its address names: the address, pinned when the output is built per universe, names exactly one result. A check covers the evidence of the analysis it's run on. Nothing changes in `Evidence`.

**What's checked**

| Rule | Checked by | Result |
|---|---|---|
| Evidence citing a result cites an unchanged one | check | the result's `unchanged`, `stale` or `missing` |

## Examples

### Example 1: `iris_pipeline`'s results in git-annex or Git LFS

`iris_pipeline` from RFC 0004, with its data loaded by a recipe (`iris_data`), has 14 results. They're built and recorded, the records are committed to git, and the results' bytes are added to git-annex (`git annex add results`) or to Git LFS (`results/** filter=lfs` in `.gitattributes`).

If someone clones the published analysis they would have every record and none of the results' bytes. At the place of, for example, `classification.accuracy#baseline` git-annex would have a link named by a key and LFS would have a pointer file. Both carry the content hash and size in its record

```
# provenance record
$ cat .astra/records/baseline/classification.accuracy.json
  ...
    "content_hash": "sha256:4a90448562c7379100ce2d32d1b0700ea6439ce84ce79d8b56802a449d4caf52",
    "size": 732,
  ...
```
  
```
# git-annex
$ git annex lookupkey results/baseline/classification.accuracy.json
SHA256E-s732--4a90448562c7379100ce2d32d1b0700ea6439ce84ce79d8b56802a449d4caf52.json
```

```
# Git LFS
$ cat results/baseline/classification.accuracy.json
version https://git-lfs.github.com/spec/v1
oid sha256:4a90448562c7379100ce2d32d1b0700ea6439ce84ce79d8b56802a449d4caf52
size 732
```

The hash of the link or pointer file itself would not be the content hash in the provenance record, but the hash of the file at that place would agree after running `git annex get results/baseline/classification.accuracy.json` or `git lfs pull --include results/baseline/classification.accuracy.json` for example (where this would still leave the other 13 results absent).

Tooling that recognises these pointers could tell the two cases apart: a pointer naming the record's content hash would mean the bytes are `absent` (they exist and can be fetched), while other bytes, or a pointer naming another hash, mean they're `modified`.

If other bytes were put at that place, say `mlp_svm`'s accuracy (also 732 bytes), a check would find `classification`'s accuracy as being modified. The result would still be unchanged, since its record says what the result should be and it's what shows the bytes are wrong.

## Implementation implications & migration

*Compatibility:* additive. A new record schema sits beside the analysis schema and nothing changes in `astra.yaml`. It requires astra 0.1.0 or later (where every output has a `format`) and RFC 0004.

*Runners:* a runner writes a record for each result it makes, writes the bytes to their default place, refuses to run while the repository has uncommitted changes other than its results and records, and records environments it can recreate at its version. Anything more a runner records about a result stays in its own files.

*Migration steps:* existing results have no record, so they're missing until a runner makes them.

## Questions or objections

- **What counts as code.** An analysis's code is its whole directory, less the exclusions in section 3, so editing a README or a `.gitignore` there makes its results stale. Code could instead be a fixed folder such as `src/`, or the paths an analysis declares, thoughts?

## Possible future RFCs

- **Result identity:** a key computed from what goes into a result, with the code each result uses rather than its analysis's whole directory, so that records and results can be kept by hash ([#43](https://github.com/LightconeResearch/astra-spec/issues/43)).
- **Fetching by content hash:** stores a project lists, asked by content hash, for inputs and results ([#66](https://github.com/LightconeResearch/astra-spec/issues/66)). As with git-annex today (section 1), a store could become the natural home of results, with the default place as its view.
- **Signed records:** a record is its runner's claim, and anyone could edit it. Signing records, as in-toto and SLSA sign build provenance, would let a reader trust a record as far as they trust its runner - and runners could be certified by re-running their records.

## References

- [RFC 0004](0004-composition.md): declared analyses, addresses and where results belong
- [#72](https://github.com/LightconeResearch/astra-spec/issues/72), [#43](https://github.com/LightconeResearch/astra-spec/issues/43), [#66](https://github.com/LightconeResearch/astra-spec/issues/66)
- [W3C PROV](https://www.w3.org/TR/prov-overview/)
- [in-toto attestations](https://github.com/in-toto/attestation) and [SLSA build provenance](https://slsa.dev/spec/v1.0/provenance): signed provenance, and trust in the builders that make it
- git-annex's `SHA256E` keys and the [Git LFS pointer specification](https://github.com/git-lfs/git-lfs/blob/main/docs/spec.md)
