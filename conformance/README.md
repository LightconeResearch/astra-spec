# The ASTRA conformance suite

The conformance suite is a set of cases that an implementation of ASTRA runs
to check that it gives the verdicts the
[specification](../docs/specification.md) gives. The suite is informative:
where a case and the specification disagree, the specification wins, and the
case is wrong.

## Layout

| Path | Holds |
|---|---|
| `documents/valid/` | documents that break no parse or schema rule |
| `documents/invalid/` | documents that each break one |
| `analyses/<NNN>-<what>/` | one analysis case each, for the validator |
| `expected.schema.json` | the JSON Schema of an analysis case's `expected.json` |

There are two kinds of case. A document is one file, judged by the parse and
schema layers ([Rules](../docs/specification.md#rules)). An analysis
case is a git repository, judged by a validator.

## Documents

A document is an `astra.yaml`, named `Analysis-<nnn>-<what>.yaml`, or a
record, named `ProvenanceRecord-<nnn>-<what>.json`. It is read as the parse
layer of [Rules](../docs/specification.md#rules) says, and checked against
`analysis.schema.json` or `provenance.schema.json`, each error given its code
as [Schema files](../docs/specification.md#schema-files) says.

An invalid document starts with two comment lines, and a third where its one
break also brings an error somewhere else:

```yaml
# rule: <CODE>
# fails at: <location>
# also: <CODE> at <pointer>
```

`<location>` is a JSON Pointer, `(root)` for the whole document, or `parse`,
and `<pointer>` a JSON Pointer or `(root)`. A record can't hold a comment, so
its lines are in a file beside it with the same name and `.header` in place
of `.json`. A comment at the start of a valid document, or a valid record's
`.header`, is a note.

An implementation gives each document a set of pairs of a code and a pointer,
over the parse and schema layers. A valid document gives none. An invalid one
gives exactly the pair of its `# rule:` and `# fails at:` lines, and that of
its `# also:` line if it has one. `(root)` is the pointer `""`. `parse` means
that the file fails to parse: its code is reported for the whole file, so
only the code is compared, and a `parse` document has no
`# also:` line.

A validator can run an `astra.yaml` document as the `astra.yaml` of a
repository with one commit, and keep only the parse and schema codes it
reports for that file. It runs with no network, since some documents declare
analyses at remote URLs.

## Analyses

An analysis case is a folder that holds:

- `files/`: the files of the repository's working tree;
- `setup.sh`, where one commit of every file isn't enough: a script that
  makes the case's repositories and their history;
- `expected.json`: what validating the analysis gives.

`files/` holds no `.gitignore`, which git would apply in astra-spec's own
repository, and no path that astra-spec's `.gitignore` ignores, which that
repository would leave out. `setup.sh` writes any such file in the working
folder.

**Building a case.**

1. Make an empty working folder, in no git repository, and copy `files/`
   into it.
2. Without `setup.sh`, in the working folder, run `git init`,
   `git add --all` and `git commit --message files`: one commit holds every
   file.
3. With `setup.sh`, run `sh -eu <the case>/setup.sh` in the working folder.
   The script stays in the case, out of the working folder. For an analysis
   outside a repository
   ([`NOT_IN_REPOSITORY`](../docs/specification.md#rules)),
   it leaves the working folder in no repository.

The commands of step 2 and the script run with `PATH` and these variables
only:

| Variable | Value |
|---|---|
| `HOME` | an empty folder outside the working folder |
| `GIT_CONFIG_NOSYSTEM` | `1` |
| `GIT_AUTHOR_NAME`, `GIT_COMMITTER_NAME` | `ASTRA conformance` |
| `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_EMAIL` | `conformance@astra.invalid` |
| `GIT_AUTHOR_DATE`, `GIT_COMMITTER_DATE` | `2026-01-01T00:00:00Z` |
| `GIT_CEILING_DIRECTORIES` | the working folder's parent |
| `GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_0`, `GIT_CONFIG_VALUE_0` | `1`, `protocol.file.allow`, `always` |
| `ASTRA_CASE_REMOTES` | an empty folder outside the working folder, removed with the case, where `setup.sh` makes any bare repository the case needs |

So no configuration of the user's or the system's applies, git adds a
submodule from a `file://` URL, which it otherwise refuses, and git looks for
no repository above the working folder. A case built twice in the same git
object format has the same commit ids, unless a commit holds a remote's URL.

A file can't hold the id of a commit that `setup.sh` makes, so it holds
`@commit:<tag>@` in its place. The script tags the commit, then writes its id
over the placeholder before it commits the file, as case
`058-declared-analysis-invalid-at-its-commit`'s does. A remote's URL names
`ASTRA_CASE_REMOTES`, which differs from one build to the next, so a file
that must hold it holds `@url:<name>@` in its place. The script makes the
remote as the bare repository `$ASTRA_CASE_REMOTES/<name>`, and writes
`file://$ASTRA_CASE_REMOTES/<name>` over the placeholder. No placeholder is
left in the working folder.

**Validating.** The validator validates the analysis in the folder `root` of
the working folder, with `GIT_CEILING_DIRECTORIES` as above, the case's bare
repositories still in `ASTRA_CASE_REMOTES`, and nothing kept from another
case, such as a cache.

**`expected.json`** follows `expected.schema.json`:

| Field | Holds |
|---|---|
| `about` | what the case is, in one sentence |
| `root` | the folder of the analysis to validate, from the top of the working folder; `.` when left out |
| `valid` | whether the analysis is valid ([Rules](../docs/specification.md#rules)) |
| `must_report` | the diagnostics that must be reported, each a `code` and, where they matter, a `file` and, for a parse or schema code, a `pointer` |
| `must_not_report` | the codes that must be reported nowhere |

`about` and `valid` are always given, and no list is empty.
Each code is that of a parse, schema or validator rule of `rules.json`, and
`valid` is false exactly when `must_report` holds a `MUST` code. A `file` is
the path of the file the diagnostic is in, from the top of the repository
that holds it, read in the working tree or at a commit. A `pointer` is a JSON Pointer into it, `""`
for the whole file. An entry gives a `pointer` only with its `file`, and only
for a parse or schema code: the specification places those
([Schema files](../docs/specification.md#schema-files)), and where in its
file a validator code is reported is the tool's choice, which the suite
doesn't test. This is case `015-input-is-a-folder`'s:

```json
{
  "about": "An input whose path names a folder rather than a file.",
  "valid": false,
  "must_report": [
    {"code": "MISSING_INPUT_FILE", "file": "astra.yaml"}
  ]
}
```

**Comparing.** The validator's report agrees with `expected.json` when:

- it finds the analysis valid exactly when `valid` is true;
- each entry of `must_report` is matched by a diagnostic with its `code`, and
  with its `file` and `pointer` where the entry gives them;
- no diagnostic has a code of `must_not_report`.

Any other diagnostic is allowed: a case says what must and mustn't be
reported, not everything that is.

## Running it

astra-spec's `just test` checks the documents with astra-spec's own reading
of the parse layer of Rules and the JSON Schemas (`tests/test_fixtures.py`),
and checks that each analysis case is well formed and builds
(`tests/test_conformance.py`). astra-spec has no validator, so it validates
no analysis case.

An implementation runs the cases of the specification it implements, from a
checkout of astra-spec at that version's tag. It reads each document and
compares its pairs, and builds, validates and compares each analysis case,
each as above.

## What isn't in it

There is no case whose verdict a YAML or JSON library decides rather than the
specification, such as a tab as separation or a file in UTF-32, nor one for
what the specification leaves to tools, such as a key that isn't a string, a
YAML `.inf` or `.nan`, or a number beyond a double's range: nobody writes
these.
