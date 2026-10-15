---
rfc: 0003
title: Delegate execution to workflow engines; deprecate recipes
status: Draft # Draft | Active | Accepted | Rejected | Superseded
authors:
  - Pete Bachant (@petebachant)
created: 2026-08-03
tracking-issue: # link to the GitHub issue opened in Step 1
superseded-by: # RFC number, once another RFC replaces this one
---

## Context

Today, an ASTRA output says how it is built with a **`recipe`**: a `command`
string, plus optional `container` and `resources`. A node-level
`Analysis.container` supplies a default environment for the recipes beneath it.

```yaml
outputs:
  - id: fit_params
    type: table
    inputs: [catalog_data]
    decisions: [fit_method]
    recipe:
      command: >-
        python src/fit_period_luminosity.py
        --catalog {inputs.catalog_data}
        --method {decisions.fit_method}
        --out {output}
```

This is under-specified in two independent ways, and the second one is not
fixable by adding fields.

**A command does not describe its environment.** `python src/fit.py` reproduces
only on a machine that already happens to have the right interpreter and the
right packages. The `container` field was added to patch this, and it does help
— but it means the spec now carries a *copy* of environment information that
also exists wherever the project actually builds things, free to drift.

**A command does not know whether it needs to run.** This is the deeper problem.
A command always runs. It never notices that its input changed, and it never
notices that it didn't. Nothing in a `recipe` lets a reader — or an agent —
answer "is this artifact current?", which is the question that separates a
reproducible result from a plausible-looking one. No additional field on
`Recipe` fixes this, because staleness is a property of a dependency graph, not
of a command string.

Both failures land hardest on the case ASTRA is built for. An agent asked to
produce an analysis will emit `python src/train.py` and consider the job
finished. The document looks complete, validates cleanly, and cannot be
rebuilt by anyone else. That is precisely the outcome the format exists to
prevent.

**Prior art solves this, and has for years.** Snakemake, DVC, Nextflow, CWL,
WDL, the R `targets` package, Make, and Calkit all own exactly these concerns:
a declared dependency graph, an environment attached to each rule, and a
staleness decision derived from both. ASTRA does not need to reinvent any of
it. It needs to name the engine and get out of the way.

Underneath both failures is a layering question the spec has never stated
outright. **ASTRA declares desired state; something else implements it.** A
command is implementation. A container is implementation. A CPU request is
implementation. The `container` field is the clearest tell that the line had
been crossed: the spec started describing *how* to build, without gaining the
ability to decide *whether* to build.

## Proposal

In plain language: **an ASTRA analysis names the workflow engine that builds
it, and each output names its rule inside that engine's own workflow
definition. ASTRA says nothing else about execution.**

Concretely, four changes to `src/astra/schema/analysis.yaml`:

### 1. `Analysis.workflow_engine` — a new enum slot

Names the engine responsible for building this node's outputs. Declared once at
the root and inherited by every descendant analysis; a sub-analysis may override
it, which matters most for one extracted to its own directory via `path` and
carrying its own workflow definition.

The vocabulary is **closed**, listed alphabetically with an explicit note that
the ordering carries no recommendation:

