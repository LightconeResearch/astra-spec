# Installation

`astra` comes in the `astra-tools` package. It needs Python 3.11 or later and git, which it runs
to read repositories.

## Install

With [uv](https://docs.astral.sh/uv/), which keeps `astra` apart from your projects'
environments:

```bash
uv tool install astra-tools
```

With pip:

```bash
pip install astra-tools
```

While astra-tools for ASTRA 0.1 has only release candidates, uv and pip skip them. Ask for them
with `uv tool install --prerelease allow astra-tools`, or `pip install --pre astra-tools`.

To run it once without installing it, name the version:

```bash
uvx astra-tools@<version> validate
```

Check that it works:

```bash
astra --version
astra --help
```

## Which ASTRA it reads

astra-tools reads ASTRA 0.1 files, those whose `spec_version` is `0.1.x`. It installs the
schemas and rules of the specification with it, as the `astra-spec` package. A file written for
ASTRA 0.0.x states its version as `version:`, and fails the schema checks: `MISSING_FIELD` for
`spec_version`, `UNKNOWN_FIELD` for `version`, and others. The 0.2 line of astra-tools reads such
a file as it is:

```bash
uv tool install 'astra-tools<0.3'
```

## Next

- [Getting started](https://astra-spec.org/0.1/getting-started/) writes a first analysis and
  validates it.
- The [CLI reference](cli.md) describes every command.
- [Tab completion](cli.md#astra-completion) for bash, zsh and fish is one line in your shell's
  startup file.
- To work on astra-tools itself, see its [README](https://github.com/LightconeResearch/astra-tools#readme).
