# Rewriting the specification: design

- **Date:** 2026-11-05, decided with Tom.
- **Branch:** `v0.1-schema`.
- **Background:** the inventory of today's specification (scratch `rewrite/INVENTORY.md`), the parse-layer research (scratch `parse-layer/PROPOSAL.md`), and the review of astra-tools phase 0 (scratch `astra-tools-review/REPORT.md`).
- **Section numbers:** "§n" is a section of this design; "spec §n" is a section of the new specification.

## 1. What astra-spec is

astra-spec is ASTRA's specification and schema. That is what tools interface with:

- **The specification** (`docs/specification.md`) says how ASTRA works and what holds.
- **The schema** is the LinkML sources and what is generated from them: the JSON Schemas for `astra.yaml` and for records (closed and open), and the record's JSON-LD context.
- **`rules.json`** is built from the specification's codes tables and the schemas. It holds every rule's code, layer, level, statement and source, and a check rule's status. It also gives the code of every schema keyword whose error makes a document fail.
- **The docs site** renders the specification and the field reference, and publishes the schema files at their URIs. This work adds a generated page listing every rule (§6).

A tool that follows the specification and uses the schemas conforms. astra-tools will be the default tool, and other tools can come later. Nothing in the specification or the schema is shaped for astra-tools, and astra-spec gives no advice about particular libraries.

**Tests.** astra-spec keeps only the tests that are valuable to it now: those that show its own pieces are right and agree.

- The generated files are what the sources give, and the build tools do what they claim.
- Each schema constraint refuses what it should, and each parse and schema code has a document that breaks it.
- The schemas are standard JSON Schema that reads the same in any validator: ECMA-262 patterns as JSON Schema reads them, standard keywords, a strict compile, one `$id` per minor version.
- `rules.json` matches the specification and the schemas.
- The specification's grammars match the schema's patterns, and its examples break no parse or schema rule.
- The JSON-LD context reads a record as the specification's PROV-O mapping says.
- The site shows what `rules.json` says.
- A patch release changes nothing that is valid, and the wheel ships exactly the schema files.
- The test harness reads files as the parse layer says, which it needs in order to check the rest.

The documents these tests use are astra-spec's own. Among them is the `__proto__` fixture, which tests `DUPLICATE_ENTRY`. A conformance suite for tools is being built in its own chat, and may later live in astra-spec. What this work hands to it is in scratch `for-conformance.md`; what astra-tools should pick up is in scratch `for-astra-tools.md`.

## 2. Goal

The specification is correct but very hard to read, for people and AIs alike. The rewrite makes it the simplest, clearest description of how ASTRA works and what holds, with no more rules than ASTRA needs.

It is done when:

- a newcomer can read Part I and understand ASTRA;
- each element has one section, read from the ground up;
- what only tool builders need sits in terse annexes;
- no rule changes meaning except as §4 records;
- the spec names none of ASTRA's own RFCs and none of its history.

## 3. Principles

1. **Implementable with ordinary tools.** Every rule can be checked with a mainstream YAML 1.2 library's normal API, any JSON Schema validator, and git. A rule that needs a patched parser or custom machinery doesn't belong. Where libraries disagree on syntax nobody writes, that is the libraries' problem. During the rewrite, every rule is checked against this principle, and any that fails goes to Tom.
2. **Simple and stable, with no concessions to tooling.** The spec makes no allowances for particular libraries and offers tools no niceties. Reading files properly with real libraries, and working around their bugs, is the tooling's job. §10's notes on Python's `jsonschema` and on Ajv left the spec ahead of the rewrite (`096500b`).
3. **No protection against typos.** A rule defines what a file means. It doesn't exist to catch a likely mistake, and tools are free to warn. Any rule that exists mainly to catch a mistake is flagged to Tom, not dropped silently. Five went on 2026-11-06 (§4, *Composition*), and the advice about `excluded: no` is another.
4. **Tool-agnostic.** The spec says what holds and what is reported, never how a tool does it. Git is the one tool it names.
5. **Ground up.** Part II is read in order. Each section uses only Part I's vocabulary and the sections before it, with three exceptions:
   - a link to the glossary, for an exact definition;
   - a link to an annex, for a tool builder's detail;
   - the Rule of a general schema code (`MISSING_FIELD` and its kind, `INVALID_ID`, `INVALID_REFERENCE`, `INVALID_PATH`, `INVALID_COMMIT`), which may list fields that later sections introduce, as the field reference does.

   A glossary link never stands in for a concept that a later section introduces. Part I may link forward to the section of each piece it names.
6. **Readable, with nothing superfluous.** Prose where it reads well, bullets where text would be dense, short sentences. No sentence that only says what something doesn't do, unless it clarifies, and no advice that isn't a rule. These go, for example:
   - "Universes are declared only in astra.yaml. A universes/ directory means nothing to ASTRA."
   - "Write a pin with no space before its #."
   - "An astra.yaml needn't be one Windows can check out."
