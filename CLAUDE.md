# ASTRA Spec - Development Notes

## Schema and Documentation

The ASTRA schema is defined in LinkML files under `src/astra/schema/`. When modifying any schema file (`analysis.yaml`, `insight.yaml`, `universe.yaml`), you **must** also update the corresponding documentation:

- **`docs/index.md`** — The human-readable specification. Update field tables, examples, and descriptions to reflect schema changes.
- **`README.md`** — If the change affects the quick example or design principles, update the README too.

Run `just gen-python` to regenerate Python datamodels and `just gen-doc` to regenerate the schema reference docs after any schema change.

## Key Commands

```bash
just test        # Run all tests
just gen-python  # Regenerate Python datamodels from schema
just gen-doc     # Regenerate schema reference documentation
just lint        # Lint the schema
just docs-serve  # Build and preview docs locally with live reload
```

## Repository Layout

- `src/astra/schema/` — LinkML schema source files (edit these)
- `src/astra/datamodel/` — Generated Python datamodel (do not edit directly)
- `docs/` — Documentation source (rendered with [Zensical](https://zensical.org/); config in `zensical.toml`)
- `docs/index.md` — The ASTRA format specification
- `examples/` — Example ASTRA projects (iris, iris_pipeline)
- `tests/data/` — Test fixtures (valid, invalid, problem)
