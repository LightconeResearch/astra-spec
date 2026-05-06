# Community

ASTRA is an open project. The schema, tooling, and documentation are all developed in the open, and contributions of every kind are welcome — from typo fixes and validation bug reports to new schema elements and downstream consumer libraries.

## Where to find us

| Channel | Use it for |
|---------|-----------|
| [`astra-spec` issues](https://github.com/LightconeResearch/astra-spec/issues) | Schema bugs, proposed schema changes, documentation issues. |
| [`ASTRA` (tools) issues](https://github.com/LightconeResearch/ASTRA/issues) | CLI bugs, validation issues, paper-cache problems. |
| [GitHub Discussions](https://github.com/LightconeResearch/astra-spec/discussions) | Questions, design discussion, "is this the right approach?" threads. |
| Pull requests | Code, schema, and documentation changes — for both repositories. |

When in doubt about which repo to file an issue in: schema or specification questions go to `astra-spec`; CLI / validator / paper-tool questions go to `ASTRA`.

## Contributing

The full guide lives in [`CONTRIBUTING.md`](https://github.com/LightconeResearch/astra-spec/blob/main/CONTRIBUTING.md). The short version:

1. **Open an issue first** for non-trivial changes — it gives reviewers context and avoids parallel work.
2. **Keep changes focused.** A schema change, a doc change, and a tooling change are three separate PRs.
3. **Run the project checks** locally before pushing. `just test` exercises schema validation, the Python data model, and the example fixtures. `just lint` lints the LinkML schema. `just docs-strict` builds the docs in strict mode.
4. **Update the docs alongside the schema.** Changes to `src/astra/schema/*.yaml` should also touch [`docs/specification.md`](specification.md) and the relevant tables.

### Adding schema elements

Schema changes follow a small ritual:

```bash
# Edit src/astra/schema/{analysis,universe,insight}.yaml

just gen-python    # Regenerate Python datamodels
just gen-doc       # Regenerate the schema reference docs (docs/elements/)
just lint          # Lint the LinkML schema
just test          # Run all tests
```

Open a PR with the schema, generated artefacts, and any doc updates in a single commit so reviewers see the full picture.

### Reporting problems

A useful issue includes:

- The version of `astra-spec` and `astra-tools` (e.g. `astra --version`).
- A minimal `astra.yaml` (or universe file) that reproduces the problem.
- The full error output, with copy-paste from the terminal.
- What you expected to happen instead.

Validation issues are easier to triage when accompanied by a fixture small enough to drop into `tests/data/` — a single decision and a single output is usually plenty.

## Citing ASTRA

The canonical namespace for ASTRA is `https://w3id.org/ASTRA/`. The schema version is recorded at the top of each LinkML source file (and in the generated artefacts). When citing the format in a paper or technical report, please reference both the version and the schema URL.

## Code of Conduct

We expect respectful, thoughtful collaboration in all project spaces — issues, pull requests, and discussions. Treat other contributors the way you would want to be treated; assume good faith; disagree with the idea, not the person. Conduct issues can be raised privately with the maintainers via GitHub.

## License

- **Schema** — [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **Code** — [BSD 3-Clause](https://github.com/LightconeResearch/astra-spec/blob/main/LICENSE)

Both licenses are permissive: you can adopt ASTRA in commercial and academic work alike. Schema reuse requires attribution; code reuse requires the standard BSD-3 notice.
