# Templates for LinkML's generators

`just gen-doc` passes this folder to `gen-doc` (`tools/docgen.py`) as its template directory (`LINKML_GENERATORS_DOC_ARGS` in `config.public.mk`), and `just gen-python` passes `pydantic/` to `gen-pydantic` as its. The templates are written in Jinja2.

- `type.md.jinja2` and `slot.md.jinja2` are LinkML's own, changed as the first comment of each says.
- `common_metadata.md.jinja2` is LinkML's own, unchanged: the type and slot templates include it from this folder.
- `pydantic/base_model.py.jinja` is LinkML's own base model of the Pydantic models, with one validator added: each entry of a map keyed by `id`, which an `astra.yaml` writes without its `id`, takes its key as its `id`.

Every other page, and every other part of the Pydantic models, uses LinkML's default template, available in the
[linkml repository](https://github.com/linkml/linkml/tree/main/linkml/generators) (`docgen/`, `pydanticgen/templates/`).
