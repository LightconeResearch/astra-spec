# The ASTRA specification

ASTRA (Agentic Schema for Transparent Research Analysis) records a research
analysis: the files it reads, the artefacts it makes, the decisions it makes
along the way, the universes it makes them in, and the claims it rests on
them. This document specifies the format and what conforming tools do with
it.

## 1. Conventions

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

**Rules.** Section 9 states every rule that a tool checks or keeps, each
with a code, such as [`MISSING_DECISION`](#validator). The other sections
explain what the rules are about and link to their codes. The two
recommendations no tool can check are stated where they apply (§7, §8), and
the runner's recommendation and permission, which no tool can check either,
after the runner's rules (§9).

**Fields.** Every class of the format has a page in the
[schema reference](elements/index.md), generated from the schema, whose
descriptions define its fields. This specification links to those pages and
doesn't restate them.

**Terms.**

| Term | Meaning | Defined in |
|---|---|---|
| analysis | a directory with an `astra.yaml` | §3 |
| element | an input, output, decision, option, universe, import, declaration or insight of an analysis | §4 |
| address | the name of an element other than an option, through the declarations that lead to it; an option is named by an option reference (§4) | §4 |
| active | of a decision or an output, when every condition of its `when` holds | §5 |
| universe | a selection of one option for every active decision | §6 |
| effective selection | what a universe selects once `derived_from` is resolved | §6 |
| built per universe, built once | whether an output has one result in each universe where it is active, or one in all | §6 |
| pin | `#` and a universe id ending a reference, after its address, which reads an output in that universe; on an input it changes nothing; in an `astra.yaml`, the id is that of an entry of the file's `universes` or, where the file has no entry with that id, of a universe of the analysis whose element the reference names | §4, §7 |
| root | the analysis being validated or built | §7 |
| analysis stack | the root and every analysis it declares, directly or through others | §7 |
| driver, driven | the analysis whose universes drive, and an analysis reached through a declaration they drive; the analysis whose universe is being built is never driven in it | §7 |
| consuming | using another analysis's element by address | §7 |
| import | an entry of `universes` that names one of another analysis's universes, in which that analysis is the driver; it selects nothing and is not one of the importing analysis's universes | §6, §7 |
| analysis from a commit | a declared analysis as it was at a given commit | §7 |
| result | what a recipe made for one output in one universe, or once | §8 |
| planned result | a result a check of the root covers: every result of the root's active outputs, every result the root's evidence cites, and every result those read, transitively | §8 |
| record | the provenance record of one result | §8 |

**Versions.** Every analysis document and every record states, in
`spec_version`, the version of this specification it is written against, as
`MAJOR.MINOR.PATCH`: three non-negative integers without leading zeros, such
as `0.1.0` ([`INVALID_VALUE`](#parse-and-schema)). Versions are ordered by
MAJOR, then MINOR, then PATCH, each compared as an integer, so `0.10.0` comes
after `0.9.0`. A version's minor version is its MAJOR and MINOR: `0.1` for
`0.1.3`. A patch release never changes what is valid, nor the code a broken
rule is reported under: a document or a record is valid under `X.Y.Z`
exactly when it is valid under every other `X.Y` version. So each minor
version has one schema of `astra.yaml` and one of a record, and every
`0.1.x` document is read by 0.1's. A validator reads each `astra.yaml` by
the schema of the minor version it states, so a validator that reads one
patch of a minor version reads them all
([`UNSUPPORTED_SPEC_VERSION`](#validator)). A file whose `spec_version` is
missing or malformed is checked against the schema of the validator's own
minor version, and every schema error in it is reported.

## 2. Overview

ASTRA describes an analysis in two kinds of document:

- the **analysis document**, `astra.yaml`, which the analysis's authors
  write: what the analysis reads, makes and decides, the universes it makes
  its results in, the other analyses it uses, and its insights. Its root is
  [Analysis](elements/Analysis.md).
- the **provenance record**, a JSON file at each place of a result, written
  by the runner that made it: what the result is and the run that made it.
  Its root is [ProvenanceRecord](elements/ProvenanceRecord.md).

Rules are enforced in five layers, set apart by what each one sees:

| Layer | Enforced by | Sees |
|---|---|---|
| **parse** | a YAML 1.2 reader (`astra.yaml`) or a JSON reader (records), as §3 says | one file's bytes |
| **schema** | the generated JSON Schema | one file's data |
| **validator** | a semantic validator | every `astra.yaml` of the analysis stack, and git (§3); no results |
| **check** | a results checker | every `astra.yaml` of the analysis stack, now and at each record's commit, and git (§3); records and results |
| **runner** | whatever runs recipes | its own actions, the checkouts it runs recipes in, and what the recipes read |

Four roles conform to this specification:

- A **document**, an `astra.yaml` or a record, conforms when it breaks no
  parse or schema rule.
- A **validator** reads an analysis, every `astra.yaml` of its stack and git
  (§3), and reports every parse, schema and validator rule that the
  analysis, or any analysis of its stack, breaks, except where §9's *What is
  checked* leaves one unchecked. One broken inside an analysis from a commit
  is also reported as [`DECLARED_ANALYSIS_INVALID`](#validator) on its
  declaration (§7). An analysis is valid when its stack breaks none of their
  `MUST`s.
- A **checker** reads an analysis, every `astra.yaml` of its stack and git
  (§3), and its records and results, and gives each planned result its
  statuses by the check rules (§8). A record that breaks a parse or schema
  rule leaves its result `missing` ([`INVALID_RECORD`](#check)). A checker
  implements one version, its own. It has the record schema of every minor
  version from 0.1 up to its own (§10): records begin at 0.1.0, and no
  earlier version has a record schema.
- A **runner** runs recipes and writes each result's bytes and record. A
  record is its runner's testimony, and names it. A runner conforms when it
  keeps the runner `MUST`s, which keep its records true.

An analysis that reads a file, makes one artefact per universe and compares
two universes in a third:

```yaml
spec_version: "0.1.0"
label: Iris classification

inputs:
  iris:
    path: data/iris.csv

decisions:
  model:
    rationale: The classifier is the main lever on accuracy.
    options:
      random_forest: {}
      svm:
        requires: [scaling.standard]
  scaling:
    options:
      none: {}
      standard: {}

outputs:
  accuracy:
    type: metric
    format: json
    inputs: [iris]
    decisions: [model, scaling]
    recipe:
      command: >-
        python src/train.py --data {inputs.iris}
        --model {decisions.model} --scaling {decisions.scaling}
        --out {output}
  comparison:
    type: table
    format: csv
    inputs: [accuracy#forest, accuracy#svm]
    recipe:
      command: >-
        python src/compare.py --a {inputs.accuracy#forest}
        --b {inputs.accuracy#svm} --out {output}

universes:
  forest:
    decisions: {model: random_forest, scaling: none}
  svm:
    derived_from: forest
    decisions: {model: svm, scaling: standard}

findings:
  svm_scores_higher:
    claim: The SVM scores higher than the random forest.
    evidence:
      - artifact: comparison
```

`accuracy` is built in each universe and `comparison` once, from both. Built,
the analysis has three results, each with a record (§8).

## 3. Files

An **analysis** is a directory with an `astra.yaml` at its top, in a git
repository: in its working tree, or at one of its commits
([`NOT_IN_REPOSITORY`](#validator)). Its recipes run in that directory
([`WRONG_WORKING_DIRECTORY`](#runner)).

**Paths.** The path of an input or a declaration (§5, §7) is relative to the
folder of the `astra.yaml` that writes it, with `/` between folders, and is
tidied as text (**Reading git**, below). It names the entry at exactly that
path, on disk in the working tree or in the commit's tree at a commit
([`MISSING_INPUT_FILE`](#validator),
[`MISSING_DECLARED_ANALYSIS`](#validator)). So `data/A.csv` and `data/a.csv`
are two paths, which name two files or folders, and `Stage` and `stage`
declare two analyses (§7).

**Reading git.** An analysis is read in the working tree or at a commit
(§7), and validators and checkers read git one way:

- A path is joined to the folder of the `astra.yaml` that writes it and
  tidied as text, never through the file system: empty and `.` segments are
  dropped, and each `..` removes the segment before it. So `./data.csv` is
  `data.csv`, `subanalysis/` is `subanalysis`, and `stage/../data` is
  `data`, whatever `stage` is on disk. A path is measured from the top of
  the root's working tree or, at a commit, from the top of the repository
  that holds it, and a declaration's path that goes above that top breaks
  [`DECLARATION_OUTSIDE_REPOSITORY`](#validator).
- In the working tree, a path names an entry on disk below the top of the
  root's working tree, tracked, untracked or ignored. At a commit, a path
  names an entry of that commit's tree.
- A symlink is an entry, and is never followed: at a path, it is neither a
  file nor a directory, and a path through a symlinked folder names nothing.
  So a declaration finds no analysis where its path, or its `astra.yaml`, is
  a symlink or goes through one ([`MISSING_DECLARED_ANALYSIS`](#validator)).
  An input's path that is a symlink names a file only where the validator
  recognises the symlink as standing in for one (§5), and otherwise names
  none ([`MISSING_INPUT_FILE`](#validator)).
- A submodule that is checked out is in the working tree, and its entries
  are read in its own repository.
- At a commit, a path that looks for a file or an analysis goes on through a
  gitlink into the submodule, at the commit the gitlink pins. Whether an
  input is tracked never crosses a gitlink.
- The repository that holds a file is the innermost one: for a file in a
  submodule, the submodule's own. [`COMMIT_NOT_FOUND`](#validator) and
  [`COMMIT_NOT_ANCESTOR`](#validator) read the repository that holds the
  declaring `astra.yaml`, where, in the working tree, HEAD stands for the
  commit a declaration is in (§7).
  [`INPUT_NOT_TRACKED`](#validator) reads the repository that holds the
  input's analysis, where a file is tracked when, in the working tree, it is
  in the index or, at a commit, in that commit's tree, reached through no
  gitlink. So a staged input is tracked, and an untracked or ignored one
  isn't, nor is one in a plain data submodule.
- The commit a gitlink pins is got from the URL that the `.gitmodules` of the
  commit holding the gitlink gives for that submodule, a relative one
  (`../lib.git`) resolved as git resolves it
  ([`REMOTE_UNREACHABLE`](#validator), §7).
- At a commit, a file is the blob git stores; in the working tree, an
  `astra.yaml` is read from the file on disk.

**`astra.yaml`** is a YAML 1.2 stream
([YAML 1.2.2](https://yaml.org/spec/1.2.2/)) with at most one document, read
under its core schema, with no tag but the core schema's
([`INVALID_SYNTAX`](#parse-and-schema)). A file with no document is null
([`WRONG_TYPE`](#parse-and-schema)). Its content is a JSON value, which the
schema checks: every key is a string and every number is finite, not `.inf`
or `.nan` ([`INVALID_SYNTAX`](#parse-and-schema)), and no map has two equal
keys ([`DUPLICATE_KEY`](#parse-and-schema)), so `a`, `'a'` and `"a"` are one
key. Plain scalars are typed by the core schema
([YAML 1.2.2 §10.3.2](https://yaml.org/spec/1.2.2/#1032-tag-resolution)), so
`spec_version: 0.1` is a number ([`WRONG_TYPE`](#parse-and-schema)) and
`spec_version: "0.1.0"` a string. A number is checked as JSON Schema checks
it, so `2.0` is an integer.

**Records** are JSON text ([RFC 8259](https://www.rfc-editor.org/rfc/rfc8259))
in UTF-8 ([`INVALID_SYNTAX`](#parse-and-schema)). No object of a record has
two equal names ([`DUPLICATE_KEY`](#parse-and-schema)).

**Every document** holds only the fields its schema defines
([`UNKNOWN_FIELD`](#parse-and-schema)), each with the JSON type the field
takes ([`WRONG_TYPE`](#parse-and-schema)). An optional field without a value
is left out: no field takes `null`.

**Locations.** In an analysis's directory:

| Path | Holds |
|---|---|
| `astra.yaml` | the analysis document |
| `.astra/records/{universe}/{name}.json`, `.astra/records/{name}.json` | the records of the results that belong to the analysis (§8) |
| `results/{universe}/{name}.{format}`, `results/{name}.{format}` | the default places of those results' bytes (§8) |

`results/` and `.astra/` belong to runners. No input's `path` and no
declaration's `path` is, or lies in, them ([`RESERVED_PATH`](#validator)):
tidied as **Reading git** says (above), a path is not the `results/` or
`.astra/` of any analysis of the stack (§7), and is not inside one. So a run
never writes over an input or a declared analysis, and a result is read by
its address (§5), never by a path.

## 4. Names and grammars

### Grammar

```abnf
id               = lower *( lower / DIGIT / "_" )
lower            = %x61-7A                      ; a-z
address          = id *( "." id )               ; [declaration "."]... element
reference        = address [ "#" id ]           ; "#" pins a universe
option-reference = address "." id              ; a decision's address, then an option id
condition        = [ "~" ] option-reference     ; "~": the option is not selected
```

The last segment of an `option-reference` is always the option, so the
option `seed_42` of the decision `random_seed` of a declared analysis `iris`
is `iris.random_seed.seed_42`.

### Named types

| Type | Form | Used by |
|---|---|---|
| [`id`](elements/Id.md) | `id` | every map key but those of `Universe.decisions`; also `Universe.derived_from`, `Universe.universe`, `Option.insights` and the values of `Universe.decisions` |
| [`address`](elements/Address.md) | `address` | `Output.decisions`, the keys of `Universe.decisions`, `Universe.analysis` |
| [`reference`](elements/Reference.md) | `reference` | `Output.inputs`, `Evidence.artifact`, `ProvenanceRecord.address`, `RecordedInput.entry` |
| [`option_reference`](elements/OptionReference.md) | `option-reference` | `Option.requires`, `Option.incompatible_with` |
| [`condition`](elements/Condition.md) | `condition` | `Output.when`, `Decision.when` |
| [`commit_id`](elements/CommitId.md) | a full git commit id: 40 lowercase hexadecimal digits (SHA-1) or 64 (SHA-256) | `AnalysisDeclaration.commit`, `Generation.commit` |
| [`content_hash`](elements/ContentHash.md) | `sha256:`, then 64 lowercase hexadecimal digits | `ProvenanceRecord.content_hash`, `RecordedInput.content_hash` |
| [`spec_version`](elements/SpecVersion.md) | `MAJOR.MINOR.PATCH`, without leading zeros | `Analysis.spec_version`, `ProvenanceRecord.spec_version` |
| [`timestamp`](elements/Timestamp.md) | a UTC time to the millisecond, `YYYY-MM-DDThh:mm:ss.sssZ`, each field in its range; whether the day exists in its month, such as 30 February, isn't checked | `Generation.started`, `Generation.finished` |
| [`iri`](elements/Iri.md) | an IRI, never a CURIE: a scheme, `:`, then characters other than ASCII spaces and controls, C1 controls, `<`, `>`, `"`, `{`, `}`, the vertical bar, `\`, `^`, the backtick and the bidi formatting characters U+200E, U+200F and U+202A–U+202E, with `%` only before two hex digits and at most one `#` | `Environment.iri`, `FragmentSelector.conforms_to` |

A value that doesn't take its type's form fails: a map key or an `id` as
[`INVALID_ID`](#parse-and-schema), any other address, reference, option
reference or condition as [`INVALID_REFERENCE`](#parse-and-schema), a commit
id as [`INVALID_COMMIT`](#parse-and-schema), and the others as
[`INVALID_VALUE`](#parse-and-schema).

### Ids and maps

Every element the author names is an entry of a map keyed by its id: inputs,
outputs, decisions, options, universes and imports (`universes`),
declarations (`analyses`), prior insights and findings. The id is written
once, as the key ([`INVALID_ID`](#parse-and-schema)): `seed_42: {}`, never
`seed_42: {id: seed_42}` ([`UNKNOWN_FIELD`](#parse-and-schema)). Ids are
unique within their map because keys are
([`DUPLICATE_KEY`](#parse-and-schema)), and the order of a map carries no
meaning. A map's entries are objects, except those of `Universe.decisions`,
each of which is the id of the option selected (`model: svm`)
([`WRONG_TYPE`](#parse-and-schema)). A list where a map is expected, as in
`outputs: [f1_score]`, is [`WRONG_TYPE`](#parse-and-schema) too. Lists hold
only what is a list: an insight's `evidence`, a record's `inputs`, and lists
of strings. No list of strings holds the same entry twice
([`DUPLICATE_ENTRY`](#parse-and-schema)). No list of strings is empty: a
field with nothing to list is left out
([`EMPTY_COLLECTION`](#parse-and-schema)), so an output lists `decisions`
or has a `when` only when it names at least one.

Every id has the one grammar `id`; an address's kind comes from the field it
is written in, so an element can be called `inputs`. Ids of different kinds
can be the same, with two exceptions. An input and an output never share an
id, since `Output.inputs` takes both ([`AMBIGUOUS_ID`](#validator)). An output
never shares its id with a declaration of its analysis, since their results'
default places could then be the same (§8,
[`CLASHING_RESULT_NAME`](#validator)).

### Addresses

An address is read in the analysis whose `astra.yaml` it is written in. (In
an option reference, the address is the segments before the last, which is
the option; a condition's leading `~` and a reference's `#` pin are not part
of the address.) Every segment of an address but the last is
the id of a declaration (§7): the first names an
entry of that analysis's `analyses`, the next an entry of the declared
analysis's `analyses`, and so on. The last segment is the id of an element of
the analysis reached. Which kind of element comes from the field the address
is written in:

| Written in | Resolves to |
|---|---|
| `Output.inputs` | an input or an output |
| `Output.decisions`, the keys of `Universe.decisions` | a decision |
| a condition, `Option.requires`, `Option.incompatible_with` | a decision, then one of its options |
| `Evidence.artifact` | an output |
| an import's `analysis`, then `.` and its `universe` | one of another analysis's universes |

An address that doesn't resolve to an element of its field's kind breaks
[`UNRESOLVED_ADDRESS`](#validator), and an option that isn't one of its
decision's options breaks [`UNKNOWN_OPTION`](#validator). In
`feature_extraction/astra.yaml`, which declares `iris: {path: ..}`,
`iris.random_seed` is the decision `random_seed` of the analysis in the
parent directory, and `iris.iris_data` in `Output.inputs` is that analysis's
output `iris_data`.

Two addresses written differently that resolve to one element of one
analysis (§7) are two **spellings** of it. In
`examples/iris_pipeline/classification/astra.yaml`,
`feature_extraction.features` and `iris.feature_extraction.features` are one
output. A list can name one element under two spellings: they are two
entries. In `Output.inputs` and `Output.decisions` each has its own
placeholder (§5), and in `Output.inputs` its own recorded input (§8). Only
the same entry written twice is refused
([`DUPLICATE_ENTRY`](#parse-and-schema)).

A record's `address` is its result as the analysis the result belongs to
addresses it, and a recorded input's `entry` is an entry of `Output.inputs`
exactly as written (§8).

### Pins

A `reference` can end in `#` and a universe id, a **pin**: `f1_score#svm`. In
an `astra.yaml`, a pin names the entry of the file's `universes` with its id,
one of the file's analysis's universes or an import, or, where the file has
no such entry, the universe with that id of the analysis whose element the
reference names (§6, §7). A pin on an output reads it in that universe; a
pin on an input changes nothing. `#` is never part of an id, so the pin is
unambiguous. A decision's address never takes a pin: the entries of
`Output.decisions` are addresses
([`INVALID_REFERENCE`](#parse-and-schema)), and so are the keys of
`Universe.decisions` ([`INVALID_ID`](#parse-and-schema)).

In YAML, `#` inside a token is literal, so `f1_score#svm` needs no quotes.

### Report addresses

A report on an analysis, written outside `astra.yaml`, refers to the
analysis's elements by address
([RFC 0002](https://github.com/LightconeResearch/astra-spec/blob/main/rfcs/0002-decouple-reports.md)):
`<id>` for an element of the analysis, `<declaration>.<id>` for an element of
a declared analysis, and so on, in the grammar above. Inputs, outputs,
decisions, universes, imports, prior insights, findings and declared analyses
are addressable, and an import's address names the universe it imports.

## 5. The analysis

[Analysis](elements/Analysis.md) is the content of an `astra.yaml`. It has a
`spec_version` and at least one output ([`MISSING_FIELD`](#parse-and-schema),
[`EMPTY_COLLECTION`](#parse-and-schema)); everything else is optional. Most
elements also take a `label`, a short display name that is optional
everywhere, a `description` in free prose, and `tags`, keywords for grouping
and finding them.

### Inputs

An [Input](elements/Input.md) is a file tracked in git with the analysis,
named by its `path`, relative to the folder of the `astra.yaml` (§3). The
path is non-empty and doesn't start with `/`
([`INVALID_PATH`](#parse-and-schema)).

- It names one file ([`MISSING_INPUT_FILE`](#validator)). Data in many files
  is many inputs.
- The file is inside the analysis's directory and outside every directory
  below it that holds an `astra.yaml` file of its own
  ([`INPUT_IN_ANOTHER_ANALYSIS`](#validator)). Another analysis reads it by
  address (`iris.data`), not by a path.
- The file is outside the places that belong to runners: the path is not,
  and doesn't lie in, the `results/` or `.astra/` of an analysis of the
  stack, tidied as §3 says ([`RESERVED_PATH`](#validator)). A result is read
  by its address, never by a path.
- The path names the file itself (not a symlink, §3), or a stand-in for it
  ([`MISSING_INPUT_FILE`](#validator)). A stand-in is something the
  validator recognises as standing in for the file, such as a large-file
  tool's pointer. The file, or its stand-in, is tracked in git
  ([`INPUT_NOT_TRACKED`](#validator)), in the repository that holds the
  analysis (§3). Something standing in for the content isn't the content.

The record of each result that reads an input holds the hash of what it read
(§8), so a change to the file makes those results stale.

Data that isn't tracked in git with the analysis, such as a download, a
loader's output or a query's answer, comes in through an output whose recipe
gets it. That output is built once, or per universe when it depends on a
decision such as which data release to use, and its record holds the hash of
what came back. Data kept in another repository, a git submodule say, isn't
tracked in git with the analysis either (§3), so it isn't an input.

### Outputs

An [Output](elements/Output.md) is an artefact the analysis makes. It has a
`type`, one of [OutputType](elements/OutputType.md) (`metric`, `figure`,
`table`, `data`, `report`: [`INVALID_VALUE`](#parse-and-schema)), a `format`
and a `recipe` ([`MISSING_FIELD`](#parse-and-schema)). The `format` is how the artefact is
encoded, as a lowercase token, `^[a-z0-9][a-z0-9_.+-]*$`: the file extension
it is written with, without the leading dot, such as `png`, `csv` or
`parquet` ([`INVALID_VALUE`](#parse-and-schema)). It is the extension of the
result's default place (§8).

- `inputs` lists what the output is made from, in order: references (§4) to
  inputs and outputs of the analysis or of analyses it declares. A reference
  can be pinned (§6). Their order counts, since `{inputs}` passes them to
  the recipe in that order.
- `decisions` lists the addresses of the decisions whose option the output
  is made with directly, not through what it reads: a different option for
  any of them, in the universe being built, can give a different result.
  Their order carries no meaning. Listing a decision that reaches the output
  through an unpinned input gives the output the same results, though
  listing a decision of another analysis consumes it, and the address it is
  listed under is then held to §7's rules on consuming
  ([`UNDRIVEN_DECLARATION`](#validator)). Listing a decision that only a
  pinned input brings in makes the output built per universe (§6), so a
  comparison between universes lists none.
- `when` makes the output conditional (below).
- `recipe` says how the output is made (below).

No output depends on itself, directly or through others
([`OUTPUT_CYCLE`](#validator)).

### Recipes

A [Recipe](elements/Recipe.md) has a `command`
([`MISSING_FIELD`](#parse-and-schema)), and optionally the context it runs in:
`resources` ([Resources](elements/Resources.md)), the CPUs, memory, time,
disk and GPUs it asks for (`cpus` at least 0 and `gpus` at least 1:
[`INVALID_VALUE`](#parse-and-schema)), and `container`, the container it runs in:
an image, or a Containerfile it is built from. `Analysis.container` is the
default container of the analysis's recipes. A recipe runs in its analysis's
directory ([`WRONG_WORKING_DIRECTORY`](#runner)).

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

A placeholder gives a path, relative or absolute, that the recipe can open
from the directory it runs in. A runner substitutes each placeholder
verbatim, with no shell quoting, so quoting is the author's job: a path may
hold a space or a character the shell treats specially, and a command that
may meet one quotes the placeholder, as in `--data '{inputs.data}'`.

In `{inputs.<entry>}` and `{decisions.<entry>}`, `<entry>` is an entry of the
output's `inputs` or `decisions` exactly as written, dots and `#` included:
`{inputs.classification.accuracy#baseline}`, `{decisions.iris.random_seed}`.
Two pins of one output are two entries, each with its own placeholder. Any
other placeholder breaks [`UNDECLARED_TEMPLATE_REF`](#validator): one naming
an entry the output doesn't list, such as `{inputs.data}` when `data` isn't
among its `inputs`, or one of none of these forms, such as `{foo}`. So does a
stray brace: a `{` with no `}` after it, or a `}` that ends no placeholder, as
in `echo }`.

A recipe should read the files inputs name, and other outputs' results, only
through its output's inputs ([`UNDECLARED_READ`](#runner)), since a checker
sees a change to them only through those inputs. Anything else it uses, its
own scripts among them, is pinned by the commit or is part of the
environment. A runner can enforce this, as §9 permits; one that does fails
the recipe.

### Decisions and options

A [Decision](elements/Decision.md) is a choice the analysis makes, such as
which estimator to use, with the `rationale` for making it. Its `options`
hold at least one [Option](elements/Option.md)
([`EMPTY_COLLECTION`](#parse-and-schema)). Each universe chooses which of a
decision's options is used (§6).

An option constrains every selection it is part of:

- `requires` lists options that are also selected whenever it is
  ([`MISSING_REQUIRED_OPTION`](#validator));
- `incompatible_with` lists options that are never selected together with it
  ([`INCOMPATIBLE_OPTIONS`](#validator)).

Both take option references (§4), so they can name an option of a declared
analysis's decision.

An option with an `excluded` reason is excluded: no effective selection
selects it ([`EXCLUDED_OPTION_SELECTED`](#validator)). It stays listed, so the
analysis records what it considered and why it ruled it out. `excluded: true`
is not a reason ([`WRONG_TYPE`](#parse-and-schema)).

An option's `insights` are the ids of the prior insights that support it
([`INVALID_INSIGHT_REF`](#validator)).

### Conditional elements

A decision or an output with a `when` is conditional. `when` is a list of
conditions (§4). A condition `d.o` holds when the option `o` of
the decision `d` is selected, and `~d.o` holds when it isn't; `d` can be a
decision of a declared analysis, by its address, as in the condition
`iris.random_seed.seed_42`. The element is **active** when every one of its
conditions holds, and an element without `when` is always active. Conditions
are evaluated in the effective selection of the universe being built (§6).

<!-- fragment: Analysis -->
```yaml
decisions:
  correction:
    options: {none: {}, calibrated: {}}
  calibration_prior:
    when: [correction.calibrated]
    options: {weak: {}, informative: {}}
outputs:
  calibrated_table:
    type: table
    format: csv
    when: [correction.calibrated]
    recipe:
      command: python make.py '{output}'
```

A universe selecting `correction.none` has neither `calibration_prior` nor
`calibrated_table`. It doesn't set an inactive decision itself
([`INACTIVE_DECISION`](#validator)) and needn't set it at all
([`MISSING_DECISION`](#validator)). An inactive output isn't built in that
universe: no output with a result planned there (§8) reads it without a pin
([`INPUT_NOT_BUILT`](#validator)), and no pin names it there
([`PIN_INACTIVE`](#validator)).

### Insights and evidence

An [Insight](elements/Insight.md) is a claim backed by evidence. The
analysis's `prior_insights` are what earlier work establishes and the
analysis builds on, which options cite by id. Its `findings` are what it
concludes. An insight has a `claim` and at least one item of `evidence`
([`MISSING_FIELD`](#parse-and-schema),
[`EMPTY_COLLECTION`](#parse-and-schema)); its `description` gives the
reasoning behind the claim, and its `scope` the conditions under which the
claim holds.

An [Evidence](elements/Evidence.md) item cites exactly one of
([`INVALID_EVIDENCE_SOURCE`](#parse-and-schema)):

- a published work, by its `doi`, such as `10.48550/arXiv.1706.03762`
  (`10.`, digit runs joined by `.`, `/`, then a non-empty suffix:
  [`INVALID_VALUE`](#parse-and-schema)), with the work's `version`, counted
  from 1, when the work has versions, as an arXiv paper does;
- an output, as an `artifact`: a reference written as in `Output.inputs`,
  which names an output ([`UNRESOLVED_ADDRESS`](#validator)).

Evidence has a `version` only with a `doi`
([`INVALID_EVIDENCE_SOURCE`](#parse-and-schema)). It locates the passage the
claim rests on with W3C Web Annotation selectors: `quote`, a
[TextQuoteSelector](elements/TextQuoteSelector.md)
(`oa:TextQuoteSelector`), whose `exact` is the passage as the work or output
writes it, with the `prefix` and `suffix` around it; and `location`, a
[FragmentSelector](elements/FragmentSelector.md) (`oa:FragmentSelector`), the
place in the work or output the claim rests on. For a `doi`, the cited
resource is the work's full text. With both a `quote` and a `location`, the
quote is sought within the location.

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
[RFC 8118 §3](https://www.rfc-editor.org/rfc/rfc8118#section-3) gives it
(it defers to ISO 32000-2), such as `page=6`, with pages counted from 1; it
can point at more than a page. Web Annotation names that syntax
`http://tools.ietf.org/rfc/rfc3778`, after the RFC that RFC 8118 obsoletes.
Writing that IRI means the same as writing none, and `value` is then read by
RFC 8118. PDF parameters are joined with `&`, never with `#` as RFC 3778
allowed, and a space or `"` in a value, as in `search=`, is percent-encoded:
`page=6&search=%22label%20noise%22`.

`value` is read by the syntax `conforms_to` names. It is non-empty, holds no
ASCII space or control character and none of `"`, `#`, `<`, `>`, `[`, `\`,
`]`, `^`, the backtick, `{`, `|` and `}`, and has `%` only before two hex
digits ([`INVALID_VALUE`](#parse-and-schema)). `conforms_to` is an
[`iri`](elements/Iri.md) (§4, [`INVALID_VALUE`](#parse-and-schema)).

Evidence isn't built in a universe. Citing an output built per universe, it
may pin it: the claim is then about one universe's result, and the pin says
which. The pin names a universe as one in `Output.inputs` does (§4, §7). A
check covers the evidence of the analysis it is run on (§8). Evidence citing
a result is checked through that result's record, and unpinned evidence
through the records of the output's results (§8).

## 6. Universes

### Declaring universes

A universe selects one option for every active decision of its analysis and
of every analysis reached through a declaration that its analysis's
universes drive (§7). An analysis's universes are entries of its
`universes`, keyed by id, unique within the map
([`DUPLICATE_KEY`](#parse-and-schema)). An entry can instead be an
**import**, which names one of another analysis's universes under the
entry's id and selects nothing: its `analysis` is the address of the
declaration that leads to that analysis, and its `universe` is the id of one
of that analysis's universes. An import has both, and neither `decisions`
nor `derived_from` ([`INVALID_IMPORT`](#parse-and-schema)). It is not one of
the analysis's universes. Both are written as a
[Universe](elements/Universe.md) object, and an import's `label`,
`description` and `tags` are its own: they describe the universe it imports
under the import's id. In this file, `main` is a universe and `catalog_main`
an import:

<!-- fragment: Analysis -->
```yaml
analyses:
  catalog: {path: catalog}
universes:
  main:
    decisions: {catalog.cut: strict}   # a universe of the analysis
  catalog_main:                        # an import of catalog's universe main
    analysis: catalog
    universe: main
```

The universe an import names is an **imported universe** of the importing
file: a pin there names it by the import's id (§4), and it is checked as a
universe of its own analysis, which is its only driver, and built as one where
it is among the universes built (§7). A pin whose file has no entry with its
id imports a universe in the same way (§7).

A universe's `decisions` map decisions to options
([DecisionSelection](elements/DecisionSelection.md)), as
`<decision>: <option>`, such as `model: svm`. A key is the id of a decision
of the analysis or, for a decision of another analysis, its address,
`<declaration>.<decision>`, a flat key (§7), or another spelling of that
address through declarations (§4, §7). No key goes through a declaration
that leads back to an analysis already on its chain, the universe's
analysis included ([`LOOPING_KEY`](#validator)). So the analysis's own
decisions are keyed by their ids alone, and where `stage` declares
`again: {path: .}`, `stage.d` is never written `stage.again.d`. A key
resolves through its declarations to one decision: an analysis, known by
its identity (§7), and the decision's id in it. A universe's own
`decisions` give each decision one key, and a derived universe sets a
decision it inherits only under the key it inherits (below): two keys that
spell one decision break
[`DUPLICATE_ELEMENT`](#validator), even when they select the same option. A
value is the id of one of that decision's options
([`UNKNOWN_OPTION`](#validator)).

`derived_from` names another universe of the same analysis, never an import
([`UNKNOWN_DERIVED_FROM`](#validator)), whose selection this one inherits, so
that it gives only the decisions it changes. No universe's chain of
`derived_from` loops ([`DERIVED_FROM_CYCLE`](#validator)). A derived universe
inherits only the selection.

### The effective selection

A universe's **effective selection** is what it selects once `derived_from`
is resolved:

1. Without `derived_from`, it is the universe's own `decisions`.
2. With `derived_from`, it is the effective selection of the universe named
   there, each of the universe's own selections replacing what the universe
   inherits for its decision. So where `stage.inner.d` and `inner.d` spell
   one decision, a universe that inherits `stage.inner.d: d1` changes it by
   setting `stage.inner.d: d2`; setting `inner.d: d2`, or `inner.d: d1`,
   breaks [`DUPLICATE_ELEMENT`](#validator) at its own key.
3. An inherited selection of a decision that isn't active in the result is
   dropped, so a universe that switches a decision off needn't undo what it
   inherited for it.

A universe whose `derived_from` doesn't resolve, or whose chain loops or
reaches a universe that has none, has no effective selection (§9, *What is
checked*).

The effective selection is held to everything a universe written in full is:

- it selects every active decision of its analysis and of every analysis
  reached through a declaration that its analysis's universes drive
  ([`MISSING_DECISION`](#validator)), so a universe that switches a decision
  on sets it;
- it names only declared decisions and their options
  ([`UNRESOLVED_ADDRESS`](#validator), [`UNKNOWN_OPTION`](#validator));
- it breaks no `requires` ([`MISSING_REQUIRED_OPTION`](#validator)) and no
  `incompatible_with` ([`INCOMPATIBLE_OPTIONS`](#validator)), and selects no
  excluded option ([`EXCLUDED_OPTION_SELECTED`](#validator)).

A selection the universe makes itself, rather than inherits, is of an active
decision ([`INACTIVE_DECISION`](#validator)). Where `gpu_optimization` has
`when: [backend.gpu]`:

<!-- fragment: Analysis -->
```yaml
universes:
  gpu_advanced:
    decisions: {mode: advanced, backend: gpu, gpu_optimization: tensor_cores}
  cpu_from_gpu:
    derived_from: gpu_advanced
    decisions: {backend: cpu}   # the inherited gpu_optimization is dropped
```

### Built per universe or built once

An output is **built per universe** when it lists `decisions`, has a `when`,
or has an unpinned entry of `inputs` that names an output built per
universe. Any other output is **built once**: it has one result, the same in
every universe. Inputs carry no universe, and a pinned entry never makes an
output built per universe, since the pin fixes the universe it reads.

An output built once has no universe of its own. It lists no decisions, so
its recipe has no `{decisions.<entry>}` placeholder
([`UNDECLARED_TEMPLATE_REF`](#validator)), and a pin on it doesn't change
which result a reference names: pinned or not, the reference names its one
result, and `{inputs.<entry>}` gives that result's path; the pin still names
a universe ([`UNKNOWN_PIN_UNIVERSE`](#validator)).

### Which universe a reference reads

An unpinned entry of `inputs` reads its output in the universe being built.
A pinned one, such as `accuracy#svm`, reads it as built in the universe the
pin names, whichever universe is being built. That is the entry `svm` of the
file's `universes`, one of the file's analysis's universes or an import, or,
where the file has no such entry, the universe `svm` of the analysis whose
element the reference names ([`UNKNOWN_PIN_UNIVERSE`](#validator), §7). A
pinned output is active in the universe it is pinned to
([`PIN_INACTIVE`](#validator)). A pin on an input, as on an output built
once, names a universe and changes nothing else.

## 7. Composition

### Declarations

An analysis declares each analysis it uses in `analyses`, keyed by the id it
addresses it by ([AnalysisDeclaration](elements/AnalysisDeclaration.md)). The
declared analysis's elements are then addressed through that id, as
`<declaration>.<element>` (§4). A declaration has exactly one of `path` and
`url` ([`INVALID_DECLARATION_SOURCE`](#parse-and-schema)), and may have a
`commit`, which a `url` needs ([`URL_WITHOUT_COMMIT`](#parse-and-schema)).

**`path`** is the directory of the declared analysis's `astra.yaml`, relative
to the folder of the declaring `astra.yaml` (§3). It is non-empty and
doesn't start with `/` ([`INVALID_PATH`](#parse-and-schema)).
Tidied as §3 says, it doesn't go above the top of the root's working tree
or, read at a commit, of the repository that holds that commit
([`DECLARATION_OUTSIDE_REPOSITORY`](#validator)). It is not, and doesn't lie
in, the `results/` or `.astra/` of an analysis of the stack
([`RESERVED_PATH`](#validator)), so a run never writes over a declared
analysis. The directory it names holds an `astra.yaml`
([`MISSING_DECLARED_ANALYSIS`](#validator)). A declared analysis can be a
git submodule, read as §3 says. A submodule that declares something outside
its own repository, such as its parent with `..`, can be validated and built
only from a root whose repository holds what it declares.

**`url`** is a remote that git fetches another repository from, in one of
git's two forms: `scheme://…` (`https://github.com/owner/analysis`,
`ssh://git@host/x.git`, `file:///srv/repo`) or scp-like `[user@]host:path`
(`git@github.com:owner/repo`). The declared analysis is the one at the top
level of that repository, at the declaration's `commit`. A bare word or a
local path (`a`, `owner/repo`, `../repo`) is not a `url`
([`INVALID_VALUE`](#parse-and-schema)): an analysis in the declaring
analysis's repository is declared by `path`, and another repository on this
machine by an explicit `file://` URL. A `url` holds no ASCII space or control
character ([`INVALID_VALUE`](#parse-and-schema)).

**`commit`** is a full commit id ([`INVALID_COMMIT`](#parse-and-schema)): a
branch moves, a tag can be moved or name another commit in a fork or a
mirror, and a shortened id can become ambiguous as a repository grows. A
declaration with a `commit` declares an analysis from a commit (below).

**Identity.** A declaration names a directory, read at a commit or in the
working tree. With a `url`, it is the top level of that repository; with a
`path`, it is the `path` joined to the folder of the declaring `astra.yaml`
and tidied, as **Reading git** in §3 says. It is read at the declaration's
`commit` or, without one, as the declaring analysis is read. The root, and
every analysis reached from it by `path` alone, is read in the working tree.
At a commit, a path that crosses a gitlink is read in the submodule's
repository at the commit the gitlink pins (§3). The directory is a path from
the top of the repository it is read in or, read in the working tree, from the
top of the root's working tree. Two declarations name the same analysis when
their directories are the same path, read at the same commit or both in the
working tree. A URL says only where to get the commit, so a fork or a mirror
with the same commit gives the same analysis. *Another analysis*, everywhere
in this specification, is one with a different identity.

An analysis, whichever analysis declares it and by whatever id, is one
analysis: each of its results is made at most once, however many
declarations reach it. A declaration by `path` alone, or a chain of them,
that leads back to the declaring analysis's own directory names the analysis
itself: `self: {path: .}`, say, or `feature_extraction.iris` in the root of
`examples/iris_pipeline`. An address through it is another spelling of one
of the analysis's own elements (§4). Consuming uses another analysis's
elements (below), so such an address consumes nothing, and no key goes
through it (§6).

Declarations by `path` alone can form cycles, such as an analysis declared
by its parent that declares its parent with `..`, but outputs never depend
on each other in a cycle ([`OUTPUT_CYCLE`](#validator)). A declaration with
a `commit` is never part of a cycle, since a commit can only name earlier
ones.

### The analysis stack

The **root** is the analysis being validated or built, and any analysis can
be the root. Its **analysis stack** is the root and every analysis it
declares, directly or through other declared analyses. A validator reads
every `astra.yaml` of the stack, each by the `spec_version` it states
([`UNSUPPORTED_SPEC_VERSION`](#validator)).

The universes built are the root's and those named by a pin on an output
built per universe, in the `inputs` of a planned result's output or in the
root's evidence (§8). Such a pin names one of the universes of the analysis
whose file it is in or, through an import or where that file has no entry
with the pin's id, another analysis's universe (*Imported universes*,
below). In the root's universes the root is the driver and is never driven,
even when a declaration in its stack leads back to it. Another analysis's
universe is used only where such a pin names it, in that analysis's file or
in another. That analysis is then its only driver: like the root, it is
never driven in that universe, and what is built there belongs to it (§8).
Neither the root nor the analysis whose file imports the universe is the
driver there: a declaration of either in that analysis's file, such as
`parent: {path: ..}`, leads back to no analysis already on the chain, and is
an ordinary declaration. Where that analysis's universes drive one of them,
as the key `parent.decision1` drives a parent, it is driven and built in
that universe like any other analysis. A validator also checks every other
universe of the stack (below).

### Driving and consuming

An analysis uses the elements of another in two ways.

**Consuming** is using an element of another analysis by address: an input
or an output in `Output.inputs`, a decision in `Output.decisions`, in a
condition or in a constraint, and an output in evidence. A consumed decision
has the option selected in the universe being built, so its address never
takes a pin, and whatever uses it can be built only where the decision's
analysis is built in that universe ([`NOT_BUILT_IN_UNIVERSE`](#validator)).

**Driving** is setting another analysis's decisions from one's own
universes, by flat keys: the decision's address,
`<declaration>.<decision>`, through as many declarations as lead to it
(`classification.classifier`, `stage.inner.d`). The analysis whose
universes drive is the **driver**, and each analysis reached through a
declaration they drive (below) is **driven** through that declaration. An
analysis with no decisions has no key to set, and is driven by being built
in its driver's universes (below).

An analysis's universes **drive** a declaration when a key in the effective
selection (§6) of any of them goes through every declaration from the
analysis's file to that one, and a declaration they drive is driven in every
one of them. A key that loops ([`LOOPING_KEY`](#validator)) drives no
declaration. The key `stage.inner.d` drives the driver's `stage` and, through
it, `stage`'s `inner`, but not an `inner` that the driver's file declares
itself: each chain of declarations from the driver's file (`stage`,
`stage.inner`, `inner`) is driven on its own. Two chains that end in one
declaration, such as `stage.lib` and `stage_undriven.lib` where `stage` and
`stage_undriven` declare one directory, are driven on their own too, and an
address or a reference is judged on its own chain. A declaration of an
analysis with no decisions is driven when the chain before it is, and so
whenever the driver's file declares it, unless the declaration leads back to
an analysis already on the chain, the declaring analysis itself included
(`self: {path: .}`). Such an analysis's outputs built per universe (§6) are
then built in each of the driver's universes where they are planned (§8), and
those results belong to the driver, while its outputs built once still belong
to it. Universes of its own don't change this. They are built only where it is
the driver: when it is the root, or where one of them is among the universes
built (*The analysis stack*, above).

- Every universe sets every active decision of every analysis reached
  through a declaration that its analysis's universes drive
  ([`MISSING_DECISION`](#validator)), whichever of them has the key that
  drives it. A universe in which `when` switches off every decision of a
  driven analysis sets nothing for it.
- Driving is judged on the effective selections, so a key a derived universe
  inherits counts as one it sets.
- An analysis reached through two driven declarations can have a decision
  set under either spelling (`stage.inner.d` or `inner.d`), but a universe
  sets it under one key, a derived universe that inherits it under the key
  it inherits ([`DUPLICATE_ELEMENT`](#validator)).
- In a universe being built, a driven analysis's own universes don't set
  its decisions. A pin naming one of them still reads it: in its own file,
  or in another through an import or, for one of its own elements, where
  that file has no entry with the pin's id (below). Each universe being
  built has one driver, the analysis whose universe it is.

A validator still checks every universe of every analysis of the stack, a
driven analysis's own included. Each universe's selections are held to §6
and to driving ([`UNRESOLVED_ADDRESS`](#validator),
[`UNKNOWN_OPTION`](#validator), [`DUPLICATE_ELEMENT`](#validator),
[`LOOPING_KEY`](#validator), [`UNKNOWN_DERIVED_FROM`](#validator),
[`DERIVED_FROM_CYCLE`](#validator), [`MISSING_DECISION`](#validator),
[`INACTIVE_DECISION`](#validator),
[`MISSING_REQUIRED_OPTION`](#validator),
[`INCOMPATIBLE_OPTIONS`](#validator),
[`EXCLUDED_OPTION_SELECTED`](#validator)). The declarations driven in a
universe are those its analysis's universes drive, as above, a declaration
back to the root included; checking a universe builds nothing, so the root
stays undriven in its own universes. Where the root drives `sub`, a
universe of `sub`'s own that leaves one of `sub`'s active decisions unset
breaks `MISSING_DECISION`, though the root's universes don't use it. The
rules on the universe being built (below:
[`NOT_BUILT_IN_UNIVERSE`](#validator), [`UNDRIVEN_DECLARATION`](#validator),
[`INPUT_NOT_BUILT`](#validator)) hold only in the universes built, as
[`RESULT_IN_TWO_PLACES`](#validator) does (§8), and for an output only where
its result is planned or, for its `when`, would be if the `when` held.

Driving leaves an analysis able to stand alone, and consuming a decision ties
the outputs that use it to the decision's analysis. By convention, a
decision that matters to one analysis is driven, and one shared by several,
such as the seed of a whole stack, is consumed.

### Imported universes

An import (§6) names one of another analysis's universes under an id of the
importing file. It resolves in its file by identity (*Declarations*, above),
so it names one universe under every root. Its `analysis` can lead to any
analysis the file's declarations reach: one below, its parent through `..`,
a sibling through the parent, or an analysis from a commit. That is another
analysis than the file's own, and its `universe` is one of that analysis's
universes, never an import in its file
([`UNRESOLVED_ADDRESS`](#validator)).

- An import selects nothing and drives nothing. No selection rule (§6)
  checks it in the importing analysis, and no `derived_from` names it
  ([`UNKNOWN_DERIVED_FROM`](#validator)). The universe it names is checked
  as a universe of its own analysis (*Driving and consuming*, above).
- In the universe an import names, that universe's analysis is the only
  driver (*The analysis stack*, above). The importing analysis doesn't drive
  it, and what is built there belongs to the universe's analysis, under the
  universe's own id (§8). The importing analysis is built there only where
  that universe drives it, as a key `parent.d` drives a parent.
- An imported universe is built where it is among the universes built (*The
  analysis stack*, above). Imports of one universe, in one file or several and
  under any ids, name that one universe, which is built once.

Where a pin's file has no entry with its id, the pin names the universe
with that id of the analysis whose element the reference names (*The
universe being built*, below), and all of the bullets above hold of that
universe. So an import is needed only where the file has an entry with the
universe's id, or for a universe of another analysis than the one whose
element the reference names, such as `stage`'s for `stage.lib.out`.

<!-- fragment: Analysis -->
```yaml
analyses:
  catalog: {path: catalog}
outputs:
  comparison:
    type: table
    format: csv
    inputs:
      - catalog.table#main
      - catalog.table#catalog_main
      - catalog.table#alone
    recipe:
      command: python make.py '{output}'
universes:
  main:
    decisions: {catalog.cut: strict}   # the root's universe: it drives catalog
  catalog_main:                        # catalog's own universe main, imported
    analysis: catalog
    universe: main
```

In this root, `catalog.table#main` reads `catalog`'s output as the root
builds it in its `main`, where the root's universes drive `catalog`, and the
result belongs to the root. `catalog.table#catalog_main` reads it as
`catalog` builds it in its own `main`, and `catalog.table#alone`, since the
root has no `alone`, as `catalog` builds it in its own `alone`. Those two
results belong to `catalog`, whichever file reads them.

An earlier commit's results are read the same way. Where the declaration
`previous` names the analysis's own directory at a commit, its universes
often have the ids of the analysis's own. If both have a `fast`,
`previous.counts#fast` names the analysis's own `fast`. Where `previous` has
decisions and no key of the analysis's universes goes through it, the
analysis doesn't build `previous` in its `fast`: a planned result's output
that reads `counts`, built per universe, through this pin breaks
[`UNDRIVEN_DECLARATION`](#validator) and
[`NOT_BUILT_IN_UNIVERSE`](#validator). With the import
`previous_fast: {analysis: previous, universe: fast}`,
`previous.counts#previous_fast` reads `counts` as it was built in `fast` at
that commit, through its record, and no recipe runs (*Analyses from a
commit*, below).

### The universe being built

A universe is named by its analysis and its id, since the same id can name a
universe in several analyses. When an analysis is built in one of its
universes, that universe is pushed through every declaration the analysis's
universes drive: it is the universe being built in every analysis they reach.
An unpinned entry of `inputs` reads its output in that universe, a pinned
one in the universe its pin names (below), and a consumed decision has the
option that universe selects. So, wherever the output of a result planned in
the universe being built (§8) reads an output built per universe without a
pin, or consumes a decision, wherever the output of a planned result, or the
root's evidence, pins an output built per universe to the universe being
built, wherever an output's `when` consumes a decision where the output's
result would be planned if the `when` held, and wherever, in an analysis
built in that universe, a decision's `when` or a constraint consumes one:

1. The analysis it belongs to is built in the universe being built
   ([`NOT_BUILT_IN_UNIVERSE`](#validator)). The analysis whose universe is
   being built is always built in it, so an analysis it drives can consume
   its decisions and read its outputs back through `..`, as
   `feature_extraction/astra.yaml` consumes `iris.random_seed` (§4).
2. In the file of the analysis whose universe is being built, the file's
   universes drive the chain of each such address of another analysis, from
   the file's declaration to the address's last
   ([`UNDRIVEN_DECLARATION`](#validator)). Uses in other files come under
   the first rule alone.

An output built once has one result, so it is read without a pin from any
universe, through any declaration. And every output that the output of a
result planned in the universe being built reads without a pin, of the
analysis itself or of another, is active there
([`INPUT_NOT_BUILT`](#validator)).

A pin `#u` resolves in the file it is written in, whatever drives that
file's analysis, so what it names is the same under every root:

- Where the file's `universes` has an entry `u`, the pin names it: one of
  the file's analysis's universes, or the universe an import there names
  (*Imported universes*, above).
- Where it has no entry `u`, the pin names the universe `u` of the analysis
  whose element the reference names, as an import of it would: one of that
  analysis's universes, never an import in its file.
- Where that analysis has no universe `u` either, as for an element of the
  file's own analysis, the pin names nothing
  ([`UNKNOWN_PIN_UNIVERSE`](#validator)).

So adding or removing an entry `u` in a file's `universes` can change what a
pin `#u` in that file names. A pin that names one of its file's universes is
in the driver's file, so both rules above hold it. One that names another
analysis's universe is not, so the first rule alone holds it.

In this root, `inner.result#u1` reads `inner`'s output as the root builds it
in its `u1`. The root has no `v1`, so `inner.result#v1` reads it as `inner`
builds it in its own `v1`. The root has a `u1` of its own, so it reads
`inner`'s `u1` through an import, as `inner.result#inner_u1`:

```yaml
spec_version: "0.1.0"
analyses:
  inner: {path: stage/inner}            # the root's universes set inner.d
outputs:
  in_root_u1:
    type: metric
    format: json
    inputs: [inner.result#u1]           # the root's universe u1
    recipe:
      command: python make.py '{output}'
  in_inner_v1:
    type: metric
    format: json
    inputs: [inner.result#v1]           # inner's own v1: the root has no v1
    recipe:
      command: python make.py '{output}'
  in_inner_u1:
    type: metric
    format: json
    inputs: [inner.result#inner_u1]     # inner's own u1, imported
    recipe:
      command: python make.py '{output}'
universes:
  u1:
    decisions:
      inner.d: d1                       # a flat key: inner's decision d
  inner_u1:                             # an import of inner's universe u1
    analysis: inner
    universe: u1
```

In a file with no `v1`, `stage.lib.out#v1` names `lib`'s `v1`, since `out`
is `lib`'s output. Where `stage`'s universes drive `lib`, the file reads
`out` as `stage` builds it in its own `v1` by importing that universe,
`stage_v1: {analysis: stage, universe: v1}`, and pinning
`stage.lib.out#stage_v1`.

A second declaration of the same directory,
`inner_undriven: {path: stage/inner}`, which no key of the root's universes
goes through, is judged on its own chain (*Driving and consuming*, above),
so it isn't driven. A read through it in one of the root's universes,
without a pin or pinned to one of them, breaks
[`UNDRIVEN_DECLARATION`](#validator):

<!-- fragment: Analysis -->
```yaml
outputs:
  in_root:
    type: metric
    format: json
    inputs: [inner_undriven.result]       # UNDRIVEN_DECLARATION
    recipe:
      command: python make.py '{output}'
  in_root_pinned:
    type: metric
    format: json
    inputs: [inner_undriven.result#u1]    # UNDRIVEN_DECLARATION
    recipe:
      command: python make.py '{output}'
```

The address's whole chain decides, up to its last declaration. Where the
root's universes drive `stage.inner` but not `stage`'s second declaration
`inner_undriven`, `stage.inner_undriven.result` read in the root's file,
without a pin or pinned to one of the root's universes, breaks
[`UNDRIVEN_DECLARATION`](#validator) too, though the root drives `stage`.
So does `stage_undriven.inner.result`, where the root's `stage_undriven`
declares `stage`'s directory a second time, though the root drives
`stage.inner`.

What is built in a driver's universes belongs to the driver (§8).

### Analyses from a commit

A declaration with a `commit` names an **analysis from a commit**: the
declared analysis as it was at that commit. With a `url`, it is the analysis
at the top level of that repository at the commit. With a `path`, it is the
analysis at that path at the commit, which the repository that holds the
declaring `astra.yaml` has ([`COMMIT_NOT_FOUND`](#validator) or, in a file
read from a remote, [`REMOTE_UNREACHABLE`](#validator)) and which should be an
ancestor of the commit the declaration is in or, for a declaration read in the
working tree, of HEAD ([`COMMIT_NOT_ANCESTOR`](#validator)). It is read from
the local repository or, when the declaring analysis is itself read from a
remote, from that remote, and each submodule it reaches through a gitlink as
§3 says. Every rule of this specification applies to an analysis from a commit
as it is, with its files read at its commit. Its results are those that belong
to it or to an analysis reached from it through declarations, each read at the
commit its analysis is read at.

**Identity.** An analysis from a commit is its directory at its commit,
whatever URL it is got from, as **Identity** under Declarations says (above).

**What is read.** An analysis from a commit is read from git at its commit,
each file as the blob git stores (§3). Unless it is driven, none of its code
runs.

**Validity.** The declared analysis, with everything it declares, is valid
at its commit ([`DECLARED_ANALYSIS_INVALID`](#validator)), each `astra.yaml`
read by the `spec_version` it states. A rule broken inside an analysis from a
commit is reported twice: `DECLARED_ANALYSIS_INVALID` on the declaration, in
the file the author can edit, and the rule's own code at its place in the
commit's file, which says why. A rule broken in the root, or in an analysis
reached from it by `path` alone, is reported once, under its own code.
Getting a commit from a remote is checked apart from that validity
([`REMOTE_UNREACHABLE`](#validator)). A commit is got from a remote when it
is a declaration's `url` and `commit`, a `path` and `commit` declared in a
file read from a remote, or the commit a gitlink pins, crossed at a commit
(§3). The remote is the `url`, the remote the file was read from, or the
submodule's URL (§3). A commit kept from an earlier fetch counts as got.

A commit that can't be got is an error on one declaration in a file outside
every analysis from a commit, read in the working tree, which the author can
edit: the declaration of the outermost analysis from a commit on the way to
it. It is reported once for each such declaration, so two declarations of
one commit get one report each. Where the root declares `sub` by `path`,
`sub` declares `upstream` by `url`, and `upstream` declares `nested` by
`url`, if `nested`'s commit can't be got, the error is on `sub`'s
declaration of `upstream`. A published analysis SHOULD declare only remotes
its readers can fetch.

**Use.** Unless it is driven, none of the recipes of an analysis from a
commit run ([`REBUILT_FROM_COMMIT`](#runner)), so the rules above let it
give only its outputs in its own universes, pinned (`upstream.summary#u1`,
in a file with no entry `u1`, or through an import), its outputs built once
(`upstream.stage.report`), and its inputs (`upstream.data`). Evidence cites
its results in the same way. One with no decisions is driven wherever the
chain before its declaration is (above). Driven or not, its results in its
own universes belong to it and are read through their records, and no
recipe runs in those universes, since every result there belongs to it
([`REBUILT_FROM_COMMIT`](#runner)). An address that doesn't exist in the
declared analysis is an error in the declaring one
([`UNRESOLVED_ADDRESS`](#validator)).

**Results.** A result of an analysis from a commit is read through its record
at the declared commit, in the analysis the result belongs to (§8), in the
repository that holds that analysis at the commit it is read at (§3). If the
declared analysis itself declares an analysis from a commit, that analysis's
records are read in its own repository, at the commit named for it. A result
can be read only once its record is committed, so the declaration names a
commit that holds the records, `B`, later than the commit their recipes ran
from, `A`, which the records name.
The result is unchanged if nothing that [`STALE_RESULT`](#check) compares
changed between `A` and `B`, and the results it was made from are unchanged
too. Their content hashes are taken from their records, without their
bytes. When a recipe reads the result, the runner gets its bytes from what
the declared commit holds at the result's default place, or through
something there it recognises as standing in for them (§5), and they are
checked against the record. An input of the declared analysis read by
address is got from its `path` at the declared commit, in the repository
that holds the declared analysis (§3), or through what the runner recognises
as standing in for it (§5).

**Driving.** A driver's universes can drive an analysis from a commit, as any
declared analysis. Its recipes then run on exactly its files at the declared
commit ([`NOT_AT_COMMIT`](#runner)). Its outputs built once aren't built:
like the rest of its results, they are read through their records at the
declared commit ([`REBUILT_FROM_COMMIT`](#runner)). Only what the driver's
universes build is built. It belongs to the driver, and its records name the
driver's commit, where the declaration says which commit the driven analysis
is from and, for a remote, where to get it.

## 8. Results and records

### Results

A **result** is what a recipe made for one output in one universe, or once
for an output built once. The root's **planned** results are:

- the result of each output of the root built once, and, in each of the
  root's universes, the result of every output of the root active there;
- every result a planned result reads through its output's `inputs`, through
  any declaration, pinned or not;
- every result the root's evidence cites (§5).

An output plans no result in a universe where it is inactive (§5). An output
of a declared analysis that no planned result reads and no evidence of the
root cites isn't planned, and building the root doesn't build it. Building it
on request is the tooling's choice, and a checker gives its record no status
(below).

A result belongs to the analysis whose universe it was built in. So what a
driven analysis builds in its driver's universes belongs to the driver. The
result of an output built once belongs to the analysis whose output it is.
A result built in a universe that a pin names belongs to that universe's
analysis, whichever file the pin is in and whether it names the universe
through an import or not (§7): it is placed in that analysis's directory,
under the universe's own id. A result's **name** is its output's id after
the ids of the driven declarations from the analysis it belongs to
(`subanalysis1.output1`). An undriven declaration, such as
`iris: {path: ..}` in `feature_extraction`'s file in the root's universes,
never adds a name. No declaration that leads back to an analysis already on
the chain from the driver is driven (§6, §7). So the result of an output of
the analysis it belongs to is named by the output's id alone, as the result
of an output built once always is. A sub-analysis's declaration of its
parent doesn't lead back where the sub-analysis is the driver: the parent's
`output0`, built in the sub-analysis's universe `v1` through a driven
`parent: {path: ..}`, is named `parent.output0` in the sub-analysis's
records, also where the parent's own file imports `v1` as `sub_v1` and reads
`output0#sub_v1`. Reached through two such chains (`inner` and
`stage.inner`, when keys go through both), a result is made once, and placed
and recorded under each name, though a planned result should have one
([`RESULT_IN_TWO_PLACES`](#validator)). The rule is judged on the planned
results, so in the universes built (§7) and not in the other universes a
validator checks. For each pair of a result's names, it is reported at the
first declaration of each of their chains that the other chain doesn't go
through, in the file that holds it: in the example, at the driver's `inner`
and `stage`. A result's **address** is a name followed, for a result built
in a universe, by `#` and the universe's own id, never an import's
(`subanalysis1.output1#u1`).
Each address is the `address` of the record at its place.

### Where records and bytes go

In the analysis a result belongs to:

| | Built in the universe `{universe}` | Built once |
|---|---|---|
| Its record | `.astra/records/{universe}/{name}.json` | `.astra/records/{name}.json` |
| Its bytes, at their default place | `results/{universe}/{name}.{format}` | `results/{name}.{format}` |

Both are worked out from an address of the result, so a result with two
names has two of each. Ids hold no `.`, but a format can (`tar.gz`), so two
default places `{name}.{format}` in one folder are the same only when one
name is a proper dotted prefix of the other: the output `stage` in format
`summary.json` and the result `stage.summary` in format `json`, say. That
needs an output and a declaration with one id in some analysis on the
longer name's chain of declarations. Every analysis of the stack keeps
[`CLASHING_RESULT_NAME`](#validator), so no two results of one analysis
share a default place. A record is the record only of the result its
`address` names, under that name ([`MISSING_RECORD`](#check),
[`MISPLACED_RECORD`](#check)). The runner writes the bytes to their default
places ([`UNRECORDED_RESULT`](#runner)) and tells the recipe where to write
through `{output}`, so a driven analysis's recipes write what they build in
the driver's universes into the driver's results. For the analysis of §2:

```text
.astra/records/
  comparison.json
  forest/accuracy.json
  svm/accuracy.json
results/
  comparison.csv
  forest/accuracy.json
  svm/accuracy.json
```

A result is one file, which its recipe writes at `{output}`. An artefact of
many files is written as an archive, or as several outputs.

A record at a commit can be read whether or not the commit holds the bytes.
The bytes needn't stay at their default place ([`ABSENT_RESULT`](#check) is a
`SHOULD`): a runner may keep them elsewhere and leave something standing in
for them (§5). Anything else at the default place, something standing in for
the bytes, other bytes or nothing, leaves the result's bytes `absent`
([`ABSENT_RESULT`](#check)).

### What a record holds

A [ProvenanceRecord](elements/ProvenanceRecord.md) gives its `spec_version`,
the result's `address`, the `content_hash` and `size` (in bytes) of the
result's bytes, and the run of the recipe that made it, `generated_by`, a
[Generation](elements/Generation.md):

- `commit`: the full id of the git commit the recipe ran from: a commit of
  the repository the record is committed in, the submodule's own commit for a
  result that belongs to an analysis in a submodule (the driver's commit for
  what a driver's universes build, §7). It pins every file of the code and
  every `astra.yaml` in that repository: an analysis in a submodule of it
  through the commit the submodule is pinned at, and an analysis from a
  commit through its declaration's `commit`.
- `inputs`: what the recipe read, as one
  [RecordedInput](elements/RecordedInput.md) for each entry the output lists
  in the `astra.yaml` files at the record's `commit`, and no other item,
  matched by its `entry`, which is written exactly as the output lists it
  ([`MISSING_RECORD_INPUTS`](#check)). Each gives the `content_hash` and
  `size` of what the recipe read through the entry: another output's result,
  or the file an input names. The order of the items carries no meaning. A
  later change to the list makes the result `stale`
  ([`STALE_RESULT`](#check)), not `missing`.
- `environment`: an [Environment](elements/Environment.md), whose `iri` is an
  IRI of the form §4 gives ([`INVALID_VALUE`](#parse-and-schema)), naming
  exactly the environment the recipe ran in, enough for its runner, at the
  version the record gives, to recreate it. It needn't resolve online: a
  `urn:` IRI or a scheme of the runner's own will do.
- `runner`: a [Runner](elements/Runner.md), the runner's `id`, ideally unique
  (an IRI, say), and its `version`.
- `started` and `finished`: when the recipe started and finished, in UTC to
  the millisecond, `YYYY-MM-DDThh:mm:ss.sssZ`, each field in its range;
  whether the day exists in its month, such as 30 February, isn't checked.

Every field of a record is required ([`MISSING_FIELD`](#parse-and-schema))
but three: `started` and `finished`, which are optional, and `inputs`, which
the schema leaves optional and [`MISSING_RECORD_INPUTS`](#check) holds to
the entries the output lists. So a record of an output that lists no inputs
can leave `inputs` out.

Every hash names its algorithm: `sha256:`, then the SHA-256 digest
([`INVALID_VALUE`](#parse-and-schema)).

```json
{
  "spec_version": "0.1.0",
  "address": "subanalysis1.output1#u1",
  "content_hash": "sha256:7af13cf14f96106b729279ec96430c5b115437053c29aeca4ff70b95770fb83e",
  "size": 732,
  "generated_by": {
    "commit": "a7d9ea93c409ab6da0d919308f91f51de7c7ec6f",
    "inputs": [
      {
        "entry": "iris.data",
        "content_hash": "sha256:549eeec2a96f853c662f95e730265f2e2b6fd840047ef2e5e487892a0ed5757e",
        "size": 10
      }
    ],
    "environment": {"iri": "urn:example-runner:env:sha256:5d1338d7b2770c256402101e2905173c46fcd60b376b2717cf6b129deb28af15"},
    "runner": {"id": "example-runner", "version": "1.2.0"},
    "started": "2026-10-26T14:00:00.000Z",
    "finished": "2026-10-26T14:00:02.000Z"
  }
}
```

A record holds only what its commit can't give: the output's declaration, the
options its decisions select and its format are in the `astra.yaml` files at
that commit. A record holds only the fields its `spec_version` defines, and is
read by its minor version's record schema (§1). A checker reading a record of
a greater minor version than its own validates it against the open variant of
the record schema, which ignores the fields the checker doesn't know, rather
than calling the record `missing`. A record whose minor version is smaller
than the checker's and has no record schema, such as `0.0.9`, is `missing`. A
record whose `spec_version` is missing or malformed is validated against the
checker's own record schema, so every error is a reason
([`INVALID_RECORD`](#check), §10). Read as RDF (§10), a record is W3C PROV-O.

Two records of one result with the same commit, inputs and environment, made
on two machines say, show whether the result reproduces: their
`content_hash` is the same.

### What a runner does

- A runner writes a record for every result it makes, at the place of each
  of its names in the analysis the result belongs to, and writes the bytes to
  their default places ([`UNRECORDED_RESULT`](#runner)).
- Every field of the record is true of the run
  ([`FALSE_RECORD`](#runner)). It records each recipe's environment as an
  RFC 3987 IRI that it can recreate at its version
  ([`UNRECREATABLE_ENVIRONMENT`](#runner)), and should let someone see what
  that environment holds, as PROV for example.
- It runs only committed code. It runs each recipe in a checkout of a
  commit, the repository's own working tree or one it makes for the run (a
  git worktree, say), and refuses to run while that checkout has changes
  other than the records and results it writes itself, each result's bytes
  the recorded ones ([`UNCOMMITTED_CHANGES`](#runner)). Changes outside
  that checkout don't stop it: a runner that runs in a checkout of its own
  while the working tree has changes writes the results and records into the
  working tree, and they are committed in a commit that has the commit they
  name in its history (below). It runs each recipe in its analysis's
  directory in that checkout ([`WRONG_WORKING_DIRECTORY`](#runner)).
- It builds no result of an analysis from a commit (§7)
  ([`REBUILT_FROM_COMMIT`](#runner)), and builds no output that reads such a
  result while it is `missing` or `stale` or its bytes can't be got or
  aren't the recorded ones ([`STALE_INPUT`](#runner)). Any other result it
  reads may be stale; what it builds from it is then stale too (*When a
  result is unchanged*, below).

A checker sees much of a breach afterwards: a result with no record is
`missing`, and bytes that aren't the recorded ones are `absent`. Enforcing
[`UNDECLARED_READ`](#runner) is the runner's choice (§5).

A record names the commit its recipe ran from, so it is committed in a later
commit. That commit adds only records and results, so it makes none of the
results whose records it adds stale. Branches that hold records SHOULD be
merged, not squashed or rebased, so that the commit each record names stays
in their history.

### When a result is unchanged

A record guarantees what its result was made from at the commit it names,
and nothing beyond that commit. At a later commit a result is **unchanged**
if, since that commit, nothing has changed in ([`STALE_RESULT`](#check)):

- its output's declaration: its recipe's command, its inputs and their order
  (`{inputs}` passes them in that order), its decisions, in any order (each
  reaches the recipe by name), and its format;
- the options its decisions select: a result is stale in its universe if any
  of its decisions selects a different option there than at the commit its
  record names;
- the content of its inputs, never what stands in for it;
- the results it reads. A result made from a stale one is stale, and once that
  one is rebuilt, it is unchanged again if the rebuilt bytes are the same.

Otherwise it is **stale**. Nothing else counts: editing a finding, a
description or another output leaves a result unchanged, unless the edit
changes something listed above (an `astra.yaml` named as an input, or an
output whose results it reads, say). The code, through the commit, and the
environment are recorded but not compared: a change to either shows only when
the recipe is run again and makes other bytes. An unchanged result suggests,
but doesn't guarantee, that the recipe would make it again. In the analysis
of §2, selecting `random_forest` in the universe `svm` makes `accuracy#svm`
stale, and `comparison` with it, while editing the finding leaves both
unchanged. Editing `src/train.py` leaves both unchanged too, but once
`accuracy#svm` is made again with other bytes, `comparison` is stale until it
is rebuilt. How a checker finds this out is the tooling's choice.

### Statuses

A checker gives every planned result two statuses ([check](#check)): one for
its record, `unchanged`, `stale`, or `missing` when it has no valid record
where its address says; and one for its bytes, `present` when the bytes at
its default place have its record's hash and size, `absent` otherwise. A
result of an analysis from a commit that no recipe reads gets only the first
(below). Outside a git repository ([`NOT_IN_REPOSITORY`](#validator)), every
planned result is `missing`. Since the bytes can be kept elsewhere, `absent` is not an error. A
tool may report more about bytes that are `absent`, such as other bytes at
the default place, but their status is `absent`.

A result with two names gets its statuses at each place. A checker reads
records only through planned results: a record at no planned result's place
gets no status, and no check rule applies to it.

Evidence citing a result gets the status of that result's record
([`STALE_EVIDENCE`](#check)), the record at the place of the result's name
along the `artifact`'s declarations, from the analysis the result belongs
to: evidence citing `stage.inner.out#u1` reads the record of
`stage.inner.out`, not of `inner.out`. Where those declarations give none of
the result's names, as for a stage's evidence citing its own output pinned
to an import of its parent's universe, the evidence gets the worst status of
the records at the result's names. An `artifact` that is pinned, or that
names an output built once, names exactly one result. An `artifact` that
names an output built per universe without a pin cites that output's
results in each of the root's universes where it is active and its analysis
is built. The evidence gets the worst of their record statuses: `missing`,
then `stale`. If there are none, it is `missing`. A check covers the
evidence of the analysis it is run on.

The results of an analysis from a commit that are read or cited get their
record status (`unchanged`, `stale`, `missing`) by the same rules, through
their records at the declared commit. Only those a recipe reads get a bytes
status ([`ABSENT_RESULT`](#check)), from what git holds at the declared
commit (§7).

## 9. Conformance

This section is the rule catalogue: the only place this specification states
a rule that a tool checks or keeps. The layers are those of §2.

**The rule is always what must (or should, or may) hold. What you get when it
is broken is always in a column of its own.** This is true in every layer:

- **Rule:** one sentence saying what holds in a conforming file, record or
  run. It is in the present tense, and its subject is what the rule is about
  ("A declaration has …", "Every pin names …", "No output …"). It never says
  what happens when it is broken.
- **Level:** `MUST`, `SHOULD` or `MAY` (RFC 2119), applied to that sentence,
  and `MAY` only in the runner table.
- **Code:** names what is wrong when the rule is broken. It is what a tool
  reports.
- **Source:** every source of the rule, as plain comma-separated tokens:
  the RFCs it comes from, and the section of this specification that
  explains it.

In the Source column, a number is an ASTRA RFC:
[0003](https://github.com/LightconeResearch/astra-spec/blob/main/rfcs/0003-cross-universe-artifact-references.md),
[0004](https://github.com/LightconeResearch/astra-spec/blob/main/rfcs/0004-composition.md),
[0005](https://github.com/LightconeResearch/astra-spec/blob/main/rfcs/0005-result-provenance-and-layout.md),
[0006](https://github.com/LightconeResearch/astra-spec/blob/main/rfcs/0006-data-inputs.md) or
[0007](https://github.com/LightconeResearch/astra-spec/blob/main/rfcs/0007-analyses-in-other-repositories.md),
followed by its section where one is given, as in `0005 §1`; two sections
of one RFC are written with its number each time, as in `0005 §1, 0005 §3`.
`tidy-up` is the draft RFC *Settling the schema for v0.1*, `main` a rule of
the specification before version 0.1,
[`#73`](https://github.com/LightconeResearch/astra-spec/pull/73) a pull
request of the specification's repository, and a bare `§n`, with no RFC
number before it, a section of this specification. In a cell, the tokens are
plain text, never code spans.

What breaking a rule leads to depends on the layer:

| Layer | When a rule is broken |
|---|---|
| parse, schema, validator | A broken `MUST` is reported as an **error** and makes the file invalid (a checker reports a record's as a reason of [`INVALID_RECORD`](#check)); a broken `SHOULD` is reported as a **warning**, and the file stays valid |
| check | A broken `MUST` is reported as an **error** and a broken `SHOULD` as a **warning**. Nothing fails, and **the result gets a status**, given in the check table's extra column, *Status when broken* |
| runner | A runner that breaks a `MUST` doesn't conform. It runs no recipe while `UNCOMMITTED_CHANGES` would be broken, and builds no output while `STALE_INPUT` would be, and when it refuses for either it reports the code. `UNDECLARED_READ` binds the recipe: breaking it leaves the analysis valid, and a runner that enforces it fails the recipe and reports the code |

The check layer is the only one laid out differently, with that extra
column, because breaking one of its rules changes what a result is. A parse,
schema or validator rule decides whether a file is valid, and only through
its `MUST`s.

A `MAY` row states what a tool may do. Leaving it out breaks nothing and
makes no tool non-conforming. The code is what a tool that does it reports.
Only the runner table, whose rules are about a tool's own actions, can have
`MAY` rows.

**What is checked.** A tool reports every rule broken, except in the cases
below, and the list is closed. In each case another broken rule leaves what a
rule is about undetermined, so the rule isn't checked and isn't reported. Each
case starts from a broken `MUST`. So a rule left unchecked never makes an
invalid analysis valid, or a `missing` result anything else: it changes only
which codes are reported. Two rules whose subjects are both determined are
both reported, even when one edit fixes both.

1. **A file that can't be read.** A file that breaks a parse rule is checked
   no further. A file whose `spec_version` is missing or malformed isn't
   checked by [`UNSUPPORTED_SPEC_VERSION`](#validator): it is checked against
   the validator's own schema (§1). A file whose well-formed `spec_version`
   breaks `UNSUPPORTED_SPEC_VERSION` isn't checked by the schema layer.
2. **A file that isn't a valid document.** A file that breaks a parse or
   schema rule, or [`UNSUPPORTED_SPEC_VERSION`](#validator), isn't checked by
   the validator layer, and its declarations aren't followed. Its analysis is
   undetermined (4).
3. **A declaration that can't be read.** On a declaration whose own analysis
   can't be got, because it breaks
   [`DECLARATION_OUTSIDE_REPOSITORY`](#validator) or
   [`COMMIT_NOT_FOUND`](#validator), or because a commit that analysis is
   read from can't be got ([`REMOTE_UNREACHABLE`](#validator), §7), neither
   [`MISSING_DECLARED_ANALYSIS`](#validator) nor
   [`DECLARED_ANALYSIS_INVALID`](#validator) is checked. On one that breaks
   `COMMIT_NOT_FOUND`, or whose own `commit` can't be got,
   [`COMMIT_NOT_ANCESTOR`](#validator) isn't checked either. Its analysis is
   undetermined (4), and so is the analysis of a declaration that breaks
   `MISSING_DECLARED_ANALYSIS`.
   `DECLARED_ANALYSIS_INVALID` isn't checked on an analysis from a commit
   whose file breaks [`UNSUPPORTED_SPEC_VERSION`](#validator). Where
   `REMOTE_UNREACHABLE` is reported on a declaration for a commit further in
   (§7), `DECLARED_ANALYSIS_INVALID` isn't checked on that declaration, and
   the analysis that couldn't be got is undetermined. The analyses read on
   the way to it are not: their declarations' `MISSING_DECLARED_ANALYSIS`,
   and addresses into them such as `upstream.summary#u1`, are still checked.
4. **An undetermined analysis.** No validator rule is checked in its file. In
   the files that declare it, nothing reached through that declaration is
   checked: no address through it, by
   [`UNRESOLVED_ADDRESS`](#validator) or by any rule on what the address
   would name, no [`MISSING_DECISION`](#validator) for its decisions, and no
   [`RESULT_IN_TWO_PLACES`](#validator) for a name through it.
5. **A name that names nothing.** An address that breaks
   [`UNRESOLVED_ADDRESS`](#validator), and an option that breaks
   [`UNKNOWN_OPTION`](#validator), name nothing, and no rule is checked on
   what they would name. That leaves out `UNKNOWN_OPTION` under such an
   address, the pin rules ([`UNKNOWN_PIN_UNIVERSE`](#validator) and
   [`PIN_INACTIVE`](#validator)), and
   [`NOT_BUILT_IN_UNIVERSE`](#validator),
   [`UNDRIVEN_DECLARATION`](#validator), [`INPUT_NOT_BUILT`](#validator),
   [`OUTPUT_CYCLE`](#validator) and [`DUPLICATE_ELEMENT`](#validator)
   through it. A pin that breaks `UNKNOWN_PIN_UNIVERSE`, or that names an
   import that names nothing or whose address runs through an undetermined
   analysis (4), names no universe: it builds none, and neither
   `PIN_INACTIVE` nor a rule on the universe being built (§7) is checked
   for it. A selection that names nothing isn't checked by
   [`INACTIVE_DECISION`](#validator),
   [`MISSING_REQUIRED_OPTION`](#validator),
   [`INCOMPATIBLE_OPTIONS`](#validator) or
   [`EXCLUDED_OPTION_SELECTED`](#validator). A `requires` or
   `incompatible_with` entry that names nothing is ignored.
6. **An element whose activity is undetermined.** In a universe, a `when` is
   undetermined when one of its conditions names nothing (5), or tests a
   decision that the universe's selection leaves unset
   ([`MISSING_DECISION`](#validator)) or sets to an option that names
   nothing. Its element's activity in that universe is then undetermined.
   `MISSING_DECISION` and [`INACTIVE_DECISION`](#validator) aren't checked
   for such a decision, [`INPUT_NOT_BUILT`](#validator) and
   [`PIN_INACTIVE`](#validator) aren't checked for such an output, nor
   [`RESULT_IN_TWO_PLACES`](#validator) for its result, nor
   [`NOT_BUILT_IN_UNIVERSE`](#validator), [`UNDRIVEN_DECLARATION`](#validator)
   or `INPUT_NOT_BUILT` for what it reads or lists in `decisions`. Nor are
   those three or `RESULT_IN_TWO_PLACES` checked for a result planned only
   through it, for the `when` of an output whose result would be planned
   only through it, or in a universe built only through a pin in its
   `inputs`. Step 3 of the effective selection (§6) doesn't drop such a
   decision.
7. **A universe with no effective selection.** A universe has none when its
   `derived_from` breaks [`UNKNOWN_DERIVED_FROM`](#validator), or its chain
   breaks [`DERIVED_FROM_CYCLE`](#validator) or reaches a universe that has
   none. For it, [`MISSING_DECISION`](#validator),
   [`INACTIVE_DECISION`](#validator), [`MISSING_REQUIRED_OPTION`](#validator),
   [`INCOMPATIBLE_OPTIONS`](#validator),
   [`EXCLUDED_OPTION_SELECTED`](#validator),
   [`NOT_BUILT_IN_UNIVERSE`](#validator),
   [`UNDRIVEN_DECLARATION`](#validator), [`INPUT_NOT_BUILT`](#validator) and
   [`RESULT_IN_TWO_PLACES`](#validator) aren't checked, and
   [`PIN_INACTIVE`](#validator) isn't checked for a pin naming it, directly
   or through an import.
   [`UNRESOLVED_ADDRESS`](#validator), [`UNKNOWN_OPTION`](#validator),
   [`DUPLICATE_ELEMENT`](#validator) and [`LOOPING_KEY`](#validator) are
   still checked on its own `decisions`. Driving (§7) counts its own
   `decisions` in place of its effective selection.
8. **An input with no file.** An input that breaks
   [`MISSING_INPUT_FILE`](#validator) isn't checked by
   [`INPUT_NOT_TRACKED`](#validator).
9. **A result with no valid record.** A result that breaks
   [`MISSING_RECORD`](#check) isn't checked by [`INVALID_RECORD`](#check),
   [`MISPLACED_RECORD`](#check) or [`MISSING_RECORD_INPUTS`](#check). One
   whose record breaks `INVALID_RECORD` isn't checked by the last two.
   [`STALE_RESULT`](#check) isn't checked for a result that is `missing`.
10. **A key that loops.** [`LOOPING_KEY`](#validator) is judged on a key's
    declarations up to the first that doesn't resolve or whose analysis is
    undetermined (4, 5). A key that loops still names its decision, if it
    resolves, and the rules on selections check it, but it drives no
    declaration (§7), and no rule counts it as going through one.
11. **An analysis outside a repository.** Where the root breaks
    [`NOT_IN_REPOSITORY`](#validator), no other validator rule is checked
    and its declarations aren't followed, so only its own `astra.yaml` is
    checked, by the parse and schema rules.

**The catalogue as data.** The rules are extracted from this section into
`rules.json` (§10), so its tables are a format that tools parse, not only
text to read:

- **Subsections.** This section has four `###` subsections, `parse and
  schema`, `validator`, `check` and `runner`, in that order, and no others.
- **Rule tables.** A rule table is a table whose header has a Code column.
  Each subsection has exactly one, and no rule table stands outside them.
  Other tables, such as the check layer's statuses, are not read.
- **Columns** are found by the names in a rule table's header: Code, Level,
  Rule and Source, with Layer in the parse and schema table and Status when
  broken in the check table, each once, and no others.
- **Rows.** Each row is one rule, with one cell per column and none empty.
  Its Code is one code span holding a capital letter, then capitals, digits
  and underscores (`[A-Z][A-Z0-9_]*`), and no other row has it. Its Layer is
  `parse` or `schema`, and its Level `MUST`, `SHOULD` or, in the runner table
  only, `MAY`. Its Rule is one sentence: as the cell reads once rendered,
  outside its code spans, no `.`, `?` or `!` is followed by white space,
  even after a closing bracket or quote. Its Rule uses no RFC 2119 keyword in
  capitals of another level, in its text, in a code span, or as the Rule cell
  reads once rendered (`MU*ST*` reads as `MUST`). Its Source is plain text:
  tokens separated by a comma and a space, each an RFC number with an
  optional `§n`, `tidy-up`, `main`, `#n` or `§n`.
- **Cells** are inline Markdown, as CommonMark with GFM tables reads them,
  and the published page shows each cell as the same text. They hold only
  text, code spans, emphasis, links and inline HTML.
  `rules.json` records a cell as Markdown rebuilt from what it parses to,
  with each link reduced to its text, so the rebuilt Markdown must parse the
  same way: an escape whose loss would change the cell, such as `\*` before
  text that would then become emphasis, is not allowed.

A table that breaks any of this is an error in this specification, and no
`rules.json` is made from it.

### parse and schema

| Code | Layer | Level | Rule | Source |
|---|---|---|---|---|
| `INVALID_SYNTAX` | parse | MUST | Every `astra.yaml` is a YAML 1.2 stream under the core schema, with at most one document, no tag but the core schema's, string keys and finite numbers, and every record is RFC 8259 JSON text in UTF-8 | 0005, tidy-up, §3 |
| `DUPLICATE_KEY` | parse | MUST | No map in an `astra.yaml` has two equal keys, and no object in a record has two equal names | 0003, 0004, tidy-up, §3, §4 |
| `INVALID_ID` | schema | MUST | Every map key matches its key's type where the map has one (an `id`, or an `address` in `Universe.decisions`); every `id`-typed value matches the `id` grammar | tidy-up, main, §3, §4 |
| `INVALID_REFERENCE` | schema | MUST | Every address, reference, option reference and condition, other than a key of `Universe.decisions`, matches its grammar | 0003, 0004 |
| `MISSING_FIELD` | schema | MUST | Every required field is present: in `astra.yaml`, `spec_version`, `outputs`, `Output.type`, `Output.format`, `Output.recipe`, `Recipe.command`, `Input.path`, `Decision.options`, `Insight.claim`, `Insight.evidence`, `TextQuoteSelector.exact` and `FragmentSelector.value`; in a record, `spec_version`, `address`, `content_hash`, `size`, `generated_by`, `Generation.commit`, `Generation.environment`, `Generation.runner`, `Environment.iri`, `Runner.id`, `Runner.version`, `RecordedInput.entry`, `RecordedInput.content_hash` and `RecordedInput.size` | 0004, 0005, 0006, tidy-up, main, §5 |
| `UNKNOWN_FIELD` | schema | MUST | Every field is one the schema defines | tidy-up, §10 |
| `EMPTY_COLLECTION` | schema | MUST | `outputs`, `Decision.options` and `Insight.evidence` each have at least one entry, and no list of strings in an `astra.yaml` is empty | 0004, tidy-up, main |
| `INVALID_DECLARATION_SOURCE` | schema | MUST | A declaration has exactly one of `path` and `url` | 0007 |
| `URL_WITHOUT_COMMIT` | schema | MUST | A declaration with a `url` has a `commit` | 0007 |
| `INVALID_IMPORT` | schema | MUST | An entry of `universes` with an `analysis` or a `universe` is an import, which has both and has neither `decisions` nor `derived_from` | §6, §7 |
| `INVALID_COMMIT` | schema | MUST | Every `commit` is a full commit id: 40 or 64 lowercase hexadecimal digits | 0007, tidy-up |
| `INVALID_PATH` | schema | MUST | Every declaration's and input's `path` is non-empty and doesn't start with `/` | 0004, 0006, tidy-up |
| `INVALID_EVIDENCE_SOURCE` | schema | MUST | Evidence has exactly one of `doi` and `artifact`, and has a `version` only with a `doi` | tidy-up |
| `WRONG_TYPE` | schema | MUST | Every value has the JSON type its field takes: a string, a number, an integer, a list or a map | tidy-up, §4, §10 |
| `DUPLICATE_ENTRY` | schema | MUST | No list of strings holds the same entry twice (`Output.inputs`, `Output.decisions`, `when`, `requires`, `incompatible_with`, `insights`, `tags`) | tidy-up, §4 |
| `INVALID_VALUE` | schema | MUST | Every value matches its pattern, enumeration or range: `Output.type` (one of `OutputType`), `Output.format`, `Evidence.doi`, `FragmentSelector.value` (a fragment identifier's characters), `FragmentSelector.conforms_to` (an IRI), `AnalysisDeclaration.url` (a remote URL), every hash, IRI and time, every `spec_version`, `size` ≥ 0, `Evidence.version` ≥ 1, `Resources.cpus` ≥ 0 and `Resources.gpus` ≥ 1 | 0005, 0007, tidy-up, main, #73 |

### validator

Every universe of every analysis of the stack is checked as §7 says.

| Code | Level | Rule | Source |
|---|---|---|---|
| `NOT_IN_REPOSITORY` | MUST | The folder of the analysis being validated is in the working tree of a git repository | §3 |
| `UNSUPPORTED_SPEC_VERSION` | MUST | Every `astra.yaml` in the stack has a `spec_version` whose minor version the validator has the schema of | 0007 §6, §1 |
| `UNRESOLVED_ADDRESS` | MUST | Every address resolves, through the declarations, to an element of the kind its field takes: an input or output in `Output.inputs`, a decision in `Output.decisions` and in `Universe.decisions` keys, a decision in conditions and option references, an output in `Evidence.artifact`, one of another analysis's universes in an import | 0004, §7 |
| `UNKNOWN_OPTION` | MUST | Every option named by a condition, option reference or selection is one of its decision's options | 0003, 0004 |
| `INVALID_INSIGHT_REF` | MUST | Every entry of `Option.insights` names a prior insight of the analysis | main |
| `UNDECLARED_TEMPLATE_REF` | MUST | Every brace in a recipe's `command` belongs to a `{{`, a `}}` or a placeholder, read from the left (§5), and every placeholder is `{inputs}`, `{output}`, or an `{inputs.<entry>}` or `{decisions.<entry>}` whose `<entry>` is an entry of its output's `inputs` or `decisions` exactly as written | 0003, 0004 |
| `AMBIGUOUS_ID` | MUST | No two elements that one field could resolve to share an id (an input and an output, both of which `Output.inputs` takes) | tidy-up, §4 |
| `CLASHING_RESULT_NAME` | MUST | No output shares its id with a declaration of the same analysis | tidy-up, §4, §8 |
| `DECLARATION_OUTSIDE_REPOSITORY` | MUST | A declaration's `path`, tidied (§3), doesn't go above the top of the root's working tree or, read at a commit, of the repository that holds that commit | 0004, 0007 §1 |
| `MISSING_DECLARED_ANALYSIS` | MUST | A declaration's `path` (at its `commit`, if it has one), or the top level of its `url`'s repository at its `commit`, holds an `astra.yaml` file, with no symlink on the way (§3) | 0004, 0007, §3 |
| `COMMIT_NOT_FOUND` | MUST | A declaration with a `path` and a `commit`, in a file not read from a remote, names a commit of the repository that holds the declaring `astra.yaml` | 0007, §3, §7 |
| `COMMIT_NOT_ANCESTOR` | SHOULD | A declaration with a `path` and a `commit` names an ancestor of the commit the declaration is in or, for a declaration read in the working tree, of HEAD of the repository that holds the declaring file | 0007, §3 |
| `REMOTE_UNREACHABLE` | MUST | Every commit the stack gets from a remote, through a `url`, a file read from a remote or a gitlink crossed at a commit, can be fetched from that remote or was kept from an earlier fetch | 0007 §6, tidy-up, §3, §7 |
| `DECLARED_ANALYSIS_INVALID` | MUST | An analysis from a commit, with everything it declares, is valid at that commit, `REMOTE_UNREACHABLE` aside | 0007, §7 |
| `MISSING_INPUT_FILE` | MUST | An input's `path` names a file (not a symlink, directory or gitlink), or something the validator recognises as standing in for one (§5) | 0006, §3 |
| `INPUT_NOT_TRACKED` | MUST | An input's file, or what stands in for it (§5), is in the index of the repository that holds the input's analysis or, read at a commit, in that commit's tree there, reached through no gitlink | 0006, §3 |
| `INPUT_IN_ANOTHER_ANALYSIS` | MUST | An input's file is inside its analysis's directory and outside every directory below it that holds an `astra.yaml` file of its own | 0006 |
| `RESERVED_PATH` | MUST | No input's `path` and no declaration's `path`, tidied (§3), is or lies in the `results/` or `.astra/` of an analysis of the stack | tidy-up, §3 |
| `UNKNOWN_DERIVED_FROM` | MUST | A universe's `derived_from` names a universe of the same analysis, never an import | 0003, §6 |
| `DERIVED_FROM_CYCLE` | MUST | No universe's chain of `derived_from` loops | 0003 |
| `MISSING_DECISION` | MUST | Every universe's effective selection sets every active decision of its analysis and of every analysis reached through a declaration that its analysis's universes drive | 0003, 0004, tidy-up, §6, §7 |
| `INACTIVE_DECISION` | MUST | A universe itself sets only decisions whose `when` holds in its effective selection | 0003 |
| `MISSING_REQUIRED_OPTION` | MUST | Every effective selection satisfies the `requires` of every option it selects | 0003 |
| `INCOMPATIBLE_OPTIONS` | MUST | Every effective selection satisfies the `incompatible_with` of every option it selects | 0003 |
| `EXCLUDED_OPTION_SELECTED` | MUST | No effective selection selects an excluded option | main, tidy-up |
| `DUPLICATE_ELEMENT` | MUST | No universe has two keys in its own `decisions` that spell one decision, or sets a decision it inherits under a key it doesn't inherit | tidy-up, §4, §6, §7 |
| `LOOPING_KEY` | MUST | No key in a universe's own `decisions` goes through a declaration that leads back to an analysis already on its chain, the universe's analysis included | main, §6, §7 |
| `NOT_BUILT_IN_UNIVERSE` | MUST | Every output built per universe of another analysis read without a pin by the output of a result planned in the universe being built, every output built per universe that the output of a planned result, or the root's evidence, pins to that universe, and every decision of another analysis that the output of a result planned there consumes, that an output's `when` consumes where the output's result would be planned if the `when` held, or that a decision's `when` or a constraint consumes in an analysis built there, belongs to an analysis built in that universe | 0004, §7 |
| `UNDRIVEN_DECLARATION` | MUST | In the file of the analysis whose universe is being built, every address by which the output of a result planned in that universe reads another analysis's output built per universe without a pin, by which the output of a planned result or the root's evidence pins another analysis's output built per universe to that universe, or by which the output of a result planned there, an output's `when` where the output's result would be planned if the `when` held, a decision's `when` or a constraint consumes another analysis's decision, has its chain of declarations driven by the file's universes (a key in their effective selections goes through every declaration of the address, or the last declaration's analysis has no decisions, the chain before it is driven, and that declaration leads back to no analysis already on the chain) | 0004, tidy-up, §7 |
| `INPUT_NOT_BUILT` | MUST | Every output read without a pin by the output of a result planned in the universe being built is active (its `when` holds) there | 0004 |
| `UNKNOWN_PIN_UNIVERSE` | MUST | Every pin in an `astra.yaml` names an entry of that file's `universes` or, where the file has no entry with its id, a universe of the analysis whose element its reference names | 0003, 0004, tidy-up, §4, §6, §7 |
| `PIN_INACTIVE` | MUST | Every pinned output is active in the universe it is pinned to | 0003 |
| `OUTPUT_CYCLE` | MUST | No output depends on itself, directly or through others | 0004 |
| `RESULT_IN_TWO_PLACES` | SHOULD | No planned result has two names: its output's analysis is reached through at most one chain of driven declarations from the analysis the result belongs to (§8) | main, §7, §8 |

### check

Read this table like the others: **the Rule column says what must hold**.
The extra column, **Status when broken**, is the status a result, or evidence
citing it, gets when the rule doesn't hold. A result for which every rule
holds is `unchanged` and `present`.

A record is a document, read by the parse and schema rules (§3). A checker
doesn't report a record's breach of one of them as an error of its own: the
record breaks `INVALID_RECORD`, so its result is `missing`, and the checker
reports `INVALID_RECORD` with each code the record breaks as its reason, the
parser's (`INVALID_SYNTAX` or `DUPLICATE_KEY`) or the one `rules.json` gives
the schema error (§10).

**Statuses.** A checker gives every planned result two statuses, one for its
record (`unchanged`, `stale` or `missing`) and one for its bytes (`present`
or `absent`). A result of an analysis from a commit that no recipe reads has
only the first. A result with two names has its statuses at each place.
Evidence citing a result gets that result's first status, at the name its
`artifact`'s declarations give or, where they give none of its names, the
worst at its names (§8). Evidence citing an output built per universe
without a pin gets the worst first status of that output's results
(`missing`, then `stale`), and `missing` when there are none.

| Status | Means |
|---|---|
| `unchanged` | The result has a valid record where its address says, and `STALE_RESULT` holds |
| `stale` | The result has a valid record where its address says, and `STALE_RESULT` doesn't hold. The checker says what changed |
| `missing` | The result has no valid record where its address says: `MISSING_RECORD`, `INVALID_RECORD` (including a record that breaks a parse or schema rule), `MISPLACED_RECORD` or `MISSING_RECORD_INPUTS` doesn't hold; or the root is outside a git repository (`NOT_IN_REPOSITORY`) |
| `present` | The bytes at the result's default place hash to the record's `content_hash` and have its `size` |
| `absent` | Anything else is at the default place, nothing, a stand-in or other bytes included |

**Rules.**

| Code | Level | Rule | Status when broken | Source |
|---|---|---|---|---|
| `MISSING_RECORD` | MUST | Every planned result has a record at `.astra/records/{universe}/{name}.json` (or `{name}.json` for an output built once), for each of its names, in the analysis it belongs to | `missing` | 0005 §1 |
| `INVALID_RECORD` | MUST | The record at each planned result's place breaks no parse rule, states a `spec_version` whose minor version has a record schema or is greater than the checker's, and breaks no schema rule against that minor version's record schema, or against the open variant when that minor version is greater than the checker's | `missing` | 0005 §2, tidy-up, §3, §8 |
| `MISPLACED_RECORD` | MUST | The record at each planned result's place has, as its `address`, the address that place is worked out from | `missing` | 0005 §1 |
| `MISSING_RECORD_INPUTS` | MUST | The record at each planned result's place has exactly one `inputs` item for each entry its output lists at the commit the record names, matched by `entry`, and no other item (their order carries no meaning) | `missing` | 0005 §2 |
| `STALE_RESULT` | MUST | Since the commit in a result's record, nothing has changed in its output's declaration (command, inputs and their order, decisions, format), the options its decisions select in its universe, the content of its inputs, never what stands in for it, or the results it reads | `stale` | 0005 §4 |
| `ABSENT_RESULT` | SHOULD | Every result's recorded bytes are at its default place | `absent` | 0005 §1 |
| `STALE_EVIDENCE` | MUST | Every evidence citing a result cites an unchanged one | the cited result's status; without a pin on an output built per universe, the worst of its results' (`missing`, then `stale`) | 0005 §5 |

The results of an analysis from a commit that are read or cited get their
record status (`unchanged`, `stale`, `missing`) by the same rules, through
their records at the declared commit. Only those a recipe reads get a bytes
status (`ABSENT_RESULT`), from what git holds at the declared commit (0007
§4–5).

### runner

| Code | Level | Rule | Source |
|---|---|---|---|
| `UNRECORDED_RESULT` | MUST | A runner writes a record for every result it makes, at the place of each of its names in the analysis the result belongs to, and writes the bytes to their default places | 0005 §1, 0005 §3 |
| `FALSE_RECORD` | MUST | Every field of a record a runner writes is true of the run it records: the commit the recipe ran from, the hash and size of what it read and of what it made, the environment it ran in, the runner and its version, and the times | 0005 §2, 0005 §3 |
| `UNRECREATABLE_ENVIRONMENT` | MUST | A runner records each recipe's environment as an RFC 3987 IRI that it can recreate at its version | 0005 §3 |
| `UNCOMMITTED_CHANGES` | MUST | A runner runs each recipe in a checkout of a commit whose only changes are the records and results it writes itself, each result's bytes the recorded ones | 0005 §3, 0007 §2, 0007 §7 |
| `WRONG_WORKING_DIRECTORY` | MUST | A runner runs each recipe in the directory of the recipe's own analysis, in the checkout it runs in, even when another analysis drives it | 0004 §1, 0004 §5 |
| `NOT_AT_COMMIT` | MUST | A runner drives an analysis from a commit on exactly its files at that commit | 0007 §7 |
| `REBUILT_FROM_COMMIT` | MUST | A runner builds no result that belongs to an analysis from a commit, or to an analysis reached from it through declarations, and reads each of those results through its record at the commit that analysis is read at | 0007 §3, 0007 §7 |
| `STALE_INPUT` | MUST | A runner builds no output that reads a result belonging to an analysis from a commit, or to an analysis reached from it through declarations, while that result is `missing` or `stale`, or its bytes can't be got or aren't the recorded ones | 0007 §4, 0007 §5 |
| `UNDECLARED_READ` | SHOULD | A recipe reads the files inputs name, and other outputs' results, only through its output's inputs | 0005 §3, tidy-up |

A recommendation and a permission. Neither is a rule of its own, because
nothing can check them: a runner SHOULD let someone see what an environment
it recorded holds, and MAY enforce `UNDECLARED_READ`, with a sandbox say. §5
and §8 explain them.

## 10. Schema artefacts

The schema is written in [LinkML](https://linkml.io/), in
`src/astra/schema/`: `types.yaml` (the named types of §4), `analysis.yaml`
(the analysis document), `insight.yaml` (insights and evidence) and
`provenance.yaml` (the record). Their descriptions are the normative
definitions of the fields, published as the
[schema reference](elements/index.md). These artefacts are generated from
them (and `rules.json` also from §9), into `src/astra/schema/generated/`,
and each is published at `https://w3id.org/astra/`, its minor version (`0.1`
for every 0.1.x) and `/`, followed by its file name:

| File | URI | What it is |
|---|---|---|
| `analysis.schema.json` | `https://w3id.org/astra/0.1/analysis.schema.json` | the JSON Schema of `astra.yaml`, rooted at `Analysis` |
| `provenance.schema.json` | `https://w3id.org/astra/0.1/provenance.schema.json` | the JSON Schema of a record, rooted at `ProvenanceRecord` |
| `provenance.open.schema.json` | `https://w3id.org/astra/0.1/provenance.open.schema.json` | the same schema, open: it allows fields it doesn't define |
| `provenance.context.jsonld` | `https://w3id.org/astra/0.1/provenance.context.jsonld` | the JSON-LD context of a record |
| `rules.json` | `https://w3id.org/astra/0.1/rules.json` | the rule catalogue of §9, with the code of each JSON Schema error that makes an instance fail |

Each JSON Schema's `$id` is its URI. So the closed and open record schemas are
distinct resources, and so are the schemas of two minor versions, which a
checker can hold side by side. The patches of one minor version share each
URI: a patch release never changes what is valid (§1), so the URI names one
schema whichever patch's file a tool holds, and a tool keeps the latest. A
pre-release is `X.Y.Z` followed by `aN`, `bN` or `rcN`, such as `0.1.0rc1`.
It is a candidate for `X.Y.Z`: its URIs carry its whole version
(`https://w3id.org/astra/0.1.0rc1/analysis.schema.json`), and the documents it
checks state `X.Y.Z`. A JSON Schema's top level holds only standard JSON
Schema keywords, so that strict validators (such as Ajv) compile it, and the
version of the release it was generated from is in its `$comment`.

**The contract.** `analysis.schema.json` is the contract for `astra.yaml`: a
document breaks no schema rule exactly when a JSON Schema draft 2019-09
validator reports no error for it against this file. `provenance.schema.json`
is the contract for records in the same way. Both are closed: a field they
don't define is an error ([`UNKNOWN_FIELD`](#parse-and-schema)), and no
optional field takes `null`.

**The open variant.** `provenance.open.schema.json` differs from
`provenance.schema.json` only in allowing fields it doesn't define. A checker
reading a record of a greater minor version than its own validates the record
against it, and so ignores the fields that version adds
([`INVALID_RECORD`](#check)).

**The rule catalogue.** `rules.json` is derived from this specification and
the schema, never written by hand, so that every tool reports the same code
for the same error and words each rule the same way. It holds:

- `rules`: one entry per rule of §9, in §9's order. Each has its `code`;
  its `layer` (`parse`, `schema`, `validator`, `check` or `runner`); its
  `level` (`MUST`, `SHOULD` or `MAY`); and its `statement`, its `source`
  and, for a rule of the check layer, its `status`: the Rule, Source and
  Status when broken cells, as inline CommonMark with each link reduced to
  its text. A `status` is display text naming the status a result, or
  evidence citing it, gets when the rule is broken, not a status token.
- `errors`: the code of every keyword of the three JSON Schemas whose error
  can make an instance fail (*From an error to its code*, below), keyed by
  the keyword's absolute keyword location, as JSON Schema 2019-09 defines
  it: the schema's `$id`, `#`, and the JSON Pointer to the keyword once
  every `$ref` is resolved. So each key names its minor version, through
  `$id`. Each code is a schema-layer rule's.
- `$comment`: the version of the release it was made from.

In the schema's sources, each constraint names the rule it enforces: a
pattern by its type or field, a class rule or an exactly-one-of by itself.
The keywords whose code never varies take a default: `required` outside such
a rule (`MISSING_FIELD`); `additionalProperties` (`UNKNOWN_FIELD`); `type`
(`WRONG_TYPE`); `minProperties` and `minItems` of 1 (`EMPTY_COLLECTION`);
`uniqueItems` (`DUPLICATE_ENTRY`); and `enum` and `minimum`
(`INVALID_VALUE`). An abridged `rules.json`:

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
      "source": "0007, tidy-up",
      "statement": "Every `commit` is a full commit id: 40 or 64 lowercase hexadecimal digits"
    },
    {
      "code": "ABSENT_RESULT",
      "layer": "check",
      "level": "SHOULD",
      "source": "0005 §1",
      "statement": "Every result's recorded bytes are at its default place",
      "status": "`absent`"
    }
  ]
}
```

**From an error to its code.** A parse code is reported for the whole file,
and [`UNSUPPORTED_SPEC_VERSION`](#validator) at `/spec_version`. A schema
error is reported with the code that `errors` gives its keyword's absolute
keyword location, at the instance location where it fails; an error on a key
is reported at its map, naming the key, and an unknown field at its object,
naming the field. Only the failures that make the document fail are
reported, not those inside an `if` or a `not`, or inside a branch of a
combinator that doesn't fail. So any JSON Schema 2019-09 validator gives the
same set of pairs of an instance location and a code.

A checker maps a record's errors the same way, through the record schema it
reads the record by, closed or open. It doesn't report them as errors of
their own: it reports [`INVALID_RECORD`](#check) for the record's result, with
the code of each error as its reason, and with the parser's code
([`INVALID_SYNTAX`](#parse-and-schema) or
[`DUPLICATE_KEY`](#parse-and-schema)) for a record that fails at parse (§3).

**RDF.** A record's RDF is what the
[JSON-LD 1.1](https://www.w3.org/TR/json-ld11-api/) toRdf algorithm gives for
it, with `provenance.context.jsonld` supplied as its context (a record carries
no `@context`), plus each node's class URI as its `rdf:type`: the root node
(the record's top-level object), each item of `inputs` and the `environment`
are `prov:Entity`, `generated_by` is a `prov:Activity`, and the `runner` a
`prov:SoftwareAgent`. The context maps a record's terms onto
[W3C PROV-O](https://www.w3.org/TR/prov-o/), with ASTRA's own, where PROV has
none, in the `https://w3id.org/astra/` namespace. It writes every IRI in full,
and no term carries JSON-LD 1.1's prefix flag, so an `iri` is its node's `@id`
exactly as written, whatever its scheme (`prov:env:1` too). It declares
`"@version": 1.1`, so a JSON-LD 1.0 processor, which would read a term as a
prefix, rejects it. Read this way, a record is PROV-O. The root node stands
for the result: a `prov:Entity` that `prov:wasGeneratedBy` its `generated_by`,
the run, which `prov:used` its inputs and its environment and
`prov:wasAssociatedWith` its runner. The root node's `address`,
`content_hash` and `size` describe the result, and its `spec_version` the
record. The run's `started` and `finished` are `prov:startedAtTime` and
`prov:endedAtTime`, typed `xsd:dateTime`, and the runner's `version` is
`schema:softwareVersion`. The schema doesn't check that a time's day exists
in its month (§4), so a time such as 30 February converts to an ill-typed
`xsd:dateTime`.

**The package.** The `astra-spec` Python package holds the LinkML sources and
these artefacts, as the namespace package `astra.schema`, read through
`importlib.resources`. It ships no Python models and has no dependencies.
