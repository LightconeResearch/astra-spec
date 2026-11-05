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
| element | an input, output, decision, option, universe, declaration or insight of an analysis | §4 |
| address | the name of an element other than an option, through the declarations that lead to it; an option is named by an option reference (§4) | §4 |
| active | of a decision or an output, when every condition of its `when` holds | §5 |
| universe | a selection of one option for every active decision | §6 |
| effective selection | what a universe selects once `derived_from` is resolved | §6 |
| built per universe, built once | whether an output has one result in each universe where it is active, or one in all | §6 |
| pin | `#` and a universe id ending a reference, after its address, which reads the output in that universe | §4 |
| root | the analysis being validated or built | §7 |
| analysis stack | the root and every analysis it declares, directly or through others | §7 |
| driver, driven | in the root's universes, the root, and an analysis reached through a declaration they drive; the root is never driven | §7 |
| consuming | using another analysis's element by address, without driving it | §7 |
| analysis from a commit | a declared analysis as it was at a given commit | §7 |
| result | what a recipe made for one output in one universe, or once | §8 |
| planned result | a result a check of the root covers: every result of the root's active outputs, every result those read, transitively, and every result the root's evidence cites | §8 |
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
([`UNSUPPORTED_SPEC_VERSION`](#validator)). A file whose `spec_version` is
missing or malformed is checked against the validator's own schema, and every
schema error in it is reported. What a minor or major version promises about
another is left to ASTRA's versioning policy.

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
| **parse** | a YAML 1.2 loader under the core schema, plus §3's checks (`astra.yaml`), or a strict JSON parser (records, §3) | one file's bytes |
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
  rule leaves its result `missing` ([`INVALID_RECORD`](#check)).
- A **runner** runs recipes and writes each result's bytes and record. A
  record is its runner's testimony, and names it. A runner conforms when it
  keeps the runner `MUST`s, which keep its records true. How it stores bytes
  or builds environments is its own.

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
run in that directory ([`WRONG_WORKING_DIRECTORY`](#runner)). The paths of
its inputs and declarations are relative to the folder of the `astra.yaml`
and separate folders with `/` (§5, §7).

**Paths.** A path in an analysis is written as git writes a path in a commit,
the same on every machine, and so is each place §8 builds from its ids and
formats; a tool on Windows maps them onto its own paths, as git does. A path
names the entry git holds at exactly that path, byte for byte, read as
**Reading git** says (below), so case and Unicode form count: a match that
ignores either names nothing ([`MISSING_INPUT_FILE`](#validator),
[`MISSING_DECLARED_ANALYSIS`](#validator)). Two paths that differ only in case
or Unicode form, such as `data/A.csv` and `data/a.csv`, name two files or
folders, as in git, so `Stage` and `stage` declare two analyses (§7). An
`astra.yaml` needn't be one Windows can check out. The path `C:/x` is `x` in a
folder `C:`, not on a drive, and a name Windows reserves, such as `con` or
`aux`, or a name ending in `.`, such as one built from `format: "csv."`, is
valid. No ASTRA rule bounds the length of an id, a format or a path: a path
git can't check out on a machine, such as one holding a name longer than its
file system allows (255 bytes on ext4), can't be used there.

**Reading git.** An analysis is read in the working tree or at a commit
(§7), and validators and checkers read git one way:

- A path is joined to the folder of the `astra.yaml` that writes it, and its
  `..` segments are removed as text, never through the file system:
  `stage/../data` is `data`, whatever `stage` is on disk.
- In the working tree, a path names an entry on disk below the top of the
  root's working tree, tracked, untracked or ignored, except an entry named
  `.git` and everything below it. At a commit, a path names an entry of that
  commit's tree.
- A symlink is an entry, and is never followed: at a path, it is neither a
  file nor a directory, and a path through a symlinked folder names nothing.
  So a declaration finds no analysis where its path, or its `astra.yaml`, is
  a symlink or goes through one ([`MISSING_DECLARED_ANALYSIS`](#validator)).
  An input's path at or through a symlink names a file only where the
  validator recognises the symlink as standing in for one (§5), and
  otherwise names none ([`MISSING_INPUT_FILE`](#validator)).
- A submodule that is checked out is in the working tree, and its entries
  are read in its own repository. A submodule that isn't checked out is an
  empty folder, and nothing is fetched for it.
- At a commit, a path that looks for a file or an analysis goes on through a
  gitlink into the submodule, at the commit the gitlink pins. Whether an
  input is tracked never crosses a gitlink.
- The repository that holds a file is the innermost one: for a file in a
  submodule, the submodule's own. [`COMMIT_NOT_FOUND`](#validator) and
  [`COMMIT_NOT_ANCESTOR`](#validator) read the repository that holds the
  declaring `astra.yaml`, where, in the working tree, HEAD stands for the
  commit a declaration is in, and during a merge so does MERGE_HEAD (§7).
  [`INPUT_NOT_TRACKED`](#validator) reads the repository that holds the
  input's analysis, where a file is tracked when, in the working tree, it is
  in the index or, at a commit, in that commit's tree, reached through no
  gitlink. So a staged input is tracked, and an untracked or ignored one
  isn't, nor is one in a plain data submodule. An intent-to-add entry
  (`git add -N`) isn't tracked, since a commit made now wouldn't hold it; an
  unmerged entry during a merge is, since it is in the index.
- The commit a gitlink pins is got from any repository that has it: the
  submodule's local repository, or a copy kept from an earlier fetch.
  Otherwise it is fetched from the URL that `.gitmodules` gives for the
  submodule: the entry whose `path` is the gitlink's, in the `.gitmodules`
  blob of the commit that holds the gitlink, never `.git/config`. A relative
  URL (`../lib.git`) is resolved against the URL that commit was got from:
  the declaration's `url` for an analysis read from a remote and, in the
  local repository, the superproject's default remote, as `git submodule`
  resolves it. A pinned commit that can't be got is unreachable
  ([`REMOTE_UNREACHABLE`](#validator), §7).
- At a commit, a file is the blob git stores, byte for byte, with no filter,
  `.gitattributes` conversion or end-of-line change, whatever the reader's
  git configuration. So an `astra.yaml` at a commit is parsed from its blob.
  In the working tree, it is parsed from the file on disk.

**`astra.yaml`** is YAML 1.2 ([YAML](https://yaml.org/spec/1.2.2/)), read
strictly, under the core schema only
([`INVALID_SYNTAX`](#parse-and-schema)):

- a file is UTF-8, and may start with a byte order mark but holds none
  anywhere else outside a quoted scalar
  ([`INVALID_SYNTAX`](#parse-and-schema)). This is ASTRA's rule, not YAML's:
  YAML 1.2.2 also reads UTF-16 and UTF-32, and allows a byte order mark at
  the start of each document
  ([§5.2](https://yaml.org/spec/1.2.2/#52-character-encodings)). Otherwise,
  its characters and line breaks are YAML 1.2.2's
  ([§5.1](https://yaml.org/spec/1.2.2/#51-character-set),
  [§5.4](https://yaml.org/spec/1.2.2/#54-line-break-characters)): a C0
  control other than tab, LF and CR makes the file invalid anywhere, and DEL,
  a C1 control other than NEL, U+FEFF, U+FFFE and U+FFFF make it invalid
  outside a quoted scalar ([`INVALID_SYNTAX`](#parse-and-schema)); NEL, LS
  and PS are ordinary characters, not line breaks; a tab is white space, but
  never indentation
  ([§6.1](https://yaml.org/spec/1.2.2/#61-indentation-spaces)); and a CR on
  its own ends a line, as a CR LF and an LF do;
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
  and floats. An integer or a float is a JSON number, and a field's type is
  checked as JSON Schema checks it, so `2.0` is an integer. `.inf`, `-.inf`
  and `.nan`, and a number beyond the range of a double (IEEE 754 binary64),
  which rounds to infinity (`1e400`, an integer of 400 digits), have no JSON
  form and make the file invalid ([`INVALID_SYNTAX`](#parse-and-schema)).
  `yes`, `no`, `on` and `off` are strings, and valid ids.
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
  and a single `e` a float, or invalid at parse when that float is beyond a
  double's range (`1234e9` followed by 34 digits); a version such as `1.2` is
  a float too. They are quoted when meant as ids or strings, as in
  `"true": {}`, and so are commit ids and versions, as in
  `commit: "0dbb615a…"` and `spec_version: "0.1.0"`. A value of another type
  than its field takes fails as [`WRONG_TYPE`](#parse-and-schema);
- every key is a string. A key the core schema reads as a boolean, a number
  or a null (`true:`, `1:`, `~:`), or a key that is a list or a map, has no
  JSON form ([`INVALID_ID`](#parse-and-schema)). It is reported at its map,
  naming the key as written, and its entry is left out of the JSON form the
  schema checks (§9, *What is checked*): the parse rules apply in the entry,
  but no schema rule does, and the rest of the file is checked as that form
  stands, so an `outputs` map whose only key is `1` is also empty
  ([`EMPTY_COLLECTION`](#parse-and-schema)). Keys are compared before that,
  so `true:` written twice in one map is [`DUPLICATE_KEY`](#parse-and-schema).
  A key that fails at parse, such as `.nan`, is
  [`INVALID_SYNTAX`](#parse-and-schema), as any value is;
- a `\u` or `\U` escape of a surrogate (U+D800–U+DFFF) is read only as half
  of a pair: a high surrogate's escape followed at once by a low one's, which
  together give one character, as in JSON, so `"\uD83D\uDE00"` is U+1F600.
  Any other surrogate escape makes the file invalid
  ([`INVALID_SYNTAX`](#parse-and-schema)).

**Records** are JSON text ([RFC 8259](https://www.rfc-editor.org/rfc/rfc8259))
in UTF-8, read strictly ([`INVALID_SYNTAX`](#parse-and-schema)):

- a record uses only JSON's forms: a comment, a trailing comma, a single
  quote, `NaN`, `Infinity` or YAML makes it invalid
  ([`INVALID_SYNTAX`](#parse-and-schema));
- a record starts with no byte order mark
  ([`INVALID_SYNTAX`](#parse-and-schema)). RFC 8259 §8.1 forbids writing one
  but lets a parser ignore one; a checker refuses it, as `JSON.parse` does, so
  that every checker reads a record alike;
- a name written twice in one object makes the record invalid
  ([`DUPLICATE_KEY`](#parse-and-schema)). Names are compared once their
  escapes are read, so `"a"` and `"\u0061"` are one name. RFC 8259 §4 doesn't
  forbid a repeated name, and Python's `json.loads` and JavaScript's
  `JSON.parse` keep the last of two, so a checker needs a parser that reports
  one (§10);
- its strings and numbers are those of every document (below): a number
  beyond a double's range (`1e400`) and the escape of a lone surrogate
  (`"\ud800"`) make it invalid ([`INVALID_SYNTAX`](#parse-and-schema)), and an
  escaped pair, `"\ud83d\ude00"`, is one character.

A record is one JSON value, checked by the same schema rules. A record that
breaks a parse or schema rule leaves its result `missing`: a checker reports
[`INVALID_RECORD`](#check), with each code the record breaks as its reason
(§9, §10).

**Every document** holds only the fields its schema defines
([`UNKNOWN_FIELD`](#parse-and-schema)), each with the JSON type the field
takes ([`WRONG_TYPE`](#parse-and-schema)). An optional field without a value
is left out: no field takes `null`. Its JSON form is what the schema checks:
each string is a sequence of Unicode scalar values, and each number is finite
and within a double's range ([`INVALID_SYNTAX`](#parse-and-schema)).

**Locations.** In an analysis's directory:

| Path | Holds |
|---|---|
| `astra.yaml` | the analysis document |
| `.astra/records/{universe}/{name}.json`, `.astra/records/{name}.json` | the records of the results that belong to the analysis, tracked in git (§8) |
| `results/{universe}/{name}.{format}`, `results/{name}.{format}` | the default places of those results' bytes (§8) |

`results/` and `.astra/` belong to runners. No input's `path` and no
declaration's `path` is, or lies in, them ([`RESERVED_PATH`](#validator)):
joined to the folder of the `astra.yaml` that writes it, with its `.` and
`..` segments and repeated `/` resolved as text, a path is not the
`results/` or `.astra/` of any analysis of the stack (§7), and is not inside
one. So a run never writes over an input or a declared analysis, and a
result is read by its address (§5), never by a path.

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
nor two spellings of one entry ([`DUPLICATE_ELEMENT`](#validator)), so an
output lists each of its inputs, decisions and conditions once.

Every id has the one grammar `id`, and no id is reserved (not even a name
Windows reserves, §3): an address's kind comes from the field it is written
in, so an element can be called `inputs`. Ids of different kinds can be the
same, with two exceptions. An input and an output never share an id, since
`Output.inputs` takes both ([`AMBIGUOUS_ID`](#validator)). An output never
shares its id with a declaration of its analysis, since their results'
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
output. Two conditions, or two option references, are spellings of one entry
when their addresses spell one decision and they name the same option, and
two conditions also need both or neither to have `~`. Two references are
spellings of one entry when their addresses spell one element and both are
unpinned, or both pin one universe (§7). No list holds two spellings of one
entry ([`DUPLICATE_ELEMENT`](#validator)), so `{inputs}` never passes one
entry twice under two spellings.

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
After a space or a tab it starts a comment: `- f1_score #svm` is the plain
reference `f1_score`, followed by a comment. Write a pin with no space before
its `#`.

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

An [Input](elements/Input.md) is a file tracked in git with the analysis,
named by its `path`, relative to the folder of the `astra.yaml` (§3). The
path doesn't start with `/` or `~`, separates folders with `/` (never `\`),
has no `..` segment and no ASCII control character (U+0000–U+001F, U+007F),
and doesn't end in `/` ([`INVALID_PATH`](#parse-and-schema)).

- It names one file ([`MISSING_INPUT_FILE`](#validator)). Data in many files
  is many inputs.
- The file is inside the analysis's directory and outside every analysis
  within it, a directory with an `astra.yaml` of its own
  ([`INPUT_IN_ANOTHER_ANALYSIS`](#validator)). Another analysis reads it by
  address (`iris.data`), not by a path.
- The file is outside the places that belong to runners: the path is not,
  and doesn't lie in, the `results/` or `.astra/` of an analysis of the
  stack, as §3 resolves it ([`RESERVED_PATH`](#validator)). A result is read
  by its address, never by a path.
- The path names the file itself (not a symlink, §3), or something the
  tooling recognises as standing in for it
  ([`MISSING_INPUT_FILE`](#validator)). The file, or what stands in for it,
  is tracked in git ([`INPUT_NOT_TRACKED`](#validator)), in the repository
  that holds the analysis (§3). Which stand-ins a tool recognises, and where
  it looks for them, is the tool's: the specification names none, and two
  tools may judge the same input differently. How a file's bytes are stored
  and got is the runner's, and every record names its runner (§8).
  Something standing in for the content isn't the content.

`astra.yaml` holds no hash of an input. The record of each result that reads
the input holds the hash of what it read (§8), so a change to the file makes
those results stale.

Data that isn't tracked in git with the analysis, such as a download, a
loader's output or a query's answer, comes in through an output whose recipe
gets it. That output is built once, or per universe when it depends on a
decision such as which data release to use, and its record holds the hash of
what came back. Data kept in another repository, a git submodule say, isn't
tracked in git with the analysis either (§3), so it isn't an input. It
belongs in the analysis's own repository or in another analysis, as that
analysis's input, or comes in through an output whose recipe gets it.

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
directory ([`WRONG_WORKING_DIRECTORY`](#runner)).

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
among its `inputs`, or one of none of these forms, such as `{foo}`.

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
that result's record, and unpinned evidence through the records of the
output's results (§8).

## 6. Universes

### Declaring universes

A [Universe](elements/Universe.md) selects one option for every active
decision of its analysis and of every analysis reached through a declaration
that a universe of its analysis drives (§7). Universes are the entries of
`universes`, keyed by id, unique within their analysis
([`DUPLICATE_KEY`](#parse-and-schema)).

A universe's `decisions` map decisions to options
([DecisionSelection](elements/DecisionSelection.md)), as
`<decision>: <option>`, such as `model: svm`. A key is the id of a decision
of the analysis or, for a decision of another analysis, its address,
`<declaration>.<decision>`, a flat key (§7), or another spelling of either
through declarations (§4, §7). A key resolves through its declarations to
one decision: an analysis, known by its identity (§7), and the decision's
id in it. A universe's own `decisions` give each decision one key
([`DUPLICATE_ELEMENT`](#validator)); a derived universe can still set a
decision it inherits under another spelling (below). A value is the id of
one of that decision's options ([`UNKNOWN_OPTION`](#validator)).

`derived_from` names another universe of the same analysis
([`UNKNOWN_DERIVED_FROM`](#validator)), whose selection this one inherits, so
that it gives only the decisions it changes. No universe's chain of
`derived_from` loops ([`DERIVED_FROM_CYCLE`](#validator)).
`derived_from` says how two universes relate and makes neither special. A
universe's `label` and `tags` are its own: they are never inherited.

### The effective selection

A universe's **effective selection** is what it selects once `derived_from`
is resolved:

1. Without `derived_from`, it is the universe's own `decisions`.
2. With `derived_from`, it is the effective selection of the universe named
   there, with each of the universe's own selections set on its decision:
   every inherited key for that decision takes the new option, and the key
   is added. So where `stage.inner.d` and `inner.d` spell one decision, a
   universe that inherits `stage.inner.d: d1` and sets `inner.d: d2` itself
   selects `d2` under both keys.
3. An inherited selection of a decision that isn't active in the result is
   dropped, so a universe that switches a decision off needn't undo what it
   inherited for it.

A universe whose `derived_from` doesn't resolve, or whose chain loops or
reaches a universe that has none, has no effective selection (§9, *What is
checked*).

The effective selection is held to everything a universe written in full is:

- it selects every active decision of its analysis and of every analysis
  reached through a declaration that a universe of its analysis drives
  ([`MISSING_DECISION`](#validator)), so a universe that switches a decision
  on sets it;
- it names only declared decisions and their options
  ([`UNRESOLVED_ADDRESS`](#validator), [`UNKNOWN_OPTION`](#validator));
- every spelling of one decision in it selects the same option
  ([`CONFLICTING_SELECTIONS`](#validator));
- it drives the same chains of declarations as every other universe of its
  analysis ([`PARTIALLY_DRIVEN`](#validator), §7);
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
([`UNDECLARED_TEMPLATE_REF`](#validator)), and a pin on it doesn't change
which result a reference names ([`REDUNDANT_PIN`](#validator)): pinned or
not, the reference names its one result, and `{inputs.<entry>}` gives that
result's path; the pin still names a universe
([`UNKNOWN_PIN_UNIVERSE`](#validator)).

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

An analysis declares each analysis it uses in `analyses`, keyed by the id it
addresses it by ([AnalysisDeclaration](elements/AnalysisDeclaration.md)). The
declared analysis's elements are then addressed through that id, as
`<declaration>.<element>` (§4). A declaration has exactly one of `path` and
`url` ([`INVALID_DECLARATION_SOURCE`](#parse-and-schema)), and may have a
`commit`, which a `url` needs ([`URL_WITHOUT_COMMIT`](#parse-and-schema)).

**`path`** is the directory of the declared analysis's `astra.yaml`, relative
to the folder of the declaring `astra.yaml` (§3). It doesn't start with `/`
or `~`, separates folders with `/` (never `\`) and has no ASCII control
character; `..` segments are allowed ([`INVALID_PATH`](#parse-and-schema)).
It stays inside the declaring analysis's repository
([`DECLARATION_OUTSIDE_REPOSITORY`](#validator)): read in the working tree,
the root's working tree, submodules included; read at a commit, the
repository that holds that commit. It is not, and doesn't lie in, the
`results/` or `.astra/` of an analysis of the stack, as §3 resolves it
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
character ([`INVALID_VALUE`](#parse-and-schema)), though git fetches a remote
with a space: a space is written `%20` in a `scheme://` URL, which git
decodes. Git doesn't decode the scp-like form, so an scp-like remote
`[user@]host:my dir/x` is written `ssh://[user@]host/~/my%20dir/x`. Whether
the URL leads to a valid analysis is the validator's to tell
([`REMOTE_UNREACHABLE`](#validator),
[`MISSING_DECLARED_ANALYSIS`](#validator),
[`DECLARED_ANALYSIS_INVALID`](#validator)).

**`commit`** is a full commit id ([`INVALID_COMMIT`](#parse-and-schema)): a
branch moves, a tag can be moved or name another commit in a fork or a
mirror, and a shortened id can become ambiguous as a repository grows. A
declaration with a `commit` declares an analysis from a commit (below).

**Identity.** A declaration names a directory, read at a commit or in the
working tree. With a `url`, it is the top level of that repository; with a
`path`, it is the `path` resolved against the folder of the declaring
`astra.yaml`, as **Reading git** in §3 says. It is read at the declaration's
`commit` or, without one, as the declaring analysis is read. The root, and
every analysis reached from it by `path` alone, is read in the working tree.
The directory is a path from the top of the repository that holds the commit
it is read at or, read in the working tree, from the top of the root's working
tree. Two declarations name the same analysis when their directories are the
same path, compared as git compares paths (§3), read at the same commit or
both in the working tree. A URL says only where to get the commit, so a fork
or a mirror with the same commit gives the same analysis. *Another analysis*,
everywhere in this specification, is one with a different identity.

One analysis, whichever analysis declares it and by whatever id, is read
once, and each of its results is made at most once, however many
declarations reach it. A declaration by `path` alone, or a chain of them,
that leads back to the declaring analysis's own directory names the analysis
itself: `self: {path: .}`, say, or `feature_extraction.iris` in the root of
`examples/iris_pipeline`. An address through it is another spelling of one
of the analysis's own elements (§4), and a universe's key through it another
spelling of one of its own decisions. Driving and consuming use another
analysis's elements (below), so such an address consumes nothing, and such a
key drives no declaration on its chain: it counts as driving for neither
[`PARTIALLY_DRIVEN`](#validator) nor [`MISSING_DECISION`](#validator).

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

The universes built are the root's and those a pin names. In the root's
universes the root is the driver and is never driven, even when a
declaration in its stack leads back to it. Another analysis's universe is
used only where a pin names it. That analysis is then its driver: like the
root, it is never driven in that universe, and what is built there belongs
to it (§8). A validator also checks every other universe of the stack
(below).

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
analysis with no decisions and no universes of its own has no key to set,
and is driven by being built in its driver's universes (below).

A universe **drives** a declaration when a key in its effective selection
(§6), for a decision of another analysis, goes through every declaration
from its analysis's file to that one. The key `stage.inner.d` drives the
driver's `stage` and, through it, `stage`'s `inner`, but not an `inner` that
the driver's file declares itself: each chain of declarations from the
driver's file (`stage`, `stage.inner`, `inner`) is driven on its own. Two
chains that end in one declaration, such as `stage.lib` and
`stage_undriven.lib` where `stage` and `stage_undriven` declare one
directory, are driven on their own too, and an address or a reference is
judged on its own chain. A declaration of an analysis with no decisions and
no universes of its own is driven by every universe that drives the chain
before it, and so by every universe of the driver when the driver's file
declares it, unless the declaration leads back to an analysis already on the
chain, the declaring analysis itself included (`self: {path: .}`). Such an
analysis's outputs built per universe (§6) are then built in each of the
driver's universes where they are planned (§8), and those results belong to
the driver, while its outputs built once still belong to it. An analysis with
universes of its own keeps them unless a key drives it.

- Every universe sets every active decision of every analysis reached
  through a declaration that a universe of its analysis drives
  ([`MISSING_DECISION`](#validator)).
- Each chain of declarations from an analysis's file is driven by all of its
  universes or by none ([`PARTIALLY_DRIVEN`](#validator)). Driving is judged
  on the effective selection, so a derived universe drives what it inherits
  keys for.
- An analysis reached through two driven declarations can have a decision
  set under either spelling (`stage.inner.d` or `inner.d`), and a universe's
  own `decisions` set it under one ([`DUPLICATE_ELEMENT`](#validator)).
  Every spelling of one decision in a universe's effective selection selects
  the same option ([`CONFLICTING_SELECTIONS`](#validator)); a derived
  universe that sets the decision under one spelling sets it under every
  spelling it inherits (§6).
- In the root's universes, a driven analysis's own universes don't set its
  decisions. A pin in its own file, or through an undriven declaration,
  still reads one of them (below). Each universe being built has one driver,
  the analysis whose universe it is.

A validator still checks every universe of every analysis of the stack, a
driven analysis's own included. Each universe's selections are held to §6
and to driving ([`UNRESOLVED_ADDRESS`](#validator),
[`UNKNOWN_OPTION`](#validator), [`DUPLICATE_ELEMENT`](#validator),
[`UNKNOWN_DERIVED_FROM`](#validator), [`DERIVED_FROM_CYCLE`](#validator),
[`MISSING_DECISION`](#validator), [`INACTIVE_DECISION`](#validator),
[`MISSING_REQUIRED_OPTION`](#validator),
[`INCOMPATIBLE_OPTIONS`](#validator),
[`EXCLUDED_OPTION_SELECTED`](#validator),
[`CONFLICTING_SELECTIONS`](#validator), [`PARTIALLY_DRIVEN`](#validator)).
The declarations a universe drives are those its effective selection
drives, as above, a declaration back to the root included; checking a
universe builds nothing, so the root stays undriven in its own universes.
Where the root drives `sub`, a universe of `sub`'s own that leaves one of
`sub`'s active decisions unset breaks `MISSING_DECISION`, though the root's
universes don't use it. The rules on the universe being built (below:
[`NOT_BUILT_IN_UNIVERSE`](#validator), [`UNDRIVEN_DECLARATION`](#validator),
[`INPUT_NOT_BUILT`](#validator)) hold only in the universes built. Checking
another analysis's universes doesn't make it the root: the root, and so its
working tree, stays the same, and each declaration is judged once
([`DECLARATION_OUTSIDE_REPOSITORY`](#validator)).

Driving leaves an analysis able to stand alone, and consuming a decision ties
the outputs that use it to the decision's analysis. By convention, a
decision that matters to one analysis is driven, and one shared by several,
such as the seed of a whole stack, is consumed.

### The universe being built

A universe is named by its analysis and its id, since the same id can name a
universe in several analyses. When an analysis is built in one of its
universes, that universe is pushed through every declaration it drives: it
is the universe being built in every analysis they reach. An unpinned entry
of `inputs` reads its output in that universe, and a consumed decision has
the option that universe selects. So, wherever an output built per universe
is read without a pin, or a decision is consumed:

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
universe, through any declaration. And every output read without a pin, of
the analysis itself or of another, is active in the universe being built
([`INPUT_NOT_BUILT`](#validator)).

A pin `#u` resolves in the file it is written in, whatever drives that
file's analysis, so it names one universe under every root. It names the
universe `u` of the first analysis along its reference, starting from the
file's own, whose universes drive the reference's declarations from that
analysis's file to its last. If there is none, it names the universe `u` of
the analysis whose output it is, which for an output of the analysis itself
is one of its own universes ([`UNKNOWN_PIN_UNIVERSE`](#validator)). Where
the root drives `stage` but not `stage.lib`, and `stage`'s universes drive
`lib`, `stage.lib.out#v1` in the root's file names `stage`'s `v1`. To read
one of a driven analysis's own universes, the driver declares the same
directory a second time, without driving that declaration:

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

The address's whole chain decides, up to its last declaration. Where the
root's universes drive `stage.inner` but not `stage`'s second declaration
`inner_undriven`, `stage.inner_undriven.result` read without a pin in the
root's file breaks [`UNDRIVEN_DECLARATION`](#validator) too, though the root
drives `stage`. So does `stage_undriven.inner.result`, where the root's
`stage_undriven` declares `stage`'s directory a second time, though the root
drives `stage.inner`.

What is built in a driver's universes belongs to the driver (§8).

### Analyses from a commit

A declaration with a `commit` names an **analysis from a commit**: the
declared analysis as it was at that commit. With a `url`, it is the analysis
at the top level of that repository at the commit. With a `path`, it is the
analysis at that path at the commit, which the declaring analysis's
repository has ([`COMMIT_NOT_FOUND`](#validator) or, in a file read from a
remote, [`REMOTE_UNREACHABLE`](#validator)) and which should be an
ancestor of the commit the declaration is in or, for a declaration read in
the working tree, of HEAD or, during a merge, MERGE_HEAD
([`COMMIT_NOT_ANCESTOR`](#validator)). It is read from the local repository
or, when the declaring analysis is itself read from a remote, from that
remote, and each submodule it reaches through a gitlink as §3 says. Every
rule of this specification applies to an analysis from a commit as it is,
with its files read at its commit. Its results are those that belong to it
or to an analysis reached from it through declarations, read at the same
commit.

**Identity.** An analysis from a commit is its directory at its commit,
whatever URL it is got from, as **Identity** under Declarations says (above).

**What is read.** An analysis from a commit is read from git at its commit,
each file as the blob git stores (§3), and git checks everything read against
the commit id. None of its code runs, and no checkout is needed. Only these
are read:

- the `astra.yaml` of the declared analysis and of every analysis it
  declares;
- the `astra.yaml` of a result's analysis at the commit the result's record
  names, to tell whether the result is unchanged (§8);
- the record of each result read or cited, and the records of the results it
  was made from;
- which files there are at a commit, and which differ between two commits,
  without their contents;
- the bytes of each result or input file that a recipe reads;
- the `.gitmodules` of each commit whose gitlink a path crosses, and the
  submodule at the commit the gitlink pins (§3).

Where a tool keeps what it read is the tool's choice, and validators,
checkers and runners can work offline from what they kept: a commit kept
from an earlier fetch counts as got ([`REMOTE_UNREACHABLE`](#validator)).
None of it is part of the declaring analysis's code, and none of it is a
change to the declaring analysis's repository that stops a runner from
running ([`UNCOMMITTED_CHANGES`](#runner)).

**Validity.** The declared analysis, with everything it declares, is valid
at its commit ([`DECLARED_ANALYSIS_INVALID`](#validator)), each `astra.yaml`
read by the `spec_version` it states. A rule broken inside an analysis from a
commit is reported twice: `DECLARED_ANALYSIS_INVALID` on the declaration, in
the file the author can edit, and the rule's own code at its place in the
commit's file, which says why. A rule broken in an analysis declared without
a `commit` is reported once, under its own code. Getting a commit from a
remote is checked apart from that validity
([`REMOTE_UNREACHABLE`](#validator)). A commit is got from a remote when it
is a declaration's `url` and `commit`, a `path` and `commit` declared in a
file read from a remote, or the commit a gitlink pins, crossed at a commit
(§3). The remote is the `url`, the remote the file was read from, or the
submodule's URL (§3). Files at a commit never change, but remotes do. So
getting a commit is checked each time, and a commit kept from an earlier
fetch counts as got. Whether the declared analysis is otherwise valid can't
change, and a validator can remember the answer for a commit it has
validated, with the schemas it has.

A commit that can't be got is an error on one declaration in a file outside
every analysis from a commit, read in the working tree, which the author can
edit: the declaration of the outermost analysis from a commit on the way to
it. It is reported once for each such declaration, so two declarations of
one commit, such as a driven and an undriven one, get one report each. Where
the root declares `sub` by `path`, `sub` declares `upstream` by `url`, and
`upstream` declares `nested` by `url`, if `nested`'s commit can't be got, the
error is on `sub`'s declaration of `upstream`. A published analysis SHOULD
declare only remotes its readers can fetch. That isn't a `MUST`, since a
remote can be private while the analysis is being worked on.

**Use.** Unless it is driven, none of the recipes of an analysis from a
commit run ([`REBUILT_FROM_COMMIT`](#runner)), so the rules above let it
give only its outputs in its own universes, pinned (`upstream.summary#u1`),
its outputs built once (`upstream.stage.report`), and its inputs
(`upstream.data`). Evidence cites its results in the same way. An address
that doesn't exist in the declared analysis is an error in the declaring one
([`UNRESOLVED_ADDRESS`](#validator)). Whether the result it names is
recorded and unchanged is the checker's to tell (§8).

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
commit ([`NOT_AT_COMMIT`](#runner)). Where the tool puts those files is the
tool's choice, and they aren't part of the declaring analysis's code and
aren't a change that stops a runner from running
([`UNCOMMITTED_CHANGES`](#runner)). Which environment the recipes run in is
the runner's choice, as for any recipe, and is recorded in the driver's
records. Its outputs built once aren't built: like the rest of its results,
they are read through their records at the declared commit
([`REBUILT_FROM_COMMIT`](#runner)). Only what the driver's universes build is
built. It belongs to the driver, and its records name the driver's commit,
where the declaration says which commit the driven analysis is from and, for
a remote, where to get it. A git submodule also records a URL and a commit,
but only in git, and its checkout can drift from them. A `url` and a
`commit` fix them in `astra.yaml`, so the declared analysis has the same
identity whether it is read or driven, and what a driver runs is the
declared commit.

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
result of an output built once belongs to the analysis whose output it is,
and a result read through a pin in a declared analysis's own universe
belongs to that analysis: a consumed analysis's results stay in its own
directory. A result's **name** is its output's id after the ids of the
driven declarations from the analysis it belongs to (`subanalysis1.output1`).
An undriven declaration, a back-edge such as `iris: {path: ..}` included,
never adds a name, since a pin through it names a universe of an analysis
further along its reference (§7). So the result of an output of the
analysis it belongs to is named by the output's id alone, as the result of an
output built once always is. Reached through two such chains (`inner` and
`stage.inner`, when keys go through both), a result is made once, and placed
and recorded under each name. Its **address** is a name followed, for a
result built in a universe, by `#` and the universe's id
(`subanalysis1.output1#u1`). Each address is the `address` of the record at
its place.

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

- A runner writes a record for every result it makes, at the place of each
  of its names in the analysis the result belongs to, and writes the bytes to
  their default places ([`UNRECORDED_RESULT`](#runner)).
- Every field of the record is true of the run
  ([`FALSE_RECORD`](#runner)). It records each recipe's environment as an
  IRI that it can recreate at its version
  ([`UNRECREATABLE_ENVIRONMENT`](#runner)), and should let someone see what
  that environment holds, as PROV for example.
- It runs only committed code. It runs each recipe in a checkout of a
  commit, the repository's own working tree or one it makes for the run (a
  git worktree, say), and refuses to run while that checkout has changes
  other than the records and results it writes itself, each result's bytes
  the recorded ones, and what a tool keeps of, or puts in place to drive, an
  analysis from a commit ([`UNCOMMITTED_CHANGES`](#runner)). Changes outside
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
results whose records it adds stale. The commit a record names stays in the
history of every commit that holds the record, so branches with records
SHOULD be merged rather than squashed or rebased.

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
its default place have its record's hash and size, `absent` otherwise. Since
the bytes can be kept elsewhere, `absent` is not an error. A tool may report
more about bytes that are `absent`, such as other bytes at the default place,
but their status is `absent`.

A result with two names gets its statuses at each place. A checker reads
records only through planned results: a record at no planned result's place
gets no status, and no check rule applies to it.

Evidence citing a result gets the status of that result's record
([`STALE_EVIDENCE`](#check)), the record at the place of the result's name
along the `artifact`'s declarations: evidence citing `stage.inner.out#u1`
reads the record of `stage.inner.out`, not of `inner.out`. An `artifact` that
is pinned, or that names an output built once, names exactly one result. An
`artifact` that names an output built per universe without a pin cites that
output's results in each of the root's universes where it is active and its
analysis is built. The evidence gets the worst of their record statuses:
`missing`, then `stale`. If there are none, it is `missing`. A check covers
the evidence of the analysis it is run on.

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
| check | Nothing fails. The code is reported and **the result gets a status**, given in the check table's extra column, *Status when broken* |
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

1. **A key that isn't a string.** A map entry whose key isn't a string (`1:`,
   `true:`, `~:`) is reported once, as [`INVALID_ID`](#parse-and-schema) at
   its map, naming the key. The entry is left out, and the rest of the file
   is checked without it.
2. **A file that can't be read.** A file that breaks a parse rule is checked
   no further. A file whose `spec_version` is missing or malformed isn't
   checked by [`UNSUPPORTED_SPEC_VERSION`](#validator): it is checked against
   the validator's own schema (§1). A file whose well-formed `spec_version`
   breaks `UNSUPPORTED_SPEC_VERSION` isn't checked by the schema layer.
3. **A file that isn't a valid document.** A file that breaks a parse or
   schema rule, or [`UNSUPPORTED_SPEC_VERSION`](#validator), isn't checked by
   the validator layer, and its declarations aren't followed. Its analysis is
   undetermined (5).
4. **A declaration that can't be read.** On a declaration whose own analysis
   can't be got, because it breaks
   [`DECLARATION_OUTSIDE_REPOSITORY`](#validator) or
   [`COMMIT_NOT_FOUND`](#validator), or because a commit that analysis is
   read from can't be got ([`REMOTE_UNREACHABLE`](#validator), §7), neither
   [`MISSING_DECLARED_ANALYSIS`](#validator) nor
   [`DECLARED_ANALYSIS_INVALID`](#validator) is checked. On one that breaks
   `COMMIT_NOT_FOUND`, or whose own `commit` can't be got,
   [`COMMIT_NOT_ANCESTOR`](#validator) isn't checked either. Its analysis is
   undetermined (5), and so is the analysis of a declaration that breaks
   `MISSING_DECLARED_ANALYSIS`.
   `DECLARED_ANALYSIS_INVALID` isn't checked on an analysis from a commit
   whose file breaks [`UNSUPPORTED_SPEC_VERSION`](#validator). Where
   `REMOTE_UNREACHABLE` is reported on a declaration for a commit further in
   (§7), `DECLARED_ANALYSIS_INVALID` isn't checked on that declaration, and
   the analysis that couldn't be got is undetermined. The analyses read on
   the way to it are not: their declarations' `MISSING_DECLARED_ANALYSIS`,
   and addresses into them such as `upstream.summary#u1`, are still checked.
5. **An undetermined analysis.** No validator rule is checked in its file. In
   the files that declare it, nothing reached through that declaration is
   checked: no address through it, by
   [`UNRESOLVED_ADDRESS`](#validator) or by any rule on what the address
   would name, no [`MISSING_DECISION`](#validator) for its decisions, and no
   [`PARTIALLY_DRIVEN`](#validator) for a chain through it.
6. **A name that names nothing.** An address that breaks
   [`UNRESOLVED_ADDRESS`](#validator), and an option that breaks
   [`UNKNOWN_OPTION`](#validator), name nothing, and no rule is checked on
   what they would name. That leaves out `UNKNOWN_OPTION` under such an
   address, the pin rules ([`PIN_ON_INPUT`](#validator),
   [`UNKNOWN_PIN_UNIVERSE`](#validator), [`PIN_INACTIVE`](#validator),
   [`REDUNDANT_PIN`](#validator), [`UNPINNED_EVIDENCE`](#validator)), and
   [`NOT_BUILT_IN_UNIVERSE`](#validator),
   [`UNDRIVEN_DECLARATION`](#validator), [`INPUT_NOT_BUILT`](#validator),
   [`OUTPUT_CYCLE`](#validator) and [`DUPLICATE_ELEMENT`](#validator)
   through it. A selection that names nothing isn't checked by
   [`INACTIVE_DECISION`](#validator),
   [`CONFLICTING_SELECTIONS`](#validator),
   [`MISSING_REQUIRED_OPTION`](#validator),
   [`INCOMPATIBLE_OPTIONS`](#validator) or
   [`EXCLUDED_OPTION_SELECTED`](#validator). A `requires` or
   `incompatible_with` entry that names nothing is ignored.
7. **An element whose activity is undetermined.** In a universe, a `when` is
   undetermined when one of its conditions names nothing (6), or tests a
   decision that the universe's selection leaves unset
   ([`MISSING_DECISION`](#validator)) or sets to an option that names
   nothing. Its element's activity in that universe is then undetermined.
   `MISSING_DECISION` and [`INACTIVE_DECISION`](#validator) aren't checked
   for such a decision, [`INPUT_NOT_BUILT`](#validator) and
   [`PIN_INACTIVE`](#validator) aren't checked for such an output, and step 3
   of the effective selection (§6) doesn't drop it.
8. **A universe with no effective selection.** A universe has none when its
   `derived_from` breaks [`UNKNOWN_DERIVED_FROM`](#validator), or its chain
   breaks [`DERIVED_FROM_CYCLE`](#validator) or reaches a universe that has
   none. For it, [`MISSING_DECISION`](#validator),
   [`INACTIVE_DECISION`](#validator), [`MISSING_REQUIRED_OPTION`](#validator),
   [`INCOMPATIBLE_OPTIONS`](#validator),
   [`EXCLUDED_OPTION_SELECTED`](#validator),
   [`CONFLICTING_SELECTIONS`](#validator),
   [`NOT_BUILT_IN_UNIVERSE`](#validator),
   [`UNDRIVEN_DECLARATION`](#validator) and [`INPUT_NOT_BUILT`](#validator)
   aren't checked, and [`PIN_INACTIVE`](#validator) isn't checked for a pin
   naming it. [`UNRESOLVED_ADDRESS`](#validator),
   [`UNKNOWN_OPTION`](#validator) and [`DUPLICATE_ELEMENT`](#validator) are
   still checked on its own `decisions`. [`PARTIALLY_DRIVEN`](#validator) is
   judged over the driver's other universes.
9. **An input with no file.** An input that breaks
   [`MISSING_INPUT_FILE`](#validator) isn't checked by
   [`INPUT_NOT_TRACKED`](#validator).
10. **A result with no valid record.** A result that breaks
    [`MISSING_RECORD`](#check) isn't checked by [`INVALID_RECORD`](#check),
    [`MISPLACED_RECORD`](#check) or [`MISSING_RECORD_INPUTS`](#check). One
    whose record breaks `INVALID_RECORD` isn't checked by the last two.
    [`STALE_RESULT`](#check) isn't checked for a result that is `missing`.

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
| `INVALID_SYNTAX` | parse | MUST | Every `astra.yaml` is UTF-8 and a well-formed YAML 1.2 stream of at most one document under the core schema, with no `%YAML` directive other than 1.2, no anchor or alias and no tag but the core schema's; in every document each string is a sequence of Unicode scalar values and each number is finite and within a double's range; and every record is RFC 8259 JSON text in UTF-8 with no byte order mark | 0005, tidy-up, §3 |
| `DUPLICATE_KEY` | parse | MUST | Every key of a map is distinct: no two are equal YAML nodes, with the same tag and canonical form; and every name of a record's object is distinct once its escapes are read. (This makes the ids of inputs, outputs, decisions, options, insights, universes and declarations unique.) | 0003, 0004, tidy-up, §3, §4 |
| `INVALID_ID` | schema | MUST | Every map key is a string, and matches its key's type where the map has one (an `id`, or an `address` in `Universe.decisions`); every `id`-typed value matches the `id` grammar | tidy-up, main, §3, §4 |
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

Every universe of every analysis of the stack is checked as §7 says.

| Code | Level | Rule | Source |
|---|---|---|---|
| `UNSUPPORTED_SPEC_VERSION` | MUST | Every `astra.yaml` in the stack has a `spec_version` the validator has the schema for (the file is then validated against that schema, by the schema layer) | 0007 §6 |
| `UNRESOLVED_ADDRESS` | MUST | Every address resolves, through the declarations, to an element of the kind its field takes: an input or output in `Output.inputs`, a decision in `Output.decisions` and in `Universe.decisions` keys, a decision in conditions and option references, an output in `Evidence.artifact` | 0004 |
| `UNKNOWN_OPTION` | MUST | Every option named by a condition, option reference or selection is one of its decision's options | 0003, 0004 |
| `INVALID_INSIGHT_REF` | MUST | Every entry of `Option.insights` names a prior insight of the analysis | main |
| `UNDECLARED_TEMPLATE_REF` | MUST | Every recipe placeholder is `{inputs}`, `{output}`, `{{`, `}}`, or an `{inputs.<entry>}` or `{decisions.<entry>}` whose `<entry>` is an entry of its output's `inputs` or `decisions` exactly as written | 0003, 0004 |
| `AMBIGUOUS_ID` | MUST | No two elements that one field could resolve to share an id (an input and an output, both of which `Output.inputs` takes) | tidy-up, §4 |
| `CLASHING_RESULT_NAME` | MUST | No output shares its id with a declaration of the same analysis | tidy-up, §4, §8 |
| `DECLARATION_OUTSIDE_REPOSITORY` | MUST | A declaration's `path` stays inside the declaring analysis's repository | 0004, 0007 §1 |
| `MISSING_DECLARED_ANALYSIS` | MUST | A declaration's `path` (at its `commit`, if it has one), or the top level of its `url`'s repository at its `commit`, holds an `astra.yaml` file, with no symlink on the way (§3) | 0004, 0007, §3 |
| `COMMIT_NOT_FOUND` | MUST | A declaration with a `path` and a `commit`, in a file not read from a remote, names a commit the declaring analysis's repository has | 0007, §3, §7 |
| `COMMIT_NOT_ANCESTOR` | SHOULD | A declaration with a `path` and a `commit` names an ancestor of the commit the declaration is in or, for a declaration read in the working tree, of HEAD or (during a merge) MERGE_HEAD of the repository that holds the declaring file | 0007, §3 |
| `REMOTE_UNREACHABLE` | MUST | Every commit the stack gets from a remote, through a `url`, a file read from a remote or a gitlink crossed at a commit, can be fetched from that remote or was kept from an earlier fetch | 0007 §6, tidy-up, §3, §7 |
| `DECLARED_ANALYSIS_INVALID` | MUST | An analysis from a commit, with everything it declares, is valid at that commit, `REMOTE_UNREACHABLE` aside | 0007, §7 |
| `MISSING_INPUT_FILE` | MUST | An input's `path` names a file (not a symlink, directory or gitlink), or something the validator recognises as standing in for one (§5) | 0006, §3 |
| `INPUT_NOT_TRACKED` | MUST | An input's file, or what stands in for it (§5), is in the index of the repository that holds the input's analysis or, read at a commit, in that commit's tree there, reached through no gitlink | 0006, §3 |
| `INPUT_IN_ANOTHER_ANALYSIS` | MUST | An input's file is outside every analysis within its analysis's directory (a directory below it with an `astra.yaml` of its own) | 0006 |
| `RESERVED_PATH` | MUST | No input's `path` and no declaration's `path`, with `.`, `..` and repeated `/` resolved, is or lies in the `results/` or `.astra/` of an analysis of the stack | tidy-up, §3 |
| `UNKNOWN_DERIVED_FROM` | MUST | A universe's `derived_from` names a universe of the same analysis | 0003 |
| `DERIVED_FROM_CYCLE` | MUST | No universe's chain of `derived_from` loops | 0003 |
| `MISSING_DECISION` | MUST | Every universe's effective selection sets every active decision of its analysis and of every analysis reached through a declaration that a universe of its analysis drives | 0003, 0004, tidy-up, §6, §7 |
| `INACTIVE_DECISION` | MUST | A universe itself sets only decisions whose `when` holds in its effective selection | 0003 |
| `MISSING_REQUIRED_OPTION` | MUST | Every effective selection satisfies the `requires` of every option it selects | 0003 |
| `INCOMPATIBLE_OPTIONS` | MUST | Every effective selection satisfies the `incompatible_with` of every option it selects | 0003 |
| `EXCLUDED_OPTION_SELECTED` | MUST | No effective selection selects an excluded option | main, tidy-up |
| `PARTIALLY_DRIVEN` | MUST | Every chain of declarations from an analysis's file is driven by all of the analysis's universes or by none, judged on their effective selections | 0004, tidy-up, §6, §7 |
| `DUPLICATE_ELEMENT` | MUST | No list of addresses, references, option references or conditions holds two spellings of one entry, and no universe's own `decisions` has two keys that spell one decision | tidy-up, §4, §6 |
| `CONFLICTING_SELECTIONS` | MUST | Every spelling of one decision in a universe's effective selection selects the same option | 0004, tidy-up, §6, §7 |
| `NOT_BUILT_IN_UNIVERSE` | MUST | Every output built per universe of another analysis read without a pin, and every decision of another analysis consumed, belongs to an analysis built in the universe being built | 0004 |
| `UNDRIVEN_DECLARATION` | MUST | In the file of the analysis whose universe is being built, every address that reads another analysis's output built per universe without a pin, or consumes another analysis's decision, has its chain of declarations driven by the file's universes (a key in their effective selections goes through every declaration of the address, or the last declaration's analysis has no decisions and no universes of its own, the chain before it is driven, and that declaration leads back to no analysis already on the chain) | 0004, tidy-up, §7 |
| `INPUT_NOT_BUILT` | MUST | Every output read without a pin is active (its `when` holds) in the universe being built | 0004 |
| `PIN_ON_INPUT` | MUST | Every pinned reference names an output | 0003 |
| `UNKNOWN_PIN_UNIVERSE` | MUST | Every pin, read in the file it is written in, names a universe of the first analysis along its reference, starting from that file's own, whose universes drive the reference's declarations from that analysis's file to its last, or, where there is none, of the analysis whose output it is | 0003, 0004, tidy-up, §7 |
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

A record is a document, read by the parse and schema rules (§3). A checker
doesn't report a record's breach of one of them as an error of its own: the
record breaks `INVALID_RECORD`, so its result is `missing`, and the checker
reports `INVALID_RECORD` with each code the record breaks as its reason, the
parser's (`INVALID_SYNTAX` or `DUPLICATE_KEY`) or the one `rules.json` gives
the schema error (§10).

**Statuses.** A checker gives every planned result two statuses, one for its
record (`unchanged`, `stale` or `missing`) and one for its bytes (`present`
or `absent`). Evidence citing a result gets that result's first status. A
result with two names has its statuses at each place. Evidence citing an
output built per universe without a pin gets the worst first status of that
output's results (`missing`, then `stale`), and `missing` when there are
none.

| Status | Means |
|---|---|
| `unchanged` | The result has a valid record where its address says, and `STALE_RESULT` holds |
| `stale` | The result has a valid record where its address says, and `STALE_RESULT` doesn't hold. The checker says what changed |
| `missing` | The result has no valid record where its address says: `MISSING_RECORD`, `INVALID_RECORD` (including a record that breaks a parse or schema rule), `MISPLACED_RECORD` or `MISSING_RECORD_INPUTS` doesn't hold |
| `present` | The bytes at the result's default place hash to the record's `content_hash` and have its `size` |
| `absent` | Anything else is at the default place, nothing, a stand-in or other bytes included |

**Rules.**

| Code | Level | Rule | Status when broken | Source |
|---|---|---|---|---|
| `MISSING_RECORD` | MUST | Every planned result has a record at `.astra/records/{universe}/{name}.json` (or `{name}.json` for an output built once), for each of its names, in the analysis it belongs to | `missing` | 0005 §1 |
| `INVALID_RECORD` | MUST | The record at each planned result's place breaks no parse rule, and no schema rule against the record schema of its `spec_version`, or against the open variant when that version is newer than the checker's | `missing` | 0005 §2, tidy-up, §3, §8 |
| `MISPLACED_RECORD` | MUST | The record at each planned result's place has, as its `address`, the address that place is worked out from | `missing` | 0005 §1 |
| `MISSING_RECORD_INPUTS` | MUST | The record at each planned result's place has exactly one `inputs` item for each entry its output lists at the commit the record names, matched by `entry`, and no other item (their order carries no meaning) | `missing` | 0005 §2 |
| `STALE_RESULT` | MUST | Since the commit in a result's record, nothing has changed in its output's declaration (command, inputs and their order, decisions, format), its decisions' options, the content of its inputs, never what stands in for it, or the results it reads | `stale` | 0005 §4 |
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
| `UNRECREATABLE_ENVIRONMENT` | MUST | A runner records each recipe's environment as an IRI that it can recreate at its version | 0005 §3 |
| `UNCOMMITTED_CHANGES` | MUST | A runner runs each recipe in a checkout of a commit whose only changes are the records and results it writes itself, each result's bytes the recorded ones, and what a tool keeps of, or puts in place to drive, an analysis from a commit | 0005 §3, 0007 §2, 0007 §7 |
| `WRONG_WORKING_DIRECTORY` | MUST | A runner runs each recipe in the directory of the recipe's own analysis, in the checkout it runs in, even when another analysis drives it | 0004 §1, 0004 §5 |
| `NOT_AT_COMMIT` | MUST | A runner drives an analysis from a commit on exactly its files at that commit | 0007 §7 |
| `REBUILT_FROM_COMMIT` | MUST | A runner builds no result that belongs to an analysis from a commit, or to an analysis reached from it through declarations, and reads each such result through its record at the commit that analysis is read at | 0007 §3, 0007 §7 |
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
  which fails on nothing. A key that isn't a string is reported without
  them: it has no JSON form, so a tool reports it from the parsed YAML, as
  [`INVALID_ID`](#parse-and-schema) at its map (§3). A tool that hands its
  validator the key unconverted gets the same code at the same place only in
  a map keyed by an id or an address, through the entry of `propertyNames`'
  `type`: among a document's or an entry's fields, it gets
  [`UNKNOWN_FIELD`](#parse-and-schema) from `additionalProperties`.
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

A checker maps a record's errors the same way, through the record schema it
reads the record by, closed or open. It doesn't report them as errors of
their own: it reports [`INVALID_RECORD`](#check) for the record's result, with
the code of each error as its reason, and with the parser's code
([`INVALID_SYNTAX`](#parse-and-schema) or
[`DUPLICATE_KEY`](#parse-and-schema)) for a record that fails at parse (§3).

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

Before `toJS()`, a tool walks the document twice more. The first walk
refuses a scalar, a key included, holding a number that isn't
`Number.isFinite` or a string that isn't `isWellFormed()`
([`INVALID_SYNTAX`](#parse-and-schema)): `yaml` reads `.inf`, `.nan`, `1e400`
and an integer of 400 digits as numbers that aren't finite, and the escape of
a lone surrogate as that surrogate. `yaml` reads an escaped pair as one
character, as §3 does, and an integer beyond 2<sup>53</sup> rounded, which no
check depends on. The second walk goes through the document's maps from the
top, reporting each pair whose key isn't a `Scalar` holding a string as
[`INVALID_ID`](#parse-and-schema) at its map, and deleting the pair without
walking into it. Without it, `toJS()` would turn the key `true` into the
valid id `"true"`, and keep only one of `true` and `"true"` in one map.
`yaml`'s `uniqueKeys: true` compares keys by value alone, so a tool passes
instead a function that compares them as §3 does: by tag (resolved from a
plain scalar's `source` by the table, since `yaml` keeps none) and canonical
form. Then `1` and `1.0` are two keys, and `? [a]` written twice is one.

A tool decodes a file's bytes itself, as UTF-8 that raises on any other byte
(§3): with `new TextDecoder('utf-8', {fatal: true})`, which skips a leading
byte order mark, before `yaml`, which takes only a string, and with
`bytes.decode('utf-8')` before ruamel.yaml, whose own reader also takes
UTF-16. Neither stock loader then reads characters, tabs and line breaks as
§3 does. ruamel.yaml refuses a tab used as white space outside a flow
collection or a quoted scalar, reads NEL, LS and PS as line breaks, refuses
DEL, the C1 controls other than NEL, U+FFFE and U+FFFF even in a quoted
scalar, and keeps U+FEFF in a plain scalar;
[the test harness's loader](https://github.com/LightconeResearch/astra-spec/blob/main/tests/conftest.py)
shows one way to correct each. `yaml` keeps a CR that no LF follows as
content, so a tool replaces each such CR with an LF before parsing, which
changes nothing else, since YAML 1.2.2 §5.4 makes every CR in the text a line
break. `yaml` checks no characters, so a tool refuses a C0 control other than
tab, LF and CR anywhere in the text, and reads the source of each plain
scalar, block scalar, comment and directive from the CST, refusing DEL, a C1
control other than NEL, U+FEFF, U+FFFE and U+FFFF in it. A tool also refuses
every `byte-order-mark` token, since `TextDecoder` has already removed the
one that may start the file ([`INVALID_SYNTAX`](#parse-and-schema)).

**Reading records.** The parse layer for a record is a JSON parser that
refuses what RFC 8259 leaves to the parser (§3), and neither stock parser is
one. Python's `json.loads` reads `NaN`, `Infinity` and `-Infinity`, keeps the
last of two repeated names, reads `1e400` as an infinity, and reads the
escape of a lone surrogate as that surrogate; given bytes, it also skips a
byte order mark and reads UTF-16 and UTF-32. So a tool decodes the bytes
itself, as UTF-8 that raises on any other byte, refuses a leading U+FEFF, and
passes `json.loads` an `object_pairs_hook` that refuses a repeated name, a
`parse_constant` that refuses whatever it is given, and a `parse_float` and a
`parse_int` that refuse a number beyond a double's range; then it walks the
value, refusing a string that holds a surrogate. In JavaScript, `JSON.parse`
refuses `NaN` and a byte order mark, but keeps the last of two repeated
names, reads `1e400` as `Infinity` and keeps a lone surrogate, and
`TextDecoder` skips a byte order mark and replaces bytes that aren't UTF-8
unless it is made with `{fatal: true, ignoreBOM: true}`. So a tool decodes
with those options, refuses a leading U+FEFF, parses with a parser that
reports a repeated name, and refuses a number that isn't `Number.isFinite`
and a string that isn't `isWellFormed()`.

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
