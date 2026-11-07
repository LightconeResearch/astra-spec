# Rewriting the specification: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. In this project, execution runs as Workflow runs (ultracode). Each task is one agent, and each has a fresh reviewer.

**Goal:** Replace `docs/specification.md` with the rewritten, condensed specification the design describes. Keep every rule's code, layer and level, except as the design's §4 records. Make `rules.json`, the tests and the docs site follow the new layout, so that astra-tools can build against one settled document.

**Architecture:**
- **Content first (Phase 0).** An audit of today's spec and schema checks:
  - that every decision is implemented as decided;
  - that nothing oversteps ASTRA's requirements;
  - that nothing contradicts anything else.

  It produces one list for Tom. His decisions land as ordinary commits on today's layout, giving baseline B. The rewrite then transcribes settled content and decides none.
- **Tooling first, in green commits.** A new extractor reads a codes table at the end of each Part II section, and the All rules page is generated. Until the switch-over, the old extractor stays the one `build_catalogue` uses, so every commit on `v0.1-schema` passes.
- **Drafts in scratch.** The new text is drafted section by section in the handover scratch, in parallel, with a ledger that traces every sentence of the baseline.
- **One switch-over commit**, then adversarial reviews, which are fixed in new commits.

**Tech Stack:** Markdown (CommonMark + GFM tables, read by markdown-it-py), Python 3.12 (tools and pytest), LinkML, Zensical for the site, `just`, `uv`.

**Spec:** `astra-spec/design/2026-11-05-specification-rewrite-design.md`, at `80ddb20`. Read it first; this plan argues from it.

## Global Constraints

