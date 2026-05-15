# ASTRA

**Agentic Schema for Transparent Research Analysis** is a YAML specification for scientific analyses. Beyond code alone, `astra.yaml` records the narrative, inputs, outputs, methodological choices, and evidence behind an experiment, making the work easier to reproduce and extend.

Agents are expanding the scale and speed of science, which shifts the bottleneck from producing results to trusting them. Luckily, agents also help with writing the `astra.yaml`, which gives each experiment a structured record and keeps the agents in check.

<video autoplay muted loop playsinline preload="metadata" width="100%">
  <source src="assets/astraspecdemo.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

[:lucide-rocket: **Get started**](getting-started.md){ .md-button .md-button--primary }
[:lucide-book-open: Read the specification](specification.md){ .md-button }

!!! warning "Alpha development"
    ASTRA is in **early alpha**. The schema, CLI, and tooling are all still moving — expect breaking changes between minor versions, and pin the schema version in your analyses. Bug reports, design challenges, and use cases that the spec doesn't yet cover are exactly what we want to hear at this stage; please open an issue on the [GitHub repo](https://github.com/LightconeResearch/astra-spec/issues) or join the [Community](community.md) tab.

## Why ASTRA?

Scientific results depend on methodological choices: which data to include, how to handle outliers, which prior to assume, and so on. In ordinary research code, those choices are often scattered across notebooks, scripts, comments, and memory. This makes results hard to reproduce, audit, and expand.

ASTRA gives every methodological choice an explicit place in the spec. In ASTRA, decisions name the options that were considered, link to evidence, and feed into a *universe*, which records the results for a given set of choices.

## At a glance

In ASTRA, an analysis declares the design space, a universe picks one option per decision, and the CLI allows for validation and inspection. Below is an example of an `astra.yaml`. For a detailed walkthrough of the spec, see our [specification explained](specification.md).

=== "Analysis (`astra.yaml`)"

```yaml
version: "1.0"
name: Period-Luminosity Fit

inputs:
  - id: catalog_data
    type: data
    source: data/catalog_data.csv
    description: Periods and mean apparent magnitudes.

outputs:
  - id: fit_params
    type: table
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
    default: ordinary_least_squares
    options:
      ordinary_least_squares:
        label: Ordinary least squares
      robust_linear:
        label: Robust linear fit
```

=== "Universe (`universes/baseline.yaml`)"

```yaml
# universes/baseline.yaml
id: baseline
description: Default configuration for the period-luminosity fit.

decisions:
  fit_method: ordinary_least_squares
```

=== "Run it"

````
```bash
uv tool install astra-tools

astra validate astra.yaml
astra info
astra viz
```
````

---

[:simple-github: GitHub](https://github.com/LightconeResearch/astra-spec){ .md-button }
[:lucide-package: PyPI (`astra-tools`)](https://pypi.org/project/astra-tools/){ .md-button }
