# Templates for the LinkML documentation generator

`just gen-doc` passes this folder to `gen-doc` as its template directory. The templates are written in Jinja2.

- `type.md.jinja2` and `slot.md.jinja2` are LinkML's own, changed as the first comment of each says.
- `common_metadata.md.jinja2` is LinkML's own, unchanged: both of them include it from this folder.

Every other page uses LinkML's default template, available in the
[linkml repository](https://github.com/linkml/linkml/tree/main/linkml/generators/docgen).
