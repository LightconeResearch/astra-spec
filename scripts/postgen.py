"""Post-generation patches for the Pydantic data model.

Injects ``@model_validator`` blocks that enforce the mutual-exclusion
rules declared on ``Input``, ``Output``, and ``Decision`` in
``analysis.yaml``. The LinkML pydantic generator currently emits the
rule metadata but not the matching runtime validators, so we add them
here. The script is idempotent — re-running it on an already-patched
file is a no-op.
"""

from __future__ import annotations

import pathlib
import re
import sys

PYDANTIC_PATH = pathlib.Path("src/astra/datamodel/astra_pydantic.py")

VALIDATORS: dict[str, str] = {
    "Input": '''
    @model_validator(mode="after")
    def _check_from_alias(self):
        if self.from_ is not None:
            extras = [
                f
                for f in (
                    "type",
                    "label",
                    "description",
                    "source",
                    "ref",
                    "ref_version",
                    "use_outputs",
                )
                if getattr(self, f) is not None
            ]
            if extras:
                raise ValueError(
                    f"Input with 'from' set must not declare {extras}; "
                    "aliased nodes inherit content from the source"
                )
        elif self.type is None:
            raise ValueError("Input must declare 'type' when 'from' is unset")
        return self

''',
    "Output": '''
    @model_validator(mode="after")
    def _check_from_alias(self):
        if self.from_ is not None:
            extras = [
                f
                for f in (
                    "type",
                    "label",
                    "description",
                    "inputs",
                    "decisions",
                    "recipe",
                )
                if getattr(self, f) is not None
            ]
            if extras:
                raise ValueError(
                    f"Output with 'from' set must not declare {extras}; "
                    "aliased nodes inherit content from the source"
                )
        elif self.type is None:
            raise ValueError("Output must declare 'type' when 'from' is unset")
        return self

''',
    "Decision": '''
    @model_validator(mode="after")
    def _check_from_alias(self):
        if self.from_ is not None:
            extras = [
                f
                for f in ("label", "options", "default", "rationale", "tags")
                if getattr(self, f) is not None
            ]
            if extras:
                raise ValueError(
                    f"Decision with 'from' set must not declare {extras}; "
                    "aliased nodes inherit content from the source"
                )
        else:
            missing = [f for f in ("label", "options") if getattr(self, f) is None]
            if missing:
                raise ValueError(
                    f"Decision must declare {missing} when 'from' is unset"
                )
        return self

''',
}


def main() -> int:
    src = PYDANTIC_PATH.read_text()

    if "model_validator" not in src:
        src = src.replace(
            "    field_validator,\n    model_serializer",
            "    field_validator,\n    model_serializer,\n    model_validator",
        )

    for class_name, validator_block in VALIDATORS.items():
        class_marker = f"class {class_name}(ConfiguredBaseModel):"
        next_class_re = re.compile(r"\n\nclass [A-Z]\w*\(", re.MULTILINE)

        try:
            class_start = src.index(class_marker)
        except ValueError:
            print(f"Warning: class {class_name} not found in {PYDANTIC_PATH}", file=sys.stderr)
            continue

        next_match = next_class_re.search(src, class_start + len(class_marker))
        class_end = next_match.start() if next_match else len(src)
        class_body = src[class_start:class_end]

        if "_check_from_alias" in class_body:
            continue

        anchor = "    @field_validator('id')"
        anchor_idx = class_body.find(anchor)
        if anchor_idx == -1:
            print(
                f"Warning: anchor '{anchor.strip()}' not found in {class_name}; skipping",
                file=sys.stderr,
            )
            continue

        insert_at = class_start + anchor_idx
        src = src[:insert_at] + validator_block.lstrip("\n") + src[insert_at:]

    PYDANTIC_PATH.write_text(src)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
