# The ASTRA specification

ASTRA records a research **analysis**, a folder in a git repository with an
`astra.yaml` at its top, so that every choice in it is explicit and every
result can be checked against how it was made. Analyses communicate
natively, sharing inputs, outputs and decisions by address. A **validator**
checks the files against git, a **runner** builds the results from committed
files and writes a **record** of how each was made, and a **checker** later
compares each record with the analysis as it then is.

## Elements

An `astra.yaml` (YAML 1.2) gives its `spec_version` (`"0.1.0"`) and maps of
**elements**, each keyed by its **id** (`[a-z][a-z0-9_]*`). The snippets
below are parts of `analysis/astra.yaml`, the file of the analysis in the
folder `analysis/`, and its paths are relative.

- An analysis can **declare** other analyses:

  ```yaml
  # analysis/astra.yaml
  analyses:
    stage: {path: stage}
    previous: {path: ., commit: <commit id>}
    module: {path: module, commit: <commit id>}
    upstream: {url: <url of a git repository>, commit: <commit id>}
  ```

  - `stage`: the folder `analysis/stage/`, read from the working tree, which,
    once committed, lets it be built
  - `previous`: `analysis/` itself at a commit
  - `module`: a git submodule at `analysis/module/`, as `analysis`'s
    repository holds it at that commit
  - `upstream`: a remote repository at a commit

  Elements of a declared analysis are obtained by **address** (declarations
  followed by an element, joined by dots): `stage.output3` points to
  `output3` defined in `stage`.

  The folder at its commit, or in the working tree, is the analysis's
  **identity**: one folder at one commit is one analysis however it is
  declared, and **another analysis** is one with another identity.

- An **input** is one file, tracked in git with its analysis, at a `path`
  from the analysis's folder; a **stand-in**, such as a large-file pointer,
  may take its place where a tool recognises it.

  ```yaml
  inputs:
    input1: {path: data/input1.csv}
  ```

  The `path` stays inside the analysis's folder, outside `results/`,
  `.astra/` and any folder contained within the analysis's folder with its
  own `astra.yaml`. Another analysis's input is read by address in an output
  (`stage.input2`); other data, such as a download, comes in as an output
  whose recipe gets it.

- A **decision** lists the **options** of a scientific choice. An option may
  be **excluded** with a reason, cite prior `insights`, and carry
  **constraints**: options it `requires` or is `incompatible_with`, by
  **option reference**, a decision's address then an option's id
  (`decision1.b`, `stage.decision2.b`).

  ```yaml
  decisions:
    decision1:
      rationale: Both are reasonable, and they may give different results.
      options:
        a:
          insights: [insight2]
        b:
          requires: [stage.decision2.b]
        c:
          excluded: It needs data this analysis doesn't have.
  ```

  - `insight2` supports option `a`
  - `b` requires `stage`'s `decision2` to be `b`
  - `c` is excluded and never selected

- An **output** has a `type`, a `format` (its file extension), the
  `decisions` it is made with, what it reads (`inputs`, ordered), and a
  **recipe**: a POSIX shell `command`, run in its analysis's folder, whose
  **placeholders** `{inputs}`, `{inputs.<entry>}`, `{decisions.<entry>}` and
  `{output}` become paths and selected options, verbatim. Its **result** is
  the one file the recipe writes.

  ```yaml
  outputs:
    output1:
      type: metric
      format: json
      inputs: [input1, stage.output3, upstream.output4]
      decisions: [decision1, stage.decision2]
      recipe:
        command: python src/output1.py {inputs} {decisions.decision1} {decisions.stage.decision2} {output}
  ```

  Another analysis's elements are read by address in an output's `inputs`
  and `decisions`, a condition, a constraint or evidence, just as if they
  were the analysis's own: `output1` reads `stage`'s `output3` and is made
  with `stage`'s `decision2`, whatever option is selected where it is built.

