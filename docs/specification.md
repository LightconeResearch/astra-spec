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
such as `DIGIT`. Patterns are regular expressions, written as §4 says.

**Rules.** Section 9 states every rule that a tool checks or keeps, each
with a code, such as [`MISSING_DECISION`](#validator). The other sections
explain what the rules are about and link to their codes. The two
recommendations no tool can check are stated where they apply (§7, §8), and
the two duties of a runner that no tool can check after the runner's rules
(§9).

**Fields.** Every class of the format has a page in the
[schema reference](elements/index.md), generated from the schema, whose
descriptions define its fields. This specification links to those pages and
doesn't restate them.

**Terms.**

| Term | Meaning | Defined in |
|---|---|---|
| analysis | a directory with an `astra.yaml` | §3 |
| element | an input, output, decision, option, universe, declaration or insight of an analysis | §4 |
| address | the name of an element other than an option, through the declarations that lead to it; an option is named by an option reference (§4) | §4 |
| active | of a decision or an output, when every condition of its `when` holds | §5 |
| universe | a selection of one option for every active decision | §6 |
| effective selection | what a universe selects once `derived_from` is resolved | §6 |
| built per universe, built once | whether an output has one result in each universe where it is active, or one in all | §6 |
| pin | `#` and a universe id ending a reference, after its address, which reads the output in that universe | §4 |
| root | the analysis being validated or built | §7 |
| analysis stack | the root and every analysis it declares, directly or through others | §7 |
| driver, driven | in the root's universes, the root, and an analysis whose decisions they set through a declaration; the root is never driven | §7 |
| consuming | using another analysis's element by address, without driving it | §7 |
| analysis from a commit | a declared analysis as it was at a given commit | §7 |
| result | what a recipe made for one output in one universe, or once | §8 |
| record | the provenance record of one result | §8 |

**Versions.** Every analysis document and every record states, in
`spec_version`, the version of this specification it is written against, as
`MAJOR.MINOR.PATCH`: three non-negative integers without leading zeros, such
as `0.1.0` ([`INVALID_VALUE`](#parse-and-schema)). A patch release never
changes what is valid: a document or a record is valid under `X.Y.Z` exactly
when it is valid under every other `X.Y` version. So one schema of
`astra.yaml` and one of a record serve each minor version, and a validator
that reads one version of it reads them all
([`UNSUPPORTED_SPEC_VERSION`](#validator)). A validator reads each
`astra.yaml` by the version it states
([`UNSUPPORTED_SPEC_VERSION`](#validator)). What a minor or major version
promises about another is left to ASTRA's versioning policy.

## 2. Overview

ASTRA describes an analysis in two kinds of document:

- the **analysis document**, `astra.yaml`, which the analysis's authors
  write: what the analysis reads, makes and decides, the universes it makes
  its results in, the other analyses it uses, and its insights. Its root is
  [Analysis](elements/Analysis.md).
- the **provenance record**, one JSON file for each result, which the runner
  that made the result writes: what the result is and the run that made it.
  Its root is [ProvenanceRecord](elements/ProvenanceRecord.md).

Rules are enforced in five layers, set apart by what each one sees:

| Layer | Enforced by | Sees |
|---|---|---|
| **parse** | a YAML 1.2 loader under the core schema, plus §3's checks | one file's text |
| **schema** | the generated JSON Schema | one file's data |
| **validator** | a semantic validator | every `astra.yaml` of the analysis stack, and git; no results |
| **check** | a results checker | every `astra.yaml` of the analysis stack, now and at each record's commit, and git; records and results |
| **runner** | whatever runs recipes | its own actions |

Four roles conform to this specification:

- A **document**, an `astra.yaml` or a record, conforms when it breaks no
  parse or schema rule.
- A **validator** reads an analysis, every `astra.yaml` of its stack and git,
  and reports every parse, schema and validator rule the analysis breaks. An
  analysis is valid when it breaks none of their `MUST`s.
- A **checker** reads an analysis, every `astra.yaml` of its stack and git,
  and its records and results, and gives each planned result its statuses by
  the check rules (§8).
- A **runner** runs recipes and writes each result's bytes and record. It
  conforms when it keeps the runner rules.

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

An **analysis** is a directory with an `astra.yaml` at its top. Its recipes
run in that directory. The paths of its inputs and declarations are relative
to the folder of the `astra.yaml` and separate folders with `/` (§5, §7).

**`astra.yaml`** is YAML 1.2 ([YAML](https://yaml.org/spec/1.2.2/)), read
strictly, under the core schema only
([`INVALID_SYNTAX`](#parse-and-schema)):

- a `%YAML` directive other than `%YAML 1.2` makes the file invalid
  ([`INVALID_SYNTAX`](#parse-and-schema)). This is ASTRA's rule, not YAML's:
  YAML 1.2.2 accepts `%YAML 1.1`
  ([§6.8.1](https://yaml.org/spec/1.2.2/#681-yaml-directives)), so a tool
  checks the directive itself;
- a file holds at most one document ([`INVALID_SYNTAX`](#parse-and-schema)):
  a `---` after a document starts another, even with nothing after it. A file
  with no document, empty or holding only comments, is null, and fails as
  [`WRONG_TYPE`](#parse-and-schema);
- a file uses no anchor (`&base`) and no alias (`*base`), so an entry is
  written out in full ([`INVALID_SYNTAX`](#parse-and-schema));
- a node's tag, with its handle expanded, is one of the core schema's,
  `tag:yaml.org,2002:` followed by `str`, `int`, `float`, `bool`, `null`,
  `seq` or `map` (written `!!str` and so on), on a node of its kind: `!!seq`
  on a list, `!!map` on a map, `!!str` on any scalar, and each of the others
  on a scalar that its row of
  [YAML 1.2.2 §10.3.2](https://yaml.org/spec/1.2.2/#1032-tag-resolution)'s
  table takes. So `!!float 1` is the float 1, and `!!bool yes` is invalid.
  Any other tag, such as `!include`, `!!omap` or `!!timestamp`, makes the
  file invalid ([`INVALID_SYNTAX`](#parse-and-schema)). A node tagged `!` is
  a string, a list or a map, by its kind
  ([YAML 1.2.2 §6.9.1](https://yaml.org/spec/1.2.2/#691-node-tags)), so
  `! 12` is the string `"12"`;
- a key written twice in one map makes the file invalid
  ([`DUPLICATE_KEY`](#parse-and-schema)). Two keys are the same when they are
  equal YAML nodes, with the same tag and canonical form
  ([YAML 1.2.2 §3.2.1.3](https://yaml.org/spec/1.2.2/#3213-node-comparison)),
  so `a`, `'a'` and `"\x61"` are one key, and `1` and `"1"` are two;
- the core schema's only scalar types are strings, nulls, booleans, integers
  and floats. An integer or a float is a JSON number, unless JSON has no
  number for it, and a field's type is checked as JSON Schema checks it, so
  `2.0` is an integer. `yes`, `no`, `on` and `off` are strings, and valid ids.
  Timestamps and merge keys are not types: an unquoted date, such as
  `2026-10-26`, is a string, and `<<` is an ordinary key, so in an entry it is
  a field the schema doesn't define ([`UNKNOWN_FIELD`](#parse-and-schema));
- an untagged plain scalar that matches a row of
  [YAML 1.2.2 §10.3.2](https://yaml.org/spec/1.2.2/#1032-tag-resolution)'s
  table is that row's type, and any other is a string. So `true` and `false`
  are booleans and `null` is a null (as are the table's other spellings of
  them, such as `True` and `~`); `1e3`, `0x1F`, `-.5` and `010` (which is 10)
  are numbers; and `1_000`, `0b101`, `12:30` and `+.nan` are strings. An
  unquoted commit id of digits only is therefore an integer, and one of digits
  and a single `e` a float, as is a version such as `1.2`. They are quoted
  when meant as ids or strings, as in `"true": {}`, and so are commit ids and
  versions, as in `commit: "0dbb615a…"` and `spec_version: "0.1.0"`. A value
  of another type than its field takes fails as
  [`WRONG_TYPE`](#parse-and-schema).

**Records** are JSON ([RFC 8259](https://www.rfc-editor.org/rfc/rfc8259)),
well-formed ([`INVALID_SYNTAX`](#parse-and-schema)). A record is one JSON
value, checked by the same schema rules.

**Every document** holds only the fields its schema defines
([`UNKNOWN_FIELD`](#parse-and-schema)), each with the JSON type the field
takes ([`WRONG_TYPE`](#parse-and-schema)). An optional field without a value
is left out: no field takes `null`.

**Locations.** In an analysis's directory:

| Path | Holds |
|---|---|
| `astra.yaml` | the analysis document |
| `.astra/records/{universe}/{name}.json`, `.astra/records/{name}.json` | the records of the results that belong to the analysis, tracked in git (§8) |
| `results/{universe}/{name}.{format}`, `results/{name}.{format}` | the default places of those results' bytes (§8) |

Universes are declared only in `astra.yaml` (§6). A `universes/` directory
means nothing to ASTRA.

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
| [`id`](elements/Id.md) | `id` | every map key but those of `Universe.decisions`; also `Universe.derived_from`, `Option.insights` and the values of `Universe.decisions` |
| [`address`](elements/Address.md) | `address` | `Output.decisions`, the keys of `Universe.decisions` |
| [`reference`](elements/Reference.md) | `reference` | `Output.inputs`, `Evidence.artifact`, `ProvenanceRecord.address`, `RecordedInput.entry` |
| [`option_reference`](elements/OptionReference.md) | `option-reference` | `Option.requires`, `Option.incompatible_with` |
| [`condition`](elements/Condition.md) | `condition` | `Output.when`, `Decision.when` |
| [`commit_id`](elements/CommitId.md) | a full git commit id: 40 lowercase hexadecimal digits (SHA-1) or 64 (SHA-256) | `AnalysisDeclaration.commit`, `Generation.commit` |
| [`content_hash`](elements/ContentHash.md) | `sha256:`, then 64 lowercase hexadecimal digits | `ProvenanceRecord.content_hash`, `RecordedInput.content_hash` |
| [`spec_version`](elements/SpecVersion.md) | `MAJOR.MINOR.PATCH`, without leading zeros | `Analysis.spec_version`, `ProvenanceRecord.spec_version` |
| [`timestamp`](elements/Timestamp.md) | a UTC time to the millisecond, `YYYY-MM-DDThh:mm:ss.sssZ`, each field in its range; whether the day exists in its month, such as 30 February, isn't checked | `Generation.started`, `Generation.finished` |
| [`iri`](elements/Iri.md) | an IRI ([RFC 3987](https://www.rfc-editor.org/rfc/rfc3987)), never a CURIE: a scheme, `:`, then RFC 3987's characters, `%` only before two hex digits and at most one `#`; its structure (authority, port, IP literal) isn't checked | `Environment.iri`, `FragmentSelector.conforms_to` |

A value that doesn't take its type's form fails: a map key or an `id` as
[`INVALID_ID`](#parse-and-schema), any other address, reference, option
reference or condition as [`INVALID_REFERENCE`](#parse-and-schema), a commit
id as [`INVALID_COMMIT`](#parse-and-schema), and the others as
[`INVALID_VALUE`](#parse-and-schema).

### Patterns

The schema checks these forms, and the others it checks, with regular
expressions in the subset that ECMA-262 and Python's `re` share, so that a
validator in either language accepts the same values. Every `$` outside a
lookahead is written `$(?!\n)`, and every anchored pattern ends in one:
Python's `$` also matches before a final newline and ECMA-262's doesn't, so
without the lookahead `"a\n"`, which a YAML block scalar gives, would be an
`id` in Python and not in JavaScript. For the same
reason no pattern uses `.`, `\s`, `\S`, `\d`, `\w` or `\b`, which the two
define differently (Python's `.` matches `\r`, and its `\s` includes
U+001C–U+001F). Patterns use explicit classes instead: `[0-9]` for a digit,
`[^\x00-\x20\x7f]` for a character other than an ASCII space or control (one
outside U+0000–U+0020 and U+007F), `[^\x00-\x1f\x7f]` for any character but
an ASCII control, and `[^\x00-\x20\x7f-\x9f]` and `[^\x00-\x1f\x7f-\x9f]` for
the same two that also leave out the C1 controls (U+0080–U+009F).
This specification writes patterns in a short form, for readability; the
schema holds them in full.

Above U+007F a class leaves out only what it names, so these fields take
characters that aren't visible:

- `Option.excluded` and `AnalysisDeclaration.url` take `[^\x00-\x20\x7f]`,
  and `FragmentSelector.value` takes it less ``"#<>[\]^`{|}`` and `%` (which
  it takes only to start a percent-encoding). Each admits every character
  above U+007F: non-ASCII spaces (U+00A0, U+3000), format characters (U+200B,
  U+FEFF, U+202E), U+2028, U+2029 and the C1 controls.
- The suffix of an `Evidence.doi` takes `[^\x00-\x20\x7f-\x9f]` at either end
  and `[^\x00-\x1f\x7f-\x9f]` inside, which admit every character above
  U+009F: non-ASCII spaces anywhere, which a DOI may hold, and the characters
  that aren't graphic, which ISO 26324 leaves out of a DOI and no rule
  checks: format characters, U+2028, U+2029, private-use characters and
  noncharacters.
- An `iri` (`Environment.iri`, `FragmentSelector.conforms_to`) takes
  `[^\x00-\x20\x7f-\x9f]` less `<>"{}|\^`, the backtick, `%` and `#`
  (which it takes only to start a percent-encoding and a fragment) and the
  bidi formatting characters RFC 3987 §4.1 forbids (U+200E, U+200F,
  U+202A–U+202E). Above U+009F it admits non-ASCII spaces, the other
  format characters (U+200B, U+FEFF), U+2028 and U+2029, which RFC 3987
  allows, and characters it doesn't, such as noncharacters, and private-use
  characters outside a query.

### Ids and maps

Every element the author names is an entry of a map keyed by its id: inputs,
outputs, decisions, options, universes, declarations (`analyses`), prior
insights and findings. The id is written once, as the key
([`INVALID_ID`](#parse-and-schema)): `seed_42: {}`, never
`seed_42: {id: seed_42}` ([`UNKNOWN_FIELD`](#parse-and-schema)). Ids are
unique within their map because keys are
([`DUPLICATE_KEY`](#parse-and-schema)), and the order of a map carries no
meaning. A map's entries are objects, except those of `Universe.decisions`,
each of which is the id of the option selected (`model: svm`)
([`WRONG_TYPE`](#parse-and-schema)). Lists hold only what is a list: an
insight's `evidence`, a record's `inputs`, and lists of strings. No list of
strings holds the same entry twice ([`DUPLICATE_ENTRY`](#parse-and-schema)),
so an output lists each of its inputs, decisions and conditions once.

Every id has the one grammar `id`, and no id is reserved: an address's kind
comes from the field it is written in, so an element can be called `inputs`.
Ids of different kinds can be the same, except where one field could resolve
to either: an input and an output never share an id, since `Output.inputs`
takes both ([`AMBIGUOUS_ID`](#validator)).

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

An address that doesn't resolve to an element of its field's kind breaks
[`UNRESOLVED_ADDRESS`](#validator), and an option that isn't one of its
decision's options breaks [`UNKNOWN_OPTION`](#validator). In
`feature_extraction/astra.yaml`, which declares `iris: {path: ..}`,
`iris.random_seed` is the decision `random_seed` of the analysis in the
parent directory, and `iris.iris_data` in `Output.inputs` is that analysis's
output `iris_data`.

A record's `address` is its result as the analysis the result belongs to
addresses it, and a recorded input's `entry` is an entry of `Output.inputs`
exactly as written (§8).

### Pins

A `reference` can end in `#` and a universe id, a **pin**: `f1_score#svm`. A
pin reads the output in that universe (§6, §7). `#` is never part of an id,
so the pin is unambiguous. A decision's address never takes a pin: the
entries of `Output.decisions` are addresses
([`INVALID_REFERENCE`](#parse-and-schema)), and so are the keys of
`Universe.decisions` ([`INVALID_ID`](#parse-and-schema)).

In YAML, `#` inside a token is literal, so `f1_score#svm` needs no quotes.
After a space it starts a comment: `- f1_score #svm` is the plain reference
`f1_score`, followed by a comment. Write a pin with no space before its `#`.

### Report addresses

A report on an analysis, written outside `astra.yaml` in whatever authoring
framework its authors choose, refers to the analysis's elements by address
([RFC 0002](https://github.com/LightconeResearch/astra-spec/blob/main/rfcs/0002-decouple-reports.md)):
`<id>` for an element of the analysis, `<declaration>.<id>` for an element of
a declared analysis, and so on, in the grammar above. Inputs, outputs,
decisions, universes, prior insights, findings and declared analyses are
addressable. How a report writes a reference, and which kind of element it
means, belongs to its framework, not to this specification.

## 5. The analysis

[Analysis](elements/Analysis.md) is the content of an `astra.yaml`. It has a
`spec_version` and at least one output ([`MISSING_FIELD`](#parse-and-schema),
[`EMPTY_COLLECTION`](#parse-and-schema)); everything else is optional. Most
elements also take a `label`, a short display name that is optional
everywhere, a `description` in free prose, and `tags`, keywords for grouping
and finding them.

### Inputs

An [Input](elements/Input.md) is a file committed with the analysis, named by
its `path`, relative to the folder of the `astra.yaml`. The path doesn't start
with `/` or `~`, separates folders with `/` (never `\`), has no `..` segment
and no ASCII control character (U+0000–U+001F, U+007F), and doesn't end in
`/` ([`INVALID_PATH`](#parse-and-schema)).

- It names one file ([`MISSING_INPUT_FILE`](#validator)). Data in many files
  is many inputs.
- The file is inside the analysis's directory and outside every analysis
  within it, a directory with an `astra.yaml` of its own
  ([`INPUT_IN_ANOTHER_ANALYSIS`](#validator)). Another analysis reads it by
  address (`iris.data`), not by a path.
- The path names the file itself, or something the tooling recognises as
  standing in for it ([`MISSING_INPUT_FILE`](#validator)). The file, or what
  stands in for it, is tracked in git ([`INPUT_NOT_TRACKED`](#validator)).
  Which stand-ins a tool recognises, and where it looks for them, is the
  tool's: the specification names none, and two tools may judge the same
  input differently. How a file's bytes are stored and got is the runner's,
  and every record names its runner (§8). Something standing in for the
  content isn't the content.

`astra.yaml` holds no hash of an input. The record of each result that reads
the input holds the hash of what it read (§8), so a change to the file makes
those results stale.

Data that isn't committed with the analysis, such as a download, a loader's
output or a query's answer, comes in through an output whose recipe gets it.
That output is built once, or per universe when it depends on a decision
such as which data release to use, and its record holds the hash of what came
back.

### Outputs

An [Output](elements/Output.md) is an artefact the analysis makes. It has a
`type`, one of [OutputType](elements/OutputType.md) (`metric`, `figure`,
`table`, `data`, `report`: [`INVALID_VALUE`](#parse-and-schema)), and a
`format` ([`MISSING_FIELD`](#parse-and-schema)). The `format` is how the artefact is
encoded, as a lowercase token, `^[a-z0-9][a-z0-9_.+-]*$`: the file extension
it is written with, without the leading dot, such as `png`, `csv` or
`parquet` ([`INVALID_VALUE`](#parse-and-schema)). Any token of that form is a
format. It is the extension of the result's default place (§8).

- `inputs` lists what the output is made from, in order: references (§4) to
  inputs and outputs of the analysis or of analyses it declares. A reference
  to an output can be pinned (§6). Their order counts, since `{inputs}`
  passes them to the recipe in that order.
- `decisions` lists the addresses of the decisions the output depends on: a
  different option for any of them can give a different result. Their order
  carries no meaning.
- `when` makes the output conditional (below).
- `recipe` says how the output is made (below).

No output depends on itself, directly or through others
([`OUTPUT_CYCLE`](#validator)).

### Recipes

A [Recipe](elements/Recipe.md) has a `command`, and the context it runs in:
`resources` ([Resources](elements/Resources.md)), the CPUs, memory, time,
disk and GPUs it asks for (`cpus` at least 0 and `gpus` at least 1:
[`INVALID_VALUE`](#parse-and-schema)), and `container`, an image name, which is pulled,
or the path of a Containerfile, which is built. `Analysis.container` is the
default container of the analysis's recipes. A recipe runs in its analysis's
directory.

The `command` is a POSIX shell command and a template. A runner substitutes
its placeholders before running it:

| Placeholder | Becomes |
|---|---|
| `{inputs.<entry>}` | the path of what an entry of the output's `inputs` names |
| `{decisions.<entry>}` | the id of the option selected for the decision an entry of the output's `decisions` names |
| `{inputs}` | the paths of all the output's inputs, in the order of `inputs`, separated by spaces |
| `{output}` | the path the result is written to |
| `{{`, `}}` | a literal `{`, `}` |

In `{inputs.<entry>}` and `{decisions.<entry>}`, `<entry>` is an entry of the
output's `inputs` or `decisions` exactly as written, dots and `#` included:
`{inputs.classification.accuracy#baseline}`, `{decisions.iris.random_seed}`.
Two pins of one output are two entries, each with its own placeholder. Any
other placeholder breaks [`UNDECLARED_TEMPLATE_REF`](#validator): one naming
an entry the output doesn't list, such as `{inputs.data}` when `data` isn't
among its `inputs`, or one of none of these forms, such as `{foo}`. A recipe
reads files and results only through its output's inputs
([`UNDECLARED_READ`](#runner)).

### Decisions and options

A [Decision](elements/Decision.md) is a choice the analysis makes, such as
which estimator to use, with the `rationale` for making it. Its `options`
hold at least one [Option](elements/Option.md)
([`EMPTY_COLLECTION`](#parse-and-schema)). A decision singles out none of its
options: each universe chooses which one is used (§6).

An option constrains every selection it is part of:

- `requires` lists options that are also selected whenever it is
  ([`MISSING_REQUIRED_OPTION`](#validator));
- `incompatible_with` lists options that are never selected together with it
  ([`INCOMPATIBLE_OPTIONS`](#validator)).

Both take option references (§4), so they can name an option of a declared
analysis's decision.

An option with an `excluded` reason is excluded: no effective selection
selects it ([`EXCLUDED_OPTION_SELECTED`](#validator)). It stays listed, so the
analysis records what it considered and why it ruled it out. The reason
contains a character other than an ASCII space or control, one outside
U+0000–U+0020 and U+007F ([`BLANK_EXCLUDED`](#parse-and-schema)), so a
reason made only of non-ASCII spaces, format characters or C1 controls still
counts (§4). `excluded: true` is not a reason
([`WRONG_TYPE`](#parse-and-schema)), while `excluded: no` or `off` is the
reason `no` or `off` (§3), so the option is excluded.

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
```

A universe selecting `correction.none` has neither `calibration_prior` nor
`calibrated_table`. It doesn't set an inactive decision itself
([`INACTIVE_DECISION`](#validator)) and needn't set it at all
([`MISSING_DECISION`](#validator)). An inactive output isn't built in that
universe: nothing reads it there without a pin
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
  (`10.`, digit runs joined by `.`, `/`, then a suffix with no control
  character and no ASCII space at either end:
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
quote is sought within the location: the FragmentSelector is `oa:refinedBy`
the TextQuoteSelector (§10).

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

`value` is read by the syntax `conforms_to` names. A tool that knows that
syntax may parse it; one that doesn't shows it as written. Whether `value`
follows the syntax, and whether the syntax fits the cited work or output,
isn't checked. The schema checks only its characters: `value` is non-empty
and holds no ASCII space or control character, none of ``"#<>[\]^`{|}``, and
`%` only before two hex digits; any other character is allowed
([`INVALID_VALUE`](#parse-and-schema)). `conforms_to` is an
[`iri`](elements/Iri.md) (§4, [`INVALID_VALUE`](#parse-and-schema)).

Evidence isn't built in a universe. Citing an output built per universe, it
may pin it, and should ([`UNPINNED_EVIDENCE`](#validator)): the claim is then
about one universe's result, and the pin says which. A pin on an output built
once is redundant ([`REDUNDANT_PIN`](#validator)). The pin names a universe as
one in `Output.inputs` does (§7), so a finding about results a driver builds
belongs in the driver's `astra.yaml`. Evidence citing a result is checked through
that result's record (§8).

## 6. Universes

### Declaring universes

A [Universe](elements/Universe.md) selects one option for every active
decision of its analysis and of every analysis it drives (§7). Universes are
the entries of `universes`, keyed by id, unique within their analysis
([`DUPLICATE_KEY`](#parse-and-schema)).

A universe's `decisions` map decisions to options
([DecisionSelection](elements/DecisionSelection.md)), as
`<decision>: <option>`, such as `model: svm`. A key is the id of a decision
of the analysis or, for a decision of an analysis the universe drives, its
address, `<declaration>.<decision>`, a flat key (§7). A value is the id of
one of that decision's options ([`UNKNOWN_OPTION`](#validator)).

`derived_from` names another universe of the same analysis
([`UNKNOWN_DERIVED_FROM`](#validator)), whose selection this one inherits, so
that it gives only the decisions it changes. No universe is derived from
itself, directly or through others ([`DERIVED_FROM_CYCLE`](#validator)).
`derived_from` says how two universes relate and makes neither special. A
universe's `label` and `tags` are its own: they are never inherited.

### The effective selection

A universe's **effective selection** is what it selects once `derived_from`
is resolved:

1. Without `derived_from`, it is the universe's own `decisions`.
2. With `derived_from`, it is the effective selection of the universe named
   there, with the universe's own `decisions` written over it.
3. An inherited selection of a decision that isn't active in the result is
   dropped, so a universe that switches a decision off needn't undo what it
   inherited for it.

The effective selection is held to everything a universe written in full is:

- it selects every active decision of its analysis and of every analysis it
  drives ([`MISSING_DECISION`](#validator)), so a universe that switches a
  decision on sets it;
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

### No privileged universe

No universe is privileged. There is no default universe, no default option
and no reserved universe id: every universe, and every relationship between
universes, is declared by the author. A universe called `baseline` is one
with that name and nothing more. Which option a reported result was made
with is said by a pin on the evidence citing it (§5).

### Built per universe or built once

An output is **built per universe** when it lists `decisions`, has a `when`,
or has an unpinned entry of `inputs` that names an output built per
universe. Any other output is **built once**: it has one result, the same in
every universe. Inputs carry no universe, and a pinned entry never makes an
output built per universe, since the pin fixes the universe it reads.

An output built once has no universe of its own. It lists no decisions, so
its recipe has no `{decisions.<entry>}` placeholder
([`UNDECLARED_TEMPLATE_REF`](#validator)), and a pin on it selects nothing
([`REDUNDANT_PIN`](#validator)).

An analysis with no decisions, whose outputs read only what is the same in
every universe, needs no universes. One with decisions, or with outputs built
per universe, but no universes has none of its own to build those outputs in.
That is expected when the root's universes drive it or it consumes a decision
(§7), and is otherwise warned about ([`NO_UNIVERSES`](#validator)).

### Which universe a reference reads

An unpinned entry of `inputs` reads its output in the universe being built.
A pinned one, such as `accuracy#svm`, reads it as built in the universe
`svm`, whichever universe is being built. Only an output takes a pin
([`PIN_ON_INPUT`](#validator)), and it is active in the universe it is pinned
to ([`PIN_INACTIVE`](#validator)). Which analysis's universe a pin names is
set out in §7 ([`UNKNOWN_PIN_UNIVERSE`](#validator)).

## 7. Composition

### Declarations

An analysis uses another by declaring it in `analyses`, keyed by the id it
addresses it by ([AnalysisDeclaration](elements/AnalysisDeclaration.md)). The
declared analysis's elements are then addressed through that id, as
`<declaration>.<element>` (§4). A declaration has exactly one of `path` and
`url` ([`INVALID_DECLARATION_SOURCE`](#parse-and-schema)), and may have a
`commit`, which a `url` needs ([`URL_WITHOUT_COMMIT`](#parse-and-schema)).

**`path`** is the directory of the declared analysis's `astra.yaml`, relative
to the folder of the declaring `astra.yaml`. It doesn't start with `/` or
`~`, separates folders with `/` (never `\`) and has no ASCII control
character; `..` segments are allowed ([`INVALID_PATH`](#parse-and-schema)).
It stays inside the repository of the root
([`DECLARATION_OUTSIDE_REPOSITORY`](#validator)) and holds an `astra.yaml`
([`MISSING_DECLARED_ANALYSIS`](#validator)). A declared analysis can be a git
submodule. A submodule that declares something outside its own repository,
such as its parent with `..`, can be validated and built only from a root
whose repository holds what it declares.

**`url`** is a remote that git fetches another repository from, in one of
git's two forms: `scheme://…` (`https://github.com/owner/analysis`,
`ssh://git@host/x.git`, `file:///srv/repo`) or scp-like `[user@]host:path`
(`git@github.com:owner/repo`). The declared analysis is the one at the top
level of that repository, at the declaration's `commit`. A bare word or a
local path (`a`, `owner/repo`, `../repo`) is not a `url`
([`INVALID_VALUE`](#parse-and-schema)): an analysis inside the root's
repository is declared by `path`, and another repository on this machine by
an explicit `file://` URL. A `url` holds no ASCII space or control character
([`INVALID_VALUE`](#parse-and-schema)), though git fetches a remote with a
space: a space is written `%20` in a `scheme://` URL, which git decodes. Git
doesn't decode the scp-like form, so an scp-like remote
`[user@]host:my dir/x` is written `ssh://[user@]host/~/my%20dir/x`. Whether
the URL leads to a valid analysis is the validator's to tell
([`REMOTE_UNREACHABLE`](#validator),
[`MISSING_DECLARED_ANALYSIS`](#validator),
[`DECLARED_ANALYSIS_INVALID`](#validator)).

**`commit`** is a full commit id ([`INVALID_COMMIT`](#parse-and-schema)): a
branch moves, a tag can be moved or name another commit in a fork or a
mirror, and a shortened id can become ambiguous as a repository grows. A
declaration with a `commit` declares an analysis from a commit (below).

The same directory is the same analysis, whichever analysis declares it and
by whatever id: it is read once, and each of its results is made at most
once, however many declarations reach it. Declarations by `path` alone can
form cycles, such as an analysis declared by its parent that
declares its parent with `..`, but outputs never depend on each other in a
cycle ([`OUTPUT_CYCLE`](#validator)). A declaration with a `commit` is never
part of a cycle, since a commit can only name earlier ones.

### The analysis stack

The **root** is the analysis being validated or built, and any analysis can
be the root. Its **analysis stack** is the root and every analysis it
declares, directly or through other declared analyses. A validator reads
every `astra.yaml` of the stack, each by the `spec_version` it states
([`UNSUPPORTED_SPEC_VERSION`](#validator)).

The universes being built are the root's. In them the root is the driver and
is never driven, even when a declaration in its stack leads back to it.
Another analysis's universe is used only where a pin names it. That analysis
is then its driver, and what is built there belongs to it (§8).

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
(`classification.classifier`, `stage.inner.d`). The analysis whose universes
set them is the **driver**, and the declared analysis is **driven** through
that declaration.

- Every universe of the driver sets every active decision of every analysis
  it drives ([`MISSING_DECISION`](#validator)).
- A declaration is driven by all of the driver's universes or by none
  ([`PARTIALLY_DRIVEN`](#validator)).
- An analysis reached through two driven declarations can have a decision
  set under either spelling (`stage.inner.d` or `inner.d`). Every spelling
  of one decision in a universe selects the same option
  ([`CONFLICTING_SELECTIONS`](#validator)).
- In the root's universes, a driven analysis's own universes don't set its
  decisions. A pin in its own file, or through an undriven declaration,
  still reads one of them (below). Each universe being built has one driver,
  the analysis whose universe it is.

Driving leaves an analysis able to stand alone, and consuming a decision ties
the outputs that use it to the decision's analysis. By convention, a
decision that matters to one analysis is driven, and one shared by several,
such as the seed of a whole stack, is consumed.

### The universe being built

A universe is named by its analysis and its id, since the same id can name a
universe in several analyses. When an analysis is built in one of its
universes, that universe is pushed through every analysis it drives: it is
the universe being built in all of them. An unpinned entry of `inputs` reads
its output in that universe, and a consumed decision has the option that
universe selects. So, wherever an output built per universe is read without
a pin, or a decision is consumed:

1. The analysis it belongs to is built in the universe being built
   ([`NOT_BUILT_IN_UNIVERSE`](#validator)). The analysis whose universe is
   being built is always built in it, so an analysis it drives can consume
   its decisions and read its outputs back through `..`, as
   `feature_extraction/astra.yaml` consumes `iris.random_seed` (§4).
2. In the file of the analysis whose universe is being built, each such
   address of another analysis goes through a declaration that the file's
   universes drive ([`UNDRIVEN_DECLARATION`](#validator)). Uses in other
   files come under the first rule alone.

An output built once has one result, so it is read without a pin from any
universe, through any declaration. And every output read without a pin, of
the analysis itself or of another, is active in the universe being built
([`INPUT_NOT_BUILT`](#validator)).

A pin `#u` names, when its reference goes through a driven declaration, the
universe `u` of the driver, and otherwise the universe `u` of the analysis
whose output it is, which for an output of the analysis itself is one of its
own universes ([`UNKNOWN_PIN_UNIVERSE`](#validator)). To read one of a driven
analysis's own universes, the driver declares the same directory a second
time, without driving that declaration:

```yaml
spec_version: "0.1.0"
analyses:
  inner: {path: stage/inner}            # the root's universes set inner.d
  inner_undriven: {path: stage/inner}   # never named in the root's universes
outputs:
  in_root_u1:
    type: metric
    format: json
    inputs: [inner.result#u1]           # the root's universe u1
  in_inner_v1:
    type: metric
    format: json
    inputs: [inner_undriven.result#v1]  # inner's own universe v1
universes:
  u1:
    decisions:
      inner.d: d1                       # a flat key: inner's decision d
```

Without a pin, `inner_undriven.result` would be read in the root's universe
through a declaration that the root's universes don't drive:

<!-- fragment: Analysis -->
```yaml
outputs:
  in_root:
    type: metric
    format: json
    inputs: [inner_undriven.result]     # UNDRIVEN_DECLARATION
```

What is built in a driver's universes belongs to the driver (§8).

### Analyses from a commit

A declaration with a `commit` names an **analysis from a commit**: the
declared analysis as it was at that commit. With a `url`, it is the analysis
at the top level of that repository at the commit. With a `path`, it is the
analysis at that path at the commit, which the repository has
([`COMMIT_NOT_FOUND`](#validator)) and which should be an ancestor of the
commit the declaration is in ([`COMMIT_NOT_ANCESTOR`](#validator)). It is
read from the local repository or, when the declaring analysis is itself read
from a remote, from that remote. Every rule of this specification applies to
an analysis from a commit as it is, with its files read at its commit.

**Identity.** The commit id, with the `path` for an analysis of the
declaring analysis's own repository, is the declared analysis's identity: two
declarations with the same commit and `path` name the same analysis. A URL
says only where to get it, so a fork or a mirror with the same commit gives
the same analysis.

**What is read.** An analysis from a commit is read from git at its commit,
and git checks everything read against the commit id. None of its code runs,
and no checkout is needed. Only these are read:

- the `astra.yaml` of the declared analysis and of every analysis it
  declares;
- the `astra.yaml` of a result's analysis at the commit the result's record
  names, to tell whether the result is unchanged (§8);
- the record of each result read or cited, and the records of the results it
  was made from;
- which files there are at a commit, and which differ between two commits,
  without their contents;
- the bytes of each result or input file that a recipe reads.

Where a tool keeps what it read is the tool's choice, and validators,
checkers and runners can work offline from what they kept. None of it is
part of the declaring analysis's code, and none of it is a change to the
declaring analysis's repository that stops a runner from running
([`UNCOMMITTED_CHANGES`](#runner)).

**Validity.** The declared analysis, with everything it declares, is valid
at its commit ([`DECLARED_ANALYSIS_INVALID`](#validator)), each `astra.yaml`
read by the `spec_version` it states. A commit's files never change, so
neither does the answer, and a validator can remember it for a commit it has
validated. A published analysis SHOULD declare only remotes its readers can
fetch. That isn't a `MUST`, since a remote can be private while the analysis
is being worked on, but a remote that can't be fetched, or doesn't have the
commit, is an error in the declaring analysis
([`REMOTE_UNREACHABLE`](#validator)).

**Use.** Unless it is driven, none of the recipes of an analysis from a
commit run, so the rules above let it give only its outputs in its own
universes, pinned (`upstream.summary#u1`), its outputs built once
(`upstream.stage.report`), and its inputs (`upstream.data`). Evidence cites
its results in the same way. An address that doesn't exist in the declared
analysis is an error in the declaring one
([`UNRESOLVED_ADDRESS`](#validator)). Whether the result it names is
recorded and unchanged is the checker's to tell (§8).

**Results.** A result of an analysis from a commit is read through its record
at the declared commit, in the analysis the result belongs to (§8), in that
analysis's repository. If the declared analysis itself declares an analysis
from a commit, that analysis's records are read in its own repository, at the
commit named for it. A result can be read only once its record is
committed, so the declaration names a commit that holds the records, `B`,
later than the commit their recipes ran from, `A`, which the records name.
The result is unchanged if nothing that [`STALE_RESULT`](#check) compares
changed between `A` and `B`, and the results it was made from are unchanged
too. Their content hashes are taken from their records, without their
bytes. When a recipe reads the result, the runner gets its bytes from what
the declared commit holds at the result's default place, or through
something there it recognises as standing in for them (§5), and they are
checked against the record. An input of the declared analysis read by
address is got from its `path` at the declared commit, or through what the
runner recognises as standing in for it (§5).

**Driving.** A driver's universes can drive an analysis from a commit, as any
declared analysis. Its recipes then run on exactly its files at the declared
commit ([`NOT_AT_COMMIT`](#runner)). Where the tool puts those files is the
tool's choice, and they aren't part of the declaring analysis's code. Which
environment the recipes run in is the runner's choice, as for any recipe, and
is recorded in the driver's records. Its outputs built once aren't built: like
the rest of its results, they are read through their records at the declared
commit ([`REBUILT_FROM_COMMIT`](#runner)). What the driver's universes build
belongs to the driver, and its records name the driver's commit, where the
declaration says which commit the driven analysis is from and, for a remote,
where to get it. A git submodule also records a URL and a commit, but only in
git, and its checkout can drift from them. A `url` and a `commit` fix them in
`astra.yaml`, so the declared analysis has the same identity whether it is
read or driven, and what a driver runs is the declared commit.

## 8. Results and records

### Results

A **result** is what a recipe made for one output in one universe, or once
for an output built once. The results an analysis's outputs and universes
call for are its **planned** results. An output plans no result in a universe
where it is inactive (§5).

A result belongs to the analysis whose universe it was built in. So what a
driven analysis builds in its driver's universes belongs to the driver. The
result of an output built once belongs to the analysis whose output it is. In
that analysis, the result's **name** is the output's id after the ids of the
declarations its universe is pushed through (`subanalysis1.output1`): driven
ones, never an undriven one, since a pin through an undriven declaration
names that analysis's own universe (§7). Its **address** is the name
followed, for a result built in a universe, by `#` and the universe's id
(`subanalysis1.output1#u1`). The address is the record's `address`.

### Where records and bytes go

In the analysis a result belongs to:

| | Built in the universe `{universe}` | Built once |
|---|---|---|
| Its record | `.astra/records/{universe}/{name}.json` | `.astra/records/{name}.json` |
| Its bytes, at their default place | `results/{universe}/{name}.{format}` | `results/{name}.{format}` |

Both are worked out from the result's address. A record is the record only
of the result its `address` names ([`MISSING_RECORD`](#check),
[`MISPLACED_RECORD`](#check)). The runner writes the bytes to their default
place ([`UNRECORDED_RESULT`](#runner)) and tells the recipe where to write
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

Records are tracked in git with the analysis, as its `astra.yaml` is, so they
can be read whether or not the bytes are there. The bytes needn't stay at
their default place ([`ABSENT_RESULT`](#check) is a `SHOULD`): a runner may
keep them elsewhere and leave something standing in for them (§5). Anything
else at the default place, something standing in for the bytes, other bytes
or nothing, leaves the result's bytes `absent` ([`ABSENT_RESULT`](#check)).

### What a record holds

A [ProvenanceRecord](elements/ProvenanceRecord.md) gives its `spec_version`,
the result's `address`, the `content_hash` and `size` (in bytes) of the
result's bytes, and the run of the recipe that made it, `generated_by`, a
[Generation](elements/Generation.md):

- `commit`: the full id of the git commit the recipe ran from, the driver's
  commit for what a driver's universes build (§7). It pins every file of the
  code and every `astra.yaml`: an analysis in a submodule through the commit
  the submodule is pinned at, and an analysis from a commit through its
  declaration's `commit`.
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
  IRI (RFC 3987) naming exactly the environment the recipe ran in, enough for
  its runner, at the version the record gives, to recreate it. It needn't
  resolve online: a `urn:` IRI or a scheme of the runner's own will do.
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
options of its decisions and its format are in the `astra.yaml` files at that
commit. The order of a record's fields carries no meaning: two records with
the same keys and values are the same record. A record holds only the fields
its `spec_version` defines. A checker reading a record of a newer version
than its own validates it against the open variant of the record schema,
which ignores the fields the checker doesn't know, rather than calling the
record `missing` ([`INVALID_RECORD`](#check), §10). Read as RDF (§10), a
record is W3C PROV-O.

Two records of one result with the same commit, inputs and environment, made
on two machines say, show whether the result reproduces: their
`content_hash` is the same.

### What a runner does

A runner writes a record for every result it makes, in the analysis the
result belongs to, and writes the bytes to their default place
([`UNRECORDED_RESULT`](#runner)). It runs only committed code: while the
repository has changes other than the results and records it writes, it
refuses to run ([`UNCOMMITTED_CHANGES`](#runner)). It records each recipe's
environment as an IRI that it can recreate at its version
([`UNRECREATABLE_ENVIRONMENT`](#runner)), and should let someone see what that
environment holds, as PROV for example. It builds an output only when every
result the output reads is `unchanged` and its bytes can be got and are the
recorded ones ([`STALE_INPUT`](#runner)). A recipe reads files and results
only through its output's inputs ([`UNDECLARED_READ`](#runner)): anything else
it uses is pinned by the commit or is part of the environment. A runner may
enforce this, with a sandbox say.

A record names the commit its recipe ran from, so it is committed in a later
commit. That commit adds only records and results, so it makes nothing
stale. The commit a record names stays in the history of every commit that
holds the record, so branches with records SHOULD be merged rather than
squashed or rebased.

### When a result is unchanged

A record guarantees what its result was made from at the commit it names,
and nothing beyond that commit. At a later commit a result is **unchanged**
if, since that commit, nothing has changed in ([`STALE_RESULT`](#check)):

- its output's declaration: its recipe's command, its inputs and their order
  (`{inputs}` passes them in that order), its decisions, in any order (each
  reaches the recipe by name), and its format;
- the options of its decisions;
- the content of its inputs, never what stands in for it;
- the results it reads. A result made from a stale one is stale, and once that
  one is rebuilt, it is unchanged again if the rebuilt bytes are the same.

Otherwise it is **stale**. Nothing else counts: editing a finding, a
description or another output leaves a result unchanged. The code, through
the commit, and the environment are recorded but not compared: a change to
either shows only when the recipe is run again and makes other bytes. An
unchanged result suggests, but doesn't guarantee, that the recipe would make
it again. In the analysis of §2, selecting `random_forest` in the universe
`svm` makes `accuracy#svm` stale, and `comparison` with it, while editing the
finding leaves both unchanged. How a checker finds this out is the tooling's
choice.

### Statuses

A checker gives every planned result two statuses ([check](#check)): one for
its record, `unchanged`, `stale`, or `missing` when it has no valid record
where its address says; and one for its bytes, `present` when the bytes at
its default place have its record's hash and size, `absent` otherwise. Since
the bytes can be kept elsewhere, `absent` is not an error. A tool may report
more about bytes that are `absent`, such as other bytes at the default place,
but their status is `absent`.

A checker reads records only through planned results: a record at no planned
result's place gets no status, and no check rule applies to it.

Evidence citing a result gets the status of the result's record
([`STALE_EVIDENCE`](#check)), through the record its address names: the
reference, pinned when the output is built per universe, names exactly one
result. A check covers the evidence of the analysis it is run on. The
results of an analysis from a commit that are read or cited are checked by
the same rules, through their records at the declared commit (§7).

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
| parse, schema, validator | A broken `MUST` is reported as an **error** and makes the file invalid; a broken `SHOULD` is reported as a **warning**, and the file stays valid |
| check | Nothing fails. The code is reported and **the result gets a status**, given in the check table's extra column, *Status when broken* |
| runner | The runner doesn't conform. Where a rule says the runner refuses, it reports the code |

The check layer is the only one laid out differently, with that extra
column, because breaking one of its rules changes what a result is. A parse,
schema or validator rule decides whether a file is valid, and only through
its `MUST`s.

A `MAY` row states what a tool may do. Leaving it out breaks nothing and
makes no tool non-conforming. The code is what a tool that does it reports.
Only the runner table, whose rules are about a tool's own actions, can have
`MAY` rows.

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
  only, `MAY`. Its Rule uses no RFC 2119 keyword in capitals of another
  level, in its text, in a code span, or as the Rule cell reads once rendered
  (`MU*ST*` reads as `MUST`). Its Source is plain text: tokens separated by a
  comma and a space, each an RFC number with an optional `§n`, `tidy-up`,
  `main`, `#n` or `§n`.
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
| `INVALID_SYNTAX` | parse | MUST | Every `astra.yaml` is a well-formed YAML 1.2 stream of at most one document under the core schema, with no `%YAML` directive other than 1.2, no anchor or alias and no tag but the core schema's, and every record is well-formed JSON | 0005, tidy-up, §3 |
| `DUPLICATE_KEY` | parse | MUST | Every key of a map is distinct: no two are equal YAML nodes, with the same tag and canonical form. (This makes the ids of inputs, outputs, decisions, options, insights, universes and declarations unique.) | 0003, 0004, tidy-up, §3, §4 |
| `INVALID_ID` | schema | MUST | Every map key matches its key's type (an `id`, or an `address` in `Universe.decisions`), and every `id`-typed value matches the `id` grammar | tidy-up, main, §4 |
| `INVALID_REFERENCE` | schema | MUST | Every address, reference, option reference and condition matches its grammar | 0003, 0004 |
| `MISSING_FIELD` | schema | MUST | Every required field is present: in `astra.yaml`, `spec_version`, `outputs`, `Output.type`, `Output.format`, `Input.path`, `Decision.options`, `Insight.claim`, `Insight.evidence`, `TextQuoteSelector.exact` and `FragmentSelector.value`; in a record, `spec_version`, `address`, `content_hash`, `size`, `generated_by`, `Generation.commit`, `Generation.environment`, `Generation.runner`, `Environment.iri`, `Runner.id`, `Runner.version`, `RecordedInput.entry`, `RecordedInput.content_hash` and `RecordedInput.size` | 0004, 0005, 0006, tidy-up, main |
| `UNKNOWN_FIELD` | schema | MUST | Every field is one the schema defines | tidy-up, §10 |
| `EMPTY_COLLECTION` | schema | MUST | `outputs`, `Decision.options` and `Insight.evidence` each have at least one entry | 0004, main |
| `INVALID_DECLARATION_SOURCE` | schema | MUST | A declaration has exactly one of `path` and `url` | 0007 |
| `URL_WITHOUT_COMMIT` | schema | MUST | A declaration with a `url` has a `commit` | 0007 |
| `INVALID_COMMIT` | schema | MUST | Every `commit` is a full commit id: 40 or 64 lowercase hexadecimal digits | 0007, tidy-up |
| `INVALID_PATH` | schema | MUST | A declaration's `path` is relative (no leading `/` or `~`), `/`-separated, with no backslash and no ASCII control character. An input's `path` is the same, and also has no `..` segment and doesn't end in `/` | 0004, 0006, tidy-up |
| `BLANK_EXCLUDED` | schema | MUST | An option's `excluded` reason is not blank | tidy-up |
| `INVALID_EVIDENCE_SOURCE` | schema | MUST | Evidence has exactly one of `doi` and `artifact`, and has a `version` only with a `doi` | tidy-up |
| `WRONG_TYPE` | schema | MUST | Every value has the JSON type its field takes: a string, an integer, a list or a map (so `excluded: true`, or a list where a map is expected, fails) | tidy-up, §4, §10 |
| `DUPLICATE_ENTRY` | schema | MUST | No list of strings holds the same entry twice (`Output.inputs`, `Output.decisions`, `when`, `requires`, `incompatible_with`, `insights`, `tags`) | tidy-up, §4 |
| `INVALID_VALUE` | schema | MUST | Every value matches its pattern, enumeration or range: `Output.type` (one of `OutputType`), `Output.format`, `Evidence.doi`, `FragmentSelector.value` (a fragment identifier's characters), `FragmentSelector.conforms_to` (an IRI), `AnalysisDeclaration.url` (a remote URL), every hash, IRI and time, every `spec_version`, `size` ≥ 0, `Evidence.version` ≥ 1, `Resources.cpus` ≥ 0 and `Resources.gpus` ≥ 1 | 0005, 0007, tidy-up, main, #73 |

### validator

| Code | Level | Rule | Source |
|---|---|---|---|
| `UNSUPPORTED_SPEC_VERSION` | MUST | Every `astra.yaml` in the stack has a `spec_version` the validator has the schema for (the file is then validated against that schema, by the schema layer) | 0007 §6 |
| `UNRESOLVED_ADDRESS` | MUST | Every address resolves, through the declarations, to an element of the kind its field takes: an input or output in `Output.inputs`, a decision in `Output.decisions` and in `Universe.decisions` keys, a decision in conditions and option references, an output in `Evidence.artifact` | 0004 |
| `UNKNOWN_OPTION` | MUST | Every option named by a condition, option reference or selection is one of its decision's options | 0003, 0004 |
| `INVALID_INSIGHT_REF` | MUST | Every entry of `Option.insights` names a prior insight of the analysis | main |
| `UNDECLARED_TEMPLATE_REF` | MUST | Every recipe placeholder is `{inputs}`, `{output}`, `{{`, `}}`, or an `{inputs.<entry>}` or `{decisions.<entry>}` whose `<entry>` is an entry of its output's `inputs` or `decisions` exactly as written | 0003, 0004 |
| `AMBIGUOUS_ID` | MUST | No two elements that one field could resolve to share an id (an input and an output, both of which `Output.inputs` takes) | tidy-up, §4 |
| `DECLARATION_OUTSIDE_REPOSITORY` | MUST | A declaration's `path` stays inside the repository of the root | 0004 |
| `MISSING_DECLARED_ANALYSIS` | MUST | A declaration's `path` (at its `commit`, if it has one), or the top level of its `url`'s repository at its `commit`, holds an `astra.yaml` | 0004, 0007 |
| `COMMIT_NOT_FOUND` | MUST | A declaration with a `path` and a `commit` names a commit the repository has | 0007 |
| `COMMIT_NOT_ANCESTOR` | SHOULD | A declaration with a `path` and a `commit` names an ancestor of the commit the declaration is in | 0007 |
| `REMOTE_UNREACHABLE` | MUST | A declaration's `url` can be fetched and has its `commit` | 0007 |
| `DECLARED_ANALYSIS_INVALID` | MUST | An analysis from a commit, with everything it declares, is valid at that commit | 0007 |
| `MISSING_INPUT_FILE` | MUST | An input's `path` names a file, or something the validator recognises as standing in for one (§5) | 0006 |
| `INPUT_NOT_TRACKED` | MUST | An input's file, or what stands in for it, is tracked in git | 0006 |
| `INPUT_IN_ANOTHER_ANALYSIS` | MUST | An input's file is outside every other analysis's directory | 0006 |
| `UNKNOWN_DERIVED_FROM` | MUST | A universe's `derived_from` names a universe of the same analysis | 0003 |
| `DERIVED_FROM_CYCLE` | MUST | No universe is derived from itself, directly or through others | 0003 |
| `MISSING_DECISION` | MUST | Every universe's effective selection sets every active decision of its analysis and of every analysis it drives | 0003, 0004 |
| `INACTIVE_DECISION` | MUST | A universe itself sets only decisions whose `when` holds in its effective selection | 0003 |
| `MISSING_REQUIRED_OPTION` | MUST | Every effective selection satisfies the `requires` of every option it selects | 0003 |
| `INCOMPATIBLE_OPTIONS` | MUST | Every effective selection satisfies the `incompatible_with` of every option it selects | 0003 |
| `EXCLUDED_OPTION_SELECTED` | MUST | No effective selection selects an excluded option | main, tidy-up |
| `PARTIALLY_DRIVEN` | MUST | Every declaration is driven by all of the driver's universes or by none | 0004 |
| `CONFLICTING_SELECTIONS` | MUST | Every spelling of one decision in a universe selects the same option | 0004 |
| `NOT_BUILT_IN_UNIVERSE` | MUST | Every output built per universe of another analysis read without a pin, and every decision of another analysis consumed, belongs to an analysis built in the universe being built | 0004 |
| `UNDRIVEN_DECLARATION` | MUST | In the file of the analysis whose universe is being built, every address that reads another analysis's output built per universe without a pin, or consumes another analysis's decision, goes through a declaration that the file's universes drive | 0004 |
| `INPUT_NOT_BUILT` | MUST | Every output read without a pin is active (its `when` holds) in the universe being built | 0004 |
| `PIN_ON_INPUT` | MUST | Every pinned reference names an output | 0003 |
| `UNKNOWN_PIN_UNIVERSE` | MUST | Every pin names a universe of the driver, through a driven declaration, or otherwise of the analysis the output belongs to | 0003, 0004 |
| `PIN_INACTIVE` | MUST | Every pinned output is active in the universe it is pinned to | 0003 |
| `OUTPUT_CYCLE` | MUST | No output depends on itself, directly or through others | 0004 |
| `REDUNDANT_PIN` | SHOULD | No reference to an output built once has a pin | 0003 |
| `UNPINNED_EVIDENCE` | SHOULD | Every evidence citing an output built per universe pins it | 0003, 0004 |
| `NO_UNIVERSES` | SHOULD | Every analysis with decisions, or with outputs built per universe, has universes, unless the root's universes drive it, or it consumes a decision | 0003, 0004 |

### check

Read this table like the others: **the Rule column says what must hold**.
The extra column, **Status when broken**, is the status a result, or evidence
citing it, gets when the rule doesn't hold. A result for which every rule
holds is `unchanged` and `present`.

**Statuses.** A checker gives every planned result two statuses, one for its
record (`unchanged`, `stale` or `missing`) and one for its bytes (`present`
or `absent`). Evidence citing a result gets that result's first status.

| Status | Means |
|---|---|
| `unchanged` | The result has a valid record where its address says, and `STALE_RESULT` holds |
| `stale` | The result has a valid record where its address says, and `STALE_RESULT` doesn't hold. The checker says what changed |
| `missing` | The result has no valid record where its address says: `MISSING_RECORD`, `INVALID_RECORD`, `MISPLACED_RECORD` or `MISSING_RECORD_INPUTS` doesn't hold |
| `present` | The bytes at the result's default place hash to the record's `content_hash` and have its `size` |
| `absent` | Anything else is at the default place, nothing, a stand-in or other bytes included |

**Rules.**

| Code | Level | Rule | Status when broken | Source |
|---|---|---|---|---|
| `MISSING_RECORD` | MUST | Every planned result has a record at `.astra/records/{universe}/{name}.json` (or `{name}.json` for an output built once) in the analysis it belongs to | `missing` | 0005 §1 |
| `INVALID_RECORD` | MUST | The record at each planned result's place is valid against the record schema of its `spec_version`, or against the open variant when that version is newer than the checker's | `missing` | 0005 §2, tidy-up, §8 |
| `MISPLACED_RECORD` | MUST | The record at each planned result's place names that result in its `address` | `missing` | 0005 §1 |
| `MISSING_RECORD_INPUTS` | MUST | The record at each planned result's place has exactly one `inputs` item for each entry its output lists at the commit the record names, matched by `entry`, and no other item (their order carries no meaning) | `missing` | 0005 §2 |
| `STALE_RESULT` | MUST | Since the commit in a result's record, nothing has changed in its output's declaration (command, inputs and their order, decisions, format), its decisions' options, the content of its inputs, never what stands in for it, or the results it reads | `stale` | 0005 §4 |
| `ABSENT_RESULT` | SHOULD | Every result's recorded bytes are at its default place | `absent` | 0005 §1 |
| `STALE_EVIDENCE` | MUST | Every evidence citing a result cites an unchanged one | the cited result's status | 0005 §5 |

The results of an analysis from a commit that are read or cited are checked
by the same rules, through their records at the declared commit (0007
§4–5).

### runner

| Code | Level | Rule | Source |
|---|---|---|---|
| `UNRECORDED_RESULT` | MUST | A runner writes a record for every result it makes, in the analysis the result belongs to, and writes the bytes to their default place | 0005 §1, 0005 §3 |
| `UNCOMMITTED_CHANGES` | MUST | A runner runs only when the repository has no changes other than the results and records it writes | 0005 §3 |
| `UNRECREATABLE_ENVIRONMENT` | MUST | A runner records each recipe's environment as an IRI that it can recreate at its version | 0005 §3 |
| `UNDECLARED_READ` | MUST | A recipe reads files and results only through its output's inputs | 0005 §3 |
| `NOT_AT_COMMIT` | MUST | A runner drives an analysis from a commit on exactly its files at that commit | 0007 §7 |
| `REBUILT_FROM_COMMIT` | MUST | A runner builds none of the outputs built once of an analysis from a commit that it drives, and reads them through their records | 0007 §7 |
| `STALE_INPUT` | MUST | A runner builds an output only when every result it reads is `unchanged` and its bytes can be got and are the recorded ones | 0007 |

Two duties that are not rules of their own, because nothing can check them: a
runner SHOULD let someone see what an environment it recorded holds, and MAY
enforce `UNDECLARED_READ` (with a sandbox, say). The specification states them
in its §8.

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
| `rules.json` | `https://w3id.org/astra/0.1/rules.json` | the rule catalogue of §9, with the code of every error the JSON Schemas can report |

Each JSON Schema's `$id` is its URI. So the closed and open record schemas are
distinct resources, and so are the schemas of two minor versions, which a
checker can hold side by side. The patches of one minor version share each
URI: a patch release never changes what is valid (§1), so the URI names one
schema whichever patch's file a tool holds, and a tool keeps the latest. A
pre-release is `X.Y.Z` followed by `aN`, `bN` or `rcN`, such as `0.1.0rc1`.
It is a candidate for `X.Y.Z`: its URIs carry its whole version
(`https://w3id.org/astra/0.1.0rc1/analysis.schema.json`), and the documents it
checks state `X.Y.Z`. `https://w3id.org/astra/` followed by a file name alone
redirects to the latest release's file and is no schema's `$id`. A JSON
Schema's top level holds only standard JSON Schema keywords, so that strict
validators (such as Ajv) compile it, and the version of the release it was
generated from is in its `$comment`.

**The contract.** `analysis.schema.json` is the contract for `astra.yaml`: a
document breaks no schema rule exactly when a JSON Schema draft 2019-09
validator reports no error for it against this file. `provenance.schema.json`
is the contract for records in the same way. Both are closed: a field they
don't define is an error ([`UNKNOWN_FIELD`](#parse-and-schema)), and no
optional field takes `null`. Their patterns stay in the subset of regular
expressions that ECMA-262 and Python share (§4), so validators in either
language agree.

**The open variant.** `provenance.open.schema.json` differs from
`provenance.schema.json` only in allowing fields it doesn't define. A checker
reading a record of a newer version than its own validates the record against
it, and so ignores the fields that version adds
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
- `errors`: the code of every keyword of the three JSON Schemas that can
  report an error, keyed by the keyword's absolute keyword location, as JSON
  Schema 2019-09 defines it: the schema's `$id`, `#`, and the JSON Pointer to
  the keyword once every `$ref` is resolved. So each key names its minor
  version, through `$id`. Each code is a schema-layer rule's. The
  parse-layer codes have no entry, because loaders and §3's checks report
  them, not schemas; nor does the open variant's `additionalProperties`,
  which fails on nothing.
- `$comment`: the version of the release it was made from.

In the schema's sources, each constraint names the rule it enforces: a
pattern by its type or field, a class rule or an exactly-one-of by itself.
The keywords whose code never varies take a default: `required` outside such
a rule (`MISSING_FIELD`); `additionalProperties` (`UNKNOWN_FIELD`); `type`
(`WRONG_TYPE`), except on a map key, which takes the key's code;
`minProperties` and `minItems` of 1 (`EMPTY_COLLECTION`); `uniqueItems`
(`DUPLICATE_ENTRY`); and `enum` and `minimum` (`INVALID_VALUE`). An abridged
`rules.json`:

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

**From an error to its code.** A tool that reports the catalogue's codes
looks up, in `errors`, the absolute keyword location of each error its
validator reports. `jsonschema` and Ajv report the innermost errors: each
names the keyword that failed, either an assertion (such as `pattern`,
`required` or `additionalProperties: false`) or a `oneOf`, `not`, `if` or
`propertyNames` that fails as a whole. Each such error has an entry,
including those that say why a `oneOf` failed. A validator that writes one
of JSON Schema's standard output formats also lists the applicators above
an error (`properties`, `items`, `$ref`, an `additionalProperties` that
holds a schema, `allOf`, `then`). Those have no entry; a tool maps the
innermost errors.

What a validator gives with an error is the path it took to the keyword,
through `$ref`s, so a tool needs one step to get the location. In both
validators below, an error comes with the subschema that holds the failing
keyword, and the location is the schema's `$id`, `#`, that subschema's JSON
Pointer in the schema, `/` and the keyword. The pointer is found by walking
the schema once and comparing objects by identity, not by value, since
equal subschemas sit in different places:

- **Python's `jsonschema`.** An error's `absolute_schema_path` runs through
  each `$ref` without naming it (and leaves out the `if` of a failing
  `then`), so it is not the location. Its `schema` is the subschema, and its
  `validator` the keyword.
- **Ajv.** Compile with the options `allErrors: true` and `verbose: true`.
  Without `allErrors`, Ajv stops at the first error it meets, which can be a
  `oneOf` above the error that matters, with another code. An error's
  `schemaPath` is relative to the part of the schema Ajv compiled the
  keyword in: a `$ref` target that Ajv inlines is written as its reference
  (`#/$defs/…`), but one it compiles on its own, as it does any target with
  a `$ref` of its own, starts again from `#`. So `schemaPath` is not always
  the location. With `verbose: true`, an error's `parentSchema` is the
  subschema, and its `keyword` the keyword.

**Reading `astra.yaml`.** The parse layer is a YAML 1.2 loader under the
core schema, plus §3's checks, and a stock loader that calls itself YAML 1.2
is not always one. ruamel.yaml's safe loader and js-yaml's `CORE_SCHEMA`
resolve plain scalars by tables of their own, not by YAML 1.2.2 §10.3.2's:
both read `1_000` as 1000 and `0b101` as 5, which the table leaves strings;
ruamel.yaml also reads `2026-10-26` as a date, and js-yaml reads `-.5` as a
string. In JavaScript, the `yaml` package follows the table under the options
`{version: '1.2', schema: 'core', uniqueKeys: true, merge: false,
resolveKnownTags: false}`. It accepts `%YAML 1.1`, as YAML 1.2.2 requires,
and every other version but 1.2 with only a `BAD_DIRECTIVE` warning, leaving
`doc.directives.yaml.version` at `'1.2'`. So a tool checks the directive
itself: a `doc.directives.yaml.version` of `'1.1'`, or a `BAD_DIRECTIVE`
warning on the `%YAML` line, makes the file invalid
([`INVALID_SYNTAX`](#parse-and-schema)). By default `yaml` builds `!!omap`,
`!!set`, `!!binary` and `!!timestamp` as YAML 1.1's types and merges at a
`!!merge` key; under `resolveKnownTags: false` it builds a node with any tag
outside the core schema as a string, a list or a map by its kind, as it does
one tagged `!`, keeping the tag in `node.tag`, with a `TAG_RESOLVE_FAILED`
warning. It reads anchors and aliases either way. So a
JS loader refuses every anchor, every alias and every tag outside the core
schema itself, walking the document with `visit`: every `Alias`, every node
with an `anchor`, and every node whose `tag` is set and is neither `!` nor a
core schema tag on a node of its kind makes the file invalid
([`INVALID_SYNTAX`](#parse-and-schema)). The warning isn't that check: `yaml`
also gives it, and leaves a string, for a core tag on a scalar whose form its
own test doesn't take, so a tool reads an explicitly tagged scalar's source
by its tag's row of the table too, refusing `!!int 1_000` and reading
`!!float 1` as the float 1. `yaml` reports a second document itself
(`MULTIPLE_DOCS`), and gives `null` for a file with none.

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
`xsd:dateTime`. No RDF reading of `astra.yaml` is published yet. In the
schema, the evidence selectors are W3C Web Annotation's
`oa:TextQuoteSelector` (with `oa:exact`, `oa:prefix` and `oa:suffix`) and
`oa:FragmentSelector` (with `rdf:value` and `dcterms:conformsTo`). A
location's `conforms_to` is its `dcterms:conformsTo`, whose object is the IRI
it names, and a location without one reads as one with
`http://tools.ietf.org/rfc/rfc3778`. With both a `quote` and a `location`,
the location is the `oa:FragmentSelector` that is `oa:refinedBy` the quote's
`oa:TextQuoteSelector`.

**The package.** The `astra-spec` Python package holds the LinkML sources and
these artefacts, as the namespace package `astra.schema`, read through
`importlib.resources`. It ships no Python models and has no dependencies.
