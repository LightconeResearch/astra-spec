# Fixtures

Each fixture is a whole document, validated by `tests/test_fixtures.py` as a
consumer would: read as YAML 1.2 (ruamel.yaml's safe loader, which keeps
`yes`, `no` and `on` as strings and rejects duplicate keys), then checked by a
plain `jsonschema` 2019-09 validator against the committed generated schema in
`src/astra/schema/generated/`.

- `valid/` holds documents the schema accepts.
- `invalid/` holds documents that each break one rule: a minimal valid
  document with one thing changed.

## Names

A fixture is named `<Root>-<nnn>-<what>.yaml`:

- `<Root>` is the class the document is an instance of, `Analysis` or
  `ProvenanceRecord`. It picks the schema (`analysis.schema.json` or
  `provenance.schema.json`), and is everything before the first `-`.
- `<nnn>` numbers the fixture: from `001` for valid fixtures, from `101` for
  invalid ones.
- `<what>` says, in a few words, what the fixture holds or breaks.

## Invalid fixtures

An invalid fixture starts with exactly two comment lines:

```yaml
# rule: <CODE>
# fails at: <location>
```

- `<CODE>` is the code of the rule it breaks, from the rule catalogue (design
  §7).
- `<location>` is where it fails: `parse` when the YAML loader rejects the
  file, otherwise the JSON Pointer of the failing value, or `(root)` for the
  document. The test asserts that the validator reports an error there.

`jsonschema` reports an error at these locations:

| What fails | Location |
|---|---|
| missing field, unknown field, `exactly_one_of`, rules | the object |
| bad map key, empty map | the map |
| wrong value or wrong type | the value |

A fixture that fails at `parse` (a duplicate key) is not valid YAML, so it is
excluded from the repository's YAML linters (`.yamllint.yaml` and
`check-yaml` in `.pre-commit-config.yaml`).
