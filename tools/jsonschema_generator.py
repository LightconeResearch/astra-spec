"""LinkML's JSON Schema generator, with id-keyed maps checked as maps.

A map is a multivalued slot inlined as a dict: each entry is written under its
key. For every map, stock LinkML 1.12.1 leaves the keys unchecked, accepts a
string or null as well as an object for an entry, and lets the entry repeat its
own key. This generator instead:

1. adds ``propertyNames``, so every key matches the key slot's pattern;
2. allows one written form per entry:
   - the compact form, when the class has its key and exactly one other slot:
     the entry is that slot's value;
   - otherwise the object form: the entry is the object, without its key. In a
     closed schema the key is then written once, as the map key; an open one
     lets an entry repeat it as a field it doesn't define.

It also:

3. adds ``uniqueItems`` to every multivalued slot of scalars, so that no list of
   strings holds the same entry twice (lists of objects are left as they are);
4. drops every ``$defs`` entry the root can't reach through ``$ref``, and keeps
   only standard JSON Schema keywords at the top level: LinkML's
   ``metamodel_version`` goes, and the schema's ``version`` moves into
   ``$comment``.

Through :func:`generate`, optional fields also reject null (``include_null=False``),
and the schema's ``$id`` can be set, so that each generated file is identified
by its own URI.
"""

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path

from linkml.generators.jsonschemagen import JsonSchema, JsonSchemaGenerator
from linkml_runtime.linkml_model.meta import SlotDefinition

DEF_PREFIX = "#/$defs/"
"""How a `$ref` to an entry of the schema's `$defs` starts."""


@dataclass
class AstraJsonSchemaGenerator(JsonSchemaGenerator):
    """A JSON Schema generator whose maps check their keys and take one form per entry."""

    _entry_keys: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    """Each object-form entry definition the maps reference, with the key property it drops."""

    def get_subschema_for_slot(
        self, slot, omit_type=False, include_null=True, cls=None
    ):
        """LinkML's subschema for `slot`; for a map, with `propertyNames` and the one form its entries take."""
        prop = super().get_subschema_for_slot(
            slot, omit_type=omit_type, include_null=include_null, cls=cls
        )
        key_slot = None if omit_type else self._map_key_slot(slot)
        if key_slot is not None:
            key_pattern = self.get_subschema_for_slot(key_slot, include_null=False).get(
                "pattern"
            )
            prop["propertyNames"] = JsonSchema({"type": "string"})
            prop["propertyNames"].add_keyword("pattern", key_pattern)
            prop["additionalProperties"] = self._entry_subschema(slot, key_slot)
        if (
            not omit_type
            and prop.is_array
            and getattr(slot, "range", None) not in self.schemaview.all_classes()
        ):
            prop["uniqueItems"] = True
        return prop

    def after_generate_schema(self, schema, sv):
        """LinkML's schema, with the keys dropped from map entries, unreachable `$defs` pruned, the top level standard."""
        schema = super().after_generate_schema(schema, sv)
        top = schema.schema_
        for name, key in self._entry_keys.items():
            entry = top["$defs"][name]
            del entry["properties"][key]
            if key in entry.get("required", []):
                entry["required"].remove(key)
        reached = _reachable_defs(top)
        top["$defs"] = {
            name: definition
            for name, definition in top["$defs"].items()
            if name in reached
        }
        top.pop("metamodel_version", None)
        version = top.pop("version", None)
        if version is not None:
            top["$comment"] = f"{self.schema.name} schema version {version}"
        return schema

    def _map_key_slot(self, slot) -> SlotDefinition | None:
        """The entries' key slot if `slot` is a map, otherwise None."""
        sv = self.schemaview
        if (
            not getattr(slot, "multivalued", False)
            or slot.inlined_as_list
            or not sv.is_inlined(slot)
        ):
            return None
        if slot.range not in sv.all_classes():
            return None
        return sv.get_identifier_slot(slot.range, use_key=True)

    def _entry_subschema(self, slot, key_slot: SlotDefinition) -> JsonSchema:
        """The one form an entry of the map `slot` takes: compact if the class has one slot besides its key."""
        others = [
            s
            for s in self.schemaview.class_induced_slots(slot.range)
            if s.name != key_slot.name
        ]
        if len(others) == 1:
            return self.get_subschema_for_slot(others[0], include_null=False)
        _, _, reference = self.get_type_info_for_slot_subschema(slot)
        entry = JsonSchema.ref_for(reference, identifier_optional=True)
        for ref in entry.get("anyOf", [entry]):
            self._entry_keys[ref["$ref"].removeprefix("#/$defs/")] = (
                self.aliased_slot_name(key_slot)
            )
        return entry


def _references(node) -> set[str]:
    """The names of the `$defs` entries that a `$ref` anywhere in `node` points to."""
    if isinstance(node, list):
        return set().union(*map(_references, node))
    if not isinstance(node, dict):
        return set()
    found = set().union(*map(_references, node.values()))
    ref = node.get("$ref")
    if isinstance(ref, str) and ref.startswith(DEF_PREFIX):
        found.add(ref.removeprefix(DEF_PREFIX))
    return found


def _reachable_defs(schema: dict) -> set[str]:
    """The `$defs` entries of `schema` that its root reaches through `$ref`, directly or through other entries."""
    defs = schema.get("$defs", {})
    reached: set[str] = set()
    todo = _references({key: value for key, value in schema.items() if key != "$defs"})
    while todo:
        name = todo.pop()
        reached.add(name)
        todo |= _references(defs[name]) - reached
    return reached


def generate(
    schema: str | Path, *, closed: bool = True, schema_id: str | None = None
) -> dict:
    """The JSON Schema for the LinkML `schema`: closed unless `closed` is false; optional fields reject null.

    Its `$id` is `schema_id` if given, otherwise the LinkML schema's own id, as LinkML sets it.
    """
    generator = AstraJsonSchemaGenerator(
        str(schema), include_null=False, not_closed=not closed
    )
    result = json.loads(generator.serialize())
    if schema_id is not None:
        result["$id"] = schema_id
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Write the JSON Schema for a LinkML schema to stdout."
    )
    parser.add_argument("schema", type=Path, help="the LinkML schema (YAML)")
    parser.add_argument(
        "--not-closed",
        action="store_true",
        help="allow fields the schema does not declare",
    )
    parser.add_argument(
        "--id",
        metavar="URI",
        dest="schema_id",
        help="the `$id` of the JSON Schema (default: the schema's id)",
    )
    args = parser.parse_args(argv)
    print(
        json.dumps(
            generate(args.schema, closed=not args.not_closed, schema_id=args.schema_id),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
