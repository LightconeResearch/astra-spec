# ASTRA Specification

The ASTRA format specification is published per release. Each released version
is **frozen** — its documents and schema artifacts are preserved indefinitely
so analyses can validate against the exact spec they were authored for.

[:lucide-book-open: Read the draft](draft/){ .md-button .md-button--primary }
[:lucide-file-json: Schema artifacts](../schema/draft/astra.schema.json){ .md-button }

## Versions

<!-- VERSIONS:START -->
- [draft](draft/) — work in progress
<!-- VERSIONS:END -->

## Schema artifacts

Machine-readable artifacts are available for every version at stable URLs:

- `https://astra-spec.org/schema/<version>/astra.yaml` — merged LinkML schema
- `https://astra-spec.org/schema/<version>/astra.schema.json` — JSON Schema
- `https://astra-spec.org/schema/<version>/astra.context.jsonld` — JSON-LD context

Replace `<version>` with `draft` for the in-progress spec, or with a released
version (e.g. `0.0.7`) for a frozen one.

## Versioning policy

- Working changes happen on the `draft` track.
- A release (`just release X.Y.Z`) snapshots `draft/` into `X.Y.Z/` and tags
  the repository. The snapshot is never edited again.
- Released versions remain reachable at `https://astra-spec.org/specification/X.Y.Z/`
  and `https://astra-spec.org/schema/X.Y.Z/...` for as long as the project
  publishes the site.
