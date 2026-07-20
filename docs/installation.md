# Installation

This page gets the `astra` CLI installed and verified. From there, [getting started](getting-started.md) takes you from scaffold to a validated analysis in about ten minutes.

If you'd rather see the schema first, jump to the [specification](specification.md).

## Install

We recommend installing with [**uv**](https://docs.astral.sh/uv/) — Astral's fast Python package and project manager. If you don't have uv yet, follow the [official installation instructions](https://docs.astral.sh/uv/getting-started/installation/) (one-line install on macOS, Linux, and Windows).

=== "uv (recommended)"

    ```bash
    uv tool install astra-tools
    ```

=== "pip"

    ```bash
    pip install astra-tools
    ```

=== "From source"

    ```bash
    git clone https://github.com/LightconeResearch/ASTRA.git
    cd ASTRA
    uv pip install -e ".[dev]"
    ```

Verify the install:

```bash
astra --version
astra --help
```

## Next: getting started

[Getting started](getting-started.md) is the tour of the format itself: scaffold a project, edit the analysis, validate it, inspect it, define universes, and attach evidence.