- A `when` lists **conditions**, `d.o` (decision `d` selects option `o`) or
  `~d.o` (decision `d` doesn't select option `o`).

  ```yaml
  decisions:
    decision3:
      when: [decision1.b, stage.decision2.b]
      options: {a: {}, b: {}}
  ```

  - `decision3` is only active when `decision1` selects `b` and `stage`'s
    `decision2` selects `b`; an output can have a `when` too

- A **universe** selects an option for each active decision: its own
  analysis's by id, another's by address. With `derived_from` it inherits
  another universe's selection, replacing what it sets and dropping what
  turns inactive: its **effective selection**.

  ```yaml
  universes:
    u1:
      decisions:
        decision1: b
        decision3: a
        stage.decision2: b
    u2:
      derived_from: u1
      decisions: {decision1: a}
  ```

  - `u1` sets `stage`'s `decision2`: it **drives** `stage` (below)
  - `u2` changes `decision1` from `u1`'s `b` to `a`, keeps `stage.decision2`
    as `b`, and drops `decision3`, whose `when` no longer holds

- An entry of an output's `inputs` is a **reference**: an address that may
  end in a **pin**, `#` and a universe's id, fixing the universe it reads.
  `#u` names, in order:
  1. the `universes` entry `u` in the same `astra.yaml` as the pin;
  2. else the universe `u` of the declared analysis whose output is read;
  3. else nothing, which breaks `UNKNOWN_PIN_UNIVERSE`.

  ```yaml
  outputs:
    output2:
      type: table
      format: csv
      inputs: [output1#u1, output1#u2, stage.output3#v1]
      recipe:
        command: python src/output2.py {inputs} {output}
  ```

  - `output2` reads `output1` as built in `u1` and in `u2`
  - `analysis` has no `v1`, so `stage.output3#v1` reads `stage`'s own
    result in its `v1`

- An output is **built per universe** if it lists `decisions`, has a `when`,
  or reads an output that is built per universe without a pin; it has a
  result in each universe where it is active. Any other output is **built
  once** with one result:

  ```yaml
  outputs:
    output1:
      decisions: [decision1, stage.decision2]
      ...
    output2:
      inputs: [output1#u1, output1#u2]
      ...
  ```
  - `output1` is built per universe because it lists decisions
  - `output2` is built once because it only reads `output1` pinned to specific universes

  Were it also to have:

  ```yaml
  outputs:
    output6:
      when: [decision1.b]
      ...
    output7:
      inputs: [output1]
      ...
  ```
  - `output6` is built per universe because it depends on a decision via `when`
  - `output7` is built per universe because it reads `output1`, which is
    built per universe, without a pin

- The analysis being validated or built, here `analysis`, is the **driving
  analysis**. Its universes can set the decisions of the analyses it declares, and of those
  they declare in turn; where they do, it **drives** them:

  ```yaml
  universes:
    u1:
      decisions:
        ...
        stage.decision2: b
  ```

  In `u1`, `stage` is built with `decision2: b`, whatever its own universes
  say. The `stage.output3` that `output1` reads is built with `b` selected
  for `stage.decision2`, and its result belongs to `analysis`.

  A universe sets a decision further down by its full address. Were `stage`
  to declare `inner`, which has a `decision4`:

  ```yaml
  universes:
    u1:
      decisions:
        ...
        stage.decision2: b
        stage.inner.decision4: a
    u2:
      derived_from: u1
      decisions: {decision1: a}
  ```
  - `stage.inner.decision4` drives `stage` and drives `inner` through `stage`


  The analyses an address goes through, here `stage` then `inner`, form a
  **chain**. Once any universe drives a chain, every universe must set all
  the active decisions of the analyses on it: had `u2` not derived from
  `u1`, it would have to set `stage.decision2` and `stage.inner.decision4`
  itself.

  - Each chain is driven on its own. Were `analysis/astra.yaml` also to declare
    `inner` directly, and set none of its decisions:

    ```yaml
    analyses:
      inner: {path: stage/inner}
    outputs:
      output11:
        inputs: [inner.output8]
        ...
    ```

    this chain isn't driven, even though `stage.inner` is. Through it,
    `output11` can read `inner`'s outputs built once, or pinned to `inner`'s
    own universes, but not one built per universe in `u1` or `u2`.

  - An analysis with no decisions of its own has nothing to set. Were
    `analysis/astra.yaml` also to declare `tools`, which has none:

    ```yaml
    # analysis/tools/astra.yaml
    analyses:
      parent: {path: ..}
    inputs:
      input3: {path: data/input3.csv}
    outputs:
      output9:
        inputs: [input3]
        ...
      output10:
        decisions: [parent.decision1]
        ...
    ```

    - `tools.output9` just exists as `tools`'s result
    - `tools.output10` varies, so it is built in `u1` and `u2`, and those
      results belong to `analysis`

  - An analysis never drives itself. A universe can't set a decision through
    a declaration that leads back, such as `self: {path: .}`, or `stage`'s
    `parent: {path: ..}`. Writing `self.decision1: b` instead of
    `decision1: b` would break `LOOPING_KEY`:

    ```yaml
    universes:
      u1:
        decisions:
          decision1: b       # self.decision1: b would break LOOPING_KEY
    ```

  - `stage`'s own universes, such as `v1`, don't set its decisions in `u1`
    and `u2`, but must still be valid: a `v1` that left `decision2` unset
    would break `MISSING_DECISION`.

  - An output that reads another analysis's output built per universe,
    without a pin or pinned to one of its own analysis's universes
    (`stage.output3#u1`), or uses one of its decisions, needs that analysis
    driven.
    `output1` reads `stage.output3` and uses `stage.decision2`, so were no
    universe of `analysis` to set a decision of `stage`:

    ```yaml
    universes:
      u1:
        decisions: {decision1: b}   # nothing of stage's: stage isn't driven
    ```

    `output1` would break `NOT_BUILT_IN_UNIVERSE`: nothing would say which
    `decision2` to build `stage.output3` with. It could still read what
    doesn't vary: `stage.input2`, `stage.output3#v1`, or `upstream.output4`,
    which is built once.

  By convention, a decision that matters to one analysis is driven, and one
  shared by several, such as a seed, is read by address from the analysis
  that holds it.

- Were `stage` to have a `u1` of its own, `#u1` in `analysis/astra.yaml`
  would still name `analysis`'s. To read `stage`'s own `u1` too it must be **imported** under
  another id and pinned to that. An import
  selects and drives nothing.

  ```yaml
  universes:
    stage_u1: {analysis: stage, universe: u1}
  outputs:
    output5:
      type: table
      format: csv
      inputs:
        - stage.output3#u1
        - stage.output3#stage_u1
      recipe:
        command: python src/output5.py {inputs} {output}
  ```

  - `stage.output3#u1` is built in, and belongs to, `analysis`'s `u1`
  - `stage.output3#stage_u1` is built in `stage`'s own `u1` and belongs to
    `stage`

- An **insight** is a `claim` whose `evidence` cites a `doi` or an output
  (`artifact`): `prior_insights` are what the analysis builds on, `findings`
  what it concludes. An `artifact` is a reference, like an output's `inputs`
  entry: it may be pinned, and by address it reads another analysis's
  output.

  ```yaml
  prior_insights:
    insight2:
      claim: An earlier study found that decision1 changes the result.
      evidence:
        - doi: 10.5555/12345678
          location: {value: page=6}
  findings:
    insight1:
      claim: The two universes give different results.
      evidence:
        - artifact: output2
  ```

## Results

- A **result** is the one file an output's recipe writes: an output built
  once has one, and an output built per universe has one in each universe
  where it is active. The driving analysis **plans** the results of its own
  outputs, and every result a planned result reads or its evidence cites,
  through any declaration; nothing else is built. A result belongs to the
  analysis whose universe built it or, for an output built once, the
  analysis whose output it is. With `stage`'s own file:

  ```yaml
  # analysis/stage/astra.yaml
  spec_version: "0.1.0"
  inputs:
    input2: {path: data/input2.csv}
  decisions:
    decision2:
      options: {a: {}, b: {}}
  outputs:
    output3:
      type: data
      format: csv
      inputs: [input2]
      decisions: [decision2]
      recipe:
        command: python src/output3.py {inputs.input2} {decisions.decision2} {output}
  universes:
    v1:
      decisions: {decision2: a}
  ```

  the build is:

  ```text
  ┌─ u1 · analysis's own ────────────────────────────────┐
  │  input1 ────────────────────────┐                    │
  │  stage.output3 (decision2 = b) ─┼─► output1          │── #u1 ──┐
  │  upstream.output4 ──────────────┘   (decision1 = b)  │         │
  └──────────────────────────────────────────────────────┘         │
  ┌─ u2 · analysis's own ────────────────────────────────┐         │
  │  input1 ────────────────────────┐                    │         ▼
  │  stage.output3 (decision2 = b) ─┼─► output1          │── #u2 ──► output2 ◄── insight1
  │  upstream.output4 ──────────────┘   (decision1 = a)  │         ▲
  └──────────────────────────────────────────────────────┘         │
  ┌─ v1 · stage's own ───────────────────────────────────┐         │
  │  output3 (decision2 = a)                             │── #v1 ──┘
  └──────────────────────────────────────────────────────┘
  ```

  - the planned results are `output2`, `output1` in `u1` and `u2`,
    `stage.output3` in `u1`, `u2` and `v1`, and `upstream.output4`

- A **runner** builds each planned result by running its output's recipe in
  a checkout of a commit, with no changes but records and results, and
  writes the result's bytes and a **record** of how it was made. Results of
  an analysis declared with a `commit`, and of those it reaches, are
  **results from a commit**: never rebuilt, but read through their records,
  and their bytes (or a stand-in), at their analysis's commit. Driven, such
  an analysis runs its recipes on exactly its files at its commit.
  - at its commit, `upstream` has an output `output4`, built once, with its
    result and record committed: the runner reads them and runs no recipe
    of `upstream`'s
  - `previous` reads the analysis's own earlier results the same way

- A **record** holds what its commit can't give: the result's address,
  content hash and size and, under `generated_by`, the commit it was made
  from, the hash and size of each input by its entry, the environment it ran
  in and the runner. The record of `output1` in `u1`:

  ```json
  {
    "spec_version": "0.1.0",
    "address": "output1#u1",
    "content_hash": "sha256:<hash>",
    "size": <size>,
    "generated_by": {
      "commit": "<commit id>",
      "inputs": [
        {"entry": "input1", "content_hash": "sha256:<hash>", "size": <size>},
        {"entry": "stage.output3", "content_hash": "sha256:<hash>", "size": <size>},
        {"entry": "upstream.output4", "content_hash": "sha256:<hash>", "size": <size>}
      ],
      "environment": {"iri": "urn:example:environment1"},
      "runner": {"id": "example-runner", "version": "1.0.0"}
    }
  }
  ```

- A **checker** later compares each record with the analysis as it then is,
  and gives each planned result a record status:
  - **missing** if there is no record, or one that doesn't parse or meet its
    schema, names another address, or doesn't list exactly the inputs its
    output had at the record's commit;
  - else **stale** if anything it is **made from** has changed since the
    record's commit;
  - else **unchanged**.

- A result is **made from** its output's command, inputs in order, decisions
  and format; the options those decisions select in its universe; its
  inputs' content, never a stand-in's; and the results it reads. Code (fixed
  by the commit) and the environment (installed software, container) are
  recorded, not compared: an edited script shows only once a rerun makes
  other bytes. A result made from a stale or missing one is stale until that
  one is rebuilt with the hash it recorded. A record otherwise in order
  leaves its result stale if its commit can't be read (squashed or rebased
  away) or its output is gone at that commit, where `MISSING_RECORD_INPUTS`
  isn't judged, or if an input is behind a stand-in that gives no hash. In
  the example:

  | Edit | Effect |
  |---|---|
  | `analysis/stage/data/input2.csv` changes | The six results built are stale; `upstream.output4` stays unchanged |
  | `u2` selects `a` for `stage.decision2` | `stage.output3` and `output1` in `u2` are stale, and so is `output2`, which reads `output1#u2` |
  | `insight1`'s claim is reworded | Every result stays unchanged |
  | `analysis/src/output1.py` is edited | Every result stays unchanged; once `output1` is rebuilt with other bytes, `output2` is stale |

