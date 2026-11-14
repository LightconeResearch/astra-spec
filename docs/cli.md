# CLI reference

`astra` is the command line of [astra-tools](https://github.com/astra-project/astra-tools). It
validates ASTRA analyses, shows what they resolve to, and checks what was built against its
records. It reads ASTRA 0.1 files; ASTRA 0.0.x files need the 0.2 line of astra-tools
([Installation](installation.md#which-astra-it-reads)).

`astra` runs no recipe. A runner, such as lightcone-cli, builds the results and writes their
records, and `astra` reads them.

## Conventions

- **The analysis** a command reads is an `astra.yaml`, the root of its
  [stack](https://astra-spec.org/0.1/specification/#rules). `validate` takes the file or its
  folder, and with none validates every analysis under the current folder. `info` takes the
  file with `-f`, and by default finds the `astra.yaml` in the current folder or the nearest
  one above. `view`, `check` and `history` take **PATH**, the analysis's folder, the current
  folder by default.
- **Exit codes:**
    - 0 when the command answers;
    - 1 when the analysis breaks a `MUST`, a quote isn't verified, a planned result isn't
      `unchanged`, or what was asked for isn't there;
    - 2 for a usage error, an analysis that can't be read, a broken environment (git or the
      cache unusable, a folder that can't be written), or an internal error.
- **Output.** Problems are grouped by file, one per line, as `line:col level CODE message`. Each
  code is a rule of the specification, listed under
  [Rules](https://astra-spec.org/0.1/specification/#rules), or one of astra-tools' own:
  `UNSUPPORTED_SPEC_VERSION`, `REMOTE_UNREACHABLE` and `COMMIT_NOT_ANCESTOR`, and, with
  `validate --verify-evidence`, `EVIDENCE_PAPER_MISSING`, `EVIDENCE_PAPER_UNREADABLE` and
  `EVIDENCE_QUOTE_NOT_FOUND`. `NO_COLOR` turns colour off.
- **JSON.** `validate`, `info`, `view` and `check` take `--json`. Each JSON document names its
  shape, such as `astra-validation-reports/1`, and a shape changes only under a new name.
  `init --json` prints its convergence report, and `paper verify-quotes` reads and writes JSON.
- **The cache** keeps the commits fetched from remotes, the validity of analyses from a commit,
  the hashes of files, and papers with their extracted text and verified quotes. It sits outside
  every repository, and everything in it is safe to delete. It is `~/.cache/astra` on Linux and
  `~/Library/Caches/astra` on macOS; `ASTRA_CACHE_DIR`, an absolute path, moves it.
- `astra --help`, and `--help` after any command, give each command's options.
  `astra --version` gives astra-tools' version.

The examples come from a small analysis, line-fit. It declares another analysis, noisy-line, at
a commit, and fits a line to noisy-line's points two ways: by least squares, in a universe
`ols`, and by the Huber loss, in a universe `huber`. Its `comparison` reads both fits.

## Commands at a glance

| Command | What it does |
|---|---|
| [`astra init`](#astra-init) | Make a minimal analysis, or complete one |
| [`astra validate`](#astra-validate) | Validate an analysis and its whole stack |
| [`astra info`](#astra-info) | Show an analysis and its stack in brief |
| [`astra view`](#astra-view) | Show the analysis as it is in one universe |
| [`astra check`](#astra-check) | Check the records and bytes of the planned results |
| [`astra history`](#astra-history) | Show what git holds of a result's records over time |
| [`astra spec`](#astra-spec) | Describe the fields of ASTRA files |
| [`astra schema`](#astra-schema) | Show or export the LinkML schemas |
| [`astra guide`](#astra-guide) | Print the guide for agents |
| [`astra paper`](#astra-paper) | Keep papers by DOI, and verify quotes in them |

## `astra init`

```
astra init [DIRECTORY] [--check] [--json]
```

Converges DIRECTORY, the current folder by default, into a minimal analysis. It creates whatever
is missing (an `astra.yaml` with a `spec_version` and a label, a `.gitignore`, and a git
repository with a first commit) and never overwrites a file, so it is safe to run again; a
folder that already holds an `astra.yaml`, or any other file, is adopted. Where a git repository
already holds DIRECTORY, no new one is made inside it. Where git knows no user name and email,
the new repository gets no first commit.

| Option | Meaning |
|---|---|
| `--check` | Write nothing: say what would be created, and exit 1 if anything would |
| `--json` | Print the convergence report as JSON: `converged`, and the lists `created`, `repaired`, `unchanged` and `warnings` |

```console
$ astra init my-analysis
✓ created astra.yaml
✓ created .gitignore
✓ created .git
✓ Converged ASTRA analysis scaffold: my-analysis
$ cat my-analysis/astra.yaml
# ASTRA Analysis Specification

spec_version: "0.1.0"
label: "my-analysis"
$ astra init my-analysis
✓ my-analysis already converged
```

## `astra validate`

```
astra validate [FILE] [-e|--verify-evidence] [--skip-evidence] [--json] [--offline]
```

Checks every parse, schema and validator rule
([Rules](https://astra-spec.org/0.1/specification/#rules)) over the whole stack: the analysis
FILE names, an `astra.yaml` or its folder, and every analysis it declares, at their commits.
With no FILE, it validates every root analysis under the current folder: each `astra.yaml` that
no other one declares, hidden, vendored and `results/` folders skipped, and ends with a summary
line. It reads no results; `astra check` does. Exits 0 when every analysis is valid and 1 when
one breaks a `MUST`. A `SHOULD` that is broken is a warning and doesn't change the exit code.

| Option | Meaning |
|---|---|
| `-e`, `--verify-evidence` | Also verify each quote the evidence takes from a paper cited by DOI, in the paper the cache holds ([`astra paper add`](#astra-paper)) |
| `--skip-evidence` | Say nothing of the evidence: without it, an analysis that has evidence gets a note to run with `--verify-evidence` |
| `--json` | Print the reports as JSON (`astra-validation-reports/1`) |
| `--offline` | Fetch nothing: use only the commits already in the cache |

An analysis declared by `url` and `commit` is fetched into the cache, once.

```console
$ astra validate
astra.yaml
  4:11 error MISSING_INPUT_FILE `data.csv` names no file, and no stand-in of Git LFS, git-annex, DVC
  10:17 error UNRESOLVED_ADDRESS `method` names nothing: this analysis has no decision `method`
astra.yaml: invalid, 2 error(s), 0 warning(s)

1/1 file(s) failed validation: astra.yaml
```

With `--verify-evidence`, a quote that isn't verified is an error of the report, at its place in
`astra.yaml`, and the command exits 1:

- `EVIDENCE_PAPER_MISSING`, at the `doi`: the paper isn't in the cache;
- `EVIDENCE_PAPER_UNREADABLE`, at the `doi`: the text of the paper in the cache can't be read;
- `EVIDENCE_QUOTE_NOT_FOUND`, at the `quote`: the quote isn't in the paper. Where the evidence
  has a `location` that gives a page (`page=6`), the quote must be on that page; with none, it
  is found on any page.

Evidence that cites an output, as an `artifact`, is counted as skipped: `astra check` gives it
the status of the result it cites. A line sums up each of `prior_insights` and `findings`.

```console
$ astra validate -e
astra.yaml
  41:14 error EVIDENCE_PAPER_MISSING the paper of 10.1214/aoms/1177703732 isn't in the cache, so its quote isn't verified: run `astra paper add 10.1214/aoms/1177703732`
astra.yaml: invalid, 1 error(s), 0 warning(s)
Evidence (prior_insights): 0/1 verified, 1 failed

1/1 file(s) failed validation: astra.yaml
```

`--json` prints one document, with FILE or without: whether every analysis is valid, and each
analysis's report, whose `diagnostics` hold the evidence's errors too.

```console
$ astra validate --json
{
  "shape": "astra-validation-reports/1",
  "valid": true,
  "reports": [
    {
      "shape": "astra-validation-report/1",
      "root": "astra.yaml",
      "valid": true,
      "diagnostics": [],
      "unchecked": []
    }
  ]
}
```

## `astra info`

```
astra info [-f FILE] [-d] [-i] [-o] [--json]
```

Shows the analysis in FILE, by default the `astra.yaml` in the current folder or the nearest
folder above: its label and description, how many inputs, outputs, decisions and universes it
has, then each of them. With `-d` (`--decisions`), `-i` (`--inputs`) or `-o` (`--outputs`), only
those parts are shown. A switch shows the decision it switches on and its cases. Each other
analysis of the stack follows, the same way, headed by the address that reaches it and its file,
with its commit for one read at a commit. It checks nothing. `--json` prints every analysis of
the stack as JSON (`astra-info/1`), the root first. Exits 1 where there is no `astra.yaml`, or
no stack to show.

```console
$ astra info
Line fit
Spec version: 0.1.0

Fit a line to noisy-line's points, by least squares and by the Huber loss.

Inputs: 0 | Outputs: 2 | Decisions: 1 | Universes: 2
Layout: 1 sub-analysis

Inputs:
┏━━━━┳━━━━━━┳━━━━━━━━━━━━━┓
┃ ID ┃ Path ┃ Description ┃
┡━━━━╇━━━━━━╇━━━━━━━━━━━━━┩
└────┴──────┴─────────────┘

Outputs:
┏━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ID         ┃ Type  ┃ Recipe                                     ┃ Description                    ┃
┡━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ fit        │ table │ python3 src/fit.py {decisions.method}      │ The fitted slope and intercept │
│            │       │ {inputs.noisy.points} {output}             │                                │
│ comparison │ table │ python3 src/compare.py {inputs} {output}   │ Both fits, side by side        │
└────────────┴───────┴────────────────────────────────────────────┴────────────────────────────────┘

Decisions:
method: Fitting method
├── Rationale: Outliers pull a least-squares fit.
└── Options:
    ├── ols: Least squares
    └── huber: Huber loss

Universes:
  ols
  huber

Analysis: noisy  astra.yaml at 18cfe9d5695d7fc13a3d93bbbba2f6a644bd284d from file:///…/noisy-line
Noisy line
Spec version: 0.1.0

Inputs: 1 | Outputs: 1 | Decisions: 0 | Universes: 0

Inputs:
┏━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ ID     ┃ Path        ┃ Description ┃
┡━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ config │ config.json │             │
└────────┴─────────────┴─────────────┘

Outputs:
┏━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ ID     ┃ Type ┃ Recipe                                         ┃ Description ┃
┡━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ points │ data │ python3 src/points.py {inputs.config} {output} │             │
└────────┴──────┴────────────────────────────────────────────────┴─────────────┘

Decisions:
```

## `astra view`

```
astra view UNIVERSE [PATH] [--json]
```

Shows the analysis as it is in UNIVERSE. For each analysis of the stack, it gives whether that
analysis is built in UNIVERSE
([Elements](https://astra-spec.org/0.1/specification/#elements)); the option selected for each
decision, or that the universe doesn't use it
([Results](https://astra-spec.org/0.1/specification/#results)); each output's result and where
it goes, or why it has none; and the case each switch takes. `--json` prints it as
`astra-universe-view/1`. Exits 2 where the analysis has no universe UNIVERSE.

```console
$ astra view huber
universe huber
astra.yaml  built
  method       huber
  fit          fit#huber  results/huber/fit.json
  comparison   comparison  results/comparison.json
astra.yaml at 18cfe9d5695d7fc13a3d93bbbba2f6a644bd284d from file:///…/noisy-line  built
  points       points  results/points.csv at 18cfe9d5695d7fc13a3d93bbbba2f6a644bd284d
```

## `astra check`

```
astra check [PATH] [--at REV] [--json]
```

Checks each planned result's record and bytes, at each of its places
([Results](https://astra-spec.org/0.1/specification/#results)):

- the record is `unchanged`, `stale` (something it was made from has changed since) or `missing`;
- the bytes are `present` (the ones the record gives, at their default place) or `absent`.

Then it gives each evidence the status of what it cites. A stale result comes with the reasons.
Where the analysis breaks a `MUST`, its errors come first, and only the results they leave
determined are shown. Exits 0 when every planned result and evidence is `unchanged`, and 1
otherwise.

| Option | Meaning |
|---|---|
| `--at REV` | Check the analysis as it is at the commit REV names, with its records and bytes there |
| `--json` | Print the report as JSON (`astra-check-report/1`) |

Here the `huber` universe has been edited to select `ols`, and nothing has been built since:

```console
$ astra check
.astra/records/points.json at 18cfe9d5695d7fc13a3d93bbbba2f6a644bd284d  points  unchanged  present
.astra/records/ols/fit.json  fit#ols  unchanged  present
.astra/records/huber/fit.json  fit#huber  stale  present
  error STALE_RESULT `method` selects `ols` in `huber`, where it selected `huber` at 3b70b4352de6
.astra/records/comparison.json  comparison  stale  present
  error STALE_RESULT `fit#huber`, which it reads, is stale
astra.yaml
  53:19 error STALE_EVIDENCE `comparison` cites `comparison`, whose record is stale
astra.yaml: 4 place(s) of planned results, 2 unchanged, 2 stale, 0 missing; 0 absent
```

An input whose content is kept outside git, behind a stand-in
([Elements](https://astra-spec.org/0.1/specification/#elements)), is compared by the hash the stand-in
gives. astra-tools recognises Git LFS pointers, git-annex links and DVC files, and fetches none
of them. Other packages, a runner say, can add their own stand-ins through the entry-point group
`astra.standins`.

## `astra history`

```
astra history timeline ADDR [PATH]
astra history lineage ADDR [PATH] [--used-by]
astra history get ADDR@REV [PATH]
astra history find (--hash H | --environment IRI) [PATH]
```

Reads a result's records over time, from git. ADDR is a result's address, as its record gives it
(`fit#ols`, `comparison`), which `astra check` lists. A record's versions are its file at each
commit along HEAD's history that changed it. Exits 1 where the analysis breaks a `MUST` or what
is asked for isn't in git, and 2 where ADDR names no planned result or REV names no commit.

| Command | What it shows |
|---|---|
| `timeline ADDR` | Each version of the result's record, newest first: the commit that changed it, and the hash, size, commit, end and environment it gives |
| `lineage ADDR` | What the result was made from, as its record at HEAD gives it, down to the input files. With `--used-by`, the planned results whose records list it instead |
| `get ADDR@REV` | The bytes the result had at the commit REV names (a commit, a branch, a tag), checked against its record there, written to standard output |
| `find` | The versions of planned results' records whose bytes have the hash H (`sha256:<hex>`), or whose environment is IRI. It takes one of the two options, not both |

```console
$ astra history timeline 'fit#ols'
fit#ols  .astra/records/ols/fit.json
  76e0a67ba81d46d58fb14ab6a24c4b5b285c6f42
    bytes        sha256:83a2d44052552a981f0bb7d48cfb46827494634183a606dcbf6a1ad6eaedac4f, 84 byte(s)
    made at      a1889b94c7b1625919f63acf9dd95347b10b45c9
    environment  urn:astra-examples:cpython-3.14
  40f49da033b761882429561e49160d3bb143ee92
    bytes        sha256:d266a39423ab53320599471891c4500987b46580e9e6546291e829d7d643e33f, 84 byte(s)
    made at      f0766da472d7b359f747994823af57a8491a32e0
    environment  urn:astra-examples:cpython-3.14
2 version(s)
$ astra history get 'fit#ols@HEAD'
{
  "method": "ols",
  "points": 60,
  "slope": 1.954668,
  "intercept": 1.766548
}
```

## `astra spec`

```
astra spec [TERM] [--full]
```

Describes the fields of ASTRA files, from the specification's schema. Without TERM, it lists the
classes and enums of the analysis and insight schemas, each with its first sentence. With TERM,
in any case, it shows that class or enum in full: its description and each of its fields.
`--full` prints the list and then every entry in full (long). A TERM that names nothing exits 1,
with the valid terms.

## `astra schema`

```
astra schema show {analysis|insights|provenance|types}
astra schema export [-o DIRECTORY]
```

The LinkML schemas of ASTRA files, as astra-spec ships them. `show` prints one: `analysis` for
`astra.yaml`, `insights` for insights and evidence, `provenance` for a record, and `types` for
the types they share. `export` writes them all into DIRECTORY, `schemas/` by default.

## `astra guide`

```
astra guide
```

Prints astra-spec's guide for agents, `llms.txt`, as it is.

## `astra paper`

```
astra paper add DOI [-v N] [--pdf FILE]
astra paper list
astra paper show DOI [-v N]
astra paper path DOI [-v N]
astra paper remove DOI [-v N]
astra paper fetch-metadata [DOI] [-v N] [--all]
astra paper verify-quotes DOI [-v N]
astra paper verify-quote DOI -q QUOTE [-v N] [-p PAGE] [--json]
```

Keeps papers in the cache, by DOI and version (`-v`, `--version`), and verifies quotes in them.
[`astra validate --verify-evidence`](#astra-validate) verifies the quotes an analysis's evidence
takes from the works it cites ([Elements](https://astra-spec.org/0.1/specification/#elements));
`verify-quotes` and `verify-quote` verify quotes you give, with no analysis. A quote is matched
against the paper's extracted text approximately, so that differences of spacing, ligatures and
the like don't matter.

| Command | What it does |
|---|---|
| `add DOI` | Keeps the paper of DOI. An arXiv DOI (`10.48550/arXiv.<id>`) is fetched from arXiv, at `--version` where given. No other paper is downloaded: `--pdf` keeps a PDF you have. A paper already in the cache is left as it is. Exits 1 where the paper can't be got or isn't a PDF |
| `list` | Lists every paper in the cache: its DOI, version, title and when it was kept |
| `show DOI` | Shows a cached paper: its title and authors (from doi.org, for a paper fetched), SHA-256, when and where from it was kept, and its file. Exits 1 where it isn't in the cache |
| `path DOI` | Prints the path of a cached paper's PDF, for a tool or an agent that reads it. Exits 1 where it isn't in the cache |
| `remove DOI` | Removes a paper from the cache. Exits 1 where it isn't there |
| `fetch-metadata` | Gets the title and authors of a cached paper from doi.org, or of every cached paper that lacks them with `--all` |
| `verify-quotes DOI` | Verifies quotes given as JSON on stdin, `{"quotes": [{"text": "…", "page": N, "prefix": "…", "suffix": "…"}]}`, in the paper of DOI, and prints `{"doi", "version", "results", "summary"}`: each quote `verified`, with the page it is found on, `not_found` or `error`. A `page` says where to look first, and the quote is found on any page. Exits 0 when every quote is verified, 1 when one isn't, and 2 where the paper isn't in the cache or the input isn't JSON |
| `verify-quote DOI -q QUOTE` | Verifies one quote, with `--page` to say where to look first, and `--json` for the result as JSON. Exits 0 when it is verified, 1 when it isn't, and 2 where the paper isn't in the cache |
