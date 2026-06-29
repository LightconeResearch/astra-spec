# CLI Reference

The `astra` command-line tool authors, validates, and inspects ASTRA analyses. It is shipped as the `astra-tools` package and is independent of any execution engine — it only reads, writes, and validates ASTRA YAML.

## Installation

```bash
uv tool install astra-tools
```

This installs the `astra` executable on your `PATH`, isolated from your project environments. See [Getting started](getting-started.md#install) for `pip` and from-source alternatives. To verify:

```bash
astra --version
astra --help
```

## Commands at a glance

| Command | Purpose |
|---------|---------|
| [`astra init`](#astra-init) | Scaffold a minimal ASTRA project |
| [`astra validate`](#astra-validate) | Validate an analysis or universe file |
| [`astra info`](#astra-info) | Show a summary of an analysis |
| [`astra viz`](#astra-viz) | Visualise the decision space |
| [`astra universe`](#astra-universe) | Generate and check universe files |
| [`astra schema`](#astra-schema) | Export or print the LinkML schema |
| [`astra paper`](#astra-paper) | Manage cached papers and verify quotes |

`astra` and most subcommands accept `--help` for full inline documentation.

---

## `astra init`

Create a minimal ASTRA analysis scaffold. The scaffold contains an `astra.yaml` boilerplate, a `universes/baseline.yaml`, an empty `src/` for analysis code, and a `.gitignore`. By default a fresh git repository is initialised in the new directory.

```bash
astra init my-analysis
astra init my-analysis --no-git     # skip git initialisation
astra init .                        # scaffold in the current directory
```

**Resulting layout:**

```
my-analysis/
├── astra.yaml              # Analysis specification (source of truth)
├── .gitignore
├── src/                    # Your analysis code
└── universes/
    └── baseline.yaml       # Default decision selection
```

The boilerplate `astra.yaml` includes a single example decision and outputs marked with `TODO:` to guide you through filling them in.

---

## `astra validate`

Validate an analysis or universe file.

```bash
astra validate astra.yaml
astra validate universes/baseline.yaml          # universe (analysis auto-discovered)
astra validate universes/foo.yaml -a astra.yaml # universe with explicit analysis
```

Validation runs in stages:

1. **Schema validation** — structure, types, required fields, format patterns (Pydantic models generated from the LinkML schema).
2. **Semantic validation** — duplicate IDs, default options exist, `from:` paths and tree-path references resolve, recipe template placeholders match `Output.inputs` / `Output.decisions`, universe selections match analysis decisions, constraints respected, etc.

### Evidence verification

When an analysis declares `prior_insights:` or `findings:`, `astra validate` can additionally check that quoted text in literature evidence actually appears in the source PDFs:

```bash
astra validate astra.yaml --verify-evidence
astra validate astra.yaml --skip-evidence    # skip even when present
```

Papers must be cached locally first with [`astra paper add`](#astra-paper-add). Evidence backed by analysis artifacts (typical for `findings`) is reported as `SKIPPED` until the artifact is materialised.

**Options:**

| Flag | Meaning |
|------|---------|
| `-a, --analysis PATH` | Analysis file (when validating a universe) |
| `-e, --verify-evidence` | Verify evidence quotes against cached papers |
| `--skip-evidence` | Skip evidence verification |

---

## `astra info`

Print a summary of an analysis: name, version, description, counts, and tables of inputs, outputs, and decisions. The analysis file is auto-discovered by walking up from the current directory if `--file` is not provided.

```bash
astra info                          # full summary
astra info --decisions              # decisions only
astra info --inputs                 # inputs only
astra info --outputs                # outputs only
astra info -f path/to/astra.yaml    # explicit file
```

Decisions are displayed as a tree, with sub-analyses nested under their parent.

---

## `astra viz`

Visualise the decision space.

```bash
astra viz                           # ASCII tree (default)
astra viz --format mermaid          # Mermaid diagram (paste into Markdown)
```

The Mermaid output renders all decisions and options, highlights defaults, and draws `incompatible_with` / `requires` constraint edges. It can be embedded directly in Markdown documentation:

````markdown
```mermaid
graph TD
    ...
```
````

---

## `astra universe`

Universe management commands.

### `astra universe generate`

Generate a universe YAML file from the analysis's `default` options.

```bash
astra universe generate --name baseline
astra universe generate -n svm-focused -d "SVM with standard scaling"
astra universe generate -n baseline -o custom/path.yaml
```

Every decision in the analysis tree must declare a `default`; otherwise the command lists the missing decisions and exits.

**Options:**

| Flag | Default | Meaning |
|------|---------|---------|
| `-n, --name` | `baseline` | Universe ID and filename stem |
| `-a, --analysis` | auto | Analysis file |
| `-o, --output` | `universes/<name>.yaml` | Output path |
| `-d, --description` | _(none)_ | Universe description string |

### `astra universe check`

Validate a universe file against the constraints declared in the analysis.

```bash
astra universe check universes/baseline.yaml
astra universe check universes/foo.yaml -a path/to/astra.yaml
```

The same checks run inside `astra validate`, but `universe check` is convenient when iterating on universe files without re-running the full analysis validation.

---

## `astra schema`

Operate on the underlying LinkML schema files (sourced from `astra-spec`).

### `astra schema export`

Copy the LinkML schema YAMLs into a directory of your choice.

```bash
astra schema export                    # default: ./schemas/
astra schema export -o vendor/astra/   # custom path
```

### `astra schema show`

Print one of the schema files to stdout.

```bash
astra schema show analysis     # main analysis schema
astra schema show universe     # universe schema
astra schema show insights     # insight + evidence schema
```

---

## `astra paper`

Manage a local cache of papers used as evidence sources, and verify that quoted text exists in the cached PDFs.

The cache lives under `~/.cache/astra/papers/` (XDG-compliant) and is keyed by DOI (and version, for arXiv). Operations are content-addressed: each cached paper records a SHA-256 of the PDF.

### `astra paper add`

Add a paper to the cache.

```bash
astra paper add 10.48550/arXiv.1706.03762 --version 7
astra paper add 10.1038/s41586-023-06221-2
astra paper add 10.1234/example --pdf ./local_paper.pdf
```

`--pdf` registers a local file in the cache without downloading. Without it, the CLI downloads the paper from the DOI: arXiv DOIs (prefix `10.48550/arXiv.`) are fetched directly from `arxiv.org`, with `--version` selecting a specific revision; other DOIs are resolved through [Unpaywall](https://unpaywall.org/) for an open-access PDF and will fail if no open copy is available. Title and authors are fetched separately via DOI content-negotiation against `doi.org`.

### `astra paper list`

List all cached papers.

```bash
astra paper list
```

### `astra paper show`

Show metadata of a single cached paper.

```bash
astra paper show 10.48550/arXiv.1706.03762 --version 7
```

### `astra paper path`

Print the absolute path of a cached PDF — handy for piping into other tools or agents.

```bash
astra paper path 10.48550/arXiv.1706.03762 -v 7
xdg-open "$(astra paper path 10.48550/arXiv.1706.03762 -v 7)"
```

### `astra paper remove`

Remove a paper from the cache.

```bash
astra paper remove 10.48550/arXiv.1706.03762 -v 7
```

### `astra paper fetch-metadata`

Fetch title and authors via DOI content negotiation. Useful when papers were added with `--pdf` and have no upstream metadata yet.

```bash
astra paper fetch-metadata 10.48550/arXiv.1706.03762
astra paper fetch-metadata --all      # back-fill metadata for all cached papers
```

### `astra paper verify-quote`

Check that a single quoted text appears in a cached paper. Uses fuzzy matching to tolerate minor extraction differences.

```bash
astra paper verify-quote 10.48550/arXiv.1706.03762 \
  -q "FlexZBoost achieves a normalized median absolute deviation of 0.018"
astra paper verify-quote DOI -q "..." --page 8
astra paper verify-quote DOI -q "..." --json     # machine-readable output
```

Exit codes: `0` (verified), `1` (not found), `2` (paper not cached or extraction error).

### `astra paper verify-quotes`

Bulk variant of `verify-quote`. Reads a JSON list of quotes from `stdin`, extracts PDF text once, and writes a JSON report to `stdout`.

```bash
echo '{"quotes":[{"text":"...","page":8},{"text":"..."}]}' \
  | astra paper verify-quotes 10.48550/arXiv.1706.03762
```

Designed to be driven by agents and CI scripts.