- A result's bytes are **present** if its default place (below) holds the
  recorded ones, else **absent**. The record of a result from a commit, at
  the declared commit B, names an earlier commit A; the result is unchanged
  if nothing compared changed between A and B and the results it was made
  from are unchanged, and gets a bytes status, from what B holds, only if a
  recipe reads it.

- **Evidence** takes the status of the result it cites. Citing an output
  built per universe without a pin, it cites its results in each of the
  driving analysis's universes where it is active and its analysis built:
  none means `missing`, several the worst status. A check covers a declared
  analysis's evidence only where it cites a planned result.

- A result's **name** is its output's id after the driven declarations
  leading there from the analysis it belongs to (`stage.output3`); two
  driven chains give two names. Its **address** adds `#` and its universe's
  own id (`stage.output3#u1`). Each name gives the result, in the folder of
  the analysis it belongs to, a **place** for its record,
  `.astra/records/{universe}/{name}.json`, and a **default place** for its
  bytes, `results/{universe}/{name}.{format}`; built once, neither has
  `{universe}/`. The build above leaves:

  ```text
  analysis/.astra/records/output2.json             analysis/results/output2.csv
  analysis/.astra/records/u1/output1.json          analysis/results/u1/output1.json
  analysis/.astra/records/u1/stage.output3.json    analysis/results/u1/stage.output3.csv
  analysis/.astra/records/u2/output1.json          analysis/results/u2/output1.json
  analysis/.astra/records/u2/stage.output3.json    analysis/results/u2/stage.output3.csv
  analysis/stage/.astra/records/v1/output3.json    analysis/stage/results/v1/output3.csv
  ```

