---
title: ASTRA
---

<h1 class="astra-hero">
  <img class="astra-hero--light astra-hero--wide" src="assets/brand/astra-lockup-descriptor.svg" alt="ASTRA: Agentic Schema for Transparent Research Analysis">
  <img class="astra-hero--dark astra-hero--wide" src="assets/brand/astra-lockup-descriptor-dark.svg" alt="ASTRA: Agentic Schema for Transparent Research Analysis">
  <img class="astra-hero--light astra-hero--narrow" src="assets/brand/astra-lockup.svg" alt="ASTRA">
  <img class="astra-hero--dark astra-hero--narrow" src="assets/brand/astra-lockup-dark.svg" alt="ASTRA">
</h1>

**Agentic Schema for Transparent Research Analysis** is a YAML specification for scientific analyses. Code captures execution, but not the full structure of an analysis: `astra.yaml` records the inputs, outputs, methodological choices, and evidence behind an experiment, making the work easier to reproduce and extend.

Agents are expanding the scale and speed of science, which shifts the bottleneck from producing results to trusting them. `astra.yaml` gives each experiment a structured record for agents to follow, keeping assumptions, choices, and evidence explicit.

ASTRA is intentionally agnostic to the execution harness so that agents, workflow runners, and humans can all read and act on the same spec.

<video autoplay muted loop playsinline preload="metadata" width="100%">
  <source src="assets/astraspecdemo.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

[:lucide-rocket: **Get started**](getting-started.md){ .md-button .md-button--primary }
[:lucide-book-open: Read the specification](specification.md){ .md-button }

!!! warning "Alpha development"
    ASTRA is in **early alpha**. The schema, CLI, and tooling are all still moving — expect breaking changes between minor versions, and pin the schema version in your analyses. Bug reports, design challenges, and use cases that the spec doesn't yet cover are exactly what we want to hear at this stage; please open an issue on the [GitHub repo](https://github.com/astra-project/astra-spec/issues), join the [Community](community.md) tab, or come help define the schema at the [Agentic AI 4 Science Developer Summit](https://lightconeresearch.org/developer-summit).
    
## Why ASTRA?

Scientific results depend on methodological choices: which data to include, how to handle outliers, which prior to assume, and so on. In ordinary research code, those choices are often scattered across notebooks, scripts, comments, and memory. This makes results hard to reproduce, audit, and expand.

ASTRA gives every methodological choice an explicit place in the spec. In ASTRA, decisions name the options that were considered, link to evidence, and feed into a *universe*, which records the results for a given set of choices.

## At a glance

In ASTRA, an analysis declares the design space, a universe picks one option per decision it uses, and the CLI allows for validation and inspection. Below is an example of an `astra.yaml`. For the full format, see the [specification](specification.md).

=== "Analysis (`astra.yaml`)"

    ```yaml
    spec_version: "0.1.0"
    label: Period-Luminosity Fit

    inputs:
      catalog_data:
        path: data/catalog_data.csv
        description: Periods and mean apparent magnitudes.

    outputs:
      fit_params:
        type: table
        format: csv
        description: Slope, intercept, and scatter for the fitted relation.
        inputs: [catalog_data]
        decisions: [fit_method]
        recipe:
          command: >-
            python src/fit_period_luminosity.py
            --catalog {inputs.catalog_data}
            --method {decisions.fit_method}
            --out {output}

    decisions:
      fit_method:
        label: Fitting method
        rationale: The fitting method determines how outliers influence the inferred relation.
        options:
          ordinary_least_squares:
            label: Ordinary least squares
          robust_linear:
            label: Robust linear fit
    ```

=== "Universe (`astra.yaml`)"

    ```yaml
    # astra.yaml, continued
    universes:
      baseline:
        description: Default configuration for the period-luminosity fit.
        decisions:
          fit_method: ordinary_least_squares
    ```

=== "Run it"

    ```bash
    uv tool install astra-tools

    astra validate
    astra info
    astra plan
    ```

---

[:simple-github: GitHub](https://github.com/astra-project/astra-spec){ .md-button }
[:lucide-package: PyPI (`astra-tools`)](https://pypi.org/project/astra-tools/){ .md-button }