7. **No history.** No RFC numbers, no `tidy-up`, `main` or `#nn`. The design docs keep the traceability: §7 of `design/2026-11-03-v0.1-schema-design.md` keeps its copy of the catalogue with RFC sources. External standards are cited briefly, without their details.
8. **YAML's share is marked.** Annex A lists the rules that exist only because `astra.yaml` is YAML, so that a later change of format knows what can go.
9. **Accurate, not hole-closing** (Tom, 2026-11-06). "Our requirement is just that the file is yaml 1.2 … reading it is on the tooling, not the spec. We want our statement to be as accurate as possible, not nit picking and closing every hole … This fact also doesn't need to be stated as a 'this specification doesn't do this' type of statements." And: "We want neat, clean, precise specification and schema of ASTRA, not how to patch astra." So the spec states what ASTRA requires, as exactly as it can, and leaves to YAML, JSON, git and the tools what they leave loose, without saying that it does.
   - **Calibration** (Tom, 2026-11-06, keeping the audit's O23). A convention that says how the model is meant to be used is an explanation, and stays: "it tells you something about the model even if its not set in stone (a bit like how decisions should be scientifically meaningful and not just parameter changes)". Advice about mechanics, tools, platforms or typing slips goes.

## 4. Changes of meaning

These are the only ones. Everything else keeps its meaning, code, layer and level. A rule Tom drops or changes during the rewrite (§3, principles 1 and 3) is added here.

### Every output has a recipe, and every recipe a `command`

Done in `757d7ba`. An output without one was planned, but could never be built. A later version can relax this without invalidating any file.

### Composition: one key per decision, and partial driving is a missing decision

Done in `767674c`, `f90c030` and `0190726` (Tom, 2026-11-05). The composition model stays as it is: driving goes route by route, a result reached through two driven routes is placed under each name, and rule 2 (`UNDRIVEN_DECLARATION`) stays, because the route an address enters by is what makes it driven.
- **One key per decision.** Two keys for one decision in a universe are `DUPLICATE_ELEMENT`, even when they agree. A derived universe changes an inherited decision under the key it inherits. `CONFLICTING_SELECTIONS` goes.
- **`PARTIALLY_DRIVEN` goes.** A declaration that any universe of the driver drives is driven in all of them, and `MISSING_DECISION` covers the rest. A universe in which `when` switches off everything of a driven analysis sets nothing for it, and is valid.
- **New warning, `RESULT_IN_TWO_PLACES`** (SHOULD). No planned result has two names. It is reported where the two routes part.

### Composition: loops, sub-analyses' universes, planned results, and five slip rules

Done in `c18febe` to `b8f5597` (Tom, 2026-11-06). Sharing stays by identity (§5 item 17), so each analysis is built at most once per universe.
- **New MUST, `LOOPING_KEY`.** No key in a universe's own `decisions` goes through a declaration that leads back to an analysis already on its chain, the universe's own analysis included. Reads, pins, conditions and `Output.decisions` may still loop. None of unions-bmodes-mystra's 98 keys loops, nor any key in the examples, fixtures or RFCs.
- **A sub-analysis's pinned universe (O4).** Where a pin names another analysis's universe, that analysis is the only driver there, "as if you were running materialise from within the subanalysis". A declaration of the root in its file is an ordinary declaration: a key `parent.d` drives the root there, and what is built belongs to the sub-analysis.
- **The build rules are judged on planned results (O1).** `NOT_BUILT_IN_UNIVERSE`, `UNDRIVEN_DECLARATION` and `INPUT_NOT_BUILT` hold for what planned results read and consume, as `RESULT_IN_TWO_PLACES` already did. An output's own `when` is judged where its result would be planned if the `when` held. The universes built are the root's and those named by a pin on an output built per universe, in a planned result's `inputs` or in the root's evidence.
- **An analysis with no decisions is driven wherever the chain before it is**, universes of its own or not (`8782a5b`, kept). The words "and no universes of its own" go.
- **Imported universes, and a pin names its own file's universe** (`732e9c1` to `3905eab`). An entry of `universes` can import another analysis's universe (`{analysis: catalog, universe: main}`, new code `INVALID_IMPORT`). A pin `#u` names its file's entry `u`, or, where there is none, the universe `u` of the analysis whose element it reads. The pin search and the second-declaration trick go. In an imported universe that universe's analysis is the only driver (O4). Rules 1 and 2 cover pinned reads. Tom: quoting another analysis's results should need nothing extra, and driving is the added benefit.
- **Five rules that only flagged likely slips go:** `NO_UNIVERSES`, `PIN_ON_INPUT`, `REDUNDANT_PIN`, `UNPINNED_EVIDENCE`, and the list half of `DUPLICATE_ELEMENT`. A tool may warn about these under codes of its own, which never make an analysis invalid: an analysis is valid when its stack breaks none of the specification's `MUST`s (spec §2).

### An analysis is in a git repository

A new validator rule, `NOT_IN_REPOSITORY`, at level MUST: the folder of the analysis being validated is in the working tree of a git repository. That repository may be an overarching analysis's.

Outside a repository:
- the validator reports this rule and checks no other validator rule, while the parse and schema rules are still checked;
- a checker gives every planned result `missing`.

Annex D lists the case. An analysis read at a commit is always in a repository.

In the spec since the audit of 2026-11-06 (its D5): the validator table's first row, with Source `§3`, so `rules.json` has 66 rules; §3's definition of an analysis ("in a git repository: in its working tree, or at one of its commits"); *What is checked* case 11, which also says that the root's declarations aren't followed, since without a working tree a path names nothing, so only its own `astra.yaml` is checked by the parse and schema rules; §8's statuses; and the check layer's `missing`. It has no fixture, since its case needs a folder outside git: it is on scratch `for-conformance.md`.

### The parse layer

Decided on 2026-11-05 (`8626ed6`), and cut back to what ASTRA requires on 2026-11-06 (the audit's H1-H10 and H36, principle 9). An `astra.yaml` is:
- a YAML 1.2 stream with at most one document, read under the core schema, with no tag but the core schema's;
- whose content is a JSON value: every key is a string, and every number is finite.

A breach is `INVALID_SYNTAX`, and two equal keys in one map are `DUPLICATE_KEY`. A file with no document is null, so `WRONG_TYPE`. A record is JSON text (RFC 8259) in UTF-8 (`INVALID_SYNTAX`), with no repeated name (`DUPLICATE_KEY`). The rest of reading YAML or JSON is theirs, and the tools'.

What the layer of 11-05 had and this one doesn't, each a change of meaning:
- **UTF-8 for `astra.yaml`** (H36). YAML 1.2.2 reads UTF-8, UTF-16 and UTF-32. Records stay UTF-8.
- **Raw characters** (H1). No rule on a raw tab, C0 or C1 control, DEL, U+2028, U+2029, U+FEFF, U+FFFE or U+FFFF, or on where a byte order mark may be: YAML's own rules apply, and in a quoted scalar YAML allows a tab and every character that isn't a C0 control.
- **Line ends** (H2). A missing final line break is no longer read as present, so a block scalar that ends the file has no line break it doesn't write.
- **Directives** (H3). `%YAML 1.1`, `%TAG` and a reserved directive are read as YAML 1.2.2 reads them.
- **Document markers** (H4). Only "at most one document" stays.
- **Aliases** (H5). An alias is read as the node it names. One inside that node leaves the content no JSON value, so `INVALID_SYNTAX`, whose statement in `rules.json` says, as spec §3 does, that the content is a JSON value.
- **Tags** (H6). The core schema's tags are allowed, `!!str` included. Any other tag is still `INVALID_SYNTAX`.
- **A double's range** (H7). Only a number that isn't finite (`.inf`, `.nan`) is refused, not one such as `1e400`, in `astra.yaml` and in records.
- **Surrogate escapes** (H8). No rule in either kind of document, and no rule that a string is a sequence of Unicode scalar values.
- **A record's byte order mark** (H9). No rule: RFC 8259 lets a parser ignore one.
- **A key that isn't a string** (H10, option A). It is `INVALID_SYNTAX`, like `.inf`, and the file is checked no further. It was `INVALID_ID` at its map, with its entry left out and the rest of the file checked. The schema's `propertyNames` lose their `type: string`, `INVALID_ID` loses "every map key is a string", `DUPLICATE_KEY` compares every key, and *What is checked* loses its case 1, so the other cases move up one.

What changes in verdicts:
- Valid now: a file in UTF-16 or UTF-32, a raw tab, C1 control or DEL in a quoted scalar, NEL in a block scalar, a tab as white space, `%YAML 1.1`, `%TAG`, a reserved directive, a second `...` line after the content, an alias, a core schema tag, and `1e400`.
- A value ending in U+2028 is no longer `INVALID_SYNTAX`: U+2028 is content in YAML 1.2, so `type: metric<U+2028>` is `INVALID_VALUE`.
- A lone surrogate escape, an escaped pair in `astra.yaml`, and a record's byte order mark are read as the reader reads them.
- A key that isn't a string goes from `INVALID_ID` to `INVALID_SYNTAX`.
- A block scalar that ends the file without a line break no longer ends in one (H2), so its value changes, and a verdict that turns on it can change either way: a list `tags` whose entries are `a` and, last in the file, a block scalar `a` was valid, its entries `a` and `a\n`, and is now `DUPLICATE_ENTRY`.
- Apart from that, no file that was valid is invalid now: each change drops a refusal, or changes the code of a file that was already invalid.

The fixtures of the dropped rules went to scratch `for-conformance.md`. Stock ruamel, which astra-spec's harness reads with, reads some files otherwise than YAML 1.2.2, and those cases are listed there too, as library splits:
- it refuses some of what is now valid: a tab as white space, a C1 control or DEL in a quoted scalar, NEL in a block scalar, UTF-32, and UTF-16 without a byte order mark;
- it opens a document on a `...` with no document before it, so it refuses a `...` alone, which YAML reads as no document (`WRONG_TYPE`), and a second `...` after the content, which is valid now;
- it reads U+2028 as a line break, and takes U+FEFF in a plain scalar, which YAML refuses.

### Paths are tidied as text

A path is joined to the folder of the `astra.yaml` that writes it. It is measured from the top of the root's working tree, or, at a commit, from the top of the repository that holds it. Empty and `.` segments are dropped, and each `..` removes the segment before it, without consulting the file system. So `./data.csv` is `data.csv`, and `subanalysis/` is `subanalysis`.

A `..` that goes above the top is `DECLARATION_OUTSIDE_REPOSITORY`. Tidying doesn't change what can be written. `RESERVED_PATH` and a declaration's identity use the same tidied path.

In spec §3 since the audit of 2026-11-06 (its D4), stated once in *Reading git*, which identity, `RESERVED_PATH` and `DECLARATION_OUTSIDE_REPOSITORY` link to. What changes:
- **Identity.** It removed only `..`, so whether `subanalysis/` and `subanalysis` were one analysis was open. They are one now.
- **`DECLARATION_OUTSIDE_REPOSITORY`.** Its statement was "stays inside the declaring analysis's repository", which for a declaration in a checked-out submodule could read as the submodule's own repository, refusing a `..` into the superproject that §7 allowed (X04, the audit's I3). It now reads "doesn't go above the top of the root's working tree or, read at a commit, of the repository that holds that commit", as §7 said. Its statement and `RESERVED_PATH`'s change in `rules.json`; `RESERVED_PATH` drops its own tidying clause, and no verdict changes.

### A path is non-empty and doesn't start with `/`

Decided on 2026-11-06 (the audit's H18). `INVALID_PATH` keeps only what makes a path a relative one: every declaration's and input's `path` is non-empty and doesn't start with `/`, and both patterns are `^[^/]`. What went, each a change of meaning:
- **A leading `~`** (H18 a). Git holds `~x` as an ordinary name; the ban only caught someone expecting a shell's home folder.
- **A backslash** (H18 b). It is an ordinary character in git, so `data\x.csv` is one file named so.
- **An ASCII control character** (H18 c). Git allows every byte but NUL.
- **An input's `..` segment and trailing `/`** (H18 d). Tidied as text (above), a `..` that leaves the analysis's folder breaks `INPUT_IN_ANOTHER_ANALYSIS`, one that stays inside names the tidied path, and a trailing `/` names a folder, so `MISSING_INPUT_FILE`.

What changes in verdicts: `~/stage`, `data\x.csv`, `..\stage` and a path with a control character are no longer `INVALID_PATH`, and `../data.csv`, `data/../x.csv` and `data/` are judged by the validator rules above instead. No file that was valid is invalid now. The fixtures of the dropped bans went to scratch `for-conformance.md`.

### `BLANK_EXCLUDED` goes

Decided on 2026-11-06 (the audit's H25). An option with an `excluded` reason is excluded whatever the reason says, so the rule only refused a blank reason, a likely slip, and `excluded` was the one free-text field with a non-blank rule. The code leaves §9 and `rules.json`, and `Option.excluded` loses its pattern, so `excluded: "   "` is valid and excludes its option. `excluded: true` stays `WRONG_TYPE`. This reverses the non-blank half of the tidy-up's change 14 and X48, reviewed in #94, so scratch `for-rfcs.md` records it for #94's reviewers. Analysis-129 went to scratch `for-conformance.md`.

### A DOI's suffix is any non-empty text

Decided on 2026-11-06 (the audit's H26). `Evidence.doi` keeps `10.`, the registrant's digit runs joined by `.`, `/` and a suffix, which is now only non-empty, and shortDOIs stay refused (X42). The suffix's bans on an ASCII space at either end and on control characters go: they guarded against paste slips, and the field's description never stated them. So `10.1234/x ` and a suffix with a tab are valid now. Analysis-196 and -197 went to scratch `for-conformance.md`.

### What a placeholder is

Decided on 2026-11-06 (the audit's H31). A recipe's `command` is read from the left: `{{` and `}}` are a literal `{` and `}`, and any other `{` opens a placeholder, which ends at the next `}`. `UNDECLARED_TEMPLATE_REF` now covers a stray brace too: a `{` with no `}` after it, or a `}` that ends no placeholder, as in `echo }`. Before, what counted as a placeholder wasn't defined, so whether those broke the rule was open; a shell's own braces are written doubled, as `awk '{{print $1}}'`. The rule's statement changes in `rules.json`, and its cases went to scratch `for-conformance.md`.

### Reading git: the corners of git's state go

Decided on 2026-11-06 (the audit's H11-H17 and H19-H21). Spec §3 keeps the reading of git that ASTRA needs: the exact path, on disk in the working tree or in the commit's tree; symlinks never followed; gitlinks crossed at a commit; the innermost repository; what is tracked; and the blob git stores. What went, each a change of meaning:
- **`.git`** (H12). In the working tree, a path names any entry on disk below the top, `.git` included. Git never tracks `.git`, so an input there is `INPUT_NOT_TRACKED`.
- **Intent-to-add and unmerged entries** (H14). "In the index" reads as git's index does, so an intent-to-add entry (`git add -N`) is tracked now, as an unmerged one already was.
- **MERGE_HEAD** (H15, with H21). `COMMIT_NOT_ANCESTOR` stays, and in the working tree HEAD alone stands for the commit a declaration is in, so during a merge a declaration merged in from the other branch may draw the warning until the merge is committed. The rule's statement changes in `rules.json`.
- **Shallow clones and unborn branches** (H19, H20). Decided on 2026-11-05 but never in the spec: where a shallow clone couldn't decide, `COMMIT_NOT_ANCESTOR` wasn't to be reported, and with no commit yet it wasn't to be checked, an Annex D case. Both are left out. The rule means ancestry, which is exact; how a tool decides it on a history it lacks is the tool's. With no commit yet, HEAD stands for the first commit, of which no declared commit is an ancestor, so the warning is the rule's answer. Annex D has no such case.
- **The submodule's local repository** (H16). Spec §3 got the commit a gitlink pins from any repository that had it, the submodule's local repository included, and fetched it from the URL in `.gitmodules` only otherwise. Now it is got from that URL, and a commit kept from an earlier fetch counts as got. So where a gitlink crossed at a commit pins a commit made in the submodule and never pushed, the declaration that reaches it breaks `REMOTE_UNREACHABLE`, which §3 didn't say before. The rule's statement doesn't change: it always named only the remote and an earlier fetch, and §3 now agrees with it.

Restated with no change of meaning: case and Unicode form (H11: a path names the entry at exactly that path, so `data/A.csv` and `data/a.csv` are two paths, and identity compares "the same path"), a submodule that isn't checked out (H13), the URL a gitlink's commit is got from (H16: the one the `.gitmodules` of the commit holding the gitlink gives, a relative one resolved as git resolves it), and a file's bytes at a commit (H17: the blob git stores).

### Identity across a gitlink, and which universes are built

Settled on 2026-11-06 (the audit's I3, I4 and I5): three passages of spec §6 and §7 now say what the decided rules say.
- **Identity across a gitlink** (I4). Read at a commit, identity read a path such as `sub/x` at the superproject's commit, while spec §3 read it in the submodule at the commit the gitlink pins, so one analysis could have two identities. Identity now reads a path that crosses a gitlink as §3 does, in the submodule's repository at the commit the gitlink pins, and the directory is a path from the top of the repository it is read in. So `sub/x`, through a gitlink that pins `P`, is the analysis `x` of the submodule's repository at `P`, whichever declaration reaches it (§5 item 17).
- **Universes built where they are among the universes built** (I5). An imported universe, and a helper's universes of its own, were "built where a pin names it", which is looser than the rule decided in `1d96912` (O1): a pin on an input, or on an output built once, builds nothing. The three sentences now say "where it is among the universes built", and link to the rule.
- **`COMMIT_NOT_FOUND`** (I3). Its statement read "a commit the declaring analysis's repository has", a phrase `DECLARATION_OUTSIDE_REPOSITORY`'s statement used for the root's working tree. It now reads "a commit of the repository that holds the declaring `astra.yaml`", as spec §3 already said, so no verdict changes; the statement changes in `rules.json`. `AnalysisDeclaration.path`'s description drops its clause on the repository, which `DECLARATION_OUTSIDE_REPOSITORY` states.

### Records: what makes a result stale, and what a runner's checkout may hold

Decided on 2026-11-06 (the audit's H23, H24 and H37).
- **The options of a result's decisions** (H23). `STALE_RESULT` compared "the options of its decisions", which read literally made a result stale when an option was added to one of its decisions. It now compares the options its decisions select: a result is stale in its universe if any of its decisions selects a different option there than at the commit its record names. This is the reading agreed in X53 (1) on 2026-11-04, brought forward from RFC L; X53 (2) and (3) stay there. The rule's statement changes in `rules.json`.
- **`UNCOMMITTED_CHANGES` has no exemption** (H37). A runner's checkout could also hold what a tool keeps of, or puts in place to drive, an analysis from a commit. Now its only changes are the records and results the runner writes itself, each result's bytes the recorded ones; where a tool puts a driven commit's files is its own business, and they mustn't be changes in that checkout. The rule's statement changes in `rules.json`, and §7's two restatements of the exemption go.

With no change of meaning: "the commit a record names has to stay in the history" read as a rule with no code. It is now the recommendation alone (H24): branches that hold records SHOULD be merged, not squashed or rebased.

### Where codes are reported

- `UNSUPPORTED_SPEC_VERSION` at `/spec_version`;
- a parse code for the whole file;
- an unknown field at its object.

How a report names things (a diagnostic's `key`, the report's shape) is for the conformance suite.

In spec §10's *From an error to its code* since the audit of 2026-11-06 (its D6), with a schema error at its instance location, and an error on a key or an unknown field at its map or object, naming the key or field. The same paragraph now gives the filter by its outcome (H32), with no change of meaning: only the failures that make the document fail are reported, not those inside an `if` or a `not`, or inside a branch of a combinator that doesn't fail, so any JSON Schema 2019-09 validator gives the same pairs of an instance location and a code. Its list of how validators shape their output goes, and the rule covers any failing combinator, `anyOf` included, which settles that slip (below). `rules.json`'s entries for an `if` and a whole `propertyNames` stay, each with the code of the keyword that fails inside it.

### A patch release keeps codes, and the check layer reports errors and warnings

Both were decided before the audit of 2026-11-06 but not stated, and are in the spec since it (its D8 and D9):
- **A patch release never changes what is valid, nor the code a broken rule is reported under** (spec §1; X30, extended by Tom on 2026-11-05). The spec promised only validity. `tools/check_patch.py` already compares `rules.json`'s `errors`, keys and codes, between patches.
- **In the check layer, a broken `MUST` is reported as an error and a broken `SHOULD` as a warning** (spec §9's layer table; X58). Nothing fails, as before, and the result gets its status.

### What §2 and §10 no longer say

Cut on 2026-11-06 (the audit's H33 (a), H34 and H38), each a promise with no code:
- **A tool's own warnings** (H38). "A validator or checker may also warn about what no rule covers, under a code §9 doesn't define. Such a warning never makes an analysis invalid or changes a status." The second sentence follows from the definitions: validity comes only from `MUST`s, and statuses only from the check rules. The first is a "tool may" sentence, which needn't be stated (principle 9).
- **An RDF reading of the evidence selectors** (H33 (a)). §10 said no RDF reading of `astra.yaml` was published, then gave the selectors one: their W3C terms, `conforms_to` as `dcterms:conformsTo`, a location without it read as RFC 3778's, and `oa:refinedBy` for a quote within a location. That goes, and so does §5's `oa:refinedBy` clause. §5 still states the meaning in plain words, and the schema's `class_uri` and `slot_uri` stay as mappings.
- **The unversioned URL** (H34). "`https://w3id.org/astra/` followed by a file name alone redirects to the latest release's file" is a hosting detail. Keeping that redirect up to date belongs to the release process (scratch `asides.md`).

### The catalogue: `ABSENT_RESULT`, levels and statuses

Settled on 2026-11-06 (the audit's I14-I16, I20 and O7), with no verdict changed:
- **`ABSENT_RESULT`** (I20). Its statement read "every result's recorded bytes", but only planned results get statuses (spec §8). It now reads "every planned result's recorded bytes are at its default place". The statement changes in `rules.json`, and so does spec §10's excerpt.
- **No `MAY` level** (I15). No rule of the catalogue was a `MAY`, so spec §9 defined a category no table used. A level is now `MUST` or `SHOULD`, in spec §9 and in `rules.json`'s `level`, and `tools/rules.py` refuses a `MAY` row. The runner's permission to enforce `UNDECLARED_READ` stays a permission, stated after the runner table with the runner's recommendation, each once (I14); spec §8 and the layer table link to them.
- **Statuses once** (I16). Spec §9 kept the status table and dropped its restatement of spec §8's statuses. `STALE_EVIDENCE`'s *Status when broken* is "the cited result's status (Statuses)", linking spec §8, so its `status` in `rules.json` changes.
- **The catalogue as data** (O7). How `tools/rules.py` reads spec §9's tables (subsections, columns, rows, cells) left the spec for the extractor's docstring. Spec §9 keeps what the Code, Level and Rule columns mean, and spec §10 still says `rules.json`'s cells are inline CommonMark.

### Slips corrected

In the spec since the audit of 2026-11-06 (its D3):
- Results reached through an analysis from a commit are read "at the commit each is read at", and the analysis's code doesn't run "unless it is driven". Two pairs of sentences contradicted each other on this. Spec §7 now says each is read at the commit its analysis is read at, and "unless it is driven, none of its code runs".
- "Which option a reference reads" becomes "which universe". The sentence went with *No privileged universe* (the audit's N18).
- "Makes the file invalid" becomes "makes the analysis invalid", in spec §9's layer table, and a parse, schema or validator rule decides whether "a document or an analysis" is valid (I23).
- A runner's lowercase "should" becomes SHOULD: the recommendation that a runner let someone see what an environment it recorded holds is stated once, after the runner table, and spec §8 links to it (I14).
- The error-mapping rule covers any failing combinator, `anyOf` included (with H32, above).
- `INPUT_IN_ANOTHER_ANALYSIS` says "an `astra.yaml` file", the test a declaration uses. Its statement changes in `rules.json`.

### The rest of the audit of 2026-11-06, with no change of meaning

The audit's other accepted items (§2's O items but O23, which stays as an explanation of the model, §4's I items and §6's N items) changed wording only: each cut a sentence about a library, a platform, this repository, advice or what is left open, stated a fact once, or made a description say what the rules say. No verdict changes, and no rule's reach changes beyond the entries above. Among them, `rules.json` changes only in `STALE_EVIDENCE`'s `status` (I16) and, recorded above, the statements of `COMMIT_NOT_FOUND`, `ABSENT_RESULT` and `INPUT_IN_ANOTHER_ANALYSIS`.

## 5. The new specification

The specification is one page: Part I, Part II, a glossary, then Part III.

### Part I: How ASTRA works

1. **What ASTRA is.** A sentence or two on why ASTRA exists, then the pieces, in prose with a short list. No rules. It gives the meaning of every term Part II leans on before its own section:
   - an analysis, its folder and its repository;
   - inputs, outputs and recipes;
   - decisions, options and universes;
   - building an analysis in one of its universes, and the universe being built;
   - declaring another analysis, the root, and its stack. Every declared analysis is an analysis at a commit, and the URL says only where to get it. A declaration by `path` without a `commit` is one still being worked on, inside the declaring analysis's repository. When it is published, its declaration becomes a `url` and a `commit`, and its own results go with it, since they are kept in its folder. So two declarations name one analysis when they reach the same directory at the same commit, or the same directory of the working tree (Tom, 2026-11-06);
   - results, records, runners and checkers.
2. **A worked example.** The minimal example (see §7), then what validating, building, recording and checking do.
3. **Conformance.**
   - The five layers, in one table: what each reads, and who checks it.
   - What valid means.
   - A broken MUST is an error, and a broken SHOULD is a warning.
   - A rule left undetermined by another rule's breach isn't checked (Annex D).
4. **Conventions.** MUST, SHOULD and MAY; how to read a codes table; placeholders in examples; and the field reference, which the spec links to rather than restating it.

### Part II: The specification

**One analysis**

5. **The `astra.yaml` file.** The folder, whose `results/` and `.astra/` belong to runners; `spec_version`; values.
6. **Names.** Ids and maps. The four forms of a name, with their grammar in Annex C:
   - an address;
   - a reference, which may end in `#` and a universe;
   - an option reference;
   - a condition, which may start with `~`.

   Then references within the analysis.
7. **Inputs.**
8. **Decisions and options.**
9. **Conditions** (`when`), on decisions and outputs, judged on what the universe being built selects.
10. **Outputs.**
11. **Recipes.**
12. **Universes.** The effective selection, on which conditions are judged. An entry of `universes` may instead import another analysis's universe (its meaning is given in spec §16).
13. **Pins, and outputs built per universe or once.** A pin names the entry of its own file's `universes` with its id, or, where there is none, that universe of the analysis whose element it reads.
14. **Insights and evidence.** Including fragment identifiers.

**Several analyses**

15. **Declared analyses.** Declarations by path, the stack, and addresses that reach into another analysis.
16. **Driving and consuming.** What a universe drives, imported universes (where the imported analysis is the only driver), and composition's edge cases, each under the rule it qualifies.
17. **Analyses from another commit or repository.** Declarations by `url` and `commit`, what is read, validity, and what can be used. Identity is stated commit first. At a commit, a path that crosses a gitlink is read in the submodule's repository at the commit the gitlink pins, so it names the same analysis as a `url` declaration of that repository at that commit. A checked-out submodule read in the working tree is an analysis of the working tree, since it may differ from the commit the gitlink pins.

**Results**

18. **Results and where they go.**
19. **Records.**
20. **Checking results.** Statuses, when a result is unchanged, and the results of an analysis from a commit, read through their records at the declared commit.
21. **Runners.**

### The glossary and Part III

**Glossary.** Normative and alphabetical, with one line per term, for every term a rule relies on.
- A concept points to the section that defines it.
- A technical term is defined here, with Annex B giving the detail: tracked (in git's index), lies inside, stand-in, and the repository that holds a file.

**Part III: For tool builders.** Normative and terse.
- **A. Reading files:** what an `astra.yaml` and a record are, in full: YAML 1.2 whose content is a JSON value, and JSON. Since the audit of 2026-11-06 this is a few lines.
- **B. Paths and git:** tidying a path as text, symlinks, gitlinks crossed at a commit, and the glossary's git terms in full.
- **C. Grammars and patterns:** the ABNF, each pattern, and the characters of fragment identifiers.
- **D. When a rule isn't checked.**
- **E. The schema files and `rules.json`:** how an error maps to its code, records as RDF, and the `rules.json` excerpt.
- **References:** external standards only.

Codes tables appear only at the end of Part II sections. Part I, the glossary and Part III hold none.

### A Part II section

Each section has:
- a sentence or two on what the element is;
- an example;
- short bullets on how it behaves;
- a link to its element in the field reference;
- its codes table, if any rule sits in it: Code, Layer, Level, Rule, plus *Status when broken* for check codes.

A section whose rules are stated generally earlier (spec §9, §18, §19) links back to them.

A recommendation or permission without a code goes on one line after the table, beginning "Recommendation:" or "Permission:". There are four:
- A published analysis SHOULD declare only remotes its readers can fetch (spec §17).
- Branches that hold records SHOULD be merged, not squashed or rebased (spec §19).
- A runner SHOULD let someone see what an environment it recorded holds (spec §21).
- A runner MAY enforce `UNDECLARED_READ` (spec §21).

For example:

> ### 7. Inputs
>
> An input is a file the analysis reads. It lives in the analysis's folder and is tracked in git, so a commit pins the data along with the code.
>
> ```yaml
> inputs:
>   input1:
>     path: data/input1.csv
>     description: The measurements, one row per sample.
> ```
>
> - `inputs` maps each input's id to the input (§6); its fields are in the [field reference](elements/Input.md).
> - `path` is relative to the folder holding the `astra.yaml`, with `/` between folders.
> - An input is one file. Data in many files is many inputs.
> - The file is in the analysis's folder, but not in a folder below it that has an `astra.yaml` file of its own: that folder is another analysis.
> - It is tracked in the analysis's repository, so a file in a git submodule can't be an input.
> - It may be a stand-in kept in git in place of the data, such as a large-file tool's pointer, where the validator recognises it.
>
> | Code | Layer | Level | Rule |
> |---|---|---|---|
> | `INVALID_PATH` | schema | MUST | A declaration's or input's `path` is non-empty and doesn't start with `/` |
> | `MISSING_INPUT_FILE` | validator | MUST | An input's `path` names a file (not a folder, a symlink or a submodule), or a stand-in for one that the validator recognises |
> | `INPUT_NOT_TRACKED` | validator | MUST | An input's file, or its stand-in, is [tracked](#glossary) in the repository that holds its analysis |
> | `INPUT_IN_ANOTHER_ANALYSIS` | validator | MUST | An input's file is inside its analysis's folder, and not inside a folder below it that has an `astra.yaml` file of its own |
> | `RESERVED_PATH` | validator | MUST | No input's or declaration's `path` is, or [lies inside](#glossary), the `results/` or `.astra/` folder of an analysis of the stack |

### Where each rule lives

A rule sits in the earliest section where every idea it uses has been introduced. There are two exceptions:
- **Runner rules** all sit in spec §21, since each binds the runner rather than an element.
- **General rules** (the general schema codes, `INVALID_ID`, `INVALID_REFERENCE`, `UNRESOLVED_ADDRESS`, `UNKNOWN_OPTION`) are worded generically where they are introduced. Each later section names its own fields and links back.

The starting placement:

| Spec section | Codes |
|---|---|
| 5. The `astra.yaml` file | INVALID_SYNTAX, DUPLICATE_KEY, MISSING_FIELD, UNKNOWN_FIELD, WRONG_TYPE, EMPTY_COLLECTION, DUPLICATE_ENTRY, INVALID_VALUE, UNSUPPORTED_SPEC_VERSION, NOT_IN_REPOSITORY |
| 6. Names | INVALID_ID, INVALID_REFERENCE, UNRESOLVED_ADDRESS |
| 7. Inputs | INVALID_PATH, MISSING_INPUT_FILE, INPUT_NOT_TRACKED, INPUT_IN_ANOTHER_ANALYSIS, RESERVED_PATH |
| 8. Decisions and options | UNKNOWN_OPTION |
| 10. Outputs | OUTPUT_CYCLE, AMBIGUOUS_ID |
| 11. Recipes | UNDECLARED_TEMPLATE_REF |
| 12. Universes | UNKNOWN_DERIVED_FROM, DERIVED_FROM_CYCLE, INACTIVE_DECISION, MISSING_REQUIRED_OPTION, INCOMPATIBLE_OPTIONS, EXCLUDED_OPTION_SELECTED, INVALID_IMPORT |
| 13. Pins | PIN_INACTIVE, INPUT_NOT_BUILT |
| 14. Insights and evidence | INVALID_EVIDENCE_SOURCE, INVALID_INSIGHT_REF |
| 15. Declared analyses | DECLARATION_OUTSIDE_REPOSITORY, MISSING_DECLARED_ANALYSIS, CLASHING_RESULT_NAME |
| 16. Driving and consuming | RESULT_IN_TWO_PLACES, NOT_BUILT_IN_UNIVERSE, UNDRIVEN_DECLARATION, MISSING_DECISION, UNKNOWN_PIN_UNIVERSE, DUPLICATE_ELEMENT, LOOPING_KEY |
| 17. Analyses from another commit or repository | INVALID_DECLARATION_SOURCE, URL_WITHOUT_COMMIT, INVALID_COMMIT, COMMIT_NOT_FOUND, COMMIT_NOT_ANCESTOR, REMOTE_UNREACHABLE, DECLARED_ANALYSIS_INVALID |
| 20. Checking results | MISSING_RECORD, INVALID_RECORD, MISPLACED_RECORD, MISSING_RECORD_INPUTS, STALE_RESULT, ABSENT_RESULT, STALE_EVIDENCE |
| 21. Runners | UNRECORDED_RESULT, FALSE_RECORD, UNRECREATABLE_ENVIRONMENT, UNCOMMITTED_CHANGES, WRONG_WORKING_DIRECTORY, NOT_AT_COMMIT, REBUILT_FROM_COMMIT, STALE_INPUT, UNDECLARED_READ |

Two rules are reworded to fit their homes:
- **`MISSING_DECLARED_ANALYSIS`** reads "The folder a declaration names holds an `astra.yaml` file, reached through no symlink". Spec §15 says which folder a `path` names. Spec §17 adds that a `commit` reads it at that commit, and that a `url` names the top level of its repository.
- **`MISSING_DECISION`'s basic case** is prose in spec §12: a universe selects one option for each active decision of its analysis. The code, which also covers driven analyses, sits in spec §16.

Composition keeps its model (§4, *Composition*), so the rewrite states it as it stands at `3905eab`, with imported universes and the pin fallback. Tom's per-declaration copies were tested on 2026-11-06 and dropped, because siblings must share: a remote's own declarations of its siblings are fixed in its files (scratch `composition/per-declaration/REPORT.md`). That settles how reads are judged. In the driver's file a read is judged by its route (`UNDRIVEN_DECLARATION`); in every other file, by identity (`NOT_BUILT_IN_UNIVERSE`).

## 6. Rules as data

- **`rules.json`** keeps its shape:
  - `statement` is the rule's new sentence;
  - `source` is the section that states it, for example `§7 Inputs`, so it links a rule back to its text;
  - the rules come in document order;
  - the code of every schema keyword is unchanged.
- **`tools/rules.py`** reads every codes table in the document, not only today's §9, with today's strictness. It also collects the recommendations and permissions.
- **The All rules page** is generated from the specification when the docs are built, and sits in the Specification nav. It lists every rule, grouped by layer and linked to its section, then the recommendations and permissions. It is never edited by hand.
- **Links.** Each code in the text links to its table, or to its own anchor if the docs build can add per-code anchors. The plan checks which.

## 7. Examples

There is one running example, built up through the spec, with neutral names:

| Kind | Names |
|---|---|
| Inputs | `input1`, `input2` |
| Decisions and options | `decision1`, `decision2` and `decision3`, with options `a`, `b` and `c`. `decision3` has a `when`, so it exists only for one option of `decision1`. |
| Outputs | `output1`, one per universe; `output2`, built once, comparing `output1#u1` and `output1#u2` through pins; `output3`, built once from `input1`; `output4`, conditional |
| Universes | `u1`; `u2`, derived from `u1`; `u3`, derived from `u2`, which changes `decision1` and so drops the now inactive `decision3` |
| Declared analyses | `subanalysis`, by path in the same repository and driven by the root's universes; `remote`, from another repository at a commit, and consumed |
| Inside `subanalysis` | `input1`, `decision1` (options `a`, `b`) and `output1`. The root reads `subanalysis.output1`, and its universes set `subanalysis.decision1`. |
| Inside `remote` | `output1`, built once and read as `remote.output1` |
| Insights | `insight1`, a finding citing `output2`; `insight2`, a prior insight citing a DOI |

- **Part I's minimal version** has `input1`, `decision1` with two options, `u1` and `u2`, `output1` and `output2`, and `insight1`, in about 40 lines.
- **Each section** shows only the fragment it needs.
- **Nothing is made up.** Commits, hashes and sizes appear as `<commit>`, `sha256:<hash of …>` and `<size of …>`, and the tests fill them in before validating. The record's times are left out. URLs use `example.org`, IRIs `urn:example:`, and the DOI is `10.5555/12345678`.
- **Every example block** stays checked by the tests at the parse and schema layers.

## 8. Process

1. **The parse layer** (done, `8626ed6` and `ebb143f`).
   - Revert the two scanner commits (`b46f18a`, `6fa2bac`).
   - Move the harness onto ruamel's stock API.
   - Change the spec's reading rules and the fixtures.
   - Reduce the tests to ASTRA's rules, and remove the vendored YAML suite.
   - Then trim any test or fixture that doesn't serve §1, handing the cases to the conformance list.

   The baseline B is the spec at `c17a491`. It adds the composition changes of 2026-11-06, imported universes, and the content audit's decisions (`80ddb20`..`c17a491`): the smaller parse layer, plain ECMA-262 patterns, and the rules and text the audit cut. Tom's answers are in the handover scratch, `rewrite/audit/AUDIT.md`. The audit's thirteen open questions (Q1-Q13) stay open: the rewrite transcribes B's text where they apply.
2. **Tooling.** `tools/rules.py`, its tests and the generated page change first, run on today's content adapted to the new table form.
3. **The rewrite.**
   - It goes section by section, following the inventory's destination map as amended by §5. The inventory's line numbers (made at `ad50115`) are first mapped to the baseline.
   - Each normative sentence of the baseline is traced, in a ledger, to its new place or to a reason for dropping it.
   - Each rule's new sentence is checked against its baseline statement.
4. **Review.**
   - Each section is reviewed adversarially, for three things: meaning, against the ledger and the baseline; ground-up order and forward references; and readability.
   - Then the whole page is read three ways:
     - by a newcomer with no context, who must answer questions from Parts I and II alone;
     - by a tool builder, against the annexes;
     - rule by rule, against `rules.json`.
5. **Tom reviews** the page.
6. **The RFCs.** Tom has split the RFC work into small RFCs plus a final tidy-up (scratch `for-rfcs.md`), and works on them in parallel with this rewrite. This work hands over, at the end, what each of those RFCs must say to match the spec. The tidy-up chat owns the tidy-up RFC, and nothing reaches it before that list.

**Left to the implementation plan:**
- which tests change, and the extractor's exact checks;
- the link count and the per-code anchors;
- the placeholder markers;
- the comments that cite section numbers;
- the text that describes the old layout: CLAUDE.md, `tools/rules.py`'s docstring, and design D13, §3 and §8 of `design/2026-11-03-v0.1-schema-design.md`.

**Done when:**
- `just docs-strict` builds, and `just test` passes with the site test run, not skipped.
- `rules.json` has every rule of the baseline with its layer and level, except those dropped in §4, plus `NOT_IN_REPOSITORY`.
- The ledger accounts for every normative sentence of the baseline, and every rule's new sentence has been checked against the baseline's.
- The spec names no ASTRA RFC and no history; the plan gives the search that shows it.
- The three readings leave nothing open.
- Tom has approved the page.

## 9. Not in this work

- **The other docs pages:** `README.md`, `docs/index.md`, `installation.md`, `getting-started.md`, `cli.md` and `llms.txt`, still in the pre-0.1 format. They follow the rewrite.
- **The check and runner phase's open points** (§12 of `design/2026-11-03-v0.1-schema-design.md`).
- **A new composition model.** Tom kept today's (2026-11-05), and dropped per-declaration copies (2026-11-06). The composition analysis (scratch `composition/COMPOSITION.md`) is closed.
- **The RFCs themselves**, beyond the hand-over in step 6.
- **Releases:** a dev build naming its minor version, the conformance suite's report format, and a PyPI release.
