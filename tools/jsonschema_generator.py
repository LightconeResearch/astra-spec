"""LinkML's JSON Schema generator, with id-keyed maps checked as maps and class-level checks guarded by type.

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
   ``$comment``;
5. moves each class-level check, the ``oneOf`` of an ``exactly_one_of`` and the
   ``if``/``then`` of each class rule, into its own member of ``allOf``, in that
   order, guarded by the JSON types of what it reads: ``{if: G, then: {oneOf:
   …}}``, and ``{if: G + the rule's if, then: the rule's then}``, where ``G`` is
   ``{type: object, properties: {f: {type: <f's JSON type>}}}`` over the fields
   ``f`` the check reads (for a field written as a ``$ref``, the JSON type of
   its range: ``string`` for an enum, ``object`` for an inlined class). Stock
   LinkML's checks only test whether a key is there, so a value that isn't an object, or a field that is null or of
   another type, breaks them too; guarded, a check is skipped exactly when a
   ``type`` keyword already fails, so no verdict changes and a value of the
   wrong type is reported once, by its ``type``. Each ``required`` in a check
   also gets its fields in a ``properties`` beside it, inside a ``not`` too (an
   empty ``{}`` elsewhere goes), so that Ajv compiles the schema under
   ``strict: true``. A check on whether a multivalued field is there reads no
   value, so the array of anything LinkML writes for it, ``{type: array,
   items: {}}``, which a map, an object, would fail, becomes ``{}``.

Each step runs in one of the lifecycle hooks LinkML's JSON Schema generator
offers for changing what it generates (``LifecycleMixin``), never in an
override of its own methods: steps 1 to 3 in ``after_generate_class_slot``, on
each field of a class, step 5 in ``after_generate_class``, and step 4, with the
keys step 2 drops from the entries' definitions, in ``after_generate_schema``.

Through :func:`generate`, optional fields also reject null (``include_null=False``),
and the schema's ``$id`` can be set, so that each generated file is identified
by its own URI. In that ``$id``, ``{series}`` stands for the series of the
schema's version (:func:`series`): ``X.Y`` for a release ``X.Y.Z``, so that
every patch of a minor version shares its URIs, the whole version for a
pre-release such as ``0.1.0rc1``, and ``dev`` between releases.
"""

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from linkml.generators.jsonschemagen import JsonSchema, JsonSchemaGenerator
from linkml_runtime.linkml_model.meta import SlotDefinition

DEF_PREFIX = "#/$defs/"
"""How a `$ref` to an entry of the schema's `$defs` starts."""

SERIES = "{series}"
"""The placeholder in a schema's `$id` for the series of its version."""

RELEASE = re.compile(r"([0-9]+\.[0-9]+)\.[0-9]+")
"""A release's version, `X.Y.Z`, whose series is `X.Y`."""

PRE_RELEASE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+(?:a|b|rc)[0-9]+")
"""A pre-release's version, `X.Y.Z` then `aN`, `bN` or `rcN` (PEP 440's normal form), its own series."""

DEV = "dev"
"""The version, and the series, of what is built between releases."""


@dataclass
class AstraJsonSchemaGenerator(JsonSchemaGenerator):
    """A JSON Schema generator whose maps check their keys and take one form per entry, and whose class-level checks
    are guarded by the types of what they read."""

    _entry_keys: dict[str, str] = field(default_factory=dict, init=False, repr=False)
    """Each object-form entry definition the maps reference, with the key property it drops."""

    def after_generate_class_slot(self, slot, cls, sv):
        """LinkML's subschema for the field `slot` of the class `cls`: for a map, with `propertyNames` and the one form
        its entries take (steps 1 and 2); for a list of scalars, with `uniqueItems` (step 3)."""
        slot = super().after_generate_class_slot(slot, cls, sv)
        prop, source = slot.schema_, slot.source
        key_slot = self._map_key_slot(source)
        if key_slot is not None:
            key_pattern = self.get_subschema_for_slot(key_slot, include_null=False).get(
                "pattern"
            )
            prop["propertyNames"] = JsonSchema({"pattern": key_pattern})
            prop["additionalProperties"] = self._entry_subschema(
                source, key_slot, prop["additionalProperties"]
            )
        if prop.is_array and source.range not in sv.all_classes():
            prop["uniqueItems"] = True
        return slot

    def after_generate_class(self, cls, sv):
        """LinkML's subschema for the class `cls`, with its class-level checks guarded in `allOf` (step 5)."""
        cls = super().after_generate_class(cls, sv)
        name = cls.source.name
        properties = cls.schema_.get("properties", {})
        ref_types = {}
        for slot in sv.class_induced_slots(name):
            prop = self.aliased_slot_name(slot)
            if slot.multivalued or "$ref" not in properties.get(prop, {}):
                continue
            if slot.range in sv.all_enums():
                ref_types[prop] = "string"
            elif slot.range in sv.all_classes() and sv.is_inlined(slot):
                ref_types[prop] = "object"
        _guard_checks(cls.schema_, name, ref_types)
        return cls

    def after_generate_schema(self, schema, sv):
        """LinkML's schema, with the keys dropped from map entries, unreachable `$defs` pruned, the top level standard."""
        schema = super().after_generate_schema(schema, sv)
        top = schema.schema_
        for name, key in self._entry_keys.items():
            entry = top["$defs"][name]
            del entry["properties"][key]
            if key in entry.get("required", []):
                entry["required"].remove(key)
            if entry.get("required") == []:
                # LinkML leaves `required` empty when the key was the entry's one required field; an empty `required`
                # checks nothing (JSON Schema 2019-09 Validation §6.5.3), so it goes.
                del entry["required"]
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

    def _entry_subschema(
        self, slot, key_slot: SlotDefinition, forms: JsonSchema
    ) -> JsonSchema:
        """The one form an entry of the map `slot` takes, of the `forms` LinkML allows it: compact if the class has one
        slot besides its key, otherwise the object form, LinkML's reference to the class's definition without its key.
        """
        others = [
            s
            for s in self.schemaview.class_induced_slots(slot.range)
            if s.name != key_slot.name
        ]
        if len(others) == 1:
            return self.get_subschema_for_slot(others[0], include_null=False)
        refs = _keyless_refs(forms)
        if not refs:
            raise ValueError(
                f"{slot.name}: LinkML allows its entries no form without their key"
            )
        for ref in refs:
            self._entry_keys[ref["$ref"].removeprefix(DEF_PREFIX)] = (
                self.aliased_slot_name(key_slot)
            )
        return refs[0] if len(refs) == 1 else JsonSchema({"anyOf": refs})


