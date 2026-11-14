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
version = "0.1.0rc1"


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
     'description': 'The provenance record: what a runner writes for each result '
                    'it makes,\n'
                    'saying what the result is and the run of the recipe that made '
                    'it. Through\n'
                    'this schema a record maps onto W3C PROV-O.',
     'id': 'https://w3id.org/astra/provenance',
     'imports': ['linkml:types', 'types'],
     'license': 'https://creativecommons.org/licenses/by/4.0/',
     'name': 'provenance',
     'prefixes': {'astra': {'prefix_prefix': 'astra',
                            'prefix_reference': 'https://w3id.org/astra/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'},
                  'prov': {'prefix_prefix': 'prov',
                           'prefix_reference': 'http://www.w3.org/ns/prov#'},
                  'schema': {'prefix_prefix': 'schema',
                             'prefix_reference': 'http://schema.org/'}},
     'source_file': 'provenance.yaml'} )


class ProvenanceRecord(ConfiguredBaseModel):
    """
    The provenance of one result, which the runner that made it writes as JSON: what the result is and the run of the recipe that made it. Read as RDF, its top-level node stands for the result.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'prov:Entity',
         'from_schema': 'https://w3id.org/astra/provenance',
         'tree_root': True})

    spec_version: str = Field(default=..., description="""The version of the ASTRA specification the record follows, such as `0.1.0`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceRecord']} })
    address: str = Field(default=..., description="""The result's address, as the analysis it belongs to names it: the output's id after the ids of the driven declarations that lead to it, then, for a result built in a universe, `#` and that universe's own id, never an import's, such as `subanalysis.output1#u1`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceRecord']} })
    content_hash: str = Field(default=..., description="""The SHA-256 digest of the result's file, never of something standing in for it.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceRecord', 'RecordedInput']} })
    size: int = Field(default=..., description="""The size of the result's file in bytes, never of something standing in for it.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceRecord', 'RecordedInput']} })
    generated_by: Generation = Field(default=..., description="""The run of the recipe that made the result.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceRecord'], 'slot_uri': 'prov:wasGeneratedBy'} })


class Generation(ConfiguredBaseModel):
    """
    A run of an output's recipe: the commit it ran from, what it read, the environment it ran in and the runner that ran it.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'prov:Activity',
         'from_schema': 'https://w3id.org/astra/provenance'})

    commit: str = Field(default=..., description="""The full id of the git commit the recipe ran from: a commit of the repository the record is committed in, the submodule's own commit for a result that belongs to an analysis in a submodule (the driver's commit for what a driver's universes build). It pins every file of the code and every `astra.yaml` in that repository: an analysis in a submodule of it through the commit the submodule is pinned at, and an analysis from a commit through its declaration's `commit`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Generation']} })
    inputs: Optional[list[RecordedInput]] = Field(default=None, description="""What the recipe read: one item for each entry the output's `inputs` lists in the `astra.yaml` files at the record's `commit`, and no other item, matched by `entry`; the order of the items carries no meaning. A later change to the list makes the result `stale`, not `missing`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Generation'], 'slot_uri': 'prov:used'} })
    environment: Environment = Field(default=..., description="""The environment the recipe ran in.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Generation'], 'slot_uri': 'prov:used'} })
    runner: Runner = Field(default=..., description="""The runner that ran the recipe.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Generation'], 'slot_uri': 'prov:wasAssociatedWith'} })
    started: Optional[str] = Field(default=None, description="""When the recipe started, in UTC to the millisecond, such as `2026-10-26T14:00:00.000Z`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Generation'], 'slot_uri': 'prov:startedAtTime'} })
    finished: Optional[str] = Field(default=None, description="""When the recipe finished, in UTC to the millisecond, such as `2026-10-26T14:00:02.000Z`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Generation'], 'slot_uri': 'prov:endedAtTime'} })


class RecordedInput(ConfiguredBaseModel):
    """
    One of the output's inputs, as the recipe read it: the entry, and the content hash and size of what the recipe read through it.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'prov:Entity', 'from_schema': 'https://w3id.org/astra/provenance'})

    entry: str = Field(default=..., description="""The entry exactly as the output's `inputs` lists it in the `astra.yaml` files at the record's `commit`, such as `input1`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['RecordedInput']} })
    content_hash: str = Field(default=..., description="""The SHA-256 digest of the content the recipe read through the entry, another output's result or the file an input names, never of something standing in for it.""", json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceRecord', 'RecordedInput']} })
    size: int = Field(default=..., description="""The size in bytes of the content the recipe read through the entry, never of something standing in for it.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['ProvenanceRecord', 'RecordedInput']} })


class Environment(ConfiguredBaseModel):
    """
    The environment a recipe ran in, named by an IRI.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'prov:Entity', 'from_schema': 'https://w3id.org/astra/provenance'})

    iri: str = Field(default=..., description="""An IRI naming exactly that environment, enough for its runner, at the version the record gives, to recreate it, such as a `urn:` IRI (`urn:example:env:sha256:…`) or one in a scheme of the runner's own.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Environment']} })


class Runner(ConfiguredBaseModel):
    """
    The software that ran the recipe and wrote the record.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'prov:SoftwareAgent',
         'from_schema': 'https://w3id.org/astra/provenance'})

    id: str = Field(default=..., description="""The runner's name, such as `example-runner`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Runner']} })
    version: str = Field(default=..., description="""The runner's version, such as `1.2.0`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Runner'], 'slot_uri': 'schema:softwareVersion'} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
ProvenanceRecord.model_rebuild()
Generation.model_rebuild()
RecordedInput.model_rebuild()
Environment.model_rebuild()
Runner.model_rebuild()
