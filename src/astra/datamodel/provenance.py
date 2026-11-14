# Auto generated from provenance.yaml by pythongen.py version: 0.0.1
# Schema: provenance
#
# id: https://w3id.org/astra/provenance
# description: The provenance record: what a runner writes for each result it makes,
#   saying what the result is and the run of the recipe that made it. Through
#   this schema a record maps onto W3C PROV-O.
# license: https://creativecommons.org/licenses/by/4.0/

import dataclasses
import re
from dataclasses import dataclass
from datetime import (
    date,
    datetime,
    time
)
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Union
)

from jsonasobj2 import (
    JsonObj,
    as_dict
)
from linkml_runtime.linkml_model.meta import (
    EnumDefinition,
    PermissibleValue,
    PvFormulaOptions
)
from linkml_runtime.utils.curienamespace import CurieNamespace
from linkml_runtime.utils.enumerations import EnumDefinitionImpl
from linkml_runtime.utils.formatutils import (
    camelcase,
    sfx,
    underscore
)
from linkml_runtime.utils.metamodelcore import (
    bnode,
    empty_dict,
    empty_list
)
from linkml_runtime.utils.slot import Slot
from linkml_runtime.utils.yamlutils import (
    YAMLRoot,
    extended_float,
    extended_int,
    extended_str
)
from rdflib import (
    Namespace,
    URIRef
)

from linkml_runtime.linkml_model.types import Integer, String

metamodel_version = "1.12.0"
version = "0.1.0rc1"

# Namespaces
ASTRA = CurieNamespace('astra', 'https://w3id.org/astra/')
LINKML = CurieNamespace('linkml', 'https://w3id.org/linkml/')
PROV = CurieNamespace('prov', 'http://www.w3.org/ns/prov#')
SCHEMA = CurieNamespace('schema', 'http://schema.org/')
XSD = CurieNamespace('xsd', 'http://www.w3.org/2001/XMLSchema#')
DEFAULT_ = ASTRA


# Types
class Id(String):
    """ An id: a lowercase ASCII letter, then any number of lowercase ASCII letters, ASCII digits (`0`–`9`) and underscores, such as `input1`. """
    type_class_uri = XSD["string"]
    type_class_curie = "xsd:string"
    type_name = "id"
    type_model_uri = ASTRA.Id


class Address(String):
    """ The address of an element: the ids of the declared analyses that lead to it, if any, then the element's own id, joined by `.`, such as `subanalysis.decision1`. """
    type_class_uri = XSD["string"]
    type_class_curie = "xsd:string"
    type_name = "address"
    type_model_uri = ASTRA.Address


class Reference(String):
    """ A reference to an element: its address, optionally followed by `#` and a universe id, which pins the reference to that universe, such as `output1#u1`. In an `astra.yaml`, the id is that of an entry of the file's `universes` or, where the file has no entry with that id, of a universe of the analysis whose element the reference names. """
    type_class_uri = XSD["string"]
    type_class_curie = "xsd:string"
    type_name = "reference"
    type_model_uri = ASTRA.Reference


class OptionReference(String):
    """ A reference to an option: the address of its decision, then `.` and the option's id. The last segment is always the option, so `subanalysis.decision1.a` is the option `a` of the decision `decision1` of the declared analysis `subanalysis`. """
    type_class_uri = XSD["string"]
    type_class_curie = "xsd:string"
    type_name = "option_reference"
    type_model_uri = ASTRA.OptionReference


class CommitId(String):
    """ A full git commit id: 40 lowercase hexadecimal digits (SHA-1) or 64 (SHA-256). """
    type_class_uri = XSD["string"]
    type_class_curie = "xsd:string"
    type_name = "commit_id"
    type_model_uri = ASTRA.CommitId


class ContentHash(String):
    """ A SHA-256 digest of content: `sha256:` followed by 64 lowercase hexadecimal digits. """
    type_class_uri = XSD["string"]
    type_class_curie = "xsd:string"
    type_name = "content_hash"
    type_model_uri = ASTRA.ContentHash


class SpecVersion(String):
    """ A version of the ASTRA specification, `MAJOR.MINOR.PATCH`: three non-negative integers without leading zeros, joined by `.`, such as `0.1.0`. """
    type_class_uri = XSD["string"]
    type_class_curie = "xsd:string"
    type_name = "spec_version"
    type_model_uri = ASTRA.SpecVersion


class Timestamp(String):
    """ A date and time in UTC to the millisecond, written `YYYY-MM-DDThh:mm:ss.sssZ`, with month 01–12, day 01–31, hour 00–23, and minute and second 00–59, such as `2026-10-26T14:00:00.000Z`. """
    type_class_uri = XSD["dateTime"]
    type_class_curie = "xsd:dateTime"
    type_name = "timestamp"
    type_model_uri = ASTRA.Timestamp