def _keyless_refs(forms: dict) -> list[dict]:
    """The `$ref`s in `forms`, LinkML's subschema for the entries of a map, to a class's definition without its key
    (``<Class>__identifier_optional``), one for each class an entry may be."""
    if "$ref" in forms:
        suffix = JsonSchema.OPTIONAL_IDENTIFIER_SUFFIX
        return [forms] if forms["$ref"].endswith(suffix) else []
    return [ref for sub in forms.get("anyOf", []) for ref in _keyless_refs(sub)]


UNGUARDED = ("anyOf", "not")
"""Class-level keywords LinkML can write that step 5 doesn't guard (an `any_of`, a `none_of`, a slot that must be
absent), any more than a rule's `else`: the generator fails on them rather than leave a check unguarded."""

SUBSCHEMAS = ("not", "if", "then", "else")
"""Keywords of a check whose value is one subschema of the same object."""

SUBSCHEMA_LISTS = ("oneOf", "anyOf", "allOf")
"""Keywords of a check whose value is a list of subschemas of the same object."""

JSON_TYPES = {"object", "array", "string", "integer", "number", "boolean"}
"""The JSON types a field a check reads may have, for its guard: one each, never `null` (no field takes it)."""

ANY_ARRAY = {"type": "array", "items": {}}
"""What LinkML writes in a check for a multivalued field whose presence alone it reads: an array of anything, even for
a map, which is an object. A presence check reads no value, so step 5 writes `{}` in its place."""


def _guard_checks(node: dict, name: str, ref_types: dict[str, str]) -> None:
    """Step 5 on `node`, the subschema of the class `name`: each class-level check moved into a guarded `allOf` member.

    The checks are the `oneOf` of the class's `exactly_one_of`, then each class rule, which LinkML writes as the
    class's `if`/`then` when there is one and as members of `allOf` when there are several. `ref_types` gives the JSON
    type of each single-valued field written as a `$ref`, which has no `type` of its own: `string` for an enum, `object`
    for an inlined class.
    """
    for keyword in UNGUARDED:
        if keyword in node:
            raise ValueError(
                f"{name}: a class-level {keyword!r}, which the generator can't guard"
            )
    checks: list[tuple[dict, dict]] = []
    if "oneOf" in node:
        checks.append(({}, {"oneOf": node.pop("oneOf")}))
    rules = []
    if {"if", "then", "else"} & node.keys():
        rules.append(
            {
                keyword: node.pop(keyword)
                for keyword in ("if", "then", "else")
                if keyword in node
            }
        )
    rules.extend(node.pop("allOf", []))
    for rule in rules:
        if "else" in rule:
            raise ValueError(
                f"{name}: a class rule's 'else', which the generator can't guard"
            )
        if "then" not in rule or set(rule) - {"if", "then"}:
            raise ValueError(
                f"{name}: a class-level check that isn't a class rule's `if` and `then`: {dict(rule)}"
            )
        checks.append((rule.get("if", {}), rule["then"]))
    if checks:
        node["allOf"] = [
            _guarded(node, name, condition, then, ref_types)
            for condition, then in checks
        ]


