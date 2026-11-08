# The ASTRA specification

This document specifies the ASTRA format and what conforming tools do with
it.

## Part I: How ASTRA works

### 1. What ASTRA is

ASTRA (Agentic Schema for Transparent Research Analysis) records a research
analysis so that every choice in it is explicit, and every result can be
checked against how it was made. An **analysis** is a folder in a git
repository with an `astra.yaml` at its top. That file lists:

- **inputs**: the files the analysis reads, tracked in git with it
  ([§7](#7-inputs));
- **decisions**: the choices it makes, each with the **options** it
  considered ([§8](#8-decisions-and-options));
- **outputs**: what it makes, each with a **recipe**, the command that makes
  it ([§10](#10-outputs), [§11](#11-recipes));
- **universes**: each selects one option per decision, so one analysis can
  be built several ways ([§12](#12-universes));
- **insights**: claims backed by evidence, which cites outputs or published
  work ([§14](#14-insights-and-evidence));
- **analyses**: other analyses it declares and uses
  ([§15](#15-declared-analyses)–[§17](#17-analyses-from-another-commit-or-repository)).

Each entry of `analyses` is a **declaration**. The analysis being validated
or built is the **root**, and its **stack** is the root and every analysis it
declares, directly or through others ([§15](#15-declared-analyses)). An
analysis's **identity** is its folder at a commit, or its folder in the
working tree, and **another analysis** is one with a different identity
([§17](#17-analyses-from-another-commit-or-repository)).

A **runner** builds the outputs in each universe and writes each **result**
with a **record** of the run that made it
([§18](#18-results-and-where-they-go), [§19](#19-records),
[§21](#21-runners)). A **checker** later compares each record with the
analysis as it is then. It says whether the result is **unchanged**,
**stale** or **missing**, and whether its bytes are **present**
([§20](#20-checking-results)).

### 2. A worked example

This analysis, the root, reads a file of its own and an output of each of
two other analyses: `stage`, in a folder of the same repository, and
`upstream`, in another repository. It makes one result from them in each of
two universes, and compares the two:

```yaml
# astra.yaml
spec_version: "0.1.0"
label: Example analysis

analyses:
  stage:
    path: stage
  upstream:
    url: https://example.org/upstream.git
    commit: <commit>

inputs:
  input1:
    path: data/input1.csv

decisions:
  decision1:
    rationale: Both are reasonable, and they may give different results.
    options:
      a: {}
      b: {}

outputs:
  output1:
    type: metric
    format: json
    inputs: [input1, stage.output3, upstream.output4]
    decisions: [decision1]
    recipe:
      command: >-
        python src/output1.py '{inputs.input1}' '{inputs.stage.output3}'
        '{inputs.upstream.output4}' '{decisions.decision1}' '{output}'
  output2:
    type: table
    format: csv
    inputs: [output1#u1, output1#u2]
    recipe:
      command: >-
        python src/output2.py '{inputs.output1#u1}' '{inputs.output1#u2}'
        '{output}'

universes:
  u1:
    decisions: {decision1: a, stage.decision2: a}
  u2:
    decisions: {decision1: b, stage.decision2: b}

findings:
  insight1:
    claim: The two universes give different results.
    evidence:
      - artifact: output2
```

The folder `stage`, in the root's folder, holds the analysis declared as
`stage`. The paths in its `astra.yaml` are relative to that folder, and its
recipe runs there:

```yaml
# stage/astra.yaml
spec_version: "0.1.0"

inputs:
  input2:
    path: data/input2.csv

decisions:
  decision2:
    options:
      a: {}
      b: {}

outputs:
  output3:
    type: data
    format: csv
    inputs: [input2]
    decisions: [decision2]
    recipe:
      command: >-
        python src/output3.py '{inputs.input2}' '{decisions.decision2}'
        '{output}'
```

The repository at `https://example.org/upstream.git` holds, at its top, an
analysis with an output `output4`, built once. At `<commit>`, it also holds
`output4`'s result and that result's record.

- `output1` lists `decision1`, so it is
  [built per universe](#13-pins-and-outputs-built-per-universe-or-once): it
  has one result in `u1` and one in `u2`.
- `stage` is declared by `path` ([§15](#15-declared-analyses)), and is read
  in the working tree, as the root is. The root's universes set its
  `decision2`, under the key `stage.decision2`: they
  [drive](#16-driving-and-consuming) `stage`. In `u1`, `output1` reads
  `stage.output3` as `stage` builds it with `decision2` set to `a`, and in
  `u2` with it set to `b`.
- `upstream` is declared by `url` and `commit`, so it is that repository's
  analysis as it was at `<commit>`
  ([§17](#17-analyses-from-another-commit-or-repository)). `output1` reads
  its `output4` without a pin, as `upstream.output4`: built once, it is the
  same result in both universes.
- `output2` reads `output1`
  [pinned](#13-pins-and-outputs-built-per-universe-or-once) to each universe,
  as `output1#u1` and `output1#u2`, so it is built once, from both.

**Validating.** A validator reads the root's and `stage`'s `astra.yaml` in
the working tree, `upstream`'s at `<commit>`, and git. It reports any rule
that an analysis of the [stack](#15-declared-analyses) breaks
([§3](#3-conformance)), such as an input that isn't tracked in git or a
universe that selects no option of `decision1` or of `stage.decision2`.

**Building.** A runner runs `stage`'s recipe in `stage`'s folder, with
`{decisions.decision2}` replaced by `a` in `u1` and by `b` in `u2`. It runs
`output1`'s with `{decisions.decision1}` replaced in the same way, then
`output2`'s once, with the paths of `output1`'s two results
([§11](#11-recipes), [§16](#16-driving-and-consuming)). `output4` belongs to
`upstream`, an
[analysis from a commit](#17-analyses-from-another-commit-or-repository), so
its recipe doesn't run: for `output1`'s recipe, the runner gets `output4`'s
bytes from `<commit>` and checks them against its record there.

**Recording.** For each of the five results it builds, the runner writes the
bytes under `results/` and a record under `.astra/records/`, all in the
root's folder ([§18](#18-results-and-where-they-go), [§19](#19-records)).
`stage`'s two results belong to the root, whose universes built them, and
are named `stage.output3`: the one in `u1` has its bytes at
`results/u1/stage.output3.csv` and its record at
`.astra/records/u1/stage.output3.json`.

**Checking.** A checker later compares each record with the analysis as it
is then ([§20](#20-checking-results)). Change `stage/data/input2.csv`, and
the five results the runner built are all stale, since each is made from it,
directly or through others; edit the finding, and every result stays
unchanged. `upstream.output4` is checked the same way, between the commit
its record names and `<commit>`.

### 3. Conformance

Rules are enforced in five layers, set apart by what each one sees:

| Layer | Enforced by | Sees |
|---|---|---|
| **parse** | a YAML 1.2 reader (`astra.yaml`) or a JSON reader (records), as [Annex A](#a-reading-files) says | one file's bytes |
| **schema** | the generated JSON Schema | one file's data |
| **validator** | a validator | every `astra.yaml` of the stack, and git ([Annex B](#b-paths-and-git)); no results |
| **check** | a checker | every `astra.yaml` of the stack, now and at each record's commit, and git ([Annex B](#b-paths-and-git)); records and results |
| **runner** | a runner | its own actions, the checkouts it runs recipes in, and what the recipes read |

Four roles conform to this specification:

- A **document**, an `astra.yaml` or a record, conforms, or is **valid**,
  when it breaks no parse or schema rule.
- A **validator** reports the parse, schema and validator rules that the
  analysis, or any analysis of its stack, breaks. An analysis is **valid**
  when no analysis of its stack breaks a `MUST` of these three layers.
- A **checker** gives each [planned result](#18-results-and-where-they-go)
  its statuses by the check rules ([§20](#20-checking-results)). A record
  that breaks a parse or schema rule leaves its result `missing`
  ([`INVALID_RECORD`](#20-checking-results)). A checker implements one
  version, its own, and has the record schema of every
  [minor version](#5-the-astrayaml-file) from 0.1, the first with records,
  up to its own ([Annex D](#d-the-schema-files-and-rulesjson)).
- A **runner** runs recipes and writes each result's bytes and record. A
  record is its runner's testimony, and names it. A runner conforms when it
  keeps the runner `MUST`s, which keep its records true.

What breaking a rule leads to depends on its layer:

| Layer | When a rule is broken |
|---|---|
| parse, schema, validator | A broken `MUST` is reported as an **error** and makes the analysis invalid (in a record, it breaks [`INVALID_RECORD`](#20-checking-results) instead); a broken `SHOULD` is reported as a **warning**, and the analysis stays valid |
| check | A broken `MUST` is reported as an **error** and a broken `SHOULD` as a **warning**. Nothing fails: the result gets the status in the rule's *Status when broken* column |
| runner | A runner that breaks a `MUST` doesn't conform |

### 4. Conventions

**Keywords.** The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL
NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and
"OPTIONAL" in this document are to be interpreted as described in BCP 14
([RFC 2119](https://www.rfc-editor.org/rfc/rfc2119),
[RFC 8174](https://www.rfc-editor.org/rfc/rfc8174)) when, and only when,
they appear in all capitals, as shown here.

**Notation.** Grammars are written in ABNF
([RFC 5234](https://www.rfc-editor.org/rfc/rfc5234)) and use its core rules,
such as `DIGIT`. Patterns are regular expressions as JSON Schema reads them
(ECMA-262).

**Codes tables.** Each rule that a tool checks or keeps has a code, and is
stated only in the codes table at the end of a section of Part II, whose text
explains what its rules are about. A table's columns are:

- **Code:** what is wrong when the rule is broken, and what a tool reports.
  Each code is unique and matches `[A-Z][A-Z0-9_]*`.
- **Layer:** the layer whose tool checks or keeps the rule
  ([§3](#3-conformance)).
- **Level:** `MUST` or `SHOULD`, applied to the rule's sentence.
- **Rule:** one sentence saying what holds in a conforming file, record or
  run.
- **Status when broken:** in the table of the check rules only, the status a
  result, or evidence citing it, gets when the rule doesn't hold
  ([§20](#20-checking-results)).

The recommendations and the permission that have no code are each stated on
a line of their own, starting "Recommendation:" or "Permission:", at the end
of their section ([§17](#17-analyses-from-another-commit-or-repository),
[§19](#19-records), [§21](#21-runners)). The [All rules](rules.md) page lists
every rule of the codes tables by layer, then the recommendations and the
permission.

**Examples.** An example shows a whole file, or only the part its section is
about. Commits, hashes and sizes are placeholders: `<commit>` stands for a
full commit id, and `sha256:<hash of …>` and `<size of …>` for the hash and
the size, in bytes, of what they name.

**Fields.** Every class of the format has a page in the
[field reference](elements/index.md), generated from the schema, whose
descriptions define its fields. Each section of Part II links to the pages
of its elements.

## Part II: The specification

Sections 5 to 14 describe one analysis, sections 15 to 17 several analyses,
and sections 18 to 21 results.

### 5. The astra.yaml file

An analysis is a folder with an `astra.yaml` at its top, in a git
repository's working tree or at one of its commits
([`NOT_IN_REPOSITORY`](#5-the-astrayaml-file)).
[Analysis](elements/Analysis.md) is the content of an `astra.yaml`:

```yaml
spec_version: "0.1.0"
label: Example analysis
description: Makes output3 from input1.
tags: [example]
inputs:
  input1:
    path: data/input1.csv
outputs:
  output3:
    type: data
    format: csv
    inputs: [input1]
    recipe:
      command: python src/output3.py '{inputs.input1}' '{output}'
```

- An `astra.yaml` is written in YAML 1.2, and a record ([§19](#19-records))
  in JSON. [Annex A](#a-reading-files) says how each is read
  ([`INVALID_SYNTAX`](#5-the-astrayaml-file)).
- Like the analysis, most [elements](#6-names) take a `label`, a short
  display name; a `description`, in free prose; and `tags`, keywords for
  grouping and finding them. All three are optional.
- Every list is a list of strings, except an
  [insight](#14-insights-and-evidence)'s `evidence` and a record's `inputs`.
- No field takes `null`: an optional field without a value is left out, and
  so is a list of strings with nothing in it
  ([`EMPTY_COLLECTION`](#5-the-astrayaml-file)). So an
  [output](#10-outputs) lists `decisions`, or has a [`when`](#9-conditions),
  only when it names at least one.

#### Versions

Every `astra.yaml` and every record states, in `spec_version`, the version
of this specification it is written against: `MAJOR.MINOR.PATCH`, three
non-negative integers without leading zeros, such as `0.1.0`
([`INVALID_VALUE`](#5-the-astrayaml-file)).

- Versions are ordered by MAJOR, then MINOR, then PATCH, each compared as an
  integer, so `0.10.0` comes after `0.9.0`.
- A version's **minor version** is its MAJOR and MINOR: `0.1` for `0.1.3`.
- A patch release never changes what is valid, nor the code a broken rule is
  reported under: an `astra.yaml` or a record is valid under `X.Y.Z` exactly
  when it is valid under every other `X.Y` version. So each minor version has
  one schema of `astra.yaml` and one record schema.
- Each `astra.yaml` is read by the schema of the minor version it states, so
  a tool that reads one patch of a minor version reads them all.

#### The folder

In an analysis's folder:

| Path | Holds |
|---|---|
| `astra.yaml` | the analysis's own file |
| `.astra/records/` | the records of the results that [belong to](#18-results-and-where-they-go) the analysis |
| `results/` | the [default places](#18-results-and-where-they-go) of those results' bytes |

`results/` and `.astra/` belong to runners, and no input's or
[declaration](#15-declared-analyses)'s `path` is, or
[lies inside](#glossary), one of them ([`RESERVED_PATH`](#7-inputs)). So a
run never writes over an input or a declared analysis, and a result is read
by its [address](#6-names), never by a path.

#### The rules

| Code | Layer | Level | Rule |
|---|---|---|---|
| `INVALID_SYNTAX` | parse | MUST | Every `astra.yaml` is a YAML 1.2 document whose content is a map, and every record is JSON text in UTF-8 in which no object has two equal names |
| `MISSING_FIELD` | schema | MUST | Every required field is present: in `astra.yaml`, `spec_version`, `outputs`, `Output.type`, `Output.format`, `Output.recipe`, `Recipe.command`, `Input.path`, `Decision.options`, `Insight.claim`, `Insight.evidence`, `TextQuoteSelector.exact` and `FragmentSelector.value`; in a record, `spec_version`, `address`, `content_hash`, `size`, `generated_by`, `Generation.commit`, `Generation.environment`, `Generation.runner`, `Environment.iri`, `Runner.id`, `Runner.version`, `RecordedInput.entry`, `RecordedInput.content_hash` and `RecordedInput.size` |
| `UNKNOWN_FIELD` | schema | MUST | Every field is one the schema defines |
| `EMPTY_COLLECTION` | schema | MUST | `outputs`, `Decision.options` and `Insight.evidence` each have at least one entry, and no list of strings in an `astra.yaml` is empty |
| `WRONG_TYPE` | schema | MUST | Every value has the JSON type its field takes: a string, a number, an integer, a list or a map |
| `DUPLICATE_ENTRY` | schema | MUST | No list of strings holds the same entry twice (`Output.inputs`, `Output.decisions`, `when`, `requires`, `incompatible_with`, `insights`, `tags`) |
| `INVALID_VALUE` | schema | MUST | Every value matches its pattern, enumeration or range: `Output.type` (one of `OutputType`), `Output.format`, `Evidence.doi`, `FragmentSelector.value` (a fragment identifier's characters), `FragmentSelector.conforms_to` (an IRI), `AnalysisDeclaration.url` (a remote URL), every hash, IRI and time, every `spec_version`, `size` ≥ 0, `Evidence.version` ≥ 1, `Resources.cpus` ≥ 0 and `Resources.gpus` ≥ 1 |
| `NOT_IN_REPOSITORY` | validator | MUST | The folder of the analysis being validated is in the working tree of a git repository |

### 6. Names

An analysis's **elements** are its inputs, outputs, decisions, options,
universes and [imports](#12-universes) (`universes`),
[declarations](#15-declared-analyses) (`analyses`), prior insights and
findings ([§14](#14-insights-and-evidence)), each an entry of a map keyed by
its **id**. An element other than an option is named by its **address**: the
ids of the declarations that lead to it, then its own id, joined by dots, as
in `subanalysis.decision1`. An element of the analysis itself is named by its
id alone. An option is named by an option reference (below).

<!-- fragment: Analysis -->
```yaml
analyses:
  subanalysis:
    path: subanalysis
decisions:
  decision1:
    options:
      a: {}
      b: {}
universes:
  u1:
    decisions: {decision1: a, subanalysis.decision1: a}
```

Here `subanalysis`, `decision1`, `a`, `b` and `u1` are ids. In `u1`, the key
`subanalysis.decision1` is an address: the decision `decision1` of the
analysis declared as `subanalysis`. Each value is the id of the option
selected.

#### Ids and maps

- The id is written once, as the key ([`INVALID_ID`](#6-names)): `a: {}`,
  never `a: {id: a}` ([`UNKNOWN_FIELD`](#5-the-astrayaml-file)).
- Ids are unique within their map, since a map's keys are, and the order of
  a map carries no meaning.
- A map's entries are objects, except those of `Universe.decisions`, each the
  id of the option selected (`decision1: a`). A map is never written as a
  list, as in `outputs: [output1]` ([`WRONG_TYPE`](#5-the-astrayaml-file)).
- Ids of different kinds can be the same, except that an input and an output
  never share an id ([`AMBIGUOUS_ID`](#10-outputs)), nor an output and a
  declaration of its analysis
  ([`CLASHING_RESULT_NAME`](#15-declared-analyses)).

#### The forms of a name

A name takes one of five forms. Each is a type of the
[field reference](elements/index.md), and
[Annex C](#c-grammars-and-patterns) gives its grammar.

| Form | Example | Written in |
|---|---|---|
| [id](elements/Id.md): a letter `a`-`z`, followed by any number of letters `a`-`z`, digits `0`-`9` and `_` | `decision1` | every map key but those of `Universe.decisions`; also `Universe.derived_from`, `Universe.universe`, `Option.insights` and the values of `Universe.decisions` |
| [address](elements/Address.md): ids joined by `.` | `subanalysis.decision1` | `Output.decisions`, the keys of `Universe.decisions`, `Universe.analysis` |
| [reference](elements/Reference.md): an address, which may be followed by a [pin](#13-pins-and-outputs-built-per-universe-or-once), `#` and a universe's id | `output1#u1` | `Output.inputs`, `Evidence.artifact`, `ProvenanceRecord.address`, `RecordedInput.entry` |
| [option reference](elements/OptionReference.md): a decision's address, `.`, then an option's id | `subanalysis.decision1.a` | `Option.requires`, `Option.incompatible_with` |
| [condition](elements/Condition.md): an option reference, possibly after `~` ([§9](#9-conditions)) | `~decision1.b` | `Output.when`, `Decision.when` |

A decision's address never takes a pin: the entries of `Output.decisions`
are addresses ([`INVALID_REFERENCE`](#6-names)), and so are the keys of
`Universe.decisions` ([`INVALID_ID`](#6-names)).

#### Addresses

An address is read in the analysis whose `astra.yaml` it is written in. A
report on an analysis, written outside `astra.yaml`, also names the
analysis's elements by address, read in that analysis. An
[import](#12-universes)'s address names the universe it imports.

A condition's leading `~` and a reference's pin are not part of the address.
In an option reference, the address is every segment but the last, which is
the option: the option `a` of the decision `decision1` of the declared
analysis `subanalysis` is `subanalysis.decision1.a`.

- Every segment of an address but the last is the id of a declaration: the
  first names an entry of the `analyses` of the analysis the address is read
  in, the next an entry of the declared analysis's `analyses`, and so on
  ([§15](#15-declared-analyses)).
- The last segment is the id of an element of the analysis reached. The
  field the address is written in gives the element's kind, as
  [`UNRESOLVED_ADDRESS`](#6-names) lists, so an element can be called
  `inputs`. In an [import](#12-universes), the address is its `analysis`,
  then `.` and its `universe`.

#### The rules

| Code | Layer | Level | Rule |
|---|---|---|---|
| `INVALID_ID` | schema | MUST | Every map key matches its key's type where the map has one (an `id`, or an `address` in `Universe.decisions`); every `id`-typed value matches the `id` grammar |
| `INVALID_REFERENCE` | schema | MUST | Every address, reference, option reference and condition, other than a key of `Universe.decisions`, matches its grammar |
| `UNRESOLVED_ADDRESS` | validator | MUST | Every address resolves, through the declarations, to an element of the kind its field takes: an input or output in `Output.inputs`, a decision in `Output.decisions` and in `Universe.decisions` keys, a decision in conditions and option references, an output in `Evidence.artifact`, one of another analysis's universes in an import |

### 7. Inputs

An [Input](elements/Input.md) is a file the analysis reads, named by its
`path`. It is [tracked](#glossary) in git with the analysis
([`INPUT_NOT_TRACKED`](#7-inputs)), so a commit holds the data along with the
code.

<!-- fragment: Analysis -->
```yaml
inputs:
  input1:
    path: data/input1.csv
    description: The measurements, one row per sample.
  input2:
    path: data/input2.csv
```

- `path`, here and in a [declaration](#15-declared-analyses), is relative to
  the folder of the `astra.yaml` that writes it, with `/` between folders
  ([`INVALID_PATH`](#7-inputs)). It is tidied as text
  ([Annex B](#b-paths-and-git)): `./data/input1.csv` is `data/input1.csv`.
  The folders that belong to runners are reserved
  ([§5](#5-the-astrayaml-file), [`RESERVED_PATH`](#7-inputs)).
- An input is one file ([`MISSING_INPUT_FILE`](#7-inputs)). Data in many
  files is many inputs.
- A **stand-in** is something kept where a file would be and recognised as
  standing in for it, such as a large-file tool's pointer
  ([`MISSING_INPUT_FILE`](#7-inputs)). It isn't the content it stands in for.
- The record of each result that reads an input holds the hash of what it
  read, so a change to the file makes those results stale
  ([§19](#19-records), [§20](#20-checking-results)).

Data that isn't an input of the analysis comes in another way:

- An input of another analysis is read by its [address](#6-names), such as
  `subanalysis.input1`, not by a path
  ([`INPUT_IN_ANOTHER_ANALYSIS`](#7-inputs)).
- Data kept in another repository, such as a git submodule, isn't tracked
  with the analysis, so it isn't an input. It belongs in the analysis's own
  repository, or in another analysis as that analysis's input.
- Other data that isn't tracked with the analysis, such as a download, a
  loader's output or a query's answer, comes in through an output whose recipe
  gets it. That output's record holds the hash of what came back.

| Code | Layer | Level | Rule |
|---|---|---|---|
| `INVALID_PATH` | schema | MUST | Every declaration's and input's `path` is non-empty and doesn't start with `/` |
| `MISSING_INPUT_FILE` | validator | MUST | An input's `path` names a file (not a symlink, folder or gitlink), or something the validator recognises as a [stand-in](#glossary) for one |
| `INPUT_NOT_TRACKED` | validator | MUST | An input's file, or its stand-in, is [tracked](#glossary) in the repository that holds the input's analysis: in its index or, read at a commit, in that commit's tree there, reached through no gitlink |
| `INPUT_IN_ANOTHER_ANALYSIS` | validator | MUST | An input's file is inside its analysis's folder and outside every folder below it that holds an `astra.yaml` file of its own |
| `RESERVED_PATH` | validator | MUST | No input's `path` and no declaration's `path`, tidied ([Annex B](#b-paths-and-git)), is, or [lies inside](#glossary), the `results/` or `.astra/` folder of an analysis of the stack read in the same tree as that path: the working tree, or one commit |

### 8. Decisions and options

A [Decision](elements/Decision.md) is a choice the analysis makes, such as
which method to use, with the `rationale` for making it. Its `options` hold
at least one [Option](elements/Option.md)
([`EMPTY_COLLECTION`](#5-the-astrayaml-file)). Each universe chooses which
of a decision's options is used ([§12](#12-universes)).

<!-- fragment: Analysis -->
```yaml
decisions:
  decision1:
    rationale: Both are reasonable, and they may give different results.
    options:
      a: {}
      b:
        requires: [decision2.b]
  decision2:
    options:
      a: {}
      b: {}
      c:
        excluded: It needs data this analysis doesn't have.
```

- A **constraint**, an option's `requires` or `incompatible_with`, constrains
  every selection the option is part of:
  - `requires` lists options that are also selected whenever it is
    ([`MISSING_REQUIRED_OPTION`](#12-universes)). Here `decision2.b` is
    selected wherever `decision1.b` is.
  - `incompatible_with` lists options that are never selected together with
    it ([`INCOMPATIBLE_OPTIONS`](#12-universes)).
- Both take option references ([§6](#6-names)), so they can name an option
  of a declared analysis's decision.
- An option with an `excluded` reason is excluded: no universe selects it,
  once what the universe inherits from another is resolved
  ([§12](#12-universes), [`EXCLUDED_OPTION_SELECTED`](#12-universes)). It
  stays listed, so the analysis records what it considered and why it ruled
  it out.
  `excluded: true` is not a reason ([`WRONG_TYPE`](#5-the-astrayaml-file)).
- A decision with a `when` is conditional ([§9](#9-conditions)).
- Every option named by a condition, an option reference or a universe's
  selection is one of its decision's options
  ([`UNKNOWN_OPTION`](#8-decisions-and-options)).

| Code | Layer | Level | Rule |
|---|---|---|---|
| `UNKNOWN_OPTION` | validator | MUST | Every option named by a condition, option reference or selection is one of its decision's options |

### 9. Conditions

A decision or an output with a [`when`](elements/when.md) is conditional.
`when` is a list of conditions ([§6](#6-names)). The element is **active**
when every one of its conditions holds, and an element without `when` is
always active.

<!-- fragment: Analysis -->
```yaml
decisions:
  decision1:
    options:
      a: {}
      b: {}
  decision3:
    when: [decision1.b]
    options:
      a: {}
      b: {}
outputs:
  output4:
    type: figure
    format: png
    when: [decision1.b]
    recipe:
      command: python src/output4.py '{output}'
```

- A condition `d.o` holds when the option `o` of the decision `d` is
  selected, and `~d.o` holds when it isn't.
- `d` can be a decision of a declared analysis, by its address, as in the
  condition `subanalysis.decision1.a`.
- Conditions are evaluated in what the
  [universe being built](#16-driving-and-consuming) selects, once
  what it inherits from another universe is resolved
  ([§12](#12-universes)).

`decision3` and `output4` are active only where `decision1.b` is selected,
so a universe selecting `decision1.a` has neither. A universe doesn't set an
inactive decision such as `decision3` itself
([`INACTIVE_DECISION`](#12-universes)), and needn't set it at all
([`MISSING_DECISION`](#16-driving-and-consuming)). An inactive output such as
`output4` isn't built in that universe
([§13](#13-pins-and-outputs-built-per-universe-or-once)).

### 10. Outputs

An output is an artefact the analysis makes, such as a metric, a figure or a
table. It says what it is made from, the decisions it is made with, and the
recipe that makes it ([§11](#11-recipes)).

<!-- fragment: Analysis -->
```yaml
outputs:
  output1:
    type: metric
    format: json
    inputs: [input1, subanalysis.output1]
    decisions: [decision1]
    recipe:
      command: >-
        python src/output1.py '{inputs.input1}' '{inputs.subanalysis.output1}'
        '{decisions.decision1}' '{output}'
  output3:
    type: data
    format: csv
    inputs: [input1]
    recipe:
      command: python src/output3.py '{inputs.input1}' '{output}'
```

- An output's fields are in the [field reference](elements/Output.md).
- An output has a `type`, a `format` and a `recipe`
  ([`MISSING_FIELD`](#5-the-astrayaml-file)).
- `type` is one of [OutputType](elements/OutputType.md): `metric`, `figure`,
  `table`, `data` or `report` ([`INVALID_VALUE`](#5-the-astrayaml-file)).
- `format` is how the artefact is encoded, as a lowercase token,
  `^[a-z0-9][a-z0-9_.+-]*$`: the file extension it is written with, without
  the leading dot, such as `png`, `csv` or `parquet`
  ([`INVALID_VALUE`](#5-the-astrayaml-file)). It is the extension of the
  result's [default place](#18-results-and-where-they-go).
- `inputs` lists what the output is made from, in order: references
  ([§6](#6-names)) to inputs and outputs of the analysis or of analyses it
  declares, such as `subanalysis.output1` ([§15](#15-declared-analyses)). A
  reference can be pinned
  ([§13](#13-pins-and-outputs-built-per-universe-or-once)). Their order
  counts, since `{inputs}` passes them to the recipe in that order
  ([§11](#11-recipes)).
- `decisions` lists the addresses of the decisions whose option the output
  is made with directly, not through what it reads: a different option for
  any of them, in the [universe being built](#16-driving-and-consuming), can
  give a different result. Their order carries no meaning.
- `when` makes the output conditional ([§9](#9-conditions)).
- `recipe` says how the output is made ([§11](#11-recipes)).

An input and an output never share an id, since `Output.inputs` takes both
([`AMBIGUOUS_ID`](#10-outputs)). An output depends on another, known by its
analysis's identity ([§17](#17-analyses-from-another-commit-or-repository)),
when it reads it through `Output.inputs`, directly or through others, pinned
or not. No output depends on itself, directly or through others
([`OUTPUT_CYCLE`](#10-outputs)).

| Code | Layer | Level | Rule |
|---|---|---|---|
| `AMBIGUOUS_ID` | validator | MUST | No two elements that one field could resolve to share an id (an input and an output, both of which `Output.inputs` takes) |
| `OUTPUT_CYCLE` | validator | MUST | No output depends on itself, directly or through others |

### 11. Recipes

A recipe says how an output is made: a shell command, and optionally the
context it runs in. The command reaches the output's inputs and decisions
through placeholders, which a runner fills in before running it.

<!-- fragment: Analysis -->
```yaml
outputs:
  output1:
    type: metric
    format: json
    inputs: [input1, subanalysis.output1]
    decisions: [decision1]
    recipe:
      command: >-
        python src/output1.py '{inputs.input1}' '{inputs.subanalysis.output1}'
        '{decisions.decision1}' '{output}'
      resources: {cpus: 2, memory: 4GB}
```

- A recipe has a `command` ([`MISSING_FIELD`](#5-the-astrayaml-file)); its
  fields are in the [field reference](elements/Recipe.md).
- `resources` ([Resources](elements/Resources.md)) are the CPUs, memory,
  time, disk and GPUs the recipe asks for. `cpus` is at least 0 and `gpus` at
  least 1 ([`INVALID_VALUE`](#5-the-astrayaml-file)).
- `container` is the container the recipe runs in: an image, or a
  Containerfile it is built from. `Analysis.container` is the default
  container of the analysis's recipes.
- A recipe runs in its analysis's folder
  ([`WRONG_WORKING_DIRECTORY`](#21-runners)).

#### The command as a template

The `command` is a POSIX shell command and a template. Read from the left,
`{{` stands for a literal `{` and `}}` for a literal `}`, and any other `{`
opens a placeholder, which ends at the next `}`. A runner substitutes each
placeholder, and each `{{` and `}}`, before running the command:

| Placeholder | Becomes |
|---|---|
| `{inputs.<entry>}` | the path of what an entry of the output's `inputs` names |
| `{decisions.<entry>}` | the id of the option selected for the decision an entry of the output's `decisions` names |
| `{inputs}` | the paths of all the output's inputs, in the order of `inputs`, separated by spaces |
| `{output}` | the path the result is written to |

- A placeholder gives a path, relative or absolute, that the recipe can open
  from the folder it runs in.
- A runner substitutes each placeholder verbatim, with no shell quoting.
- In `{inputs.<entry>}` and `{decisions.<entry>}`, `<entry>` is an entry of
  the output's `inputs` or `decisions` exactly as written, dots and `#`
  included: `{inputs.subanalysis.output1}`, `{inputs.output1#u1}`,
  `{decisions.subanalysis.decision1}`. Two
  [pins](#13-pins-and-outputs-built-per-universe-or-once) of one output are
  two entries, each with its own placeholder.
- Any other placeholder breaks [`UNDECLARED_TEMPLATE_REF`](#11-recipes): one
  naming an entry the output doesn't list, such as `{inputs.input2}` when
  `input2` isn't among its `inputs`, or one of none of these forms, such as
  `{foo}`. So does a stray brace: a `{` with no `}` after it, or a `}` that
  ends no placeholder, as in `echo }`.

#### What a recipe reads

A recipe should read the files inputs name, and other outputs' results, only
through its output's inputs ([`UNDECLARED_READ`](#21-runners)), since a
checker sees a change to them only through those inputs. Anything else it
uses, its own scripts among them, is pinned by the commit or is part of the
environment.

#### The rules

| Code | Layer | Level | Rule |
|---|---|---|---|
| `UNDECLARED_TEMPLATE_REF` | validator | MUST | Every brace in a recipe's `command` belongs to a `{{`, a `}}` or a placeholder, read from the left, and every placeholder is `{inputs}`, `{output}`, or an `{inputs.<entry>}` or `{decisions.<entry>}` whose `<entry>` is an entry of its output's `inputs` or `decisions` exactly as written |

### 12. Universes

A universe selects one option for each active decision of its analysis: it
is one way of making the analysis's choices.
[§16](#16-driving-and-consuming) adds the decisions of the analyses its
universes [drive](#16-driving-and-consuming). An analysis's universes are
entries of its `universes`. An entry can instead be an import (below). No
universe is privileged: there is no default universe or option, and a
universe called `baseline` is one with that name and nothing more.

<!-- fragment: Analysis -->
```yaml
universes:
  u1:
    decisions: {decision1: a, decision2: a, subanalysis.decision1: a}
  u2:
    derived_from: u1
    decisions: {decision1: b, decision2: b, decision3: a}
  u3:
    derived_from: u2
    decisions: {decision1: a}   # the inherited decision3 is dropped
```

Here `decision3` has `when: [decision1.b]` ([§9](#9-conditions)), and
`subanalysis.decision1` is a decision of the declared analysis
`subanalysis`, which these universes set ([§16](#16-driving-and-consuming)).
Once `derived_from` is resolved (below), the three universes select:

| Universe | Selects |
|---|---|
| `u1` | `decision1: a`, `decision2: a`, `subanalysis.decision1: a` |
| `u2` | `decision1: b`, `decision2: b`, `decision3: a`, `subanalysis.decision1: a` |
| `u3` | `decision1: a`, `decision2: b`, `subanalysis.decision1: a` |

- A universe's fields are in the [field reference](elements/Universe.md).
- A universe's `decisions` map decisions to options
  ([DecisionSelection](elements/DecisionSelection.md)), as
  `<decision>: <option>`, such as `decision1: a`.
- A key is the id of a decision of the analysis or, for a decision of
  another analysis, its address, `<declaration>.<decision>` ([§6](#6-names)).
  [§16](#16-driving-and-consuming) gives in full the keys that set another
  analysis's decisions.
- A value is the id of one of that decision's options
  ([`UNKNOWN_OPTION`](#8-decisions-and-options)).
- `derived_from` names another universe of the same analysis, never an
  import ([`UNKNOWN_DERIVED_FROM`](#12-universes)). The universe inherits
  that universe's selection, so it gives only the decisions it changes.
- A derived universe inherits only the selection.

#### The effective selection

A universe's **effective selection** is what it selects once `derived_from`
is resolved. Conditions ([§9](#9-conditions)) are judged on it.

1. Without `derived_from`, it is the universe's own `decisions`.
2. With `derived_from`, it is the effective selection of the universe named
   there, each of the universe's own selections replacing what the universe
   inherits for its decision.
3. An inherited selection of a decision that isn't active in the resulting
   selection is dropped, so a universe that switches a decision off needn't
   undo what it inherited for it. `u3` selects `decision1: a`, which switches
   `decision3` off, so the `decision3: a` it inherits from `u2` is dropped.

The effective selection is held to everything a universe written in full is:

- it selects every active decision of its analysis, so a universe that
  switches a decision on sets it
  ([`MISSING_DECISION`](#16-driving-and-consuming), which
  [§16](#16-driving-and-consuming) extends to the analyses a universe
  drives);
- it names only declared decisions and their options
  ([`UNRESOLVED_ADDRESS`](#6-names),
  [`UNKNOWN_OPTION`](#8-decisions-and-options));
- it breaks no `requires` ([`MISSING_REQUIRED_OPTION`](#12-universes)) and
  no `incompatible_with` ([`INCOMPATIBLE_OPTIONS`](#12-universes)), and
  selects no excluded option ([`EXCLUDED_OPTION_SELECTED`](#12-universes)).

A selection the universe makes itself, rather than inherits, is of an
active decision ([`INACTIVE_DECISION`](#12-universes)). So `u3` couldn't
select `decision3` itself.

#### Imports

An entry of `universes` can instead be an **import**, which names one of
another analysis's universes under the entry's id and selects nothing. Its
`analysis` is the address of the declaration that leads to that analysis,
and its `universe` is the id of one of that analysis's universes. Where
`subanalysis` has a universe `v1` of its own, `u1` is a universe of this
file and `subanalysis_v1` an import:

<!-- fragment: Analysis -->
```yaml
analyses:
  subanalysis: {path: subanalysis}
universes:
  u1:
    decisions: {decision1: a, decision2: a, subanalysis.decision1: a}
  subanalysis_v1:                  # an import of subanalysis's own universe v1
    analysis: subanalysis
    universe: v1
```

- An import has both `analysis` and `universe`, and neither `decisions` nor
  `derived_from` ([`INVALID_IMPORT`](#12-universes)).
- It is not one of the analysis's universes.
- A universe and an import are both written as a
  [Universe](elements/Universe.md) object. An import's `label`,
  `description` and `tags` are its own: they describe the universe it
  imports under the import's id.
- [§16](#16-driving-and-consuming) says which analysis drives the universe
  an import names, and where it is built.

#### The rules

| Code | Layer | Level | Rule |
|---|---|---|---|
| `INVALID_IMPORT` | schema | MUST | An entry of `universes` with an `analysis` or a `universe` is an import, which has both and has neither `decisions` nor `derived_from` |
| `UNKNOWN_DERIVED_FROM` | validator | MUST | A universe's `derived_from` names a universe of the same analysis, never an import |
| `DERIVED_FROM_CYCLE` | validator | MUST | No universe's chain of `derived_from` loops back to it |
| `MISSING_REQUIRED_OPTION` | validator | MUST | Every effective selection satisfies the `requires` of every option it selects |
| `INCOMPATIBLE_OPTIONS` | validator | MUST | Every effective selection satisfies the `incompatible_with` of every option it selects |
| `EXCLUDED_OPTION_SELECTED` | validator | MUST | No effective selection selects an excluded option |
| `INACTIVE_DECISION` | validator | MUST | A universe itself sets only decisions whose `when` holds in its effective selection |

### 13. Pins, and outputs built per universe or once

An output is either built per universe, with a result in each universe where
it is active, or built once, with one result for all of them. A pin fixes the
universe a reference reads, so an output built once can compare the results
of two universes:

<!-- fragment: Analysis -->
```yaml
outputs:
  output2:
    type: table
    format: csv
    inputs: [output1#u1, output1#u2]
    recipe:
      command: >-
        python src/output2.py '{inputs.output1#u1}' '{inputs.output1#u2}'
        '{output}'
```

`output1` lists `decisions`, so it is built per universe
([§10](#10-outputs)). `output2` reads it as built in `u1` and as built in
`u2`, and is built once. So is `output3`, which reads only `input1`.

#### Pins

A [reference](elements/Reference.md) ([§6](#6-names)) can end in `#` and a
universe id, a **pin**: `output1#u1`. `#` is never part of an id, so the pin
is unambiguous. In an `astra.yaml`, a pin names the entry of the file's
`universes` with its id, one of the file's analysis's universes or an import
([§12](#12-universes)), or, where the file has no such entry, the universe
with that id of the analysis whose element the reference names.
[§16](#16-driving-and-consuming) gives that case in full
([`UNKNOWN_PIN_UNIVERSE`](#16-driving-and-consuming)).

- A pin on an output reads it in that universe.
- A pin on an input names a universe and changes nothing else.

#### Built per universe or built once

An output is **built per universe** when it lists `decisions`, has a `when`,
or has an unpinned entry of `inputs` that names an output built per
universe. Any other output is **built once**: it has one result, the same in
every universe.

- Inputs carry no universe, and a pinned entry never makes an output built
  per universe, since the pin fixes the universe it reads.
- Listing a decision that reaches the output through an unpinned input gives
  the output the same results as not listing it, though listing a decision
  of another analysis [consumes](#16-driving-and-consuming) it, and the
  address it is listed under is then held to the rules on consuming
  ([`UNDRIVEN_DECLARATION`](#16-driving-and-consuming)).
- Listing a decision that only a pinned input brings in makes the output
  built per universe, so a comparison between universes, such as `output2`,
  lists none.
- An output built once has no universe of its own. It lists no decisions, so
  its recipe has no `{decisions.<entry>}` placeholder
  ([`UNDECLARED_TEMPLATE_REF`](#11-recipes)). A pin on it doesn't change
  which result a reference names: pinned or not, the reference names its one
  result, and `{inputs.<entry>}` gives that result's path. The pin still
  names a universe ([`UNKNOWN_PIN_UNIVERSE`](#16-driving-and-consuming)).

#### Which universe a reference reads

An unpinned entry of `inputs` reads its output in the
[universe being built](#16-driving-and-consuming).
A pinned one, such as `output1#u1`, reads it as built in the universe the
pin names, whichever universe is being built.

Where `output4` has `when: [decision1.b]`, the reference `output4#u1` breaks
[`PIN_INACTIVE`](#13-pins-and-outputs-built-per-universe-or-once), since `u1`
selects `decision1: a`. An output with a result planned
([§18](#18-results-and-where-they-go)) in `u1` that reads `output4` without a
pin breaks
[`INPUT_NOT_BUILT`](#13-pins-and-outputs-built-per-universe-or-once).

#### The rules

| Code | Layer | Level | Rule |
|---|---|---|---|
| `PIN_INACTIVE` | validator | MUST | Every pinned output is active in the universe it is pinned to |
| `INPUT_NOT_BUILT` | validator | MUST | Every output read without a pin by the output of a result planned in the universe being built is active (its `when` holds) there |

### 14. Insights and evidence

An insight is a claim backed by evidence. An analysis's `prior_insights` are
what earlier work establishes and the analysis builds on, which options cite
by id. Its `findings` are what it concludes.

<!-- fragment: Analysis -->
```yaml
prior_insights:
  insight2:
    claim: An earlier study found that decision1 changes the result.
    evidence:
      - doi: 10.5555/12345678
        location: {value: page=6}
findings:
  insight1:
    claim: Options a and b of decision1 give different results.
    evidence:
      - artifact: output2
```

- An insight's fields are in the [field reference](elements/Insight.md).
- An insight has a `claim` and at least one item of `evidence`
  ([`MISSING_FIELD`](#5-the-astrayaml-file),
  [`EMPTY_COLLECTION`](#5-the-astrayaml-file)). Its `description` gives the
  reasoning behind the claim, and its `scope` the conditions under which the
  claim holds.
- An option's `insights` are the ids of the prior insights that support it,
  such as `insights: [insight2]`
  ([`INVALID_INSIGHT_REF`](#14-insights-and-evidence)).

#### Evidence

An [Evidence](elements/Evidence.md) item cites exactly one of
([`INVALID_EVIDENCE_SOURCE`](#14-insights-and-evidence)):

- a published work, by its `doi`, such as `10.5555/12345678` (`10.`, digit
  runs joined by `.`, `/`, then a non-empty suffix:
  [`INVALID_VALUE`](#5-the-astrayaml-file)), with the work's `version`,
  counted from 1, when the work has versions, as an arXiv paper does;
- an output, as an `artifact`: a reference written as in `Output.inputs`,
  which names an output ([`UNRESOLVED_ADDRESS`](#6-names)).

Evidence has a `version` only with a `doi`
([`INVALID_EVIDENCE_SOURCE`](#14-insights-and-evidence)). It locates the
passage the claim rests on with W3C Web Annotation selectors:

- `quote`, a [TextQuoteSelector](elements/TextQuoteSelector.md)
  (`oa:TextQuoteSelector`): its `exact` is the passage as the work or output
  writes it, with the `prefix` and `suffix` around it;
- `location`, a [FragmentSelector](elements/FragmentSelector.md)
  (`oa:FragmentSelector`): the place in the work or output the claim rests
  on.

For a `doi`, the cited resource is the work's full text. With both a `quote`
and a `location`, the quote is sought within the location.

#### Fragment identifiers

A location's `value` is a fragment identifier of the cited work or output,
without the `#`. An optional `conforms_to` is the IRI of the specification
of the fragment syntax `value` follows, as
[Web Annotation §4.2.1](https://www.w3.org/TR/annotation-model/#fragment-selector)
gives it:

| Syntax | `conforms_to` | `value`, for example |
|---|---|---|
| CSV ([RFC 7111](https://www.rfc-editor.org/rfc/rfc7111)) | `http://tools.ietf.org/rfc/rfc7111` | `row=5-7` |
| Plain text ([RFC 5147](https://www.rfc-editor.org/rfc/rfc5147)) | `http://tools.ietf.org/rfc/rfc5147` | `char=0,10` |
| Image, audio or video ([Media Fragments](https://www.w3.org/TR/media-frags/)) | `http://www.w3.org/TR/media-frags/` | `xywh=50,50,640,480`, `t=10,20` |
| HTML ([RFC 3236](https://www.rfc-editor.org/rfc/rfc3236)) | `http://tools.ietf.org/rfc/rfc3236` | `results` |
| EPUB ([EPUB CFI](https://idpf.org/epub/linking/cfi/epub-cfi.html)) | `http://www.idpf.org/epub/linking/cfi/epub-cfi.html` | `epubcfi(/6/4!/4/10/2/1:1)` |

Without `conforms_to`, `value` is a PDF fragment identifier as
[RFC 8118 §3](https://www.rfc-editor.org/rfc/rfc8118#section-3) gives it (it
defers to ISO 32000-2), such as `page=6`, with pages counted from 1; it can
point at more than a page. Web Annotation names that syntax
`http://tools.ietf.org/rfc/rfc3778`, after the RFC that RFC 8118 obsoletes.
Writing that IRI means the same as writing none, and `value` is then read by
RFC 8118.

`value` is read by the syntax `conforms_to` names.
[Annex C](#c-grammars-and-patterns) gives the characters `value` may hold,
and the form of `conforms_to`, an IRI
([`INVALID_VALUE`](#5-the-astrayaml-file)).

#### Evidence and universes

Evidence isn't built in a universe. Citing an output built per universe, it
may pin it, as `output1#u2`: the claim is then about one universe's result,
and the pin says which. The pin names a universe as one in `Output.inputs`
does ([§13](#13-pins-and-outputs-built-per-universe-or-once),
[§16](#16-driving-and-consuming)).

#### The rules

| Code | Layer | Level | Rule |
|---|---|---|---|
| `INVALID_EVIDENCE_SOURCE` | schema | MUST | Evidence has exactly one of `doi` and `artifact`, and has a `version` only with a `doi` |
| `INVALID_INSIGHT_REF` | validator | MUST | Every entry of `Option.insights` names a prior insight of the analysis |

### 15. Declared analyses

An analysis can use the elements of other analyses. It declares each one by
a **declaration**, an entry of `analyses` keyed by the id it addresses it by,
and then addresses the declared analysis's elements through that id, as
`<declaration>.<element>`.
Here the root declares the analysis in the folder `subanalysis`, and the
root's `output1` reads that analysis's `output1`:

<!-- fragment: Analysis -->
```yaml
analyses:
  subanalysis:
    path: subanalysis
outputs:
  output1:
    type: metric
    format: json
    inputs: [input1, subanalysis.output1]
    decisions: [decision1]
    recipe:
      command: >-
        python src/output1.py '{inputs.input1}' '{inputs.subanalysis.output1}'
        '{decisions.decision1}' '{output}'
```

The folder `subanalysis` holds an analysis of its own, whose `astra.yaml` is:

```yaml
spec_version: "0.1.0"
inputs:
  input1:
    path: data/input1.csv
decisions:
  decision1:
    options:
      a: {}
      b: {}
outputs:
  output1:
    type: metric
    format: json
    inputs: [input1]
    decisions: [decision1]
    recipe:
      command: python src/output1.py '{inputs.input1}' '{decisions.decision1}' '{output}'
```

- A declaration's fields are in the
  [field reference](elements/AnalysisDeclaration.md). A declaration names its
  analysis by a `path`, as here, or by a `url` and a `commit`, and a `path`
  can have a `commit` too
  ([§17](#17-analyses-from-another-commit-or-repository)).
- The declarations an address goes through, in order, form a **chain of
  declarations**. A chain starts in one file, and each of its declarations
  is in the file of the analysis the one before reaches. The analyses **on
  the chain** are the one whose file it starts in and each one its
  declarations reach. A declaration **leads back** when the analysis it
  reaches, known by its identity
  ([§17](#17-analyses-from-another-commit-or-repository)), is already on the
  chain.
- The **root** is the analysis being validated or built, and any analysis can
  be the root. Its **analysis stack** is the root and every analysis it
  declares, directly or through other declared analyses.

#### A declaration by path

- `path` is the folder of the declared analysis's `astra.yaml`
  ([§7](#7-inputs)).
- Tidied as text ([Annex B](#b-paths-and-git)), it doesn't go above the top
  of the root's working tree or, read at a commit, of the repository that
  holds that commit
  ([`DECLARATION_OUTSIDE_REPOSITORY`](#15-declared-analyses)).
- The folder it names holds an `astra.yaml` file, reached through no symlink
  ([`MISSING_DECLARED_ANALYSIS`](#15-declared-analyses),
  [Annex B](#b-paths-and-git)).
- A declared analysis can be a git submodule, read as
  [Annex B](#b-paths-and-git) says. A submodule that declares something
  outside its own repository, such as its parent with `..`, can be validated
  and built only from a root whose repository holds what it declares.

#### One analysis, however it is declared

An analysis, whichever analysis declares it and by whatever id, is one
analysis: each of its results is made at most once, however many
declarations reach it ([§17](#17-analyses-from-another-commit-or-repository)).

- Two addresses written differently that resolve to one element of one
  analysis are two **spellings** of it. Were the root also to declare
  `again: {path: subanalysis}`, `again.output1` and `subanalysis.output1`
  would be one output.
- A list can name one element under two spellings: they are two entries. In
  `Output.inputs` and `Output.decisions` each has its own placeholder
  ([§11](#11-recipes)), and in `Output.inputs` its own recorded input
  ([§19](#19-records)). Only the same entry written twice is refused
  ([`DUPLICATE_ENTRY`](#5-the-astrayaml-file)).
- A declaration by `path` alone, or a chain of them, that leads back to the
  declaring analysis's own folder names the analysis itself:
  `self: {path: .}`, say, or `subanalysis.parent` in the root's file, where
  `subanalysis` declares `parent: {path: ..}`. An address through it is
  another spelling of one of the analysis's own elements.
  [Consuming](#16-driving-and-consuming) uses another analysis's elements, so
  such an address consumes nothing, and no key goes through it
  ([§16](#16-driving-and-consuming)).
- Declarations by `path` alone can form cycles, such as an analysis declared
  by its parent that declares its parent with `..`, but outputs never depend
  on each other in a cycle ([`OUTPUT_CYCLE`](#10-outputs)). A declaration with
  a `commit` is never part of a cycle, since a commit can only name earlier
  ones.
- An output never shares its id with a declaration of its analysis, since
  their results' [default places](#18-results-and-where-they-go) could then
  be the same ([`CLASHING_RESULT_NAME`](#15-declared-analyses)).

#### The rules

| Code | Layer | Level | Rule |
|---|---|---|---|
| `DECLARATION_OUTSIDE_REPOSITORY` | validator | MUST | A declaration's `path`, tidied ([Annex B](#b-paths-and-git)), doesn't go above the top of the root's working tree or, read at a commit, of the repository that holds that commit |
| `MISSING_DECLARED_ANALYSIS` | validator | MUST | The folder a declaration names holds an `astra.yaml` file, reached through no symlink ([Annex B](#b-paths-and-git)) |
| `CLASHING_RESULT_NAME` | validator | MUST | No output shares its id with a declaration of the same analysis |

### 16. Driving and consuming

An analysis uses the elements of another in two ways: it consumes them, and
its universes can drive the other analysis. Here the root's universes drive
`subanalysis` by setting its `decision1`:

<!-- fragment: Analysis -->
```yaml
analyses:
  subanalysis:
    path: subanalysis
universes:
  u1:
    decisions: {decision1: a, decision2: a, subanalysis.decision1: a}
```

`u2` and `u3` inherit the key `subanalysis.decision1` from `u1`
([§12](#12-universes)). So in each of the root's universes, the root's
`output1` reads `subanalysis.output1` as `subanalysis` builds it with its
`decision1` set to `a`, and those results
[belong to](#18-results-and-where-they-go) the root. A universe's
keys are in the [field reference](elements/DecisionSelection.md).

#### Consuming

**Consuming** is using an element of another analysis by address: an input
or an output in `Output.inputs`, a decision in `Output.decisions`, in a
condition or in a constraint, and an output in evidence. A consumed decision
has the option selected in the universe being built, so its address never
takes a pin, and whatever uses it can be built only where the decision's
analysis is built in that universe
([`NOT_BUILT_IN_UNIVERSE`](#16-driving-and-consuming)).

#### Driving

**Driving** is setting another analysis's decisions from one's own
universes, by **flat keys**: the decision's address,
`<declaration>.<decision>`, through as many declarations as lead to it
(`subanalysis.decision1`, `stage.inner.d`). The analysis whose universes
drive is the **driver**, and each analysis reached through a declaration they
drive is **driven** through that declaration. An analysis with no decisions
has no key to set, and is driven by being built in its driver's universes.

- A key resolves through its declarations to one decision: an analysis,
  known by its identity
  ([§17](#17-analyses-from-another-commit-or-repository)), and the decision's
  id in it, so two keys can spell one decision (below).
- No key goes through a declaration that leads back to an analysis already
  on its chain, the universe's analysis included
  ([`LOOPING_KEY`](#16-driving-and-consuming)). So the analysis's own
  decisions are keyed by their ids alone, and where `stage` declares
  `again: {path: .}`, `stage.d` is never written `stage.again.d`.

**Which declarations are driven.** An analysis's universes **drive** a
declaration when a key in the effective selection ([§12](#12-universes)) of
any of them goes through every declaration from the analysis's file to that
one, and a declaration they drive is driven in every one of them. A key that
loops ([`LOOPING_KEY`](#16-driving-and-consuming)) drives no declaration.

- Each chain of declarations from the driver's file, such as `stage`,
  `stage.inner` and `inner`, is driven on its own. The key `stage.inner.d`
  drives the driver's `stage` and, through it, `stage`'s `inner`, but not an
  `inner` that the driver's file declares itself. Two chains that end in one
  declaration, such as `stage.lib` and `stage_undriven.lib` where `stage` and
  `stage_undriven` declare one folder, are driven on their own too, and an
  address or a reference is judged on its own chain.
- A declaration of an analysis with no decisions is driven when the chain
  before it is, and so whenever the driver's file declares it, unless the
  declaration leads back to an analysis already on the chain, the declaring
  analysis itself included (`self: {path: .}`). Such an analysis's outputs
  built per universe are then built in each of the driver's universes where
  they are [planned](#18-results-and-where-they-go), and those results
  belong to the driver, while its outputs built once still belong to it.
  Universes of its own don't change this. They are built only where it is the
  driver: when it is the root, or where one of them is among the universes
  built (below).

**What a universe sets.**

- Every universe sets every active decision of every analysis reached
  through a declaration that its analysis's universes drive
  ([`MISSING_DECISION`](#16-driving-and-consuming)), whichever of them has
  the key that drives it. A universe in which `when` switches off every
  decision of a driven analysis sets nothing for it.
- Driving is judged on the effective selections, so a key a derived universe
  inherits counts as one it sets.
- An analysis reached through two driven declarations can have a decision
  set under either spelling (`stage.inner.d` or `inner.d`). A universe's own
  `decisions` give each decision one key: two keys that spell one decision
  break [`DUPLICATE_ELEMENT`](#16-driving-and-consuming), even when they
  select the same option. A universe that inherits a decision under one key
  changes it under that key: setting it under another, even to the same
  option, breaks [`DUPLICATE_ELEMENT`](#16-driving-and-consuming) at its own
  key.
- In a universe being built, a driven analysis's own universes don't set its
  decisions. A pin naming one of them still reads it: in its own file, or in
  another through an import or, for one of its own elements, where that file
  has no entry with the pin's id (below). Each universe being built has one
  driver, the analysis whose universe it is.

Driving leaves an analysis able to stand alone, and consuming a decision
ties the outputs that use it to the decision's analysis. By convention, a
decision that matters to one analysis is driven, and one shared by several,
such as the seed of a whole stack, is consumed.

#### The universe being built

A universe is named by its analysis and its id, since the same id can name a
universe in several analyses. When an analysis is built in one of its
universes, that universe is the **universe being built** in the analysis and
in every analysis reached through a declaration its universes drive.

The **universes built** are the root's and those named by a pin on an output
built per universe, in the `inputs` of a
[planned result](#18-results-and-where-they-go)'s output or in the root's
evidence. Such a pin names one of the universes of the analysis whose file
it is in or, through an import or where that file has no entry with the
pin's id, another analysis's universe (below).

- In the root's universes the root is the driver and is never driven, even
  when a declaration in its stack leads back to it.
- Another analysis's universe is used only where such a pin names it, in
  that analysis's file or in another. That analysis is then its only driver:
  like the root, it is never driven in that universe, and what is built there
  [belongs to](#18-results-and-where-they-go) it.
- Neither the root nor the analysis whose file imports the universe is the
  driver there: a declaration of either in that analysis's file, such as
  `parent: {path: ..}`, leads back to no analysis already on the chain, and
  is an ordinary declaration. Where that analysis's universes drive one of
  them, as the key `parent.decision1` drives a parent, it is driven and built
  in that universe like any other analysis.

Two rules hold in the universe being built. They apply wherever:

- the output of a result planned there reads an output built per universe
  without a pin, or consumes a decision;
- the output of a planned result, or the root's evidence, pins an output
  built per universe to the universe being built;
- an output's `when` consumes a decision where the output's result would be
  planned if the `when` held;
- in an analysis built in that universe, a decision's `when` or a constraint
  consumes one.

The rules are:

1. The analysis of the output read or pinned, or of the decision consumed,
   is built in the universe being built
   ([`NOT_BUILT_IN_UNIVERSE`](#16-driving-and-consuming)). The analysis
   whose universe is being built is always built in it, so an analysis it
   drives can consume its decisions and read its outputs back through `..`:
   where `subanalysis` declares `parent: {path: ..}`, it can consume the
   root's `decision1` as `parent.decision1`.
2. In the file of the analysis whose universe is being built, the file's
   universes drive the chain of each such address of another analysis, from
   the file's declaration to the address's last
   ([`UNDRIVEN_DECLARATION`](#16-driving-and-consuming)). Uses in other files
   come under the first rule alone.

**A second declaration of one folder.** Where the root also declares
`subanalysis`'s folder as `undriven: {path: subanalysis}`, which no key of
the root's universes goes through, that declaration is judged on its own
chain, so it isn't driven. A read through it in one of the root's universes,
without a pin or pinned to one of them, breaks
[`UNDRIVEN_DECLARATION`](#16-driving-and-consuming):

<!-- fragment: Analysis -->
```yaml
analyses:
  subanalysis:
    path: subanalysis
  undriven:
    path: subanalysis
outputs:
  output6:
    type: metric
    format: json
    inputs:
      - undriven.output1      # UNDRIVEN_DECLARATION
      - undriven.output1#u1   # UNDRIVEN_DECLARATION
    recipe:
      command: python make.py '{output}'
```

The address's whole chain decides, up to its last declaration. Where the
root's universes drive `stage.inner` but not `stage`'s second declaration
`inner_undriven`, `stage.inner_undriven.out` read in the root's file, without
a pin or pinned to one of the root's universes, breaks
[`UNDRIVEN_DECLARATION`](#16-driving-and-consuming) too, though the root
drives `stage`. So does `stage_undriven.inner.out`, where the root's
`stage_undriven` declares `stage`'s folder a second time, though the root
drives `stage.inner`.

#### Pins and imported universes

A pin `#u` resolves in the file it is written in
([§13](#13-pins-and-outputs-built-per-universe-or-once)), whatever drives
that file's analysis, so what it names is the same under every root. Where
the file's `universes` has no entry `u`, the pin names the universe `u` of
the analysis whose element the reference names, as an import of it would:
one of that analysis's universes, never an import in its file. Where that
analysis has no universe `u` either, as for an element of the file's own
analysis, the pin names nothing
([`UNKNOWN_PIN_UNIVERSE`](#16-driving-and-consuming)).

So adding or removing an entry `u` in a file's `universes` can change what a
pin `#u` in that file names. A pin that names one of its file's universes is
in the driver's file, so both rules above hold it. One that names another
analysis's universe is not, so the first rule alone holds it.

The universe an import ([§12](#12-universes)) names is an **imported
universe** of the importing file, which a pin there names by the import's
id. An import resolves in its file by identity, so it names one universe
under every root. Its `analysis` can lead to any analysis the file's
declarations reach: one below, its parent through `..`, a sibling through
the parent, or an
[analysis from a commit](#17-analyses-from-another-commit-or-repository).
That is another analysis than the file's own, and its `universe` is one of
that analysis's universes, never an import in its file
([`UNRESOLVED_ADDRESS`](#6-names)).

- An import selects nothing and drives nothing. No selection rule
  ([§12](#12-universes)) checks it in the importing analysis, and no
  `derived_from` names it ([`UNKNOWN_DERIVED_FROM`](#12-universes)). The
  universe it names is checked as a universe of its own analysis (below).
- The importing analysis is built in the universe an import names only where
  that universe drives it, as a key `parent.d` drives a parent.
- An imported universe is built where it is among the universes built
  (above). Imports of one universe, in one file or several and under any ids,
  name that one universe, which is built once.

The universe a pin names where its file has no entry with its id is an
imported universe too, and all of the bullets above hold of it. So an import
is needed only where the file has an entry with the universe's id, or for a
universe of another analysis than the one whose element the reference names,
such as `stage`'s for `stage.lib.out`.

Where `subanalysis` has universes of its own, `u1` and `v1`, this root reads
its `output1` in three universes:

<!-- fragment: Analysis -->
```yaml
analyses:
  subanalysis:
    path: subanalysis
outputs:
  output5:
    type: table
    format: csv
    inputs:
      - subanalysis.output1#u1               # the root's u1
      - subanalysis.output1#subanalysis_u1   # subanalysis's own u1, imported
      - subanalysis.output1#v1               # subanalysis's own v1
    recipe:
      command: python make.py '{output}'
universes:
  u1:                                        # the root's u1 drives subanalysis
    decisions: {decision1: a, decision2: a, subanalysis.decision1: a}
  subanalysis_u1:                            # an import of subanalysis's u1
    analysis: subanalysis
    universe: u1
```

- `subanalysis.output1#u1` reads `subanalysis`'s output as the root builds it
  in its `u1`, where the root's universes drive `subanalysis`, and the result
  belongs to the root.
- `subanalysis.output1#subanalysis_u1`, since the root has a `u1` of its
  own, reads it through an import, as `subanalysis` builds it in its own
  `u1`.
- `subanalysis.output1#v1`, since the root has no `v1`, reads it as
  `subanalysis` builds it in its own `v1`.
- Those last two results belong to `subanalysis`, whichever file reads them.

In a file with no `v1`, `stage.lib.out#v1` names `lib`'s `v1`, since `out` is
`lib`'s output. Where `stage`'s universes drive `lib`, the file reads `out`
as `stage` builds it in its own `v1` by importing that universe,
`stage_v1: {analysis: stage, universe: v1}`, and pinning
`stage.lib.out#stage_v1`.

#### What a validator checks

A validator checks every universe of every analysis of the stack, a driven
analysis's own included. Each universe's selections are held to
[§12](#12-universes) and to driving ([`UNRESOLVED_ADDRESS`](#6-names),
[`UNKNOWN_OPTION`](#8-decisions-and-options),
[`DUPLICATE_ELEMENT`](#16-driving-and-consuming),
[`LOOPING_KEY`](#16-driving-and-consuming),
[`UNKNOWN_DERIVED_FROM`](#12-universes),
[`DERIVED_FROM_CYCLE`](#12-universes),
[`MISSING_DECISION`](#16-driving-and-consuming),
[`INACTIVE_DECISION`](#12-universes),
[`MISSING_REQUIRED_OPTION`](#12-universes),
[`INCOMPATIBLE_OPTIONS`](#12-universes),
[`EXCLUDED_OPTION_SELECTED`](#12-universes)).

- The declarations driven in a universe are those its analysis's universes
  drive, as above, a declaration back to the root included; checking a
  universe builds nothing, so the root stays undriven in its own universes.
  Where the root drives `subanalysis`, a universe of `subanalysis`'s own
  that leaves its active `decision1` unset breaks
  [`MISSING_DECISION`](#16-driving-and-consuming), though the root's
  universes don't use it.
- The rules on the universe being built
  ([`NOT_BUILT_IN_UNIVERSE`](#16-driving-and-consuming),
  [`UNDRIVEN_DECLARATION`](#16-driving-and-consuming),
  [`INPUT_NOT_BUILT`](#13-pins-and-outputs-built-per-universe-or-once)) hold
  only in the universes built, as
  [`RESULT_IN_TWO_PLACES`](#16-driving-and-consuming) does, and for an
  output only where its result is planned or, for its `when`, would be if the
  `when` held.

#### The rules

| Code | Layer | Level | Rule |
|---|---|---|---|
| `NOT_BUILT_IN_UNIVERSE` | validator | MUST | Every output built per universe of another analysis read without a pin by the output of a result planned in the universe being built, every output built per universe that the output of a planned result, or the root's evidence, pins to that universe, and every decision of another analysis that the output of a result planned there consumes, that an output's `when` consumes where the output's result would be planned if the `when` held, or that a decision's `when` or a constraint consumes in an analysis built there, belongs to an analysis built in that universe |
| `DUPLICATE_ELEMENT` | validator | MUST | No universe has two keys in its own `decisions` that spell one decision, or sets a decision it inherits under a key it doesn't inherit |
| `LOOPING_KEY` | validator | MUST | No key in a universe's own `decisions` goes through a declaration that leads back to an analysis already on its chain, the universe's analysis included |
| `MISSING_DECISION` | validator | MUST | Every universe's effective selection sets every active decision of its analysis and of every analysis reached through a declaration that its analysis's universes drive |
| `UNDRIVEN_DECLARATION` | validator | MUST | In the file of the analysis whose universe is being built, every address by which the output of a result planned in that universe reads another analysis's output built per universe without a pin, by which the output of a planned result or the root's evidence pins another analysis's output built per universe to that universe, or by which the output of a result planned there, an output's `when` where the output's result would be planned if the `when` held, a decision's `when` or a constraint consumes another analysis's decision, has its chain of declarations driven by the file's universes (a key in their effective selections goes through every declaration of the address, or the last declaration's analysis has no decisions, the chain before it is driven, and that declaration leads back to no analysis already on the chain) |
| `UNKNOWN_PIN_UNIVERSE` | validator | MUST | Every pin in an `astra.yaml` names an entry of that file's `universes` or, where the file has no entry with its id, a universe of the analysis whose element its reference names |
| `RESULT_IN_TWO_PLACES` | validator | SHOULD | No planned result has two names: its output's analysis is reached through at most one chain of driven declarations from the analysis the result belongs to ([§18](#18-results-and-where-they-go)) |

### 17. Analyses from another commit or repository

A declaration with a `commit` names an **analysis from a commit**: the
declared analysis as it was at that commit. With a `url` in place of a
`path`, it comes from another repository. Here the root declares
`subanalysis`, in its own repository, and `remote`, an analysis of another
repository at a commit:

<!-- fragment: Analysis -->
```yaml
analyses:
  subanalysis:
    path: subanalysis
  remote:
    url: https://example.org/remote.git
    commit: <commit>
```

`remote`'s `output1` is built once, so an output of the root reads it as
`remote.output1`, without a pin. Its result is read through its record at
that commit, and none of `remote`'s recipes runs.

- A declaration has exactly one of `path` and `url`
  ([`INVALID_DECLARATION_SOURCE`](#17-analyses-from-another-commit-or-repository)),
  and may have a `commit`, which a `url` needs
  ([`URL_WITHOUT_COMMIT`](#17-analyses-from-another-commit-or-repository)).
  Its fields are in the [field reference](elements/AnalysisDeclaration.md).
- `url` is a remote that git fetches another repository from. The declared
  analysis is the one at the top level of that repository, at the
  declaration's `commit`. A `url` holds no ASCII space or control character,
  and takes one of two forms
  ([`INVALID_VALUE`](#5-the-astrayaml-file)):
  - `scheme://` and at least one character, where the scheme is an ASCII
    letter followed by any ASCII letters, digits, `+`, `.` and `-`:
    `https://example.org/remote.git`, `ssh://git@example.org/remote.git`,
    `file:///srv/remote.git`;
  - scp-like, `[user@]host:path`, where `host`, `path` and any `user` are
    non-empty, `user` and `host` hold no `/`, `@` or `:`, and the value
    doesn't start with a scheme and `://`: `git@example.org:remote.git`.
- A bare word or a local path (`a`, `owner/repo`, `../repo`) is not a `url`
  ([`INVALID_VALUE`](#5-the-astrayaml-file)): an analysis in the declaring
  analysis's repository is declared by `path`, and another repository on this
  machine by an explicit `file://` URL.
- `commit` is a full commit id
  ([`INVALID_COMMIT`](#17-analyses-from-another-commit-or-repository)): a
  branch moves, a tag can be moved or name another commit in a fork or a
  mirror, and a shortened id can become ambiguous as a repository grows.
- With a `path` and a `commit`, the declared analysis is the analysis at that
  path at the commit. The repository that holds the declaring `astra.yaml`
  has that commit
  ([`COMMIT_NOT_FOUND`](#17-analyses-from-another-commit-or-repository) for
  a file not read from a remote). It is read from the local repository or,
  when the declaring analysis is itself read from a remote, from that remote,
  and each submodule it reaches through a gitlink as
  [Annex B](#b-paths-and-git) says.
- So the folder a declaration with a `commit` names is read at that commit,
  and the folder a `url` names is the top level of its repository. That
  folder holds an `astra.yaml` file
  ([`MISSING_DECLARED_ANALYSIS`](#15-declared-analyses)).

#### Identity

An analysis's **identity** is its folder at a commit, or its folder in the
working tree. Two declarations name the same analysis when their folders are
the same path, read at the same commit or both in the working tree.

- A declaration's folder is, with a `url`, the top level of that repository
  and, with a `path`, the `path` joined to the folder of the declaring
  `astra.yaml` and tidied as text ([Annex B](#b-paths-and-git)).
- It is read at the declaration's `commit` or, without one, as the declaring
  analysis is read. The root, and every analysis reached from it by `path`
  alone, is read in the working tree.
- At a commit, a path that crosses a gitlink is read in the submodule's
  repository at the commit the gitlink pins ([Annex B](#b-paths-and-git)).
  So a path to the top of a submodule, read at a commit, names the same
  analysis as a `url` declaration of the submodule's repository at the commit
  the gitlink pins. A checked-out submodule read in the working tree is an
  analysis of the working tree, since it may differ from the commit the
  gitlink pins.
- The folder is a path from the top of the repository it is read in or, read
  in the working tree, from the top of the root's working tree.
- A URL says only where to get the commit, so a fork or a mirror with the
  same commit gives the same analysis: an analysis from a commit is its
  folder at its commit, whatever URL it is got from.

*Another analysis*, everywhere in this specification, is one with a
different identity.

#### What is read, and validity

- Every rule of this specification applies to an analysis from a commit as
  it is, with its files read at its commit, each file as the blob git stores
  ([Annex B](#b-paths-and-git)).
- Its results are those that [belong to](#18-results-and-where-they-go) it
  or to an analysis reached from it through declarations, each read at the
  commit its analysis is read at ([§20](#20-checking-results)).
- The declared analysis, with everything it declares, is valid at its commit
  ([`DECLARED_ANALYSIS_INVALID`](#17-analyses-from-another-commit-or-repository)).

#### Getting a commit from a remote

A commit is got from a remote when it is:

- a declaration's `url` and `commit`;
- a `path` and `commit` declared in a file read from a remote;
- the commit a gitlink pins, where a path read at a commit crosses it
  ([Annex B](#b-paths-and-git)).

A file is read from a remote when the commit it is read at is got from one.
The remote is the `url`, the remote the file was read from, or the
submodule's URL ([Annex B](#b-paths-and-git)). A commit counts as got when it
can be fetched from that remote, was kept from an earlier fetch or, for a
gitlink's commit, is held by the submodule's checkout. A repository left
in `.git/modules` after `git submodule deinit` doesn't count.

#### Using one

Unless it is driven, none of the recipes of an analysis from a commit run
([`REBUILT_FROM_COMMIT`](#21-runners)), so the rules on the universe being
built ([§16](#16-driving-and-consuming)) let it give only:

- its outputs in its own universes, pinned, in a file with no entry with the
  pin's id or through an import;
- its outputs built once, such as `remote.output1`;
- its inputs.

Evidence cites its results in the same way. One with no decisions is driven
wherever the chain before its declaration is
([§16](#16-driving-and-consuming)). Driven or not, its results in its own
universes belong to it and are read through their records, and no recipe
runs in those universes, since every result there belongs to it
([`REBUILT_FROM_COMMIT`](#21-runners)). An address that doesn't exist in the
declared analysis is an error in the declaring one
([`UNRESOLVED_ADDRESS`](#6-names)).

When a recipe reads such a result, the runner gets its bytes from what the
declared commit holds at the result's
[default place](#18-results-and-where-they-go), or through something
there it recognises as standing in for them ([§7](#7-inputs)), and they are
checked against the record ([`STALE_INPUT`](#21-runners)). An input of the
declared analysis read by address is got from its `path` at the declared
commit, in the repository that holds the declared analysis
([Annex B](#b-paths-and-git)), or through what the runner recognises as
standing in for it ([§7](#7-inputs)).

An earlier commit's results are read the same way, through a pin or an
import. Where the declaration `previous` names the analysis's own folder at
a commit, its universes often have the ids of the analysis's own. If both
have a `u1`, `previous.output1#u1` names the analysis's own `u1`. Where
`previous` has decisions and no key of the analysis's universes goes through
it, the analysis doesn't build `previous` in its `u1`: a
[planned result](#18-results-and-where-they-go)'s output that reads
`output1`, built per universe, through this pin breaks
[`UNDRIVEN_DECLARATION`](#16-driving-and-consuming) and
[`NOT_BUILT_IN_UNIVERSE`](#16-driving-and-consuming). With this import,
`previous.output1#previous_u1` reads `output1` in `u1`, through its record
at that commit, and no recipe runs. The commit is one that holds the
records, later than the one they name ([§20](#20-checking-results)):

<!-- fragment: Analysis -->
```yaml
analyses:
  previous:
    path: .
    commit: <commit>
universes:
  previous_u1:                 # previous's own u1, imported
    analysis: previous
    universe: u1
```

#### Driving one

A driver's universes can drive an analysis from a commit, as any declared
analysis. Its recipes then run on exactly its files at the declared commit
([`NOT_AT_COMMIT`](#21-runners)). Its outputs built once aren't built: like
the rest of its results, they are read through their records at the
declared commit ([`REBUILT_FROM_COMMIT`](#21-runners)). Only what the
driver's universes build is built. It belongs to the driver, and its records
name the driver's commit, where the declaration says which commit the driven
analysis is from and, for a remote, where to get it.

#### The rules

| Code | Layer | Level | Rule |
|---|---|---|---|
| `INVALID_DECLARATION_SOURCE` | schema | MUST | A declaration has exactly one of `path` and `url` |
| `URL_WITHOUT_COMMIT` | schema | MUST | A declaration with a `url` has a `commit` |
| `INVALID_COMMIT` | schema | MUST | Every `commit` is a full commit id: 40 or 64 lowercase hexadecimal digits |
| `COMMIT_NOT_FOUND` | validator | MUST | A declaration with a `path` and a `commit`, in a file not read from a remote, names a commit of the [repository that holds](#glossary) the declaring `astra.yaml` |
| `DECLARED_ANALYSIS_INVALID` | validator | MUST | An analysis from a commit, with everything it declares, is valid at that commit |

Recommendation: a published analysis SHOULD declare only remotes its readers
can fetch.

### 18. Results and where they go

A **result** is what a recipe made for one output in one universe, or once
for an output built once
([§13](#13-pins-and-outputs-built-per-universe-or-once)). It is one file,
which the recipe writes at `{output}` ([§11](#11-recipes)). An artefact of
many files is written as an archive, or as several outputs.

The root's **planned** results are:

- the result of each output of the root built once, and, in each of the
  root's universes, the result of every output of the root active there;
- every result a planned result reads through its output's `inputs`,
  through any declaration, pinned or not;
- every result the root's evidence cites
  ([§14](#14-insights-and-evidence)).

An output plans no result in a universe where it is inactive
([§9](#9-conditions)). An output of a declared analysis that no planned
result reads and no evidence of the root cites isn't planned, and building
the root doesn't build it.

#### Whose a result is, and its name

A result **belongs** to the analysis whose universe it was built in or, for
an output built once, to the analysis whose output it is:

- What a driven analysis builds in its driver's universes belongs to the
  driver.
- A result built in a universe that a pin names belongs to that universe's
  analysis, whichever file the pin is in and whether it names the universe
  through an import or not ([§16](#16-driving-and-consuming)). It is placed
  in that analysis's folder, under the universe's own id.

A result's **name** is its output's id after the ids of the driven
declarations from the analysis it belongs to. The root's universes drive
`subanalysis`, so the result of `subanalysis`'s `output1` in `u1` is the
root's, named `subanalysis.output1`.

- An undriven declaration never adds a name. Where `subanalysis` declares
  `parent: {path: ..}`, that declaration isn't driven in the root's
  universes, and adds no name there.
- No declaration that leads back to an analysis already on the chain from
  the driver is driven ([§16](#16-driving-and-consuming)). So the result of
  an output of the analysis it belongs to is named by the output's id alone,
  as the result of an output built once always is.
- A sub-analysis's declaration of its parent doesn't lead back where the
  sub-analysis is the driver. The parent's `output1`, built in
  `subanalysis`'s universe `v1` through a driven `parent: {path: ..}`, is
  named `parent.output1` in `subanalysis`'s records. It is named so also
  where the parent's own file imports `v1` as `subanalysis_v1` and reads
  `output1#subanalysis_v1`.

A result reached through two chains of driven declarations has a name for
each. Where the root declares `inner` and `stage`, and `stage` declares the
same folder as `inner`, a result of `inner` reached through `inner` and
through `stage.inner`, when keys go through both, is made once. It is placed
and recorded under each name, though a planned result should have one
([`RESULT_IN_TWO_PLACES`](#16-driving-and-consuming)).

A result's **address** is a name followed, for a result built in a universe,
by `#` and the universe's own id, never an import's:
`subanalysis.output1#u1`. Each address is the `address` of the record at its
place ([§19](#19-records)).

#### Where records and bytes go

A result's **place**, for one of its addresses, is where its record, and its
bytes at their **default place**, go in the folder of the analysis it belongs
to:

| | Built in the universe `{universe}` | Built once |
|---|---|---|
| Its record | `.astra/records/{universe}/{name}.json` | `.astra/records/{name}.json` |
| Its bytes, at their default place | `results/{universe}/{name}.{format}` | `results/{name}.{format}` |

Once built, the root's folder in the worked example
([§2](#2-a-worked-example)) holds:

```text
.astra/records/
  output2.json
  u1/output1.json
  u1/stage.output3.json
  u2/output1.json
  u2/stage.output3.json
results/
  output2.csv
  u1/output1.json
  u1/stage.output3.csv
  u2/output1.json
  u2/stage.output3.csv
```

- Both are worked out from an address of the result, so a result with two
  names has two of each.
- A record is the record only of the result its `address` names, under that
  name ([`MISSING_RECORD`](#20-checking-results),
  [`MISPLACED_RECORD`](#20-checking-results)).
- The runner writes the bytes to their default places
  ([`UNRECORDED_RESULT`](#21-runners)), and tells the recipe where to write
  through `{output}`. So a driven analysis's recipes write what they build in
  the driver's universes into the driver's results.
- A record at a commit can be read whether or not the commit holds the
  bytes.
- The bytes should be at their default place
  ([`ABSENT_RESULT`](#20-checking-results)), except for a result of an
  analysis from a commit that no planned result reads
  ([§20](#20-checking-results)). Where a runner keeps them
  elsewhere, with a stand-in for them there ([§7](#7-inputs)), they are
  `absent`, which is no error.

Ids hold no `.`, but a format can (`tar.gz`). So two default places
`{name}.{format}` in one folder are the same only when one name is a proper
dotted prefix of the other: an output `subanalysis` in the format
`output1.json`, and the result `subanalysis.output1` in the format `json`,
say. That needs an output and a declaration that share an id in some
analysis on the longer name's chain of declarations. Every analysis of the
stack keeps [`CLASHING_RESULT_NAME`](#15-declared-analyses), so no two
results of one analysis share a default place.

### 19. Records

A record is the provenance of one result: what the result is, and the run of
the recipe that made it. The runner that made the result writes it as JSON
at each of the result's places ([§18](#18-results-and-where-they-go)). The
record of `output1` in `u1`, in the worked example
([§2](#2-a-worked-example)):

```json
{
  "spec_version": "0.1.0",
  "address": "output1#u1",
  "content_hash": "sha256:<hash of output1 in u1>",
  "size": <size of output1 in u1>,
  "generated_by": {
    "commit": "<commit>",
    "inputs": [
      {
        "entry": "input1",
        "content_hash": "sha256:<hash of input1>",
        "size": <size of input1>
      },
      {
        "entry": "stage.output3",
        "content_hash": "sha256:<hash of stage.output3 in u1>",
        "size": <size of stage.output3 in u1>
      },
      {
        "entry": "upstream.output4",
        "content_hash": "sha256:<hash of upstream.output4>",
        "size": <size of upstream.output4>
      }
    ],
    "environment": {"iri": "urn:example:environment1"},
    "runner": {"id": "example-runner", "version": "1.2.0"}
  }
}
```

A record, a [ProvenanceRecord](elements/ProvenanceRecord.md), gives its
`spec_version` ([§5](#5-the-astrayaml-file)), the result's `address`, the
`content_hash` and `size` (in bytes) of the result's bytes, and the run of
the recipe that made it, `generated_by`, a
[Generation](elements/Generation.md). Its `address` is the result's address
as the analysis the result belongs to addresses it
([§18](#18-results-and-where-they-go)). The run gives:

- `commit`: the full id of the git commit the recipe ran from. It is a commit
  of the repository the record is committed in: for a result that belongs to
  an analysis in a submodule, the submodule's own commit, and for what a
  driver's universes build, the driver's commit
  ([§16](#16-driving-and-consuming)). It pins every file of the code and
  every `astra.yaml` in that repository: an analysis in a submodule of it
  through the commit the submodule is pinned at, and an analysis from a
  commit through its declaration's `commit`.
- `inputs`: what the recipe read, as one
  [RecordedInput](elements/RecordedInput.md) for each entry the output lists
  in the `astra.yaml` files at the record's `commit`, and no other item
  ([`MISSING_RECORD_INPUTS`](#20-checking-results)).
  - Each item is matched by its `entry`, which is an entry of
    `Output.inputs` exactly as written.
  - Each gives the `content_hash` and `size` of what the recipe read through
    the entry: another output's result, or the file an input names.
  - The order of the items carries no meaning.
  - A later change to the list makes the result `stale`
    ([`STALE_RESULT`](#20-checking-results)), not `missing`.
- `environment`: an [Environment](elements/Environment.md), whose `iri` is
  an IRI of the form [Annex C](#c-grammars-and-patterns) gives
  ([`INVALID_VALUE`](#5-the-astrayaml-file)). The IRI names exactly the
  environment the recipe ran in, enough for its runner, at the version the
  record gives, to recreate it ([`UNRECREATABLE_ENVIRONMENT`](#21-runners)).
  It can be a `urn:` IRI, say, or one in a scheme of the runner's own.
- `runner`: a [Runner](elements/Runner.md), the runner's `id` and its
  `version`.
- `started` and `finished`: when the recipe started and finished, each a
  [`timestamp`](elements/Timestamp.md) ([Annex C](#c-grammars-and-patterns)).

Every field of a record is required
([`MISSING_FIELD`](#5-the-astrayaml-file)) but three: `started` and
`finished`, which are optional, and `inputs`, which the schema leaves
optional and [`MISSING_RECORD_INPUTS`](#20-checking-results) holds to the
entries the output lists. So a record of an output that lists no inputs can
leave `inputs` out.

Every hash names its algorithm: `sha256:`, then the SHA-256 digest
([`INVALID_VALUE`](#5-the-astrayaml-file)).

A record holds only what its commit can't give: the output's declaration,
the options its decisions select and its format are in the `astra.yaml`
files at that commit.

A record holds only the fields its `spec_version` defines, and is read by
its minor version's record schema ([§5](#5-the-astrayaml-file)). A checker
reading a record of a greater minor version than its own validates it
against the open variant of its own record schema
([Annex D](#d-the-schema-files-and-rulesjson)), which ignores the fields it
doesn't know ([`INVALID_RECORD`](#20-checking-results)). Read as RDF
([Annex D](#d-the-schema-files-and-rulesjson)), a record is W3C PROV-O.

Two records of one result with the same commit, inputs and environment, made
on two machines say, show whether the result reproduces: it does when their
`content_hash` is the same.

A record names the commit its recipe ran from, so it is committed in a later
commit. Records and results are no input and no part of a declaration, so
committing them doesn't by itself make a result stale.

Recommendation: branches that hold records SHOULD be merged, not squashed or
rebased.

### 20. Checking results

A checker gives every planned result two statuses
([§18](#18-results-and-where-they-go)): one for its record, `unchanged`,
`stale` or `missing`, and one for its bytes, `present` or `absent`.

| Status | Means |
|---|---|
| `unchanged` | The result has a valid record where its address says, and [`STALE_RESULT`](#20-checking-results) holds |
| `stale` | The result has a valid record where its address says, and [`STALE_RESULT`](#20-checking-results) doesn't hold |
| `missing` | The result has no valid record where its address says: [`MISSING_RECORD`](#20-checking-results), [`INVALID_RECORD`](#20-checking-results), [`MISPLACED_RECORD`](#20-checking-results) or [`MISSING_RECORD_INPUTS`](#20-checking-results) doesn't hold |
| `present` | The bytes at the result's default place hash to its valid record's `content_hash` and have its `size` |
| `absent` | Anything else is at the default place, nothing, a stand-in or other bytes included |

- A result with two names gets its statuses at each place.
- A checker reads records only through planned results.

#### When a result is unchanged

A record says what its result was made from at the commit it names. Later,
in the working tree or at a later commit, a result is **unchanged** if, since
that commit, nothing has changed in ([`STALE_RESULT`](#20-checking-results)):

- its output's declaration: its recipe's command, its inputs and their order
  (`{inputs}` passes them in that order), its decisions, in any order (each
  reaches the recipe by name), and its format;
- the options its decisions select: a result is stale in its universe if any
  of its decisions selects a different option there than at the commit its
  record names;
- the content of its inputs, never what stands in for it;
- the results it reads, compared through their records: a result made from a
  stale or `missing` one is stale, and once that one is rebuilt, it is
  unchanged again only if the rebuilt one's `content_hash` is the one its own
  record noted for it.

Otherwise it is **stale**. Nothing else counts:

- Editing a finding, a description or another output leaves a result
  unchanged, unless the edit changes something listed above (an
  `astra.yaml` named as an input, or an output whose results it reads, say).
- The code, through the commit, and the environment are recorded but not
  compared: a change to either shows only when the recipe is run again and
  makes other bytes.

A result with a valid record where its address says is stale, not `missing`,
when what [`STALE_RESULT`](#20-checking-results) compares can't be read: its
record's commit can't be read (it was squashed or rebased away, or wasn't
got with the declared commit), its output doesn't exist at that commit, or
an input's content sits behind a stand-in that gives no hash. Nothing shows
it unchanged.

An unchanged result suggests, but doesn't guarantee, that the recipe would
make it again. In the worked example ([§2](#2-a-worked-example)):

| Edit | Effect |
|---|---|
| `u1` selects another option for `decision1` | `output1` in `u1` is stale, and so is `output2`, which reads it |
| `insight1`'s claim is reworded | Every result stays unchanged |
| The script that `output1`'s recipe runs is edited | Every result stays unchanged; once `output1` in `u1` is made again with other bytes, `output2` is stale until it is rebuilt |

#### Evidence

Evidence citing a result gets the status of that result's record
([`STALE_EVIDENCE`](#20-checking-results)): the record at the place of the
result's name along the `artifact`'s declarations, from the analysis the
result belongs to. So evidence citing `stage.inner.output1#u1` reads the
record of `stage.inner.output1`, not of `inner.output1`
([§18](#18-results-and-where-they-go)). Where those declarations give none
of the result's names, as for `subanalysis`'s evidence citing its own
`output1` pinned to an import of its parent's universe, the evidence gets
the worst status of the records at the result's names.

- An `artifact` that is pinned, or that names an output built once, names
  exactly one result.
- An `artifact` that names an output built per universe without a pin cites
  that output's results in each of the root's universes where it is active
  and its analysis is built.

The evidence gets the worst of their record statuses: `missing`, then
`stale`. If there are none, it is `missing`. A check covers the evidence of
the analysis it is run on. Of each analysis that analysis declares, directly
or through others, it covers only the items of evidence that cite a result
the root plans.

#### Results of an analysis from a commit

A result of an analysis from a commit is read through its record at the
declared commit, in the analysis the result belongs to
([§18](#18-results-and-where-they-go)), in the repository that holds that
analysis at the commit it is read at ([Annex B](#b-paths-and-git)). If the
declared analysis itself declares an analysis from a commit, that analysis's
records are read in its own repository, at the commit named for it.

A result can be read only once its record is committed. So the declaration
names a commit that holds the records, `B`, later than the commit their
recipes ran from, `A`, which the records name. The result is unchanged if
nothing that [`STALE_RESULT`](#20-checking-results) compares changed between
`A` and `B`, and the results it was made from are unchanged too. Their
content hashes are taken from their records, without their bytes.

The results of an analysis from a commit that are read or cited get their
record status (`unchanged`, `stale`, `missing`) by the same rules. Only those
a recipe reads get a bytes status ([`ABSENT_RESULT`](#20-checking-results)),
from what git holds at the declared commit
([§17](#17-analyses-from-another-commit-or-repository)).

#### The rules

A checker reports [`INVALID_RECORD`](#20-checking-results) with each code a
record breaks as its reason: the parser's
([`INVALID_SYNTAX`](#5-the-astrayaml-file)), or the one `rules.json` gives the
schema error ([Annex D](#d-the-schema-files-and-rulesjson)).

| Code | Layer | Level | Rule | Status when broken |
|---|---|---|---|---|
| `MISSING_RECORD` | check | MUST | Every planned result has a record at `.astra/records/{universe}/{name}.json` (or `{name}.json` for an output built once), for each of its names, in the analysis it belongs to | `missing` |
| `INVALID_RECORD` | check | MUST | The record at each planned result's place breaks no parse rule, states a `spec_version` whose minor version has a record schema or is greater than the checker's, and breaks no schema rule against that minor version's record schema or, when that minor version is greater than the checker's, against the open variant of the checker's own record schema | `missing` |
| `MISPLACED_RECORD` | check | MUST | The record at each planned result's place has, as its `address`, the address that place is worked out from | `missing` |
| `MISSING_RECORD_INPUTS` | check | MUST | The record at each planned result's place has exactly one `inputs` item for each entry its output lists at the commit the record names, where that commit can be read and its output exists there, matched by `entry`, and no other item (their order carries no meaning) | `missing` |
| `STALE_RESULT` | check | MUST | Since the commit in a result's record, nothing has changed in its output's declaration (command, inputs and their order, decisions, format), the options its decisions select in its universe, the content of its inputs, never what stands in for it, or the results it reads | `stale` |
| `ABSENT_RESULT` | check | SHOULD | Every planned result's recorded bytes are at its default place, except a result of an analysis from a commit that no planned result reads | `absent` |
| `STALE_EVIDENCE` | check | MUST | Every evidence citing a result cites an unchanged one | the cited result's record status |

### 21. Runners

A runner runs recipes, and writes each result's bytes and its record
([`UNRECORDED_RESULT`](#21-runners), [§18](#18-results-and-where-they-go),
[§19](#19-records)). Letting someone see what an environment it recorded
holds, as PROV for example, is recommended (below).

- It runs only committed code. It runs each recipe in a checkout of a
  commit: the repository's own working tree, or one it makes for the run (a
  git worktree, say). It refuses to run while that checkout has changes
  other than the records and results of any run, each result's bytes the
  recorded ones ([`UNCOMMITTED_CHANGES`](#21-runners)). Changes outside that
  checkout don't stop it.
- It builds no result that belongs to an analysis from a commit, or to an
  analysis reached from it through declarations
  ([§17](#17-analyses-from-another-commit-or-repository),
  [`REBUILT_FROM_COMMIT`](#21-runners)). It builds no output that reads such
  a result while it is `missing` or `stale`, or its bytes can't be got or
  aren't the recorded ones ([`STALE_INPUT`](#21-runners)).
- A result it reads that [`STALE_INPUT`](#21-runners) doesn't cover may be
  stale or `missing`; what it builds from it is then stale too
  ([§20](#20-checking-results)).

[`UNDECLARED_READ`](#21-runners) binds the recipe ([§11](#11-recipes)), and
breaking it leaves the analysis valid.

A checker sees much of a breach afterwards: a result with no record is
`missing`, and bytes that aren't the recorded ones are `absent`
([§20](#20-checking-results)).

| Code | Layer | Level | Rule |
|---|---|---|---|
| `UNRECORDED_RESULT` | runner | MUST | A runner writes a record for every result it makes, at the place of each of its names in the analysis the result belongs to, and writes the bytes to their default places |
| `FALSE_RECORD` | runner | MUST | Every field of a record a runner writes is true of the run it records: the commit the recipe ran from, the hash and size of what it read and of what it made, the environment it ran in, the runner and its version, and the times |
| `UNRECREATABLE_ENVIRONMENT` | runner | MUST | A runner records each recipe's environment as an IRI, of the form [Annex C](#c-grammars-and-patterns) gives, that it can recreate at its version |
| `UNCOMMITTED_CHANGES` | runner | MUST | A runner runs each recipe in a checkout of a commit whose only changes (what git reports in it, untracked files and submodules included, ignored files not) are the records and results of any run, each result's bytes the recorded ones |
| `WRONG_WORKING_DIRECTORY` | runner | MUST | A runner runs each recipe in the folder of the recipe's own analysis, in the checkout it runs in, even when another analysis drives it |
| `NOT_AT_COMMIT` | runner | MUST | A runner drives an analysis from a commit on exactly its files at that commit |
| `REBUILT_FROM_COMMIT` | runner | MUST | A runner builds no result that belongs to an analysis from a commit, or to an analysis reached from it through declarations, and reads each of those results through its record at the commit that analysis is read at |
| `STALE_INPUT` | runner | MUST | A runner builds no output that reads a result belonging to an analysis from a commit, or to an analysis reached from it through declarations, while that result is `missing` or `stale`, or its bytes can't be got or aren't the recorded ones |
| `UNDECLARED_READ` | runner | SHOULD | A recipe reads the files inputs name, and other outputs' results, only through its output's inputs |

Recommendation: a runner SHOULD let someone see what an environment it
recorded holds.

Permission: a runner MAY enforce [`UNDECLARED_READ`](#21-runners); one that
does fails the recipe.

## Glossary

Each term links to the sections that define it or give its detail.

- **active** ([§9](#9-conditions))
- **address** ([§6](#6-names), [§18](#18-results-and-where-they-go))
- **analysis** ([§1](#1-what-astra-is), [§5](#5-the-astrayaml-file))
- **analysis from a commit** ([§17](#17-analyses-from-another-commit-or-repository))
- **analysis stack**, or **stack** ([§1](#1-what-astra-is),
  [§15](#15-declared-analyses))
- **another analysis** ([§1](#1-what-astra-is),
  [§17](#17-analyses-from-another-commit-or-repository))
- **belongs to** ([§18](#18-results-and-where-they-go))
- **built per universe, built once** ([§13](#13-pins-and-outputs-built-per-universe-or-once))
- **chain of declarations** ([§15](#15-declared-analyses))
- **checker** ([§1](#1-what-astra-is), [§3](#3-conformance))
- **condition** ([§6](#6-names), [§9](#9-conditions))
- **constraint** ([§8](#8-decisions-and-options))
- **consuming** ([§16](#16-driving-and-consuming))
- **declaration** ([§1](#1-what-astra-is), [§15](#15-declared-analyses))
- **default place** ([§18](#18-results-and-where-they-go))
- **drive** ([§16](#16-driving-and-consuming))
- **driver, driven** ([§16](#16-driving-and-consuming))
- **effective selection** ([§12](#12-universes))
- **element** ([§6](#6-names))
- **excluded option** ([§8](#8-decisions-and-options))
- **flat key** ([§16](#16-driving-and-consuming))
- **id** ([§6](#6-names), [Annex C](#c-grammars-and-patterns))
- **identity** ([§1](#1-what-astra-is),
  [§17](#17-analyses-from-another-commit-or-repository))
- **import** ([§12](#12-universes), [§16](#16-driving-and-consuming))
- **imported universe** ([§16](#16-driving-and-consuming))
- **insight** ([§1](#1-what-astra-is), [§14](#14-insights-and-evidence))
- **leads back** ([§15](#15-declared-analyses))
- **lies inside** ([Annex B](#b-paths-and-git)): of a path and a folder, both
  tidied: the folder's segments begin the path's, and the path has more.
- **minor version** ([§5](#5-the-astrayaml-file))
- **name of a result** ([§18](#18-results-and-where-they-go))
- **on the chain** ([§15](#15-declared-analyses))
- **option reference** ([§6](#6-names))
- **pin** ([§13](#13-pins-and-outputs-built-per-universe-or-once),
  [§16](#16-driving-and-consuming))
- **place** ([§18](#18-results-and-where-they-go))
- **placeholder** ([§11](#11-recipes))
- **planned result** ([§18](#18-results-and-where-they-go))
- **record** ([§1](#1-what-astra-is), [§19](#19-records))
- **record schema, open variant** ([§5](#5-the-astrayaml-file),
  [Annex D](#d-the-schema-files-and-rulesjson))
- **reference** ([§6](#6-names))
- **repository that holds a file** ([Annex B](#b-paths-and-git)): the innermost
  git repository the file is in: for a file in a submodule, the submodule's
  own.
- **result** ([§1](#1-what-astra-is), [§18](#18-results-and-where-they-go))
- **root** ([§1](#1-what-astra-is), [§15](#15-declared-analyses))
- **runner** ([§1](#1-what-astra-is), [§3](#3-conformance), [§21](#21-runners))
- **spelling** ([§15](#15-declared-analyses))
- **stand-in** ([§7](#7-inputs), [Annex B](#b-paths-and-git)): something kept in
  a file's place, such as a large-file tool's pointer, that is recognised as
  standing in for the file.
- **status** ([§20](#20-checking-results))
- **tracked** ([Annex B](#b-paths-and-git)): of a file in a repository: read in
  the working tree, in the repository's index; read at a commit, in that
  commit's tree; either way reached through no gitlink.
- **unchanged, stale** ([§1](#1-what-astra-is), [§20](#20-checking-results))
- **universe** ([§1](#1-what-astra-is), [§12](#12-universes))
- **universe being built** ([§16](#16-driving-and-consuming))
- **universes built** ([§16](#16-driving-and-consuming))
- **valid** ([§3](#3-conformance))
- **validator** ([§3](#3-conformance))

## Part III: For tool builders

Part III is normative.

### A. Reading files

**`astra.yaml`** is a YAML 1.2 document
([YAML 1.2.2](https://yaml.org/spec/1.2.2/)), read under its core schema,
whose content is a map ([`INVALID_SYNTAX`](#5-the-astrayaml-file)). The
schema checks that content.

- Plain scalars are typed by the core schema
  ([YAML 1.2.2 §10.3.2](https://yaml.org/spec/1.2.2/#1032-tag-resolution)),
  so `spec_version: 0.1` is a number ([`WRONG_TYPE`](#5-the-astrayaml-file))
  and `spec_version: "0.1.0"` a string.
- A number is checked as JSON Schema checks it, so `2.0` is an integer.

**Records** are JSON text ([RFC 8259](https://www.rfc-editor.org/rfc/rfc8259))
in UTF-8, in which no object has two equal names
([`INVALID_SYNTAX`](#5-the-astrayaml-file)).

### B. Paths and git

**Paths.** The path of an input or a declaration ([§7](#7-inputs),
[§15](#15-declared-analyses)) names the entry at exactly that path: on disk in
the working tree, or in the commit's tree at a commit
([`MISSING_INPUT_FILE`](#7-inputs),
[`MISSING_DECLARED_ANALYSIS`](#15-declared-analyses)). So `data/A.csv` and
`data/a.csv` are two paths, which name two files or folders, and `Subanalysis`
and `subanalysis` declare two analyses
([§17](#17-analyses-from-another-commit-or-repository)).

**Reading git.** An analysis is read in the working tree or at a commit
([§17](#17-analyses-from-another-commit-or-repository)), and validators and
checkers read git one way:

- **Tidying.** A path is joined to the folder of the `astra.yaml` that
  writes it and tidied as text, never through the file system: empty and `.`
  segments are dropped, each `..` removes the segment before it, and a `..`
  with no segment before it takes the path above the top. So
  `./data.csv` is `data.csv`, `subanalysis/` is `subanalysis`, and
  `subanalysis/../data` is `data`, whatever `subanalysis` is on disk.
- **The top.** A path is measured from the top of the root's working tree
  or, at a commit, from the top of the repository that holds it. A
  declaration's path that goes above that top breaks
  [`DECLARATION_OUTSIDE_REPOSITORY`](#15-declared-analyses). The root's
  working tree is that of the repository that holds the root's `astra.yaml`,
  and the repository that holds an analysis is the one that holds its
  `astra.yaml`.
- **Lies inside.** A path lies inside a folder, or is inside it, when, both
  tidied, the folder's segments begin the path's, and the path has more. So
  `results/u1/output1.csv` lies inside `results`, and `results2/x.csv`
  doesn't.
- **Entries.** In the working tree, a path names an entry on disk below the
  top of the root's working tree, tracked, untracked or ignored. At a commit,
  a path names an entry of that commit's tree.
- **Symlinks.** A symlink is an entry, and is never followed: at a path, it is
  neither a file nor a folder, and a path through a symlinked folder names
  nothing. So a declaration finds no analysis where its path, or its
  `astra.yaml`, is a symlink or goes through one
  ([`MISSING_DECLARED_ANALYSIS`](#15-declared-analyses)). An input's path that
  is a symlink names a file only where the validator recognises the symlink as
  standing in for one ([§7](#7-inputs)), and otherwise names none
  ([`MISSING_INPUT_FILE`](#7-inputs)).
- **Stand-ins.** A stand-in is something kept in a file's place, such as a
  large-file tool's pointer, that is recognised as standing in for the file.
  An input's file, or its stand-in, is what is tracked
  ([`INPUT_NOT_TRACKED`](#7-inputs)).
- **Submodules.** A submodule that is checked out is in the working tree, and
  its entries are read in its own repository. At a commit, a path that looks
  for a file or an analysis goes on through a gitlink into the submodule, at
  the commit the gitlink pins. Whether an input is tracked never crosses a
  gitlink.
- **The repository that holds a file.** It is the innermost one: for a file
  in a submodule, the submodule's own.
  [`COMMIT_NOT_FOUND`](#17-analyses-from-another-commit-or-repository) reads
  the repository that holds the declaring `astra.yaml`
  ([§17](#17-analyses-from-another-commit-or-repository)).
- **Tracked.** [`INPUT_NOT_TRACKED`](#7-inputs) reads the repository that
  holds the input's analysis, where a file is tracked when, in the working
  tree, it is in the index or, at a commit, in that commit's tree, reached
  through no gitlink. So a staged input is tracked, and an untracked or
  ignored one isn't, nor is one in a plain data submodule.
- **A gitlink's commit.** It is got from the submodule's checkout when that
  holds it, or from the URL that the `.gitmodules` of the commit holding the
  gitlink gives for that submodule, a relative one (`../other.git`) resolved
  as git resolves it ([§17](#17-analyses-from-another-commit-or-repository)).
- **Bytes.** At a commit, a file is the blob git stores. In the working tree,
  an `astra.yaml` is read from the file on disk.

### C. Grammars and patterns

**Grammar.** The five forms of a name ([§6](#6-names)) are written in ABNF:

```abnf
id               = lower *( lower / DIGIT / "_" )
lower            = %x61-7A                      ; a-z
address          = id *( "." id )               ; [declaration "."]... element
reference        = address [ "#" id ]           ; "#" pins a universe
option-reference = address "." id              ; a decision's address, then an option id
condition        = [ "~" ] option-reference     ; "~": the option is not selected
```

**Named types.** The other named types' values take these forms:

| Type | Form |
|---|---|
| [`commit_id`](elements/CommitId.md) | a full git commit id: 40 lowercase hexadecimal digits (SHA-1) or 64 (SHA-256) |
| [`content_hash`](elements/ContentHash.md) | `sha256:`, then 64 lowercase hexadecimal digits |
| [`spec_version`](elements/SpecVersion.md) | `MAJOR.MINOR.PATCH`, without leading zeros |
| [`timestamp`](elements/Timestamp.md) | a UTC time to the millisecond, `YYYY-MM-DDThh:mm:ss.sssZ`, with month 01–12, day 01–31, hour 00–23, and minute and second 00–59 |
| [`iri`](elements/Iri.md) | an IRI, never a CURIE: a scheme (an ASCII letter, then any ASCII letters, digits, `+`, `.` and `-`), `:`, at least one character other than `#`, then optionally `#` and any characters other than `#`; none of these characters is an ASCII space or control, a C1 control, `<`, `>`, `"`, `{`, `}`, the vertical bar, `\`, `^`, the backtick or a bidi formatting character U+200E, U+200F or U+202A–U+202E, and `%` comes only before two hex digits |

**Other patterns.** The other fields with a pattern state it in their sections:
`Output.format` ([§10](#10-outputs)), an input's and a declaration's `path`
([§7](#7-inputs), [§15](#15-declared-analyses)), `AnalysisDeclaration.url`
([§17](#17-analyses-from-another-commit-or-repository)) and `Evidence.doi`
([§14](#14-insights-and-evidence)). `FragmentSelector.value`'s is below.

**Fragment identifiers.** A location's `value` is read by the syntax its
`conforms_to` names ([§14](#14-insights-and-evidence)). It is non-empty, holds
no ASCII space or control character and none of `"`, `#`, `<`, `>`, `[`, `\`,
`]`, `^`, the backtick, `{`, `|` and `}`, and has `%` only before two hex digits
([`INVALID_VALUE`](#5-the-astrayaml-file)). `conforms_to` is an
[`iri`](elements/Iri.md) (above, [`INVALID_VALUE`](#5-the-astrayaml-file)).

### D. The schema files and rules.json

The schema is written in [LinkML](https://linkml.io/), in four modules:
`types` (the named types of Annex C), `analysis` (`astra.yaml`), `insight`
(insights and evidence) and `provenance` (the record). Their descriptions are
the normative definitions of the fields, published as the
[field reference](elements/index.md). These files are generated from them,
and `rules.json` also from the codes tables of Part II. Each is published at
`https://w3id.org/astra/`, its minor version (`0.1` for every 0.1.x) and `/`,
followed by its file name:

| File | URI | What it is |
|---|---|---|
| `analysis.schema.json` | `https://w3id.org/astra/0.1/analysis.schema.json` | the JSON Schema of `astra.yaml`, rooted at `Analysis` |
| `provenance.schema.json` | `https://w3id.org/astra/0.1/provenance.schema.json` | the JSON Schema of a record, rooted at `ProvenanceRecord` |
| `provenance.open.schema.json` | `https://w3id.org/astra/0.1/provenance.open.schema.json` | the same schema, open: it allows fields it doesn't define |
| `provenance.context.jsonld` | `https://w3id.org/astra/0.1/provenance.context.jsonld` | the JSON-LD context of a record |
| `rules.json` | `https://w3id.org/astra/0.1/rules.json` | the rule catalogue: every rule of the codes tables, with the code of each JSON Schema error that makes an instance fail |

**URIs.** Each JSON Schema's `$id` is its URI. So the closed and open record
schemas are distinct resources, and so are the schemas of two minor versions.
The patches of one minor version share each URI: a patch release never changes
what is valid ([§5](#5-the-astrayaml-file)), so the URI names one schema
whichever patch's file a tool holds. Each JSON Schema uses only JSON Schema
2019-09 keywords, and the version of the release it was generated from is in
its `$comment`.

**The contract.** `analysis.schema.json` is the contract for `astra.yaml`: a
document breaks no schema rule exactly when a JSON Schema draft 2019-09
validator reports no error for it against this file.
`provenance.schema.json` is the contract for records in the same way.

**The open variant.** `provenance.open.schema.json` differs from
`provenance.schema.json` only in allowing fields it doesn't define.

**The rule catalogue.** `rules.json` is made from this specification and the
schema, so that every tool reports the same code for the same error and words
each rule the same way. It holds:

- `rules`: one entry per row of the codes tables, in document order. Each has
  its `code`; its `layer` (`parse`, `schema`, `validator`, `check` or
  `runner`); its `level` (`MUST` or `SHOULD`); its `statement`, the Rule
  cell; its `source`, the section whose table lists it, as in `§7 Inputs`;
  and, for a rule of the check layer, its `status`, the Status when broken
  cell. The cells are given as inline CommonMark, with each link reduced to
  its text. A `status` is display text naming the status a result, or
  evidence citing it, gets when the rule is broken, not a status token.
- `errors`: the code of every keyword of the three JSON Schemas whose error
  can make an instance fail (*From an error to its code*, below), keyed by
  the keyword's absolute keyword location, as JSON Schema 2019-09 defines it:
  the schema's `$id`, `#`, and the JSON Pointer to the keyword once every
  `$ref` is resolved. So each key names its minor version, through `$id`.
  Each code is a schema-layer rule's.
- `$comment`: the version of the release it was made from.

An abridged `rules.json`:

<!-- excerpt: rules.json -->
```json
{
  "$comment": "ASTRA rule catalogue, schema version 0.1.0",
  "errors": {
    "https://w3id.org/astra/0.1/analysis.schema.json#/$defs/AnalysisDeclaration__identifier_optional/properties/commit/pattern": "INVALID_COMMIT",
    "https://w3id.org/astra/0.1/analysis.schema.json#/$defs/AnalysisDeclaration__identifier_optional/allOf/1/then/required": "URL_WITHOUT_COMMIT",
    "https://w3id.org/astra/0.1/analysis.schema.json#/properties/outputs/propertyNames/pattern": "INVALID_ID"
  },
  "rules": [
    {
      "code": "INVALID_COMMIT",
      "layer": "schema",
      "level": "MUST",
      "source": "§17 Analyses from another commit or repository",
      "statement": "Every `commit` is a full commit id: 40 or 64 lowercase hexadecimal digits"
    },
    {
      "code": "ABSENT_RESULT",
      "layer": "check",
      "level": "SHOULD",
      "source": "§20 Checking results",
      "statement": "Every planned result's recorded bytes are at its default place, except a result of an analysis from a commit that no planned result reads",
      "status": "`absent`"
    }
  ]
}
```

**From an error to its code.** A parse code is reported for the whole file.
A schema error is reported with the code that `errors` gives its keyword's
absolute keyword location, at the instance location where it fails; an error
on a key is reported at its map, naming the key, and an unknown field at its
object, naming the field. Only the failures that make the document fail are
reported, not those inside an `if` or a `not`, or inside a branch of a
combinator that doesn't fail. So any JSON Schema 2019-09 validator gives the
same set of pairs of an instance location and a code.

**RDF.** A record's RDF is what the
[JSON-LD 1.1](https://www.w3.org/TR/json-ld11-api/) toRdf algorithm gives for
it, with `provenance.context.jsonld` supplied as its context (a record carries
no `@context`), plus each node's class URI as its `rdf:type`: the root node
(the record's top-level object), each item of `inputs` and the `environment`
are `prov:Entity`, `generated_by` is a `prov:Activity`, and the `runner` a
`prov:SoftwareAgent`. The context maps a record's terms onto
[W3C PROV-O](https://www.w3.org/TR/prov-o/), with ASTRA's own, where PROV has
none, in the `https://w3id.org/astra/` namespace. The context is JSON-LD 1.1,
and an `iri` is its node's `@id` exactly as written, whatever its scheme
(`prov:env:1` too). Read this way, a record is PROV-O. The root node stands
for the result: a `prov:Entity` that `prov:wasGeneratedBy` its
`generated_by`, the run, which `prov:used` its inputs and its environment and
`prov:wasAssociatedWith` its runner. The root node's `address`,
`content_hash` and `size` describe the result, and its `spec_version` the
record. The run's `started` and `finished` are `prov:startedAtTime` and
`prov:endedAtTime`, typed `xsd:dateTime`, and the runner's `version` is
`schema:softwareVersion`.

### References

- **BCP 14**: [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119), Key words for
  use in RFCs to Indicate Requirement Levels, and
  [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174), Ambiguity of Uppercase
  vs Lowercase in RFC 2119 Key Words.
- **CommonMark**: the [CommonMark Spec](https://spec.commonmark.org/).
- **ECMA-262**: the [ECMAScript Language
  Specification](https://ecma-international.org/publications-and-standards/standards/ecma-262/),
  whose regular expressions are JSON Schema's patterns.
- **EPUB CFI**: [EPUB Canonical Fragment
  Identifiers](https://idpf.org/epub/linking/cfi/epub-cfi.html).
- **FIPS 180-4**: [Secure Hash
  Standard](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.180-4.pdf), which
  defines SHA-1 and SHA-256.
- **ISO 32000-2**: Document management — Portable document format — Part 2: PDF
  2.0.
- **JSON-LD 1.1**: [JSON-LD 1.1](https://www.w3.org/TR/json-ld11/) and [JSON-LD
  1.1 Processing Algorithms and API](https://www.w3.org/TR/json-ld11-api/).
- **JSON Schema 2019-09**: [JSON Schema: A Media Type for Describing JSON
  Documents](https://json-schema.org/draft/2019-09/json-schema-core.html) and
  [JSON Schema
  Validation](https://json-schema.org/draft/2019-09/json-schema-validation.html),
  draft 2019-09.
- **Media Fragments**: [Media Fragments URI
  1.0](https://www.w3.org/TR/media-frags/).
- **POSIX**: [IEEE Std
  1003.1](https://pubs.opengroup.org/onlinepubs/9799919799/), The Open Group
  Base Specifications, whose Shell Command Language a recipe's `command` is
  written in.
- **PROV-O**: [PROV-O: The PROV Ontology](https://www.w3.org/TR/prov-o/).
- **RFC 3236**: [The 'application/xhtml+xml' Media
  Type](https://www.rfc-editor.org/rfc/rfc3236).
- **RFC 3778**: [The application/pdf Media
  Type](https://www.rfc-editor.org/rfc/rfc3778), obsoleted by RFC 8118.
- **RFC 5147**: [URI Fragment Identifiers for the text/plain Media
  Type](https://www.rfc-editor.org/rfc/rfc5147).
- **RFC 5234**: [Augmented BNF for Syntax Specifications:
  ABNF](https://www.rfc-editor.org/rfc/rfc5234).
- **RFC 6901**: [JavaScript Object Notation (JSON)
  Pointer](https://www.rfc-editor.org/rfc/rfc6901).
- **RFC 7111**: [URI Fragment Identifiers for the text/csv Media
  Type](https://www.rfc-editor.org/rfc/rfc7111).
- **RFC 8118**: [The application/pdf Media
  Type](https://www.rfc-editor.org/rfc/rfc8118).
- **RFC 8259**: [The JavaScript Object Notation (JSON) Data Interchange
  Format](https://www.rfc-editor.org/rfc/rfc8259).
- **Web Annotation**: [Web Annotation Data
  Model](https://www.w3.org/TR/annotation-model/).
- **YAML 1.2.2**: [YAML Ain't Markup Language (YAML™) revision
  1.2.2](https://yaml.org/spec/1.2.2/).