class Iri(String):
    """ An IRI, never a CURIE: a scheme (an ASCII letter, then any ASCII letters, digits, `+`, `.` and `-`), `:`, at least one character other than `#`, then optionally `#` and any characters other than `#`, such as `http://tools.ietf.org/rfc/rfc7111`. None of these characters is an ASCII space or control, a C1 control, `<`, `>`, `"`, `{`, `}`, the vertical bar, the backslash, `^`, the backtick or a bidi formatting character U+200E, U+200F or U+202A–U+202E, and `%` comes only before two hex digits. """
    type_class_uri = XSD["string"]
    type_class_curie = "xsd:string"
    type_name = "iri"
    type_model_uri = ASTRA.Iri


# Class references
class EnvironmentIri(Iri):
    pass


@dataclass(repr=False)
class ProvenanceRecord(YAMLRoot):
    """
    The provenance of one result, which the runner that made it writes as JSON: what the result is and the run of the
    recipe that made it. Read as RDF, its top-level node stands for the result.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = PROV["Entity"]
    class_class_curie: ClassVar[str] = "prov:Entity"
    class_name: ClassVar[str] = "ProvenanceRecord"
    class_model_uri: ClassVar[URIRef] = ASTRA.ProvenanceRecord

    spec_version: Union[str, SpecVersion] = None
    address: Union[str, Reference] = None
    content_hash: Union[str, ContentHash] = None
    size: int = None
    generated_by: Union[dict, "Generation"] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.spec_version):
            self.MissingRequiredField("spec_version")
        if not isinstance(self.spec_version, SpecVersion):
            self.spec_version = SpecVersion(self.spec_version)

        if self._is_empty(self.address):
            self.MissingRequiredField("address")
        if not isinstance(self.address, Reference):
            self.address = Reference(self.address)

        if self._is_empty(self.content_hash):
            self.MissingRequiredField("content_hash")
        if not isinstance(self.content_hash, ContentHash):
            self.content_hash = ContentHash(self.content_hash)

        if self._is_empty(self.size):
            self.MissingRequiredField("size")
        if not isinstance(self.size, int):
            self.size = int(self.size)

        if self._is_empty(self.generated_by):
            self.MissingRequiredField("generated_by")
        if not isinstance(self.generated_by, Generation):
            self.generated_by = Generation(**as_dict(self.generated_by))

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Generation(YAMLRoot):
    """
    A run of an output's recipe: the commit it ran from, what it read, the environment it ran in and the runner that
    ran it.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = PROV["Activity"]
    class_class_curie: ClassVar[str] = "prov:Activity"
    class_name: ClassVar[str] = "Generation"
    class_model_uri: ClassVar[URIRef] = ASTRA.Generation

    commit: Union[str, CommitId] = None
    environment: Union[dict, "Environment"] = None
    runner: Union[dict, "Runner"] = None
    inputs: Optional[Union[Union[dict, "RecordedInput"], list[Union[dict, "RecordedInput"]]]] = empty_list()
    started: Optional[Union[str, Timestamp]] = None
    finished: Optional[Union[str, Timestamp]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.commit):
            self.MissingRequiredField("commit")
        if not isinstance(self.commit, CommitId):
            self.commit = CommitId(self.commit)

        if self._is_empty(self.environment):
            self.MissingRequiredField("environment")
        if not isinstance(self.environment, Environment):
            self.environment = Environment(**as_dict(self.environment))

        if self._is_empty(self.runner):
            self.MissingRequiredField("runner")
        if not isinstance(self.runner, Runner):
            self.runner = Runner(**as_dict(self.runner))

        self._normalize_inlined_as_list(slot_name="inputs", slot_type=RecordedInput, key_name="entry", keyed=False)

        if self.started is not None and not isinstance(self.started, Timestamp):
            self.started = Timestamp(self.started)

        if self.finished is not None and not isinstance(self.finished, Timestamp):
            self.finished = Timestamp(self.finished)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class RecordedInput(YAMLRoot):
    """
    One of the output's inputs, as the recipe read it: the entry, and the content hash and size of what the recipe
    read through it.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = PROV["Entity"]
    class_class_curie: ClassVar[str] = "prov:Entity"
    class_name: ClassVar[str] = "RecordedInput"
    class_model_uri: ClassVar[URIRef] = ASTRA.RecordedInput

    entry: Union[str, Reference] = None
    content_hash: Union[str, ContentHash] = None
    size: int = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.entry):
            self.MissingRequiredField("entry")
        if not isinstance(self.entry, Reference):
            self.entry = Reference(self.entry)

        if self._is_empty(self.content_hash):
            self.MissingRequiredField("content_hash")
        if not isinstance(self.content_hash, ContentHash):
            self.content_hash = ContentHash(self.content_hash)

        if self._is_empty(self.size):
            self.MissingRequiredField("size")
        if not isinstance(self.size, int):
            self.size = int(self.size)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Environment(YAMLRoot):
    """
    The environment a recipe ran in, named by an IRI.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = PROV["Entity"]
    class_class_curie: ClassVar[str] = "prov:Entity"
    class_name: ClassVar[str] = "Environment"
    class_model_uri: ClassVar[URIRef] = ASTRA.Environment

    iri: Union[str, EnvironmentIri] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.iri):
            self.MissingRequiredField("iri")
        if not isinstance(self.iri, EnvironmentIri):
            self.iri = EnvironmentIri(self.iri)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Runner(YAMLRoot):
    """
    The software that ran the recipe and wrote the record.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = PROV["SoftwareAgent"]
    class_class_curie: ClassVar[str] = "prov:SoftwareAgent"
    class_name: ClassVar[str] = "Runner"
    class_model_uri: ClassVar[URIRef] = ASTRA.Runner

    id: str = None
    version: str = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, str):
            self.id = str(self.id)

        if self._is_empty(self.version):
            self.MissingRequiredField("version")
        if not isinstance(self.version, str):
            self.version = str(self.version)

        super().__post_init__(**kwargs)


# Enumerations


# Slots
class slots:
    pass

slots.provenanceRecord__spec_version = Slot(uri=ASTRA.spec_version, name="provenanceRecord__spec_version", curie=ASTRA.curie('spec_version'),
                   model_uri=ASTRA.provenanceRecord__spec_version, domain=None, range=Union[str, SpecVersion])

slots.provenanceRecord__address = Slot(uri=ASTRA.address, name="provenanceRecord__address", curie=ASTRA.curie('address'),
                   model_uri=ASTRA.provenanceRecord__address, domain=None, range=Union[str, Reference])

slots.provenanceRecord__content_hash = Slot(uri=ASTRA.content_hash, name="provenanceRecord__content_hash", curie=ASTRA.curie('content_hash'),
                   model_uri=ASTRA.provenanceRecord__content_hash, domain=None, range=Union[str, ContentHash])

slots.provenanceRecord__size = Slot(uri=ASTRA.size, name="provenanceRecord__size", curie=ASTRA.curie('size'),
                   model_uri=ASTRA.provenanceRecord__size, domain=None, range=int)

slots.provenanceRecord__generated_by = Slot(uri=PROV.wasGeneratedBy, name="provenanceRecord__generated_by", curie=PROV.curie('wasGeneratedBy'),
                   model_uri=ASTRA.provenanceRecord__generated_by, domain=None, range=Union[dict, Generation])

slots.generation__commit = Slot(uri=ASTRA.commit, name="generation__commit", curie=ASTRA.curie('commit'),
                   model_uri=ASTRA.generation__commit, domain=None, range=Union[str, CommitId])

slots.generation__inputs = Slot(uri=PROV.used, name="generation__inputs", curie=PROV.curie('used'),
                   model_uri=ASTRA.generation__inputs, domain=None, range=Optional[Union[Union[dict, RecordedInput], list[Union[dict, RecordedInput]]]])

slots.generation__environment = Slot(uri=PROV.used, name="generation__environment", curie=PROV.curie('used'),
                   model_uri=ASTRA.generation__environment, domain=None, range=Union[dict, Environment])

slots.generation__runner = Slot(uri=PROV.wasAssociatedWith, name="generation__runner", curie=PROV.curie('wasAssociatedWith'),
                   model_uri=ASTRA.generation__runner, domain=None, range=Union[dict, Runner])

slots.generation__started = Slot(uri=PROV.startedAtTime, name="generation__started", curie=PROV.curie('startedAtTime'),
                   model_uri=ASTRA.generation__started, domain=None, range=Optional[Union[str, Timestamp]])

slots.generation__finished = Slot(uri=PROV.endedAtTime, name="generation__finished", curie=PROV.curie('endedAtTime'),
                   model_uri=ASTRA.generation__finished, domain=None, range=Optional[Union[str, Timestamp]])

slots.recordedInput__entry = Slot(uri=ASTRA.entry, name="recordedInput__entry", curie=ASTRA.curie('entry'),
                   model_uri=ASTRA.recordedInput__entry, domain=None, range=Union[str, Reference])

slots.recordedInput__content_hash = Slot(uri=ASTRA.content_hash, name="recordedInput__content_hash", curie=ASTRA.curie('content_hash'),
                   model_uri=ASTRA.recordedInput__content_hash, domain=None, range=Union[str, ContentHash])

slots.recordedInput__size = Slot(uri=ASTRA.size, name="recordedInput__size", curie=ASTRA.curie('size'),
                   model_uri=ASTRA.recordedInput__size, domain=None, range=int)

slots.environment__iri = Slot(uri=ASTRA.iri, name="environment__iri", curie=ASTRA.curie('iri'),
                   model_uri=ASTRA.environment__iri, domain=None, range=URIRef)

slots.runner__id = Slot(uri=ASTRA.id, name="runner__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.runner__id, domain=None, range=str)

slots.runner__version = Slot(uri=SCHEMA.softwareVersion, name="runner__version", curie=SCHEMA.curie('softwareVersion'),
                   model_uri=ASTRA.runner__version, domain=None, range=str)
