from __future__ import annotations

import re
import sys
from datetime import (
    date,
    datetime,
    time
)
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Literal,
    Optional,
    Union
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    field_validator,
    model_serializer
)


metamodel_version = "1.12.0"
version = "dev"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        serialize_by_alias = True,
        validate_by_name = True,
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True,
        strict = False,
    )

    @field_validator("*", mode="before")
    @classmethod
    def entries_take_their_keys(cls, value, info):
        """Each entry of a map keyed by `id`, which an `astra.yaml` writes without its `id` (the entry's key), with its
        key as its `id`."""
        annotation = cls.model_fields[info.field_name].annotation
        for candidate in (annotation, *getattr(annotation, "__args__", ())):
            if getattr(candidate, "__origin__", None) is not dict:
                continue
            entry_class = candidate.__args__[1]
            if not (isinstance(entry_class, type) and issubclass(entry_class, BaseModel)):
                continue
            if "id" in entry_class.model_fields and isinstance(value, dict):
                return {
                    key: {"id": key, **entry} if isinstance(entry, dict) else entry
                    for key, entry in value.items()
                }
        return value





class LinkMLMeta(RootModel):
    root: dict[str, Any] = {}
    model_config = ConfigDict(frozen=True)

    def __getattr__(self, key:str):
        return getattr(self.root, key)

    def __getitem__(self, key:str):
        return self.root[key]

    def __setitem__(self, key:str, value):
        self.root[key] = value

    def __contains__(self, key:str) -> bool:
        return key in self.root


linkml_meta = LinkMLMeta({'default_prefix': 'astra',
     'default_range': 'string',
     'description': 'The validation report: what a validator found in an analysis '
                    'and every\n'
                    'analysis it declares, directly or not.',
     'id': 'https://w3id.org/astra/validation',
     'imports': ['linkml:types', 'results'],
     'license': 'https://creativecommons.org/licenses/by/4.0/',
     'name': 'validation',
     'prefixes': {'astra': {'prefix_prefix': 'astra',
                            'prefix_reference': 'https://w3id.org/astra/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'}},
     'source_file': 'tmp/schema/validation.yaml'} )

class ElementKind(str, Enum):
    """
    The kind of element an address resolves to.
    """
    input = "input"
    """
    An input.
    """
    output = "output"
    """
    An output.
    """
    decision = "decision"
    """
    A decision.
    """
    universe = "universe"
    """
    A universe.
    """


class Level(str, Enum):
    """
    How a broken rule counts.
    """
    error = "error"
    """
    A broken `MUST`.
    """
    warning = "warning"
    """
    A broken `SHOULD`.
    """



class Identity(ConfiguredBaseModel):
    """
    What an analysis is known by: its folder and the commit it is read at. One folder at one commit is one analysis however it is declared.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/results'})

    folder: str = Field(default=..., description="""The analysis's folder, as a path from the top of the repository it is read in or, read in the working tree, from the top of the driving analysis's working tree. The top itself is the empty string.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Identity']} })
    commit: Optional[str] = Field(default=None, description="""The full id of the commit the analysis is read at. Left out for an analysis read in the working tree.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Identity', 'Read', 'Location']} })


class Element(ConfiguredBaseModel):
    """
    An element of an analysis: what an address resolves to. Two addresses that resolve to one element are two spellings of it.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/results'})

    analysis: Identity = Field(default=..., description="""The analysis the element is in.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Element']} })
    kind: ElementKind = Field(default=..., description="""The kind of element.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Element']} })
    id: str = Field(default=..., description="""The element's id in its analysis.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Element']} })


class Place(ConfiguredBaseModel):
    """
    Where one name of a planned result puts it, in the folder of the analysis the result belongs to.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/results'})

    name: str = Field(default=..., description="""The result's name: its output's id after the ids of the driven declarations that lead to it from the analysis it belongs to, such as `subanalysis.output1`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Place']} })
    address: str = Field(default=..., description="""The name, then, for a result built in a universe, `#` and that universe's own id, such as `subanalysis.output1#u1`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Place']} })
    record: str = Field(default=..., description="""The place of the result's record, as a path from the top of the tree its analysis is read in.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Place']} })
    bytes: str = Field(default=..., description="""The default place of the result's bytes, as a path from the top of the tree its analysis is read in.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Place']} })