def _guarded(
    node: dict, name: str, condition: dict, then: dict, ref_types: dict[str, str]
) -> dict:
    """The `allOf` member for one check of the class `name` (subschema `node`): `then` applies where `condition` holds,
    the value is an object, and each field the check reads, if present, has its JSON type (from `ref_types` for a field
    written as a `$ref`).

    So the member's `if` fails, and the check is skipped, only where a `type` keyword of the class already fails.
    """
    condition, then = _declare_required(condition), _declare_required(then)
    properties = node.get("properties", {})
    guard: dict[str, Any] = {"type": "object", "properties": {}}
    for prop in sorted(_fields_read(condition) | _fields_read(then)):
        sub = properties.get(prop, {})
        if "type" in sub:
            json_type = sub["type"]
        elif "$ref" in sub:
            json_type = ref_types.get(prop)
        else:
            json_type = None
        if json_type not in JSON_TYPES:
            raise ValueError(
                f"{name}.{prop}: a class-level check reads it, but it has no JSON type to guard on"
            )
        guard["properties"][prop] = {"type": json_type}
    for keyword, value in condition.items():
        if keyword == "properties":
            for prop, sub in value.items():
                typed = guard["properties"][prop]
                if any(typed.get(k, v) != v for k, v in sub.items()):
                    raise ValueError(
                        f"{name}.{prop}: a class-level check contradicts its type"
                    )
                guard["properties"][prop] = {**typed, **sub}
        elif keyword in guard:
            raise ValueError(
                f"{name}: a class-level check's condition has its own {keyword!r}"
            )
        else:
            guard[keyword] = value
    return {"if": guard, "then": then}


def _declare_required(node: Any) -> Any:
    """A copy of `node`, part of a check, with each `required` field in a `properties` beside it, at every level.

    Ajv's `strictRequired` (on under `strict: true`) wants each field a `required` names defined in the same subschema
    or a parent, and LinkML writes a field that must be absent with its `properties` beside the `not`, not inside it.
    An empty `{}` there checks nothing, so a field that isn't required in the same subschema loses it. A multivalued
    field's `ANY_ARRAY` is read as `{}`.
    """
    if isinstance(node, list):
        return [_declare_required(sub) for sub in node]
    if not isinstance(node, dict):
        return node
    result = {
        keyword: _declare_required(value)
        if keyword in SUBSCHEMAS + SUBSCHEMA_LISTS
        else value
        for keyword, value in node.items()
    }
    required = result.get("required", [])
    properties = {}
    for prop, sub in result.pop("properties", {}).items():
        if sub == ANY_ARRAY:
            sub = {}
        if sub or prop in required:
            properties[prop] = sub
    properties.update({prop: {} for prop in required if prop not in properties})
    if properties:
        result["properties"] = properties
    return result


def _fields_read(node: Any) -> set[str]:
    """The fields of the object that `node`, part of a check, reads: those named in a `properties` or a `required`."""
    if not isinstance(node, dict):
        return set()
    found = set(node.get("properties", {})) | set(node.get("required", []))
    for keyword in SUBSCHEMAS:
        found |= _fields_read(node.get(keyword))
    for keyword in SUBSCHEMA_LISTS:
        for sub in node.get(keyword, []):
            found |= _fields_read(sub)
    return found


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


def series(version: str) -> str:
    """The series of `version`, which a schema's `$id` carries: `X.Y` for a release `X.Y.Z`, the whole version for a
    pre-release (`0.1.0rc1`), and `dev` for `dev`. Any other version raises `ValueError`."""
    if version == DEV or PRE_RELEASE.fullmatch(version):
        return version
    release = RELEASE.fullmatch(version)
    if release:
        return release[1]
    raise ValueError(
        f"version {version!r} has no series: it isn't X.Y.Z, X.Y.Z followed by aN, bN or rcN, or {DEV!r}"
    )


def generate(
    schema: str | Path,
    *,
    closed: bool = True,
    schema_id: str | None = None,
    root: str | None = None,
) -> dict:
    """The JSON Schema for the LinkML `schema`: closed unless `closed` is false; optional fields reject null.

    It is rooted at the class `root` if given, otherwise at the schema's tree root: a schema that imports another
    with a tree root of its own, as the resolved analysis imports the analysis document, names its root.

    Its `$id` is `schema_id` if given, with `{series}` replaced by the series of the LinkML schema's version, otherwise
    the LinkML schema's own id, as LinkML sets it.
    """
    generator = AstraJsonSchemaGenerator(
        str(schema), include_null=False, not_closed=not closed, top_class=root
    )
    result = json.loads(generator.serialize())
    if schema_id is not None:
        if SERIES in schema_id:
            schema_id = schema_id.replace(SERIES, series(str(generator.schema.version)))
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
        help="the `$id` of the JSON Schema, in which `{series}` stands for the series of the schema's version: X.Y "
        "for a release X.Y.Z, the whole version for a pre-release, `dev` for `dev` (default: the schema's id)",
    )
    parser.add_argument(
        "--root",
        metavar="CLASS",
        help="the class the JSON Schema is rooted at (default: the schema's tree root)",
    )
    args = parser.parse_args(argv)
    print(
        json.dumps(
            generate(
                args.schema,
                closed=not args.not_closed,
                schema_id=args.schema_id,
                root=args.root,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