- **Repository and branch:** `/home/r/Projects/LightconeResearch/astra-spec`, branch `v0.1-schema`. The baseline **B** is `docs/specification.md` at `c17a491`, the commit that ended Phase 0 (Tom's content decisions, `80ddb20`..`c17a491`). The rewrite design was aligned with them in `86cd9c9`.
- **Git:**
  - Never amend, rebase or push. Fixes go in new commits.
  - Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
  - Before every commit, run `git status` and `git log -1`. Another session has astra-spec open: if HEAD moved, or a change appears that the task didn't make, stop and report it.
- **Tools:**
  - Export `PATH=/nix/store/1sf33724ai5nydnck9ndwrd785faarsy-just-1.58.0/bin:/nix/store/9cg9w4h3i9afkh37cb08qwxz6xi1kq8a-uv-0.13.5/bin:$PATH` and `UV_OFFLINE=1`.
  - Every commit passes `just gen-schema` (the tree stays clean), `just test` and `just check-generated`.
  - From Task 1 on, `just docs-strict` passes, and so does `uv run python -m pytest tests/test_site.py` after it.
- **Scratch:**
  - Drafts, the ledger and the helper scripts live in `/home/r/Projects/LightconeResearch/astra-spec-handover/scratch/rewrite/`, called **R** below. They are never committed to astra-spec.
  - The helper scripts run with `python3 -I` or astra-spec's `uv run python`.
- **Off limits:**
  - Don't edit `rfcs/`.
  - In `design/`, edit only the passages Task 13 lists.
  - Don't edit `docs/llms.txt` or the other docs pages (design §9).
- **Meaning:**
  - No rule changes meaning except as design §4 lists.
  - A rule dropped or changed during the rewrite (principles 1 and 3) goes to Tom first and is added to §4. It is never dropped silently.
- **Requirements only** (Tom, 2026-11-06). The spec and the schema state ASTRA's requirements as accurately as they can. They close no holes in YAML, JSON Schema, regular expressions, git or platforms: reading files properly is a tool's job. Nor do they say so: there are no "this specification doesn't…" sentences. Tom: "We want neat, clean, precise specification and schema of ASTRA, not how to patch astra." This holds for the spec's text, its annexes, the schema's descriptions and patterns, and `rules.json`.
- **No history:** `grep -n -E '\b000[1-9]\b|tidy-up|\(#[0-9]+\)' docs/specification.md` prints nothing. External standards (RFC 2119, RFC 3986, YAML 1.2.2, JSON Schema 2019-09, JSON-LD 1.1, PROV-O) may be cited briefly.
- **Style:**
  - Short, plain sentences, with bullets where text would be dense.
  - No sentence that only says what something doesn't do, and no advice that isn't a rule (design §3.6).
  - Prose lines wrap at 80 columns.
  - Examples use design §7's running example and neutral names, and invent no commits, hashes, sizes or times.
- **The page's headings, exactly.** Anchors follow the site's slugs: lowercase, punctuation dropped, spaces as `-`. Use no backticks in headings. A `####` heading may be used inside a section, but nothing links to it.

  | Heading | Anchor |
  |---|---|
  | `# The ASTRA specification` | the-astra-specification |
  | `## Part I: How ASTRA works` | part-i-how-astra-works |
  | `### 1. What ASTRA is` | 1-what-astra-is |
  | `### 2. A worked example` | 2-a-worked-example |
  | `### 3. Conformance` | 3-conformance |
  | `### 4. Conventions` | 4-conventions |
  | `## Part II: The specification` | part-ii-the-specification |
  | `### 5. The astra.yaml file` | 5-the-astrayaml-file |
  | `### 6. Names` | 6-names |
  | `### 7. Inputs` | 7-inputs |
  | `### 8. Decisions and options` | 8-decisions-and-options |
  | `### 9. Conditions` | 9-conditions |
  | `### 10. Outputs` | 10-outputs |
  | `### 11. Recipes` | 11-recipes |
  | `### 12. Universes` | 12-universes |
  | `### 13. Pins, and outputs built per universe or once` | 13-pins-and-outputs-built-per-universe-or-once |
  | `### 14. Insights and evidence` | 14-insights-and-evidence |
  | `### 15. Declared analyses` | 15-declared-analyses |
  | `### 16. Driving and consuming` | 16-driving-and-consuming |
  | `### 17. Analyses from another commit or repository` | 17-analyses-from-another-commit-or-repository |
  | `### 18. Results and where they go` | 18-results-and-where-they-go |
  | `### 19. Records` | 19-records |
  | `### 20. Checking results` | 20-checking-results |
  | `### 21. Runners` | 21-runners |
  | `## Glossary` | glossary |
  | `## Part III: For tool builders` | part-iii-for-tool-builders |
  | `### A. Reading files` | a-reading-files |
  | `### B. Paths and git` | b-paths-and-git |
  | `### C. Grammars and patterns` | c-grammars-and-patterns |
  | `### D. When a rule isn't checked` | d-when-a-rule-isnt-checked |
  | `### E. The schema files and rules.json` | e-the-schema-files-and-rulesjson |
  | `### References` | references |

- **Codes tables:**
  - **Where.** One per Part II `###` section at most, as its last block. Only a `Recommendation:` or `Permission:` paragraph may follow it.
  - **Columns.** `| Code | Layer | Level | Rule |`, or `| Code | Layer | Level | Rule | Status when broken |` for a table whose every row has layer `check`. Every `check` row is in a table with that fifth column.
  - **Placement.** Each code goes where design §5's "Where each rule lives" puts it, as Task 3 updates that table.
- **Code links:**
  - In prose, a code is written ``[`CODE`](#anchor)``, where the anchor is that of the section whose table lists `CODE`.
  - In its own table's Code cell, a code is a bare code span.
- **`rules.json`:**
  - Its shape stays: `$comment`, `errors` and `rules`.
  - `rules` comes in document order. `source` is `§<n> <heading title>`, for example `§7 Inputs` or `§5 The astra.yaml file`.
  - The codes are exactly those at B: 66, `NOT_IN_REPOSITORY` included. Their layers and levels are unchanged.

## Review Focus

1. **A rule's meaning drifts in rewording.** A qualifier is lost, such as "unpinned", "built per universe" or "in the driver's file". The reader expects the code to forbid exactly what it did. Task 3's `compare_catalogue.py` prints every statement beside its baseline. Task 15's rule-by-rule reading checks each pair, and any difference not in design §4 is a must-fix.
2. **A normative sentence of the baseline vanishes**, typically a hole-closing detail such as a path, git or character rule. Task 3's `check_ledger.py` fails unless every baseline sentence has a destination or a reason, and Task 13 runs it before the switch.
3. **A code links to a section that no longer states it.** Task 13 adds `test_every_code_link_points_to_its_table` to `tests/test_specification.py`.
4. **A section leans on a term defined later** (design principle 5). Task 3's `check_order.py` lists every glossary term whose first Part II use comes before its defining section, and Task 14's reviewers judge each.
5. **An example stops validating, or keeps a placeholder unfilled.** Task 6 fills `<commit>`, `sha256:<hash of …>` and `<size of …>` before validation, and its test fails on any other `<…>` left in a YAML or JSON value.

---

### Phase 0: settle the content

#### Task 0a: Audit today's spec and schema (read only)

A workflow, with one agent per region plus a decision-register agent, then a merge and a critic. The regions are:
- §1-§3 with `types.yaml`'s patterns;
- §4-§5 with `analysis.yaml`;
- §6-§7;
- §8 with `provenance.yaml` and `insight.yaml`;
- §9-§10 with `rules.json`.

It writes `R/audit/AUDIT.md`: one list of decisions for Tom. Each item gives where it is, what it says, why it is in the list, a recommendation, and its impact (codes, schema, tests and fixtures). The items fall into five groups:
1. **Overreach:** sentences, rules or schema features about libraries, platforms, implementation or this repository's tooling, typo protection, or advice. Examples are the Windows notes (spec:192-200), the ECMA-262/Python regex notes (spec:407-414, :2141), the patterns' `$(?!
)`, "such as Ajv", the CommonMark reading of the catalogue, and the package paragraph.
2. **Hole-closing rules to drop or keep, one item per rule.** This covers the parse layer (§3), path and git details, and *What is checked*'s cascade cases. Each says whether it states a requirement of ASTRA (keep) or closes a hole in YAML, a library or a platform (drop).
3. **Inconsistencies:** one thing stated twice in different ways, or a term used in two senses.
4. **Decisions not implemented as decided.** Built from the 127-item inventory (`/tmp/claude-1001/-home-r-Projects-LightconeResearch-astra-spec-handover/b9f5c6e1-a7d8-465b-a748-c7f384c43d4d/scratchpad/rfc-split/*.json`), `for-rfcs.md`, design §4 and the decisions of 11-05 and 11-06. It covers both a decision missing from the text and text a later decision reversed.
5. **"This specification doesn't…" sentences** to remove.

#### Task 0b: Tom decides

Go through `AUDIT.md` with Tom. Record each answer in the file.

#### Task 0c: Land the decisions on today's layout

One commit per group of decisions, each passing `just gen-schema`, `just test` and `just check-generated`. They cover the spec text, the schema (descriptions, patterns, class rules), the tests and fixtures that test a dropped rule (the per-rule parse fixtures 225-232 and valid 014 among them, as Tom decides), `rules.json`, and design §4 (each dropped rule recorded as a change of meaning). The last commit is B.

### Task 1: The strict docs build passes (done in Phase 0, `57f5c8a`)

`just docs-strict` fails at `3905eab` on two generated pages. If Phase 0 changes the `iri` pattern or the `value` description, re-check which pages still fail.
- `docs/elements/Iri.md:28`: the `iri` pattern's `[^` reads as a footnote reference.
- `docs/elements/value.md:116`: `[\]` in `FragmentSelector.value`'s description reads as a link reference.

**Files:**
- Modify: the `just gen-doc` pipeline (justfile `gen-doc`/`_add-artifacts`), or a post-processing step it calls. Alternatively the two LinkML descriptions in `src/astra/schema/types.yaml` and `insight.yaml`, if a rewording keeps their text.
- Test: `tests/test_site.py`.

- [ ] **Step 1:** Add `test_element_pages_show_their_patterns` to `tests/test_site.py`. On the built `site/elements/Iri/index.html`, it asserts that the rendered text contains the `iri` type's pattern exactly as `types.yaml` gives it. On the `value` page, it asserts that the description contains ``"#<>[\]^`{|}``.
- [ ] **Step 2:** Run `just docs-strict`. Expected: it FAILs with the 2 issues.
- [ ] **Step 3:** Make the generated pages escape the two constructs, or change the source wording without changing what it says. Patterns and descriptions must read the same on the page.
- [ ] **Step 4:** Run `just docs-strict && uv run python -m pytest tests/test_site.py -q`. Expected: the build succeeds with 0 issues, and the tests pass. Then run `just gen-schema`, `just test` and `just check-generated`, all passing.
- [ ] **Step 5:** Commit: "Docs: the strict site build passes".

### Task 2: Hand the per-rule parse fixtures to the conformance list (done in Phase 0, `c688405` and later)

Task 0c removes the fixtures of every rule Tom drops, and lists their cases in `for-conformance.md`. What remains of this task applies only to fixtures of rules that stay but have more than one fixture per code.

Design §1: astra-spec keeps one document per parse or schema code. ASTRA's individual parse rules are tested in `tests/test_loader.py`.

**Files:**
- Delete: `tests/data/invalid/Analysis-225-*` to `Analysis-232-*`, and `tests/data/valid/Analysis-014-anchor-without-alias.yaml`.
- Modify: any test or list that names them (`git grep -n -E 'Analysis-(22[5-9]|23[0-2])|Analysis-014'`), and `tests/data/README.md` if it lists them.
- Modify: `astra-spec-handover/scratch/for-conformance.md`.

- [ ] **Step 1:** For each fixture, confirm that `tests/test_loader.py` tests its rule. If one isn't covered, add the loader test first, in `test_loader.py`'s style.
- [ ] **Step 2:** Add the nine cases to `for-conformance.md`, each with its file content, its expected code and the rule it breaks.
- [ ] **Step 3:** Delete the files and their references. Run `just test`. Expected: PASS, with `test_every_schema_rule_has_a_fixture` and `test_harness_checks_every_parse_and_schema_code` still passing, since every parse code keeps a fixture.
- [ ] **Step 4:** Commit: "Tests: per-rule parse fixtures go to the conformance list".

### Task 3: The rewrite toolkit (scratch only, no commit)

**Files (all under R):**
- Create: `baseline/specification-B.md` and `baseline/rules-B.json`, from `git show B:…`.
- Create: `tools/sentences.py`, `tools/check_ledger.py`, `tools/compare_catalogue.py`, `tools/assemble.py`, `tools/check_order.py`.
- Create: `ledger/baseline.jsonl`, `draft/`, `destinations.md` and `destinations.jsonl`.
- Modify: design §5's placement table, in `design/2026-11-05-specification-rewrite-design.md`. Commit only that, as "Design: placement of codes, rebased".

**Interfaces (Produces):**
- `sentences.py BASELINE > ledger/baseline.jsonl`. One object per sentence: `{"id": "L<line>.<n>", "line": int, "heading": "<## title> > <### title>", "text": str}`. It reads paragraphs and list items outside code blocks, splitting on `.`, `?` or `!` followed by white space, outside code spans. Each table row is one entry, and each code block is one entry of kind `example`.
- **Ledger parts:** each drafting task writes `ledger/<draft-file-stem>.jsonl`, with objects `{"id": <baseline id>, "to": ["§16", "D"], "how": "kept"|"reworded"|"merged"|"moved"|"dropped", "why": str}`. `why` is required when `how` is `dropped`. Its reasons are "not normative (example, navigation or history)", "design §4: <entry>" or "design §3.<n>: <principle>".
- `check_ledger.py [--draft STEM]`: exits 0 only if every baseline id is covered by at least one ledger entry and every `dropped` has a `why`. It prints the uncovered ids, grouped by heading. With `--draft`, it checks only the ids whose line `destinations.jsonl` assigns to that draft file.
- `compare_catalogue.py OLD NEW`: exits 0 only if NEW's codes are exactly OLD's, with each code's layer and level unchanged. It prints, for every code, the old and new statements side by side, and the new `source`.
- `assemble.py`: concatenates `draft/*.md` in the heading order of the Global Constraints table into `draft/specification.md`. The draft files are `00-title.md`, `01-part-i.md` … `04-…`, `05-…` to `21-…`, `30-glossary.md`, `40-part-iii.md`, `41-a.md` … `46-references.md`. It fails if a heading is missing or out of order.
- `check_order.py DRAFT`: for each `## Glossary` term, compares the section that defines it (the glossary line's link) with its first use in Part II, and prints each use that comes earlier.
- `destinations.jsonl`: one object per baseline line range, `{"from_line": int, "to_line": int, "draft": "<draft-file-stem>", "note": str}`. Together the ranges cover every baseline line once. `destinations.md` is the same map for people to read: the inventory's destination map (INVENTORY.md §3), its snapshot line numbers mapped to the baseline (INVENTORY.md's header gives the offsets at `e404214`; recompute them against B with `git diff ad50115 B -- docs/specification.md`), and each destination renamed to the new section numbers. The baseline text added since `ad50115` (imports, `LOOPING_KEY`, the parse layer, O4, O1) gets destinations too.

- [ ] **Step 1:** Write `sentences.py` and run it. Expected: about 1,500-2,000 entries. Spot-check 20 of them against the baseline.
- [ ] **Step 2:** Write `check_ledger.py`. Test it on a two-entry ledger that covers one of two ids. Expected: it exits 1 and names the other id.
- [ ] **Step 3:** Write `compare_catalogue.py`. Test it with OLD as the baseline rules.json and NEW as a copy with one level changed. Expected: it exits 1 naming that code. With NEW identical to OLD, it exits 0.
- [ ] **Step 4:** Write `assemble.py` and `check_order.py`, with a two-section smoke test each.
- [ ] **Step 5:** Write `destinations.md` and `destinations.jsonl`. Check that design §5's placement table lists every code of B exactly once, against `baseline/rules-B.json`. If it doesn't, fix the table and commit the design change.

### Task 4: The extractor reads a codes table in every Part II section

**Files:**
- Modify: `tools/rules.py`.
- Test: `tests/test_rules.py`, in a new block of tests on synthetic documents.

**Interfaces (Produces):**
- `extract_section_rules(markdown: str) -> list[dict]`. Each rule is `{"code", "layer", "level", "statement", "source"}`, plus `"status"` for check rows, in document order.
- `extract_notes(markdown: str) -> list[dict]`. Each note is `{"kind": "recommendation"|"permission", "level": "SHOULD"|"MAY", "text": str, "source": str}`, in document order.
- `build_catalogue` still calls the old `extract_rules`. Task 13 switches it.

**What it enforces, with an error naming the line:**
- Exactly one `## Part II: The specification`.
- A codes table is a GFM table whose header row's first cell is `Code`.
- Each codes table sits under a Part II `###` section, at most one per section, as the section's last block, apart from `Recommendation:` and `Permission:` paragraphs.
- The columns are exactly as the Global Constraints give them.
- Every rule from today's `extract_rules` holds, minus the Source checks:
  - the layer is one of `parse`, `schema`, `validator`, `check` or `runner`, and `MAY` appears only on `runner` rows;
  - the keywords agree with the level;
  - each rule is one sentence;
  - codes are unique across the document;
  - no cell is empty, and every cell is markup-limited and rebuildable;
  - a row has one cell per column.
- `source` is `§<n> <title>` from the `###` heading. The heading's text has its numbering removed (`7. Inputs` → `§7 Inputs`).
- **Notes:** a paragraph whose text starts `Recommendation:` must state `SHOULD`, and one that starts `Permission:` must state `MAY`, each once. A note outside Part II is an error.

- [ ] **Step 1:** Write the failing tests:
  - `test_section_tables_are_read_in_document_order`: a document with §5 (two schema rows), §7 (one validator row) and §20 (one check row with a status) gives the four rules in that order, with sources `§5 The astra.yaml file`, `§7 Inputs` and `§20 Checking results`.
  - `test_malformed_section_tables_fail`, parametrised over: a table in Part I; a table in the glossary; two tables in one section; a table followed by a paragraph; a check row in a four-column table; a five-column table with a validator row; a `MAY` row on a validator; a duplicate code across sections; a missing Part II; an empty cell; two sentences in a rule. Each case asserts its error with `pytest.raises(SystemExit, match=...)` and the line number.
  - `test_notes_are_read`: one `Recommendation:` and one `Permission:` with the right keywords give two notes with their levels and sources.
  - `test_a_note_with_the_wrong_keyword_fails`.
- [ ] **Step 2:** Run `uv run python -m pytest tests/test_rules.py -q -k "section_tables or notes"`. Expected: FAIL, since the functions aren't defined.
- [ ] **Step 3:** Implement both functions in `tools/rules.py`. Reuse `_markdown`, `_rows`, `_cells`, `_inline_markdown`, `_code`, `_keywords` and `_sentence_break` as they are.
- [ ] **Step 4:** Run the same tests (expected: PASS), then `just test` (expected: PASS, and `rules.json` unchanged).
- [ ] **Step 5:** Commit: "Tools: read a codes table in each section of Part II".

### Task 5: The All rules page

**Files:**
- Create: `tools/rules_page.py`.
- Modify: `justfile` (`_docs-prep` writes the page), `zensical.toml` (add `{ "All rules" = "rules.md" }` under Specification, after "Format reference") and `.gitignore` (`docs/rules.md`).
- Test: `tests/test_rules.py` (rendering) and `tests/test_site.py` (the built page).

**Interfaces:**
- **Consumes:** `extract_section_rules` and `extract_notes` (Task 4). Until Task 13, the page falls back to the old `extract_rules` when the document has no `## Part II: The specification`, with an empty notes list.
- **Produces:** `render_rules_page(rules: list[dict], notes: list[dict]) -> str`, and `tools/rules_page.py SPEC OUT`.

**The page:**
- `# All rules`, then one sentence saying it is generated from the specification.
- One `## <Layer>` per layer, in the order parse, schema, validator, check, runner. Each has a table `| Code | Level | Rule | Section |` (plus `Status when broken` under check). The Section cell is a link to `specification.md#<anchor>`.
- Then `## Recommendations and permissions`, one bullet each, with its section link.

- [ ] **Step 1:** Write the tests:
  - `test_rules_page_groups_by_layer_in_order` (synthetic rules from three layers);
  - `test_rules_page_lists_notes`;
  - in `test_site.py`, `test_all_rules_page_lists_every_rule`, which checks that the built `site/rules/index.html` has every `rules.json` code once, under its layer.
- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement `render_rules_page` and `rules_page.py`, and wire up `_docs-prep`, the nav and `.gitignore`.
- [ ] **Step 4:** Run `just docs-strict`, `uv run python -m pytest tests/test_site.py tests/test_rules.py -q` and `just test`. Expected: all PASS.
- [ ] **Step 5:** Commit: "Docs: a generated page lists every rule".

### Task 6: Examples may show commits, hashes and sizes as placeholders

**Files:** `tests/test_specification.py`.

**Interfaces (Produces):**
- `fill_placeholders(text: str) -> str`. It replaces:
  - `<commit>` with `0123456789abcdef0123456789abcdef01234567`;
  - `sha256:<hash of X>` with `sha256:` and the SHA-256 hex of `X`;
  - `<size of X>` with the decimal byte length of `X`.
- It is applied to every fenced YAML and JSON block before it is parsed, in `examples()`.

- [ ] **Step 1:** Write the tests:
  - `test_placeholders_are_filled`: a record with all three, once filled, is valid against `provenance.schema.json`;
  - `test_fill_placeholders_leaves_unknown_ones`: `<other>` survives filling unchanged;
  - `test_no_example_keeps_a_placeholder`: for each spec example after filling, no YAML or JSON scalar matches `^<[^>]+>$` or contains `sha256:<`.
- [ ] **Step 2:** Run them. Expected: FAIL.
- [ ] **Step 3:** Implement `fill_placeholders`, and call it in `examples()`.
- [ ] **Step 4:** Run `just test`. Expected: PASS, since today's spec has no placeholders.
- [ ] **Step 5:** Commit: "Tests: examples may show commits, hashes and sizes as placeholders".

### Tasks 7-12: Draft the sections (parallel; scratch only)

Each drafting task writes its files in `R/draft/` and its ledger part in `R/ledger/`. They run in parallel, and none commits. Each starts by reading:
- the design, in full;
- `R/destinations.md`, for its baseline lines;
- `R/baseline/specification-B.md`;
- INVENTORY.md §4.4-4.6, for the running example, and design §7;
- the Global Constraints above.

Each task:
- [ ] **Step 1:** Write its sections. Each Part II section follows design §5, *A Part II section*:
  - a sentence or two;
  - an example fragment from the running example, marked `<!-- fragment: Analysis -->` unless it's whole;
  - short bullets;
  - the field-reference link;
  - its codes table, with the codes design §5's placement table gives it;
  - its `Recommendation:` or `Permission:` lines.

  Each rule's Rule cell is one sentence, checked against its baseline statement. Apply design §4's entries that fall in its sections, slips corrected included, and make no other change of meaning. Design §5 rewords two rules: `MISSING_DECLARED_ANALYSIS` and `MISSING_DECISION`'s basic case.
- [ ] **Step 2:** Write its ledger part. It covers every baseline id that `destinations.jsonl` sends to its draft files, and every other id it used.
- [ ] **Step 3:** Run `python3 -I R/tools/check_ledger.py --draft <stem>` for each of its draft files. Expected: 0 uncovered.
- [ ] **Step 4:** Return its list of open questions for Tom, each a candidate under principle 1 or 3. Never drop such a rule silently.

| Task | Writes | Covers |
|---|---|---|
| 7 | `00-title.md`, `01`-`04` | the title and Part I: what ASTRA is (with design §5 Part I's term list, commit-first identity included), the worked example (about 40 lines, valid whole), conformance (the five layers; MUST is an error and SHOULD a warning; what valid means; a tool's own warnings, from spec §2 at the baseline), conventions |
| 8 | `05`-`09` | the astra.yaml file (with `NOT_IN_REPOSITORY`), names, inputs, decisions and options, conditions |
| 9 | `10`-`14` | outputs, recipes, universes (with imports), pins and built per universe or once, insights and evidence |
| 10 | `15`-`17` | declared analyses, driving and consuming (with imported universes, O4, `LOOPING_KEY`, planned-results scope), analyses from another commit or repository (identity commit first, design item 17) |
| 11 | `18`-`21` | results, records, checking results, runners |
| 12 | `30-glossary.md`, `40`-`46` | the glossary (one line per term, each linking to its section), annexes A-E (design §5 *Part III*: path tidying, shallow clones and where codes are reported, from design §4) and the references |

### Task 13: Assemble and switch over (one commit)

**Files:**
- Modify: `docs/specification.md`, replaced by `R/draft/specification.md`.
- Modify: `tools/rules.py`. `build_catalogue` calls `extract_section_rules`. The old `extract_rules` and its constants (`SECTION`, `COLUMNS`, `LAYERS`, `MAY_TABLE`, `SOURCE_WORDS`, `SOURCE_SEPARATOR`) and the old tests go. `extract_section_rules` is renamed `extract_rules`, and `rules_page.py`'s fallback goes. The module docstring describes the new layout.
- Modify: `tests/test_rules.py` (the old §9 tests go), `tests/test_specification.py` (the catalogue tests read the new layout; add `test_every_code_link_points_to_its_table`), `tests/test_site.py` (it compares every codes table on the page with `rules.json`, not only §9's, and adds `test_every_in_page_link_resolves`) and `tests/test_grammar.py` (the grammar is read from Annex C: `### C. Grammars and patterns`).
- Modify: every comment and docstring that cites a spec section by number. `git grep -n -E '§ ?[0-9]+|spec(ification)? §' -- tools tests src CLAUDE.md justfile .github` gives the list; map each through `R/destinations.md`.
- Modify: CLAUDE.md's text on the layout and rules.json, and the passages design §8 lists in `design/2026-11-03-v0.1-schema-design.md` (D13, §3 and §8).
- Regenerate: `rules.json`, with the 66 rules of B.

- [ ] **Step 1:** Run `python3 -I R/tools/assemble.py`. Expected: exit 0.
- [ ] **Step 2:** Run `python3 -I R/tools/check_ledger.py`. Expected: exit 0, all ids covered. If not, return to the owning drafting task.
- [ ] **Step 3:** Write the new tests (`test_every_code_link_points_to_its_table`, `test_every_in_page_link_resolves`, and the catalogue tests on the new layout). Run them on the old spec. Expected: FAIL.
- [ ] **Step 4:** Copy the draft over `docs/specification.md`, and make the other file changes above.
- [ ] **Step 5:** Run `just gen-schema`, then `python3 -I R/tools/compare_catalogue.py R/baseline/rules-B.json src/astra/schema/generated/rules.json > R/statements.md`. Expected: exit 0. `R/statements.md` holds every statement beside its baseline, for Task 15.
- [ ] **Step 6:** Run `just test`, `just check-generated`, `just docs-strict` and `uv run python -m pytest tests/test_site.py -q`, plus the no-history grep from the Global Constraints. Expected: all pass, and the grep prints nothing.
- [ ] **Step 7:** Commit: "Spec: rewritten for readability".

### Task 14: Section reviews (parallel), then one fix commit

There is one reviewer per drafting group (7-12). Each reads its sections, `R/ledger/`, the baseline and `R/statements.md`. Each reports findings as must-fix, should-fix or note, on three lenses:
- **meaning:** every ledger entry's destination really says what the baseline said, and every rule's sentence is equivalent, unless design §4 records the change;
- **ground-up order:** take each line of `check_order.py`'s output, and any other forward reference beyond principle 5's exceptions;
- **readability:** principle 6.

- [ ] **Step 1:** Run the reviews.
- [ ] **Step 2:** One agent fixes every must-fix, and every should-fix that holds, in one new commit, "Spec: section review fixes". The checks of Task 13 Steps 5 and 6 pass first.

### Task 15: Four readings of the whole page, then one fix commit

- **Newcomer**, with no other context. Answer these from Parts I and II alone, and report every answer that needed the glossary, an annex or a guess:
  1. What is a universe, and when does an output have one result per universe?
  2. When is an `astra.yaml` valid?
  3. How does an analysis read another analysis's output, and in which universe?
  4. What does `out#u` name when the file has no universe `u`?
  5. What does `when` do to a decision, and to an output?
  6. What does a universe that sets `stage.d` do?
  7. Why must an input be tracked in git?
  8. What is recorded for a result, and how does a checker find it stale?
  9. How do I read a result of this analysis at an earlier commit?
  10. What may a runner refuse to do, and what must it never do?
- **Tool builder.** For every rule, can a validator decide it from the annexes and its section alone? Report each rule that needs knowledge from outside the page.
- **Requirements only.** Read every sentence of the page, every schema description and every pattern. Report anything that isn't a requirement of ASTRA or an explanation of one: a library, a platform, an implementation, this repository's tooling, typo protection, advice, or a "this specification doesn't…" sentence.
- **Rule by rule.** For each of the 66 rows of `R/statements.md`, is the new statement equivalent to the baseline's, apart from design §4? Does the section text agree with the table? Does the All rules page show the rule?

- [ ] **Step 1:** Run the four readings in parallel.
- [ ] **Step 2:** One agent fixes their findings in one new commit, "Spec: whole-page review fixes", with the checks of Task 13 Steps 5 and 6 passing.
- [ ] **Step 3:** A recheck agent confirms each finding's fix, runs the checks, and confirms there were no amends (`git reflog`).

### Task 16: Hand over

**Files:** the handover scratch's `for-astra-tools.md`, `for-rfcs.md` and `for-conformance.md`, and the rewrite design's §4.

- [ ] **Step 1:** In `for-astra-tools.md`:
  - the new HEAD;
  - that statements and sources changed for every rule, and that codes didn't apart from `NOT_IN_REPOSITORY`;
  - the All rules page;
  - that its §2's "landing next" items have landed.

  Then send that session a short message with the HEAD.
- [ ] **Step 2:** In `for-rfcs.md`: for each proposed RFC, the new sections that state its items, so each RFC can cite the spec.
- [ ] **Step 3:** Ask Tom to review the page (design §8, step 5). Give him the HEAD and the built site's path, plus every open question the drafting tasks raised.