## Rules

Each rule has a code, a level (MUST or SHOULD, as in BCP 14) and a layer, set
by what its tool sees: one file (parse, schema), the stack's files and git
(validator), also records and results (check), or its own runs (runner). The
driving analysis's **stack** is it and every analysis it declares, directly or
not. In the first four layers a broken MUST is an error and a broken SHOULD a warning;
a runner that breaks a MUST doesn't conform. A file is **valid** if it breaks
no parse or schema rule, read by the schema of its `spec_version`'s minor
version (`0.1` for `0.1.2`); an analysis is valid if no analysis of its stack
breaks a MUST of the first three layers. A broken check rule gives the status
after the arrow. Rows that share a code are cases of one rule.

| Code | Level | Rule |
|---|---|---|
| **parse** | | |
| `INVALID_SYNTAX` | MUST | An `astra.yaml` is a YAML 1.2 document holding a map |
| `INVALID_SYNTAX` | MUST | A record is UTF-8 JSON text, no object repeating a name |
| **schema** | | |
| `MISSING_FIELD` | MUST | `astra.yaml` has `spec_version` and `outputs`; an output, `type`, `format` and `recipe.command` |
| `MISSING_FIELD` | MUST | An input has `path`; a decision, `options`; an insight, `claim`, `evidence`; `quote`, `exact`; `location`, `value` |
| `MISSING_FIELD` | MUST | A record has every field but `started`, `finished` and `inputs` |
| `UNKNOWN_FIELD` | MUST | Every field is one the schema defines |
| `WRONG_TYPE` | MUST | Every value has its field's JSON type, never null (leave an optional field out) |
| `EMPTY_COLLECTION` | MUST | `outputs`, `options`, `evidence` and every list of strings in `astra.yaml` are non-empty |
| `DUPLICATE_ENTRY` | MUST | No list of strings holds one entry twice |
| `INVALID_VALUE` | MUST | `type` is `metric`, `figure`, `table`, `data` or `report`; `format` matches `^[a-z0-9][a-z0-9_.+-]*$` |
| `INVALID_VALUE` | MUST | Every `spec_version`, hash, IRI, time, `doi`, `url` and location `value` has its form |
| `INVALID_VALUE` | MUST | `size` ≥ 0, evidence `version` ≥ 1, `resources.cpus` ≥ 0, `resources.gpus` ≥ 1 |
| `INVALID_ID` | MUST | Map keys and id-typed values are ids; a universe's `decisions` keys are addresses |
| `INVALID_REFERENCE` | MUST | Every address, reference, option reference and condition, bar universe keys, matches its grammar |
| `INVALID_PATH` | MUST | Every input's and declaration's `path` is non-empty and doesn't start with `/` |
| `INVALID_IMPORT` | MUST | A `universes` entry with `analysis` or `universe` has both, and no `decisions` or `derived_from` |
| `INVALID_EVIDENCE_SOURCE` | MUST | Evidence has exactly one of `doi` and `artifact`, and `version` only with `doi` |
| `INVALID_DECLARATION_SOURCE` | MUST | A declaration has exactly one of `path` and `url` |
| `URL_WITHOUT_COMMIT` | MUST | A declaration with a `url` has a `commit` |
| `INVALID_COMMIT` | MUST | Every `commit` is a full commit id: 40 or 64 lowercase hex digits |
| **validator** | | |
| `NOT_IN_REPOSITORY` | MUST | The driving analysis is in a git repository's working tree |
| `MISSING_INPUT_FILE` | MUST | An input's `path` names a file (no symlink, folder or gitlink) or a stand-in |
| `INPUT_NOT_TRACKED` | MUST | An input's file or stand-in is tracked in its analysis's repository |
| `INPUT_IN_ANOTHER_ANALYSIS` | MUST | An input's file is in its analysis's folder, in no **nested analysis** (a folder below with an `astra.yaml`) |
| `RESERVED_PATH` | MUST | No input or declaration `path` is, or lies inside, a stack analysis's `results/` or `.astra/` in its tree |
| `MISSING_DECLARED_ANALYSIS` | MUST | A declared folder holds an `astra.yaml`, reached through no symlink |
| `DECLARATION_OUTSIDE_REPOSITORY` | MUST | A tidied declaration `path` doesn't go above the top of the driving analysis's working tree or, at a commit, of its repository |
| `COMMIT_NOT_FOUND` | MUST | In a file not read from a remote, a `path` and `commit` name a commit of the file's repository |
| `DECLARED_ANALYSIS_INVALID` | MUST | An analysis from a commit, with all it declares, is valid at that commit |
| `UNRESOLVED_ADDRESS` | MUST | An address in `inputs` reaches an input or output; in `artifact`, an output |
| `UNRESOLVED_ADDRESS` | MUST | In `decisions`, universe keys, conditions and option references, a decision; in an import, another analysis's universe |
| `AMBIGUOUS_ID` | MUST | No input and output of one analysis share an id |
| `CLASHING_RESULT_NAME` | MUST | No output shares its id with a declaration of its analysis |
| `UNKNOWN_OPTION` | MUST | Each option a condition, option reference or selection names is one of its decision's |
| `INVALID_INSIGHT_REF` | MUST | An option's `insights` name prior insights of its analysis |
| `OUTPUT_CYCLE` | MUST | No output reads itself through `inputs`, directly or not, pinned or not |
| `UNDECLARED_TEMPLATE_REF` | MUST | Every brace of a `command`, read from the left, is in `{{`, `}}` or a placeholder |
| `UNDECLARED_TEMPLATE_REF` | MUST | Placeholders are `{inputs}`, `{output}`, and `{inputs.<entry>}` or `{decisions.<entry>}` for entries as listed |
| `UNKNOWN_DERIVED_FROM` | MUST | `derived_from` names a universe of its analysis, never an import |
| `DERIVED_FROM_CYCLE` | MUST | No chain of `derived_from` loops back to its universe |
| `INACTIVE_DECISION` | MUST | A universe's own `decisions` set only decisions active in its effective selection |
| `MISSING_DECISION` | MUST | An effective selection sets every active decision of its analysis and of those its universes drive |
| `MISSING_REQUIRED_OPTION` | MUST | An effective selection meets the `requires` of each option it selects |
| `INCOMPATIBLE_OPTIONS` | MUST | An effective selection meets the `incompatible_with` of each option it selects |
| `EXCLUDED_OPTION_SELECTED` | MUST | No effective selection selects an excluded option |
| `DUPLICATE_ELEMENT` | MUST | No two keys of a universe's own `decisions` name one decision |
| `DUPLICATE_ELEMENT` | MUST | A universe sets an inherited decision only under the key it inherits |
| `LOOPING_KEY` | MUST | No universe key goes through a declaration that leads back |
| `UNKNOWN_PIN_UNIVERSE` | MUST | Every pin names a universe: its analysis's entry or, lacking one, that of the analysis whose output it reads |
| `PIN_INACTIVE` | MUST | Every pinned output is active in the universe it is pinned to |
| ***validator, in each universe where results are built*** | | |
| `INPUT_NOT_BUILT` | MUST | Every output a result planned in a universe reads without a pin is active there |
| `NOT_BUILT_IN_UNIVERSE` | MUST | An output reading another analysis's output built per universe, unpinned or pinned to a universe it is built in, or one of its decisions, reads it from an analysis built in that universe |
| `UNDRIVEN_DECLARATION` | MUST | In the file of a universe's analysis, every address using another analysis's element there has a driven chain |
| `RESULT_IN_TWO_PLACES` | SHOULD | No planned result has two names |
| **check** | | |
| `MISSING_RECORD` | MUST | Every planned result has a record at each of its places → `missing` |
| `INVALID_RECORD` | MUST | The record at each place parses; its minor version has a record schema or exceeds the checker's → `missing` |
| `INVALID_RECORD` | MUST | It meets that record schema or, if newer, the checker's open variant → `missing` |
| `MISPLACED_RECORD` | MUST | Its `address` is the one its place is worked out from → `missing` |
| `MISSING_RECORD_INPUTS` | MUST | Its `inputs` hold one item per entry its output lists at its commit, by `entry`, no more → `missing` |
| `STALE_RESULT` | MUST | Nothing the result is made from has changed since its record's commit → `stale` |
| `ABSENT_RESULT` | SHOULD | Its recorded bytes are at its default place, bar an unread result from a commit → `absent` |
| `STALE_EVIDENCE` | MUST | Evidence citing a result cites an unchanged one → the result's record status |
| **runner** | | |
| `UNRECORDED_RESULT` | MUST | A runner writes each result it makes: a record at each place, bytes at each default place |
| `FALSE_RECORD` | MUST | Every field of a record a runner writes is true of its run |
| `UNRECREATABLE_ENVIRONMENT` | MUST | A runner records each recipe's environment as an IRI it can recreate at its version |
| `UNCOMMITTED_CHANGES` | MUST | Each recipe runs in a commit's checkout changed only by records and recorded results |
| `UNCOMMITTED_CHANGES` | MUST | There, untracked files and submodules count as changes; ignored files don't |
| `WRONG_WORKING_DIRECTORY` | MUST | Each recipe runs in its own analysis's folder, even when driven |
| `NOT_AT_COMMIT` | MUST | A runner drives an analysis from a commit on exactly its files at that commit |
| `REBUILT_FROM_COMMIT` | MUST | A runner builds no result from a commit, and reads each through its record at its analysis's commit |
| `STALE_INPUT` | MUST | A runner builds nothing from a result from a commit that is missing, stale or lacks its recorded bytes |
| `UNDECLARED_READ` | SHOULD | A recipe reads input files and other results only through its output's `inputs` |
| `CODE_OUTSIDE_ANALYSIS` | SHOULD | Beyond its environment, a recipe runs only code its inputs give, or tracked in its analysis's folder outside nested analyses |