| Value | Engine | Workflow definition |
|---|---|---|
| `calkit` | [Calkit](https://github.com/calkit/calkit) | `calkit.yaml` |
| `cwl` | [Common Workflow Language](https://www.commonwl.org) | `*.cwl` |
| `dvc` | [DVC](https://dvc.org) | `dvc.yaml` |
| `make` | Make | `Makefile` |
| `nextflow` | [Nextflow](https://www.nextflow.io) | `main.nf` |
| `snakemake` | [Snakemake](https://snakemake.github.io) | `Snakefile` |
| `targets` | The R [`targets`](https://books.ropensci.org/targets/) package | `_targets.R` |
| `wdl` | [Workflow Description Language](https://openwdl.org) | `*.wdl` |
| `other` | An engine outside this list | name it in the analysis `description` |

The membership criterion is **staleness tracking**: an engine must be able to
decide, from declared dependencies, whether an existing artifact still reflects
its inputs. A bare command runner or task launcher (`just`, a shell script, a
`Makefile` used only as an alias book) does not qualify — admitting those would
reintroduce exactly the gap this RFC closes.

### 2. `Output.workflow_target` — a new string slot

Names the rule, stage, or target inside the engine's definition that builds this
output: a Snakemake rule, a DVC or Calkit stage, a Make target, a Nextflow
process.

Deliberately a bare name. The command, the environment, the resource request,
and the staleness rule are all read from the workflow definition, where the
engine can act on them. Several outputs may name the same target; that is the
normal case when one script emits multiple artifacts.

### 3. Deprecate the execution surface

Not just `command` — the whole implementation surface, as a unit:

| Element | Status |
|---|---|
| `Recipe` (class) | Deprecated |
| `Recipe.command` | Deprecated |
| `Recipe.container` | Deprecated |
| `Recipe.resources` | Deprecated |
| `Resources` (class) | Deprecated |
| `Analysis.container` | Deprecated |

Deprecating `command` alone would be half a line. A spec that still declares a
container is a spec that has started implementing, and it would still have no
answer on staleness. Each element carries a LinkML `deprecated:` metaslot with
its rationale plus a `DEPRECATED —` lead in its description, so both surface in
the generated `docs/elements/` reference.

Nothing is removed. Every existing document remains valid.

### 4. Two structural rules on `Output`

- **`from_alias_forbids_workflow_target`** — a re-exported output (`from:`) is a
  pure pointer; the source already declares how the artifact is built.
- **`workflow_target_forbids_recipe`** — an output declares how it is built
  exactly once.

Note that the second forbids the *entire* `recipe`, not merely `recipe.command`.
This is the layering principle expressed as a constraint: there is no
half-migrated state where the engine builds the artifact but ASTRA still
declares its environment.

### 5. One semantic rule for `astra-tools`

`workflow_target` resolves only against an engine, so an output declaring one
must have a `workflow_engine` in scope at its own node or an ancestor. This
crosses analysis nodes and cannot be expressed structurally in LinkML; it
belongs to the semantic validation stage.

## Examples

Before and after, with the environment and resource request moving across the
line rather than disappearing:

```yaml
# Before (deprecated)
outputs:
  - id: fit_params
    type: table
    inputs: [catalog_data]
    decisions: [fit_method]
    recipe:
      command: >-
        python src/fit_period_luminosity.py
        --catalog {inputs.catalog_data}
        --method {decisions.fit_method}
        --out {output}
      container: python:3.12-slim
      resources:
        cpus: 4
        memory: "8Gi"
```

```yaml
# After
workflow_engine: snakemake

outputs:
  - id: fit_params
    type: table
    inputs: [catalog_data]
    decisions: [fit_method]
    workflow_target: fit_period_luminosity
```

```python
# Snakefile — command, environment, and resources live here, where the
# engine can act on them and decide whether the artifact is stale.
rule fit_period_luminosity:
    input: "data/catalog.csv"
    output: "results/{universe}/fit_params.csv"
    container: "docker://python:3.12-slim"
    resources: cpus=4, mem_mb=8192
    shell: "python src/fit_period_luminosity.py "
           "--catalog {input} --method {wildcards.fit_method} --out {output}"
```

`inputs` and `decisions` are untouched. They were always the provenance
contract — what this artifact depends on, and which choices shape it — and that
is squarely desired state, on ASTRA's side of the line.

Inheritance and override:

```yaml
workflow_engine: snakemake        # inherited by every descendant

analyses:
  validation:
    workflow_engine: dvc          # this subtree builds with DVC instead
    outputs:
      - id: purity_curve
        type: figure
        workflow_target: purity_curve
```

Rejected by the schema:

```yaml
outputs:
  - id: result                    # two contradictory answers
    type: metric
    workflow_target: evaluate
    recipe:
      command: python src/evaluate.py

  - id: reexport                  # a pure pointer cannot also build
    from: child.metric
    workflow_target: regenerate
```

## Implementation implications & migration

**`astra-spec` (this repo).** Implemented on branch `workflow-engine`, pending
this RFC:

- `src/astra/schema/analysis.yaml`: the `WorkflowEngine` enum, the two new
  slots, six `deprecated:` annotations, two `Output` rules.
- `src/astra/datamodel/`: regenerated via `just gen-python`.
- Docs: `specification.md` gains a "Workflow engines and build targets" section
  and a migration walkthrough; the Recipe section is reframed as deprecated;
  `index.md`, `getting-started.md`, `cli.md`, and `README.md` examples
  converted. `docs/elements/` regenerates via `just gen-doc`.
- Examples: both `iris` and `iris_pipeline` converted to Snakemake, the latter
  demonstrating root-level inheritance across sub-analyses.
- Tests: a valid fixture covering inheritance and override, three invalid
  fixtures (target-with-recipe, aliased-output-with-target, engine outside the
  vocabulary). `Analysis-001.yaml` deliberately retains the deprecated recipe
  path as back-compatibility coverage.

**`astra-tools` (Python CLI + SDK).** Not yet done:

- The semantic check that every `workflow_target` has a `workflow_engine` in
  scope, with a new error code.
- `astra init` currently scaffolds a `container:` default and a
  `recipe.command`; it should emit `workflow_engine` + `workflow_target`, and
  ideally a starter workflow definition alongside `astra.yaml`.
- Deprecation warnings on documents still using `recipe`, routed through the
  existing non-blocking warning channel.
- `UNDECLARED_TEMPLATE_REF` and the rest of the placeholder-checking logic stay
  as-is for as long as `recipe.command` survives.

**`astra-typescript` (`@astra-spec/sdk`).** Types and validation mirror the
Python schema surface and need regenerating for the new enum and slots.

**Compatibility / versioning: minor bump.** The change is additive plus
deprecation. Nothing is removed, and no document that validates today stops
validating: the one new prohibition (`workflow_target_forbids_recipe`) can only
fire on documents using a field that did not previously exist. Deprecation is
carried as metadata, not enforcement.

**Migration** is mechanical and needs no tooling: move the command into the
workflow definition, name the rule, replace `recipe:` with `workflow_target:`.
`container` and `resources` move with it, as does any node-level
`Analysis.container`. The `{inputs.<id>}` / `{decisions.<id>}` / `{output}`
placeholders become the engine's own substitution syntax, which every candidate
engine provides in some form.

**Eventual removal** of `Recipe`, `Resources`, and `Analysis.container` would be
a major bump, and is explicitly *not* proposed here. This RFC only establishes
the direction; a later RFC can retire them once real analyses have migrated.

## Questions or objections

Recorded as open. These are the forks this draft expects discussion to resolve.

- **Closed vocabulary, or free string?** A closed enum is machine-checkable and
  lets the "tracks staleness" criterion actually mean something, but it makes
  every new engine an RFC (or at least a PR). `other` is the escape hatch,
  though it is weak: it validates without telling a reader anything, relying on
  the analysis `description` to carry the real answer. An open string with a
  documented recommended vocabulary is the obvious alternative. Which failure
  is worse — an author blocked by the list, or a vocabulary that quietly fills
  with task runners that don't track staleness?

- **Is forbidding `resources` alongside `workflow_target` too strict?** The
  strong reading — the one implemented — is that a resource request is
  implementation and belongs to the engine. But HPC users may reasonably want
  the request *visible in the spec* as a declaration of what the analysis needs,
  independent of how any particular engine spells it. Counter-argument: that is
  a request for a portable resource vocabulary, which is a much larger design
  problem than this RFC, and `Resources` was never that. Worth deciding
  explicitly rather than by omission.

  (Note: LinkML forced this to some degree. A rule scoped narrowly to
  `recipe.command` via a nested `range_expression` postcondition mistranslates
  in `gen-json-schema` — it emits `'recipe' is a required property`, the
  opposite of the intent. The whole-`recipe` rule is both correct on the merits
  and the only form that reliably enforces.)

- **Should `workflow_target` be required on non-aliased outputs?** It is
  currently optional, so an output may declare neither a target nor a recipe —
  meaning "no declared build path". That is useful while drafting and for
  outputs produced by hand, but it is also how an analysis silently stays
  under-specified, which is the failure mode this RFC is about. Requiring it
  would be a breaking change and is not proposed; a validator *warning* may be
  the right middle ground.

- **Where does the artifact land?** `{output}` previously told a reader the path
  the artifact would be written to. A bare `workflow_target` does not, so
  answering "where is this figure?" now requires reading the workflow
  definition. An optional `path` alongside `workflow_target` was considered and
  rejected as a re-import of implementation — but the loss is real, and matters
  for `findings` whose evidence points at an artifact.

- **No engine version pinning.** `workflow_engine: snakemake` says nothing about
  which Snakemake. The workflow definition can pin it, and adding a `version`
  field would start rebuilding the structured-execution-context object this RFC
  removes. Recorded so the omission is deliberate rather than overlooked.

- **Self-promotion.** Calkit is authored by this RFC's author. It appears in the
  vocabulary on the same terms as every other engine — one line, alphabetical
  ordering, an explicit note that ordering implies no recommendation — and is
  deliberately *not* used in any example or worked walkthrough; both shipped
  examples use Snakemake. Flagged here so the choice is on the record and can be
  challenged.

## References

- [Snakemake](https://snakemake.github.io), [DVC](https://dvc.org),
  [Nextflow](https://www.nextflow.io), [CWL](https://www.commonwl.org),
  [WDL](https://openwdl.org), [`targets`](https://books.ropensci.org/targets/),
  [Calkit](https://github.com/calkit/calkit) — the prior art this RFC delegates
  to rather than reimplements.
- [The Turing Way, *Reproducible Environments*](https://book.the-turing-way.org/reproducible-research/renv)
  — on why recording an invocation without its environment is insufficient.
- [RFC-0001](0001-establish-the-rfc-process.md) — the process this RFC follows.
- [RFC-0002](0002-decouple-reports.md) — the same layering instinct applied to
  reports: ASTRA holds the record and the addressing, an external medium holds
  the prose. This RFC applies it to execution.
- Tracking issue: TBD.
