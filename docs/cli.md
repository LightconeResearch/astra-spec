# CLI reference

`astra` is the command line of [astra-tools](https://github.com/astra-project/astra-tools). It
validates ASTRA analyses, shows what they plan to build, and checks what was built against its
records. It reads ASTRA 0.1 files; ASTRA 0.0.x files need the 0.2 line of astra-tools
([Installation](installation.md#which-astra-it-reads)).

`astra` runs no recipe. A runner, such as lightcone-cli, builds the results and writes their
records, and `astra` reads them.

## Conventions

- **PATH** is an analysis's folder, the current folder by default. Nothing is searched for: the
  analysis is the `astra.yaml` in that folder, the root of its
  [stack](https://astra-spec.org/0.1/specification/#rules). `validate` takes an `astra.yaml` or
  its folder, and `info -f` an `astra.yaml`, found in the current folder or above by default.
- **Exit codes:**
    - 0 when the command answers;
    - 1 when the analysis breaks a `MUST`, a planned result isn't `unchanged`, or what was
      asked for isn't there;
    - 2 for a usage error, an analysis that can't be read, a broken environment (a paper that
      can't be got, a folder that can't be written, git or the cache
      unusable), or an internal error.
- **Output.** Problems are grouped by file, one per line, as `line:col level CODE message`. Each
  code is a rule of the specification, listed under [Rules](https://astra-spec.org/0.1/specification/#rules),
  or one of astra-tools' own three, which `astra rules` lists. `astra paper verify` adds two
  warnings of its own. `NO_COLOR` turns colour off.
- **JSON.** `plan`, `view` and `check` take `--json`. Each JSON document names its shape, such
  as `astra-plan/1`, and a shape changes only under a new name. `validate --json` and `info
  --json` print their text as one JSON-encoded string, with no ANSI escape, safe to embed in any
  JSON document; `init --json` prints its convergence report, and `paper verify-quotes` reads
  and writes JSON.
- **The cache** keeps the commits fetched from remotes, the validity of analyses from a commit,
  the hashes of files, the checkouts runners make for their runs, and papers. It sits outside
  every repository, and everything in it is safe to delete. `ASTRA_CACHE_DIR`, an absolute
  path, moves it.
- `astra --help`, and `--help` after any command, give each command's options.
  `astra --version` gives astra-tools' version.

The examples come from a small analysis, line-fit. It declares another analysis, noisy-line, at
a commit, and fits a line to noisy-line's points two ways: by least squares, in a universe
`ols`, and by the Huber loss, in a universe `huber`. Its `comparison` reads both fits.

## Commands at a glance

| Command | What it does |
|---|---|
| [`astra init`](#astra-init) | Make a minimal analysis |
| [`astra validate`](#astra-validate) | Validate an analysis and its whole stack |
| [`astra info`](#astra-info) | Show the stack in brief |
| [`astra universe`](#astra-universe) | List the universes, or show one's selection |
| [`astra plan`](#astra-plan) | Show the planned results, their places and commands |
| [`astra view`](#astra-view) | Show the analysis as it is in one universe |
| [`astra check`](#astra-check) | Check the records and bytes of the planned results |
| [`astra history`](#astra-history) | Show what git holds of a result's records over time |
| [`astra rules`](#astra-rules) | List the rules, or show one |
| [`astra spec`](#astra-spec) | Describe the fields of ASTRA files |
| [`astra schema`](#astra-schema) | Show or export the JSON Schemas |
| [`astra guide`](#astra-guide) | Print the guide for agents |
| [`astra paper`](#astra-paper) | Keep papers by DOI, and verify quotes in them |
| [`astra cache`](#astra-cache) | Show or clear the cache |
| [`astra completion`](#astra-completion) | Print a shell completion script |

## `astra init`

```
astra init [DIRECTORY] [--no-git] [--check] [--json]
```

Converges DIRECTORY, the current folder by default, into a minimal analysis. It creates whatever
is missing (an `astra.yaml` with a `spec_version` and one output, a `.gitignore`, and a git
repository with a first commit) and never overwrites a file, so it is safe to run again; a
folder that already holds an `astra.yaml`, or any other file, is adopted. Where a git repository
already holds DIRECTORY, no new one is made inside it. Universes, if any, are written in
`astra.yaml`.

| Option | Meaning |
|---|---|
| `--no-git` | Make no git repository |
| `--check` | Write nothing: say what would be created, and exit 1 if anything would |
| `--json` | Print the convergence report as JSON: `converged`, and the lists `created`, `repaired`, `unchanged` and `warnings` |

```console
$ astra init my-analysis
✓ created astra.yaml
✓ created .gitignore
✓ created .git
✓ Converged ASTRA analysis scaffold: my-analysis
$ cat my-analysis/astra.yaml
spec_version: "0.1.0"
outputs:
  result:
    type: metric
    format: json
    recipe:
      command: python src/result.py '{output}'
```

## `astra validate`

```
astra validate [FILE] [-e|--verify-evidence] [--skip-evidence] [--json] [--offline]
```

Checks every parse, schema and validator rule
([Rules](https://astra-spec.org/0.1/specification/#rules)) over the whole stack: the analysis
FILE names, an `astra.yaml` or its folder, and every analysis it declares, at their commits.
With no FILE, it validates every root analysis under the current folder: each `astra.yaml` that
no other one declares, hidden, vendored and `results/` folders skipped, and ends with a summary.
It reads no results; `astra check` does. Exits 0 when every analysis is valid and 1 when one
breaks a `MUST`. A `SHOULD` that is broken is a warning and doesn't change the exit code.

| Option | Meaning |
|---|---|
| `-e`, `--verify-evidence` | Also seek each quote the evidence takes from a paper, as [`astra paper verify`](#astra-paper) does; the papers must be in the cache |
| `--skip-evidence` | Say nothing of the evidence: without it, an analysis whose evidence quotes papers gets a note to run with `--verify-evidence` |
| `--json` | Print the report as one JSON-encoded string; the exit code is unchanged |
| `--offline` | Fetch nothing: use only the commits already in the cache |

An analysis declared by `url` and `commit` is fetched into the cache, once.

```console
$ astra validate
astra.yaml
  4:11 error MISSING_INPUT_FILE `data.csv` names no file, and no stand-in of Git LFS, git-annex, DVC
  10:17 error UNRESOLVED_ADDRESS `method` names nothing: this analysis has no decision `method`
astra.yaml: invalid, 2 error(s), 0 warning(s)

1/1 analysis(es) failed validation: astra.yaml
```

## `astra info`

```
astra info [-f FILE] [-d] [-i] [-o] [--json]
```

Shows each analysis of the stack of FILE, by default the `astra.yaml` in the current folder or
the nearest folder above, the root first, with its declarations, inputs, outputs, decisions and
universes; with `-d` (`--decisions`), `-i` (`--inputs`) or `-o` (`--outputs`), only those rows.
A switch shows the decision it switches on and its cases. It checks nothing. `--json` prints the
text as one JSON-encoded string. Exits 1 where there is no `astra.yaml`, or no stack to show.

```console
$ astra info
astra.yaml
  analyses  noisy: astra.yaml at 18cfe9d5695d7fc13a3d93bbbba2f6a644bd284d from file:///…/noisy-line
  outputs   fit: table, json
            comparison: table, json
  decisions method: ols, huber
  universes ols
            huber
astra.yaml at 18cfe9d5695d7fc13a3d93bbbba2f6a644bd284d from file:///…/noisy-line
  inputs    config: config.json
  outputs   points: data, csv
```

## `astra universe`

```
astra universe list [PATH]
astra universe show UNIVERSE [PATH]
```

`list` names the analysis's universes, and the universes it imports from other analyses.
`show` gives a universe's effective selection
([Elements](https://astra-spec.org/0.1/specification/#elements)): each decision with the option
selected, and, where the option is inherited through `derived_from`, the universe it comes from.

```console
$ astra universe show huber
huber
  method: huber
```

## `astra plan`

```
astra plan [PATH] [--json] [--notes]
```

Lists every planned result, each after what it reads. For each result it shows where its record
and its bytes go ([Results](https://astra-spec.org/0.1/specification/#results)),
the folder its recipe runs in, the resources the recipe asks for, if any, and its command with
the placeholders filled in
([Elements](https://astra-spec.org/0.1/specification/#elements)). A result that belongs to an
analysis from a commit isn't built here: it is read through its record at that commit
([Results](https://astra-spec.org/0.1/specification/#results)).

| Option | Meaning |
|---|---|
| `--json` | Print the plan as JSON (`astra-plan/1`), with every note |
| `--notes` | List each note, not only how many there are of each kind |

```console
$ astra plan
points
  record    .astra/records/points.json at 18cfe9d5695d7fc13a3d93bbbba2f6a644bd284d
  bytes     results/points.csv at 18cfe9d5695d7fc13a3d93bbbba2f6a644bd284d
  read through its record at 18cfe9d5695d7fc13a3d93bbbba2f6a644bd284d
fit#ols
  record    .astra/records/ols/fit.json
  bytes     results/ols/fit.json
  run in    .
  command   python3 src/fit.py ols 18cfe9d5695d7fc13a3d93bbbba2f6a644bd284d:results/points.csv results/ols/fit.json
fit#huber
  record    .astra/records/huber/fit.json
  bytes     results/huber/fit.json
  run in    .
  command   python3 src/fit.py huber 18cfe9d5695d7fc13a3d93bbbba2f6a644bd284d:results/points.csv results/huber/fit.json
comparison
  record    .astra/records/comparison.json
  bytes     results/comparison.json
  run in    .
  command   python3 src/compare.py results/ols/fit.json results/huber/fit.json results/comparison.json
4 planned result(s)
```

A path written `<commit>:<path>` names a file in that commit, as git names it: the runner gets
the bytes and gives the recipe a path to them.

The notes point out things that are valid but easy to miss. None of them is a breach:

- a pin that names another analysis's universe only because its own file has no universe of
  that id;
- a result with two names;
- an output with no planned result;
- an output that isn't built in some universe, because a switch it reads has no case there for
  the option selected, and a switch that nothing reads with no such case
  ([Elements](https://astra-spec.org/0.1/specification/#elements));
- results that are one computation in several universes;
- a command that names a path outside its analysis's folder, or inside a folder below it that
  holds an analysis of its own.

The text counts and lists only the pins, outputs and commands that concern what the analysis in
PATH builds: a pin that a planned result reads through, and the outputs and commands of the
analysis and of the analyses its universes drive. A line gives the whole stack's count where it
is more.

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
(`fit#ols`, `comparison`), which `astra plan` lists. A record's versions are its file at each
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

## `astra rules`

```
astra rules [CODE]
```

Without CODE, lists every rule of the specification by layer, with its code, level and
statement, and then astra-tools' own three. With CODE, in any case, shows that rule, with its
layer and level (and astra-tools, for astra-tools' own) and, for a check rule, its status when
broken.

```console
$ astra rules MISSING_INPUT_FILE
MISSING_INPUT_FILE
validator, MUST
An input's `path` names a file (no symlink, folder or gitlink) or a stand-in
```

## `astra spec`

```
astra spec [TERM] [--full]
```

Describes the fields of ASTRA files, from the specification's schema. Without TERM, it lists
every class, enum and type with its first sentence. With TERM, in any case, it shows a class,
enum or type in full, a field of every class that has it, or one field as `Class.field`. `--full`
shows every class, enum and type in full (long). A TERM that names nothing exits 1, with the
valid terms.

## `astra schema`

```
astra schema show NAME
astra schema export FOLDER
```

The JSON Schemas of ASTRA files, as astra-spec ships them: `analysis` for `astra.yaml`,
`provenance` for a record, and `provenance.open` for a record of a later minor version. `show`
prints one; `export` writes all three into FOLDER as `NAME.schema.json`.

## `astra guide`

```
astra guide
```

Prints astra-spec's guide for agents, `llms.txt`, as it is.

## `astra paper`

```
astra paper add DOI [-v N] [--pdf PATH] [--email ADDRESS]
astra paper list
astra paper show DOI [-v N]
astra paper path DOI [-v N]
astra paper verify-quotes DOI [-v N]
astra paper verify [PATH]
astra paper seek DOI QUOTE... [--version N] [--page N]
```

Keeps papers in the cache, by DOI and version (`-v`, `--version`), and seeks quotes in them: the
quotes an analysis's evidence takes from the works it cites
([Elements](https://astra-spec.org/0.1/specification/#elements)), or quotes you give. For
`verify`, a paper not in the cache (`EVIDENCE_PAPER_MISSING`), or a quote not found
(`EVIDENCE_QUOTE_NOT_FOUND`), is a warning, never an error.

| Command | What it does |
|---|---|
| `add DOI` | Keeps the paper of DOI. An arXiv DOI (`10.48550/arXiv.<id>`) is fetched from arXiv, at `--version` where given; any other from the open-access copy Unpaywall knows, which asks for `--email`. `--pdf` keeps a PDF you have instead. A paper already in the cache is left as it is. Exits 2 where the paper can't be got or isn't a PDF |
| `list` | Lists every paper in the cache: its DOI, version, title and when it was kept |
| `show DOI` | Shows a cached paper: its title and authors (from doi.org, for a paper fetched), SHA-256, when and where from it was kept, and its file. Exits 1 where it isn't in the cache |
| `path DOI` | Prints the path of a cached paper's PDF, for a tool or an agent that reads it. Exits 1 where it isn't in the cache |
| `verify-quotes DOI` | Seeks quotes given as JSON on stdin, `{"quotes": [{"text": "…", "page": N, "prefix": "…", "suffix": "…"}]}`, in the whole text of the paper of DOI, and prints `{"doi", "version", "results", "summary"}`: each quote `verified`, with the pages it is found on, `not_found` or `error`. Exits 0 when every quote is verified, 1 when one isn't, and 2 where the paper isn't in the cache or the input isn't JSON |
| `verify` | Seeks each quote the analysis's evidence takes from a work it cites by DOI. Exits 0 whatever it finds |
| `seek DOI QUOTE...` | Seeks each QUOTE in the paper of DOI that `add` kept, as `verify` would, with no analysis: within `--page` where given, or in the whole text. Shows the pages each quote is found on, which a location such as `page=6` can give. Exits 1 when a quote isn't found, and 2 where the paper isn't in the cache or has no page `--page` |

## `astra cache`

```
astra cache path
astra cache clear
```

`path` prints the cache's folder. `clear` deletes what astra keeps there, and leaves anything
else in that folder alone.

## `astra completion`

```
astra completion bash|zsh|fish
```

Prints the shell's completion script. Load it from the shell's startup file:

- bash, in `~/.bashrc`: `eval "$(astra completion bash)"`
- zsh, in `~/.zshrc`: `eval "$(astra completion zsh)"`
- fish, in `~/.config/fish/config.fish`: `astra completion fish | source`