class Read(ConfiguredBaseModel):
    """
    One entry of an output's `inputs`, and what a planned result reads through it: an input's file, or another planned result's bytes. An entry that names a switch reads what the case the switch takes names.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/results'})

    entry: str = Field(default=..., description="""The entry exactly as the output's `inputs` lists it.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Read', 'Selected']} })
    path: str = Field(default=..., description="""The input's file, or the default place of the bytes of the result read, as a path from the top of the tree it is read in.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Read']} })
    commit: Optional[str] = Field(default=None, description="""The full id of the commit `path` is read at. Left out for the working tree.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Identity', 'Read', 'Location']} })
    result: Optional[int] = Field(default=None, description="""The planned result read, as its index in the `results` that hold this one. Left out for an input.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Read']} })


class Selected(ConfiguredBaseModel):
    """
    One entry of an output's `decisions`, and the option a planned result is made with for it.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/results'})

    entry: str = Field(default=..., description="""The entry exactly as the output's `decisions` lists it.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Read', 'Selected']} })
    option: Optional[str] = Field(default=None, description="""The id of the option selected where the result is built. Left out where none is.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Selected']} })


class Result(ConfiguredBaseModel):
    """
    A planned result: one output's, in the universe it is built in or, for an output built once, once.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/results'})

    names: list[str] = Field(default=..., description="""The result's names, one for each driven chain that reaches it.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Result']} })
    owner: Identity = Field(default=..., description="""The analysis the result belongs to: the one whose universe builds it or, for an output built once, the one whose output it is.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Result']} })
    output: Element = Field(default=..., description="""The output the result is of.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Result']} })
    universe: Optional[str] = Field(default=None, description="""The id of the universe the result is built in, one of its owner's. Left out for an output built once.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Result']} })
    places: list[Place] = Field(default=..., description="""The result's places, one for each of its names, in their order.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Result']} })
    inputs: list[Read] = Field(default=..., description="""What the result reads: one item for each entry of its output's `inputs`, in their order.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Result']} })
    decisions: list[Selected] = Field(default=..., description="""What the result is made with: one item for each entry of its output's `decisions`, in their order.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Result']} })


class Location(ConfiguredBaseModel):
    """
    Where a diagnostic is: a file, and a place in it.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/results'})

    file: str = Field(default=..., description="""The file's path from the top of the repository that holds it.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Location']} })
    pointer: str = Field(default=..., description="""A JSON Pointer to the place in the file. The whole file is the empty string.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Location']} })
    line: Optional[int] = Field(default=None, description="""The line of the place in the file, counted from 1.""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Location']} })
    column: Optional[int] = Field(default=None, description="""The column of the place in its line, counted from 1.""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Location']} })
    key: Optional[str] = Field(default=None, description="""The map key or field the diagnostic names at the place.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Location']} })
    commit: Optional[str] = Field(default=None, description="""The full id of the commit the file is read at. Left out for the working tree.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Identity', 'Read', 'Location']} })
    url: Optional[str] = Field(default=None, description="""The URL of the remote the file is read from, if any.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Location']} })


class Diagnostic(ConfiguredBaseModel):
    """
    A rule broken: its code, how it counts, and where.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/results'})

    code: str = Field(default=..., description="""The rule's code, one of the specification's codes table or one of the tool's own, such as `UNRESOLVED_ADDRESS`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Diagnostic']} })
    level: Level = Field(default=..., description="""How the broken rule counts.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Diagnostic']} })
    message: str = Field(default=..., description="""What is wrong and what to do about it, in a sentence.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Diagnostic']} })
    location: Location = Field(default=..., description="""Where the rule is broken.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Diagnostic']} })
    related: Optional[list[Location]] = Field(default=None, description="""Other places the diagnostic is about.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Diagnostic']} })


class ValidationReport(ConfiguredBaseModel):
    """
    What validating an analysis found.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/validation', 'tree_root': True})

    shape: Literal["astra-validation-report/1"] = Field(default=..., description="""The name and version of this shape.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ValidationReport'],
         'equals_string': 'astra-validation-report/1'} })
    root: str = Field(default=..., description="""The driving analysis's `astra.yaml`, as a path from the top of the repository that holds it.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ValidationReport']} })
    valid: bool = Field(default=..., description="""Whether the analysis is valid: no diagnostic is an error.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ValidationReport']} })
    diagnostics: list[Diagnostic] = Field(default=..., description="""The rules broken, in the order of their places.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ValidationReport']} })
    unchecked: list[str] = Field(default=..., description="""The codes of the validator rules the tool didn't check, so that a report with no diagnostic for them says nothing of them.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ValidationReport']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
Identity.model_rebuild()
Element.model_rebuild()
Place.model_rebuild()
Read.model_rebuild()
Selected.model_rebuild()
Result.model_rebuild()
Location.model_rebuild()
Diagnostic.model_rebuild()
ValidationReport.model_rebuild()
