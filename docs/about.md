# About ASTRA

**ASTRA** stands for *Agentic Schema for Transparent Research Analysis*. It is a declarative format for describing scientific analyses in a way that is precise enough to drive automated execution and transparent enough to be audited, reproduced, and revisited.

## Who builds it

ASTRA is developed by [**Lightcone Research**](https://github.com/LightconeResearch). We write most of the code today, but ASTRA is intended to grow into a community-owned standard — we are looking for collaborators across disciplines and tooling stacks to help shape it.

## Open source by design

The position paper that motivated ASTRA argues that the substrate for agentic-era scientific records cannot live behind a vendor wall. We agree, and we are committed to keeping ASTRA open in three concrete ways:

- **Open licenses.** The schema is released under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and the code under [BSD 3-Clause](https://github.com/LightconeResearch/astra-spec/blob/main/LICENSE). Both permit unrestricted commercial and academic use.
- **Open development.** All work happens on public GitHub repositories — issues, discussions, and pull requests are visible from the first commit onward. There is no parallel private fork.
- **Open governance, eventually.** As ASTRA stabilises beyond alpha, we will move it into a community-governed structure (steering group, public RFC process, version-decision protocol). The current Lightcone Research stewardship is a starting point, not the long-term home.

If you would like to help shape that trajectory — through code, schema review, downstream tooling, or simply by trying ASTRA on a real analysis — see the [Community](community.md) page.

## License

- **Schema** — [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- **Code** — [BSD 3-Clause](https://github.com/LightconeResearch/astra-spec/blob/main/LICENSE)

## Citing

If you use ASTRA in your work, please cite the GitHub repository — the easiest way is the **"Cite this repository"** button on the [`astra-spec` GitHub page](https://github.com/LightconeResearch/astra-spec), which produces APA and BibTeX entries from the [`CITATION.cff`](https://github.com/LightconeResearch/astra-spec/blob/main/CITATION.cff) at the repo root. Include the schema version you targeted (it is recorded at the top of each LinkML source file and in every generated artefact).

The canonical namespace for ASTRA is `https://w3id.org/astra/`.

For the broader argument that motivates the project — agentic-era science, per-result trust, and why an open substrate matters — see the [Lightcone Research position paper](https://github.com/LightconeResearch/astra-paper) (a separate citation; not a replacement for citing ASTRA itself).

## Credits

The repository scaffolding is based on [`linkml-project-copier`](https://github.com/dalito/linkml-project-copier).