Recommendations and a permission that no tool checks:

| Who | Level | Recommendation or permission |
|---|---|---|
| A published analysis | SHOULD | declare only remotes its readers can fetch |
| Branches that hold records | SHOULD | be merged, not squashed or rebased |
| A runner | SHOULD | let someone see what an environment it recorded holds |
| A runner | MAY | enforce `UNDECLARED_READ` and `CODE_OUTSIDE_ANALYSIS`, failing a recipe that breaks one |

## Schema files

The schema is written in [LinkML](https://linkml.io/); its descriptions of
the fields are published as the field reference. These files are generated
from it, each at `https://w3id.org/astra/<minor version>/<file>`, shared by
every patch of that minor version:

| File | What it is |
|---|---|
| `analysis.schema.json` | the JSON Schema (2019-09) of `astra.yaml` |
| `provenance.schema.json` | the JSON Schema of a record |
| `provenance.open.schema.json` | the same, but allowing fields it doesn't define, for records of a newer minor version |
| `provenance.context.jsonld` | the JSON-LD context that reads a record as W3C PROV-O |
| `rules.json` | every rule's code, layer, level and statement, and the code of each schema keyword whose error can fail a file |

A file breaks no schema rule exactly when a JSON Schema 2019-09 validator
reports no error for it against its schema.
