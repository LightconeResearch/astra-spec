# Auto generated from analysis.yaml by pythongen.py version: 0.0.1
# Schema: analysis
#
# id: https://w3id.org/astra/analysis
# description: Agentic Schema for Transparent Research Analysis.
#   The analysis document, `astra.yaml`: the files an analysis reads, the
#   artefacts it makes, and the decisions it makes along the way.
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

from linkml_runtime.linkml_model.types import Float, Integer, String

metamodel_version = "1.12.0"
version = "dev"

# Namespaces
ASTRA = CurieNamespace('astra', 'https://w3id.org/astra/')
DCTERMS = CurieNamespace('dcterms', 'http://purl.org/dc/terms/')
LINKML = CurieNamespace('linkml', 'https://w3id.org/linkml/')
OA = CurieNamespace('oa', 'http://www.w3.org/ns/oa#')
RDF = CurieNamespace('rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#')
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
class InputId(Id):
    pass


class OutputId(Id):
    pass


class SwitchCaseCase(Id):
    pass


class DecisionId(Id):
    pass


class OptionId(Id):
    pass


class UniverseId(Id):
    pass


class DecisionSelectionDecision(Address):
    pass


class AnalysisDeclarationId(Id):
    pass


class InsightId(Id):
    pass


@dataclass(repr=False)
class Resources(YAMLRoot):
    """
    The compute resources a recipe asks for.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Resources"]
    class_class_curie: ClassVar[str] = "astra:Resources"
    class_name: ClassVar[str] = "Resources"
    class_model_uri: ClassVar[URIRef] = ASTRA.Resources

    cpus: Optional[float] = None
    memory: Optional[str] = None
    time_limit: Optional[str] = None
    disk: Optional[str] = None
    gpus: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.cpus is not None and not isinstance(self.cpus, float):
            self.cpus = float(self.cpus)

        if self.memory is not None and not isinstance(self.memory, str):
            self.memory = str(self.memory)

        if self.time_limit is not None and not isinstance(self.time_limit, str):
            self.time_limit = str(self.time_limit)

        if self.disk is not None and not isinstance(self.disk, str):
            self.disk = str(self.disk)

        if self.gpus is not None and not isinstance(self.gpus, int):
            self.gpus = int(self.gpus)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Recipe(YAMLRoot):
    """
    How an output is made: a `command` and the compute `resources` it asks for. What the output is made from and the
    decisions it is made with are the output's `inputs` and `decisions`; the command reaches the inputs and decisions
    through its placeholders.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Recipe"]
    class_class_curie: ClassVar[str] = "astra:Recipe"
    class_name: ClassVar[str] = "Recipe"
    class_model_uri: ClassVar[URIRef] = ASTRA.Recipe

    command: str = None
    resources: Optional[Union[dict, Resources]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.command):
            self.MissingRequiredField("command")
        if not isinstance(self.command, str):
            self.command = str(self.command)

        if self.resources is not None and not isinstance(self.resources, Resources):
            self.resources = Resources(**as_dict(self.resources))

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Input(YAMLRoot):
    """
    A file the analysis reads, tracked in git with it and named by its path.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Input"]
    class_class_curie: ClassVar[str] = "astra:Input"
    class_name: ClassVar[str] = "Input"
    class_model_uri: ClassVar[URIRef] = ASTRA.Input

    id: Union[str, InputId] = None
    path: str = None
    label: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, InputId):
            self.id = InputId(self.id)

        if self._is_empty(self.path):
            self.MissingRequiredField("path")
        if not isinstance(self.path, str):
            self.path = str(self.path)

        if self.label is not None and not isinstance(self.label, str):
            self.label = str(self.label)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if not isinstance(self.tags, list):
            self.tags = [self.tags] if self.tags is not None else []
        self.tags = [v if isinstance(v, str) else str(v) for v in self.tags]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Output(YAMLRoot):
    """
    An entry of `outputs`: an artefact the analysis makes, such as a metric, a figure or a table, with what it is,
    what it is made from and how; or a switch, which has a `switch` and `cases`, makes nothing, and is read as the
    case it takes.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Output"]
    class_class_curie: ClassVar[str] = "astra:Output"
    class_name: ClassVar[str] = "Output"
    class_model_uri: ClassVar[URIRef] = ASTRA.Output

    id: Union[str, OutputId] = None
    label: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[Union[str, list[str]]] = empty_list()
    type: Optional[Union[str, "OutputType"]] = None
    format: Optional[str] = None
    inputs: Optional[Union[Union[str, Reference], list[Union[str, Reference]]]] = empty_list()
    decisions: Optional[Union[Union[str, Address], list[Union[str, Address]]]] = empty_list()
    recipe: Optional[Union[dict, Recipe]] = None
    switch: Optional[Union[str, Address]] = None
    cases: Optional[Union[dict[Union[str, SwitchCaseCase], Union[dict, "SwitchCase"]], list[Union[dict, "SwitchCase"]]]] = empty_dict()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, OutputId):
            self.id = OutputId(self.id)

        if self.label is not None and not isinstance(self.label, str):
            self.label = str(self.label)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if not isinstance(self.tags, list):
            self.tags = [self.tags] if self.tags is not None else []
        self.tags = [v if isinstance(v, str) else str(v) for v in self.tags]

        if self.type is not None and not isinstance(self.type, OutputType):
            self.type = OutputType(self.type)

        if self.format is not None and not isinstance(self.format, str):
            self.format = str(self.format)

        if not isinstance(self.inputs, list):
            self.inputs = [self.inputs] if self.inputs is not None else []
        self.inputs = [v if isinstance(v, Reference) else Reference(v) for v in self.inputs]

        if not isinstance(self.decisions, list):
            self.decisions = [self.decisions] if self.decisions is not None else []
        self.decisions = [v if isinstance(v, Address) else Address(v) for v in self.decisions]

        if self.recipe is not None and not isinstance(self.recipe, Recipe):
            self.recipe = Recipe(**as_dict(self.recipe))

        if self.switch is not None and not isinstance(self.switch, Address):
            self.switch = Address(self.switch)

        self._normalize_inlined_as_dict(slot_name="cases", slot_type=SwitchCase, key_name="case", keyed=True)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class SwitchCase(YAMLRoot):
    """
    What a switch is read as where its decision selects one option, written in the switch's `cases` as `<option>:
    <reference>`, such as `b: stage.output3`.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["SwitchCase"]
    class_class_curie: ClassVar[str] = "astra:SwitchCase"
    class_name: ClassVar[str] = "SwitchCase"
    class_model_uri: ClassVar[URIRef] = ASTRA.SwitchCase

    case: Union[str, SwitchCaseCase] = None
    target: Union[str, Reference] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.case):
            self.MissingRequiredField("case")
        if not isinstance(self.case, SwitchCaseCase):
            self.case = SwitchCaseCase(self.case)

        if self._is_empty(self.target):
            self.MissingRequiredField("target")
        if not isinstance(self.target, Reference):
            self.target = Reference(self.target)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Decision(YAMLRoot):
    """
    A choice the analysis makes between options, such as which method to use.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Decision"]
    class_class_curie: ClassVar[str] = "astra:Decision"
    class_name: ClassVar[str] = "Decision"
    class_model_uri: ClassVar[URIRef] = ASTRA.Decision

    id: Union[str, DecisionId] = None
    options: Union[dict[Union[str, OptionId], Union[dict, "Option"]], list[Union[dict, "Option"]]] = empty_dict()
    label: Optional[str] = None
    rationale: Optional[str] = None
    tags: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DecisionId):
            self.id = DecisionId(self.id)

        if self._is_empty(self.options):
            self.MissingRequiredField("options")
        self._normalize_inlined_as_dict(slot_name="options", slot_type=Option, key_name="id", keyed=True)

        if self.label is not None and not isinstance(self.label, str):
            self.label = str(self.label)

        if self.rationale is not None and not isinstance(self.rationale, str):
            self.rationale = str(self.rationale)

        if not isinstance(self.tags, list):
            self.tags = [self.tags] if self.tags is not None else []
        self.tags = [v if isinstance(v, str) else str(v) for v in self.tags]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Option(YAMLRoot):
    """
    One of the options a decision chooses between.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Option"]
    class_class_curie: ClassVar[str] = "astra:Option"
    class_name: ClassVar[str] = "Option"
    class_model_uri: ClassVar[URIRef] = ASTRA.Option

    id: Union[str, OptionId] = None
    label: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[Union[str, list[str]]] = empty_list()
    insights: Optional[Union[Union[str, Id], list[Union[str, Id]]]] = empty_list()
    requires: Optional[Union[Union[str, OptionReference], list[Union[str, OptionReference]]]] = empty_list()
    incompatible_with: Optional[Union[Union[str, OptionReference], list[Union[str, OptionReference]]]] = empty_list()
    excluded: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, OptionId):
            self.id = OptionId(self.id)

        if self.label is not None and not isinstance(self.label, str):
            self.label = str(self.label)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if not isinstance(self.tags, list):
            self.tags = [self.tags] if self.tags is not None else []
        self.tags = [v if isinstance(v, str) else str(v) for v in self.tags]

        if not isinstance(self.insights, list):
            self.insights = [self.insights] if self.insights is not None else []
        self.insights = [v if isinstance(v, Id) else Id(v) for v in self.insights]

        if not isinstance(self.requires, list):
            self.requires = [self.requires] if self.requires is not None else []
        self.requires = [v if isinstance(v, OptionReference) else OptionReference(v) for v in self.requires]

        if not isinstance(self.incompatible_with, list):
            self.incompatible_with = [self.incompatible_with] if self.incompatible_with is not None else []
        self.incompatible_with = [v if isinstance(v, OptionReference) else OptionReference(v) for v in self.incompatible_with]

        if self.excluded is not None and not isinstance(self.excluded, str):
            self.excluded = str(self.excluded)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Universe(YAMLRoot):
    """
    An entry of `universes`: a universe of the analysis, a selection of one option for every decision it uses of the
    analysis and of every analysis, declared directly or not, that the analysis's universes drive, or an import, which
    has an `analysis` and a `universe`, names one of another analysis's universes and selects nothing. A universe's
    effective selection is the effective selection of the universe it is derived from, if any, with its own
    `decisions` written over it decision by decision.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Universe"]
    class_class_curie: ClassVar[str] = "astra:Universe"
    class_name: ClassVar[str] = "Universe"
    class_model_uri: ClassVar[URIRef] = ASTRA.Universe

    id: Union[str, UniverseId] = None
    label: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[Union[str, list[str]]] = empty_list()
    derived_from: Optional[Union[str, Id]] = None
    decisions: Optional[Union[dict[Union[str, DecisionSelectionDecision], Union[dict, "DecisionSelection"]], list[Union[dict, "DecisionSelection"]]]] = empty_dict()
    analysis: Optional[Union[str, Address]] = None
    universe: Optional[Union[str, Id]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, UniverseId):
            self.id = UniverseId(self.id)

        if self.label is not None and not isinstance(self.label, str):
            self.label = str(self.label)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if not isinstance(self.tags, list):
            self.tags = [self.tags] if self.tags is not None else []
        self.tags = [v if isinstance(v, str) else str(v) for v in self.tags]

        if self.derived_from is not None and not isinstance(self.derived_from, Id):
            self.derived_from = Id(self.derived_from)

        self._normalize_inlined_as_dict(slot_name="decisions", slot_type=DecisionSelection, key_name="decision", keyed=True)

        if self.analysis is not None and not isinstance(self.analysis, Address):
            self.analysis = Address(self.analysis)

        if self.universe is not None and not isinstance(self.universe, Id):
            self.universe = Id(self.universe)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DecisionSelection(YAMLRoot):
    """
    The option a universe selects for one decision, written in the universe's `decisions` as `<decision>: <option>`,
    such as `decision1: a`.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["DecisionSelection"]
    class_class_curie: ClassVar[str] = "astra:DecisionSelection"
    class_name: ClassVar[str] = "DecisionSelection"
    class_model_uri: ClassVar[URIRef] = ASTRA.DecisionSelection

    decision: Union[str, DecisionSelectionDecision] = None
    option: Union[str, Id] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.decision):
            self.MissingRequiredField("decision")
        if not isinstance(self.decision, DecisionSelectionDecision):
            self.decision = DecisionSelectionDecision(self.decision)

        if self._is_empty(self.option):
            self.MissingRequiredField("option")
        if not isinstance(self.option, Id):
            self.option = Id(self.option)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class AnalysisDeclaration(YAMLRoot):
    """
    An analysis that this analysis uses, found by exactly one of `path` and `url`. Its elements are addressed through
    the declaration's id, as `<declaration>.<element>`.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["AnalysisDeclaration"]
    class_class_curie: ClassVar[str] = "astra:AnalysisDeclaration"
    class_name: ClassVar[str] = "AnalysisDeclaration"
    class_model_uri: ClassVar[URIRef] = ASTRA.AnalysisDeclaration

    id: Union[str, AnalysisDeclarationId] = None
    path: Optional[str] = None
    url: Optional[str] = None
    commit: Optional[Union[str, CommitId]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, AnalysisDeclarationId):
            self.id = AnalysisDeclarationId(self.id)

        if self.path is not None and not isinstance(self.path, str):
            self.path = str(self.path)

        if self.url is not None and not isinstance(self.url, str):
            self.url = str(self.url)

        if self.commit is not None and not isinstance(self.commit, CommitId):
            self.commit = CommitId(self.commit)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Analysis(YAMLRoot):
    """
    An analysis: the files it reads, the artefacts it makes and the decisions it makes along the way. It is the
    content of an `astra.yaml` file.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Analysis"]
    class_class_curie: ClassVar[str] = "astra:Analysis"
    class_name: ClassVar[str] = "Analysis"
    class_model_uri: ClassVar[URIRef] = ASTRA.Analysis

    spec_version: Union[str, SpecVersion] = None
    label: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[Union[str, list[str]]] = empty_list()
    inputs: Optional[Union[dict[Union[str, InputId], Union[dict, Input]], list[Union[dict, Input]]]] = empty_dict()
    outputs: Optional[Union[dict[Union[str, OutputId], Union[dict, Output]], list[Union[dict, Output]]]] = empty_dict()
    decisions: Optional[Union[dict[Union[str, DecisionId], Union[dict, Decision]], list[Union[dict, Decision]]]] = empty_dict()
    analyses: Optional[Union[dict[Union[str, AnalysisDeclarationId], Union[dict, AnalysisDeclaration]], list[Union[dict, AnalysisDeclaration]]]] = empty_dict()
    universes: Optional[Union[dict[Union[str, UniverseId], Union[dict, Universe]], list[Union[dict, Universe]]]] = empty_dict()
    prior_insights: Optional[Union[dict[Union[str, InsightId], Union[dict, "Insight"]], list[Union[dict, "Insight"]]]] = empty_dict()
    findings: Optional[Union[dict[Union[str, InsightId], Union[dict, "Insight"]], list[Union[dict, "Insight"]]]] = empty_dict()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.spec_version):
            self.MissingRequiredField("spec_version")
        if not isinstance(self.spec_version, SpecVersion):
            self.spec_version = SpecVersion(self.spec_version)

        if self.label is not None and not isinstance(self.label, str):
            self.label = str(self.label)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if not isinstance(self.tags, list):
            self.tags = [self.tags] if self.tags is not None else []
        self.tags = [v if isinstance(v, str) else str(v) for v in self.tags]

        self._normalize_inlined_as_dict(slot_name="inputs", slot_type=Input, key_name="id", keyed=True)

        self._normalize_inlined_as_dict(slot_name="outputs", slot_type=Output, key_name="id", keyed=True)

        self._normalize_inlined_as_dict(slot_name="decisions", slot_type=Decision, key_name="id", keyed=True)

        self._normalize_inlined_as_dict(slot_name="analyses", slot_type=AnalysisDeclaration, key_name="id", keyed=True)

        self._normalize_inlined_as_dict(slot_name="universes", slot_type=Universe, key_name="id", keyed=True)

        self._normalize_inlined_as_dict(slot_name="prior_insights", slot_type=Insight, key_name="id", keyed=True)

        self._normalize_inlined_as_dict(slot_name="findings", slot_type=Insight, key_name="id", keyed=True)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class TextQuoteSelector(YAMLRoot):
    """
    W3C TextQuoteSelector for locating text in a document. The authoritative anchor for verification.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = OA["TextQuoteSelector"]
    class_class_curie: ClassVar[str] = "oa:TextQuoteSelector"
    class_name: ClassVar[str] = "TextQuoteSelector"
    class_model_uri: ClassVar[URIRef] = ASTRA.TextQuoteSelector

    exact: str = None
    prefix: Optional[str] = None
    suffix: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.exact):
            self.MissingRequiredField("exact")
        if not isinstance(self.exact, str):
            self.exact = str(self.exact)

        if self.prefix is not None and not isinstance(self.prefix, str):
            self.prefix = str(self.prefix)

        if self.suffix is not None and not isinstance(self.suffix, str):
            self.suffix = str(self.suffix)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class FragmentSelector(YAMLRoot):
    """
    A place in the cited work or output, given as a fragment identifier in the syntax `conforms_to` names, such as
    `row=5-7` in a CSV (RFC 7111). Without `conforms_to`, it is a PDF fragment identifier (RFC 8118 §3), such as
    `page=6`, with pages counted from 1.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = OA["FragmentSelector"]
    class_class_curie: ClassVar[str] = "oa:FragmentSelector"
    class_name: ClassVar[str] = "FragmentSelector"
    class_model_uri: ClassVar[URIRef] = ASTRA.FragmentSelector

    value: str = None
    conforms_to: Optional[Union[str, Iri]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.value):
            self.MissingRequiredField("value")
        if not isinstance(self.value, str):
            self.value = str(self.value)

        if self.conforms_to is not None and not isinstance(self.conforms_to, Iri):
            self.conforms_to = Iri(self.conforms_to)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Evidence(YAMLRoot):
    """
    What a claim rests on: a published work, cited by its `doi`, or an output, cited as an `artifact`. It has exactly
    one of the two, and a `version` only with a `doi`.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Evidence"]
    class_class_curie: ClassVar[str] = "astra:Evidence"
    class_name: ClassVar[str] = "Evidence"
    class_model_uri: ClassVar[URIRef] = ASTRA.Evidence

    doi: Optional[str] = None
    artifact: Optional[Union[str, Reference]] = None
    version: Optional[int] = None
    quote: Optional[Union[dict, TextQuoteSelector]] = None
    location: Optional[Union[dict, FragmentSelector]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.doi is not None and not isinstance(self.doi, str):
            self.doi = str(self.doi)

        if self.artifact is not None and not isinstance(self.artifact, Reference):
            self.artifact = Reference(self.artifact)

        if self.version is not None and not isinstance(self.version, int):
            self.version = int(self.version)

        if self.quote is not None and not isinstance(self.quote, TextQuoteSelector):
            self.quote = TextQuoteSelector(**as_dict(self.quote))

        if self.location is not None and not isinstance(self.location, FragmentSelector):
            self.location = FragmentSelector(**as_dict(self.location))

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Insight(YAMLRoot):
    """
    A claim backed by evidence: as a prior insight, what earlier work establishes and the analysis builds on; as a
    finding, what the analysis concludes.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Insight"]
    class_class_curie: ClassVar[str] = "astra:Insight"
    class_name: ClassVar[str] = "Insight"
    class_model_uri: ClassVar[URIRef] = ASTRA.Insight

    id: Union[str, InsightId] = None
    claim: str = None
    evidence: Union[Union[dict, Evidence], list[Union[dict, Evidence]]] = None
    label: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[str] = None
    tags: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, InsightId):
            self.id = InsightId(self.id)

        if self._is_empty(self.claim):
            self.MissingRequiredField("claim")
        if not isinstance(self.claim, str):
            self.claim = str(self.claim)

        if self._is_empty(self.evidence):
            self.MissingRequiredField("evidence")
        if not isinstance(self.evidence, list):
            self.evidence = [self.evidence] if self.evidence is not None else []
        self.evidence = [v if isinstance(v, Evidence) else Evidence(**as_dict(v)) for v in self.evidence]

        if self.label is not None and not isinstance(self.label, str):
            self.label = str(self.label)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if self.scope is not None and not isinstance(self.scope, str):
            self.scope = str(self.scope)

        if not isinstance(self.tags, list):
            self.tags = [self.tags] if self.tags is not None else []
        self.tags = [v if isinstance(v, str) else str(v) for v in self.tags]

        super().__post_init__(**kwargs)


# Enumerations
class OutputType(EnumDefinitionImpl):
    """
    The kind of artefact an output is.
    """
    metric = PermissibleValue(
        text="metric",
        description="A metric or measurement.")
    figure = PermissibleValue(
        text="figure",
        description="A figure or visualisation.")
    table = PermissibleValue(
        text="table",
        description="A table of data.")
    data = PermissibleValue(
        text="data",
        description="A data file or dataset.")
    report = PermissibleValue(
        text="report",
        description="A report or document.")

    _defn = EnumDefinition(
        name="OutputType",
        description="The kind of artefact an output is.",
    )

# Slots
class slots:
    pass

slots.resources__cpus = Slot(uri=ASTRA.cpus, name="resources__cpus", curie=ASTRA.curie('cpus'),
                   model_uri=ASTRA.resources__cpus, domain=None, range=Optional[float])

slots.resources__memory = Slot(uri=ASTRA.memory, name="resources__memory", curie=ASTRA.curie('memory'),
                   model_uri=ASTRA.resources__memory, domain=None, range=Optional[str])

slots.resources__time_limit = Slot(uri=ASTRA.time_limit, name="resources__time_limit", curie=ASTRA.curie('time_limit'),
                   model_uri=ASTRA.resources__time_limit, domain=None, range=Optional[str])

slots.resources__disk = Slot(uri=ASTRA.disk, name="resources__disk", curie=ASTRA.curie('disk'),
                   model_uri=ASTRA.resources__disk, domain=None, range=Optional[str])

slots.resources__gpus = Slot(uri=ASTRA.gpus, name="resources__gpus", curie=ASTRA.curie('gpus'),
                   model_uri=ASTRA.resources__gpus, domain=None, range=Optional[int])

slots.recipe__command = Slot(uri=ASTRA.command, name="recipe__command", curie=ASTRA.curie('command'),
                   model_uri=ASTRA.recipe__command, domain=None, range=str)

slots.recipe__resources = Slot(uri=ASTRA.resources, name="recipe__resources", curie=ASTRA.curie('resources'),
                   model_uri=ASTRA.recipe__resources, domain=None, range=Optional[Union[dict, Resources]])

slots.input__id = Slot(uri=ASTRA.id, name="input__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.input__id, domain=None, range=URIRef)

slots.input__label = Slot(uri=ASTRA.label, name="input__label", curie=ASTRA.curie('label'),
                   model_uri=ASTRA.input__label, domain=None, range=Optional[str])

slots.input__description = Slot(uri=ASTRA.description, name="input__description", curie=ASTRA.curie('description'),
                   model_uri=ASTRA.input__description, domain=None, range=Optional[str])

slots.input__tags = Slot(uri=ASTRA.tags, name="input__tags", curie=ASTRA.curie('tags'),
                   model_uri=ASTRA.input__tags, domain=None, range=Optional[Union[str, list[str]]])

slots.input__path = Slot(uri=ASTRA.path, name="input__path", curie=ASTRA.curie('path'),
                   model_uri=ASTRA.input__path, domain=None, range=str,
                   pattern=re.compile(r'^[^/]'))

slots.output__id = Slot(uri=ASTRA.id, name="output__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.output__id, domain=None, range=URIRef)

slots.output__label = Slot(uri=ASTRA.label, name="output__label", curie=ASTRA.curie('label'),
                   model_uri=ASTRA.output__label, domain=None, range=Optional[str])

slots.output__description = Slot(uri=ASTRA.description, name="output__description", curie=ASTRA.curie('description'),
                   model_uri=ASTRA.output__description, domain=None, range=Optional[str])

slots.output__tags = Slot(uri=ASTRA.tags, name="output__tags", curie=ASTRA.curie('tags'),
                   model_uri=ASTRA.output__tags, domain=None, range=Optional[Union[str, list[str]]])

slots.output__type = Slot(uri=ASTRA.type, name="output__type", curie=ASTRA.curie('type'),
                   model_uri=ASTRA.output__type, domain=None, range=Optional[Union[str, "OutputType"]])

slots.output__format = Slot(uri=ASTRA.format, name="output__format", curie=ASTRA.curie('format'),
                   model_uri=ASTRA.output__format, domain=None, range=Optional[str],
                   pattern=re.compile(r'^[a-z0-9][a-z0-9_.+-]*$'))

slots.output__inputs = Slot(uri=ASTRA.inputs, name="output__inputs", curie=ASTRA.curie('inputs'),
                   model_uri=ASTRA.output__inputs, domain=None, range=Optional[Union[Union[str, Reference], list[Union[str, Reference]]]])

slots.output__decisions = Slot(uri=ASTRA.decisions, name="output__decisions", curie=ASTRA.curie('decisions'),
                   model_uri=ASTRA.output__decisions, domain=None, range=Optional[Union[Union[str, Address], list[Union[str, Address]]]])

slots.output__recipe = Slot(uri=ASTRA.recipe, name="output__recipe", curie=ASTRA.curie('recipe'),
                   model_uri=ASTRA.output__recipe, domain=None, range=Optional[Union[dict, Recipe]])

slots.output__switch = Slot(uri=ASTRA.switch, name="output__switch", curie=ASTRA.curie('switch'),
                   model_uri=ASTRA.output__switch, domain=None, range=Optional[Union[str, Address]])

slots.output__cases = Slot(uri=ASTRA.cases, name="output__cases", curie=ASTRA.curie('cases'),
                   model_uri=ASTRA.output__cases, domain=None, range=Optional[Union[dict[Union[str, SwitchCaseCase], Union[dict, SwitchCase]], list[Union[dict, SwitchCase]]]])

slots.switchCase__case = Slot(uri=ASTRA.case, name="switchCase__case", curie=ASTRA.curie('case'),
                   model_uri=ASTRA.switchCase__case, domain=None, range=URIRef)

slots.switchCase__target = Slot(uri=ASTRA.target, name="switchCase__target", curie=ASTRA.curie('target'),
                   model_uri=ASTRA.switchCase__target, domain=None, range=Union[str, Reference])

slots.decision__id = Slot(uri=ASTRA.id, name="decision__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.decision__id, domain=None, range=URIRef)

slots.decision__label = Slot(uri=ASTRA.label, name="decision__label", curie=ASTRA.curie('label'),
                   model_uri=ASTRA.decision__label, domain=None, range=Optional[str])

slots.decision__rationale = Slot(uri=ASTRA.rationale, name="decision__rationale", curie=ASTRA.curie('rationale'),
                   model_uri=ASTRA.decision__rationale, domain=None, range=Optional[str])

slots.decision__tags = Slot(uri=ASTRA.tags, name="decision__tags", curie=ASTRA.curie('tags'),
                   model_uri=ASTRA.decision__tags, domain=None, range=Optional[Union[str, list[str]]])

slots.decision__options = Slot(uri=ASTRA.options, name="decision__options", curie=ASTRA.curie('options'),
                   model_uri=ASTRA.decision__options, domain=None, range=Union[dict[Union[str, OptionId], Union[dict, Option]], list[Union[dict, Option]]])

slots.option__id = Slot(uri=ASTRA.id, name="option__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.option__id, domain=None, range=URIRef)

slots.option__label = Slot(uri=ASTRA.label, name="option__label", curie=ASTRA.curie('label'),
                   model_uri=ASTRA.option__label, domain=None, range=Optional[str])

slots.option__description = Slot(uri=ASTRA.description, name="option__description", curie=ASTRA.curie('description'),
                   model_uri=ASTRA.option__description, domain=None, range=Optional[str])

slots.option__tags = Slot(uri=ASTRA.tags, name="option__tags", curie=ASTRA.curie('tags'),
                   model_uri=ASTRA.option__tags, domain=None, range=Optional[Union[str, list[str]]])

slots.option__insights = Slot(uri=ASTRA.insights, name="option__insights", curie=ASTRA.curie('insights'),
                   model_uri=ASTRA.option__insights, domain=None, range=Optional[Union[Union[str, Id], list[Union[str, Id]]]])

slots.option__requires = Slot(uri=ASTRA.requires, name="option__requires", curie=ASTRA.curie('requires'),
                   model_uri=ASTRA.option__requires, domain=None, range=Optional[Union[Union[str, OptionReference], list[Union[str, OptionReference]]]])

slots.option__incompatible_with = Slot(uri=ASTRA.incompatible_with, name="option__incompatible_with", curie=ASTRA.curie('incompatible_with'),
                   model_uri=ASTRA.option__incompatible_with, domain=None, range=Optional[Union[Union[str, OptionReference], list[Union[str, OptionReference]]]])

slots.option__excluded = Slot(uri=ASTRA.excluded, name="option__excluded", curie=ASTRA.curie('excluded'),
                   model_uri=ASTRA.option__excluded, domain=None, range=Optional[str])

slots.universe__id = Slot(uri=ASTRA.id, name="universe__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.universe__id, domain=None, range=URIRef)

slots.universe__label = Slot(uri=ASTRA.label, name="universe__label", curie=ASTRA.curie('label'),
                   model_uri=ASTRA.universe__label, domain=None, range=Optional[str])

slots.universe__description = Slot(uri=ASTRA.description, name="universe__description", curie=ASTRA.curie('description'),
                   model_uri=ASTRA.universe__description, domain=None, range=Optional[str])

slots.universe__tags = Slot(uri=ASTRA.tags, name="universe__tags", curie=ASTRA.curie('tags'),
                   model_uri=ASTRA.universe__tags, domain=None, range=Optional[Union[str, list[str]]])

slots.universe__derived_from = Slot(uri=ASTRA.derived_from, name="universe__derived_from", curie=ASTRA.curie('derived_from'),
                   model_uri=ASTRA.universe__derived_from, domain=None, range=Optional[Union[str, Id]])

slots.universe__decisions = Slot(uri=ASTRA.decisions, name="universe__decisions", curie=ASTRA.curie('decisions'),
                   model_uri=ASTRA.universe__decisions, domain=None, range=Optional[Union[dict[Union[str, DecisionSelectionDecision], Union[dict, DecisionSelection]], list[Union[dict, DecisionSelection]]]])

slots.universe__analysis = Slot(uri=ASTRA.analysis, name="universe__analysis", curie=ASTRA.curie('analysis'),
                   model_uri=ASTRA.universe__analysis, domain=None, range=Optional[Union[str, Address]])

slots.universe__universe = Slot(uri=ASTRA.universe, name="universe__universe", curie=ASTRA.curie('universe'),
                   model_uri=ASTRA.universe__universe, domain=None, range=Optional[Union[str, Id]])

slots.decisionSelection__decision = Slot(uri=ASTRA.decision, name="decisionSelection__decision", curie=ASTRA.curie('decision'),
                   model_uri=ASTRA.decisionSelection__decision, domain=None, range=URIRef)

slots.decisionSelection__option = Slot(uri=ASTRA.option, name="decisionSelection__option", curie=ASTRA.curie('option'),
                   model_uri=ASTRA.decisionSelection__option, domain=None, range=Union[str, Id])

slots.analysisDeclaration__id = Slot(uri=ASTRA.id, name="analysisDeclaration__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.analysisDeclaration__id, domain=None, range=URIRef)

slots.analysisDeclaration__path = Slot(uri=ASTRA.path, name="analysisDeclaration__path", curie=ASTRA.curie('path'),
                   model_uri=ASTRA.analysisDeclaration__path, domain=None, range=Optional[str],
                   pattern=re.compile(r'^[^/]'))

slots.analysisDeclaration__url = Slot(uri=ASTRA.url, name="analysisDeclaration__url", curie=ASTRA.curie('url'),
                   model_uri=ASTRA.analysisDeclaration__url, domain=None, range=Optional[str],
                   pattern=re.compile(r'^(?:[A-Za-z][A-Za-z0-9+.-]*://[^\x00-\x20\x7f]+|(?![A-Za-z][A-Za-z0-9+.-]*://)(?:[^\x00-\x20\x7f/@:]+@)?[^\x00-\x20\x7f/@:]+:[^\x00-\x20\x7f]+)$'))

slots.analysisDeclaration__commit = Slot(uri=ASTRA.commit, name="analysisDeclaration__commit", curie=ASTRA.curie('commit'),
                   model_uri=ASTRA.analysisDeclaration__commit, domain=None, range=Optional[Union[str, CommitId]])

slots.analysis__spec_version = Slot(uri=ASTRA.spec_version, name="analysis__spec_version", curie=ASTRA.curie('spec_version'),
                   model_uri=ASTRA.analysis__spec_version, domain=None, range=Union[str, SpecVersion])

slots.analysis__label = Slot(uri=ASTRA.label, name="analysis__label", curie=ASTRA.curie('label'),
                   model_uri=ASTRA.analysis__label, domain=None, range=Optional[str])

slots.analysis__description = Slot(uri=ASTRA.description, name="analysis__description", curie=ASTRA.curie('description'),
                   model_uri=ASTRA.analysis__description, domain=None, range=Optional[str])

slots.analysis__tags = Slot(uri=ASTRA.tags, name="analysis__tags", curie=ASTRA.curie('tags'),
                   model_uri=ASTRA.analysis__tags, domain=None, range=Optional[Union[str, list[str]]])

slots.analysis__inputs = Slot(uri=ASTRA.inputs, name="analysis__inputs", curie=ASTRA.curie('inputs'),
                   model_uri=ASTRA.analysis__inputs, domain=None, range=Optional[Union[dict[Union[str, InputId], Union[dict, Input]], list[Union[dict, Input]]]])

slots.analysis__outputs = Slot(uri=ASTRA.outputs, name="analysis__outputs", curie=ASTRA.curie('outputs'),
                   model_uri=ASTRA.analysis__outputs, domain=None, range=Optional[Union[dict[Union[str, OutputId], Union[dict, Output]], list[Union[dict, Output]]]])

slots.analysis__decisions = Slot(uri=ASTRA.decisions, name="analysis__decisions", curie=ASTRA.curie('decisions'),
                   model_uri=ASTRA.analysis__decisions, domain=None, range=Optional[Union[dict[Union[str, DecisionId], Union[dict, Decision]], list[Union[dict, Decision]]]])

slots.analysis__analyses = Slot(uri=ASTRA.analyses, name="analysis__analyses", curie=ASTRA.curie('analyses'),
                   model_uri=ASTRA.analysis__analyses, domain=None, range=Optional[Union[dict[Union[str, AnalysisDeclarationId], Union[dict, AnalysisDeclaration]], list[Union[dict, AnalysisDeclaration]]]])

slots.analysis__universes = Slot(uri=ASTRA.universes, name="analysis__universes", curie=ASTRA.curie('universes'),
                   model_uri=ASTRA.analysis__universes, domain=None, range=Optional[Union[dict[Union[str, UniverseId], Union[dict, Universe]], list[Union[dict, Universe]]]])

slots.analysis__prior_insights = Slot(uri=ASTRA.prior_insights, name="analysis__prior_insights", curie=ASTRA.curie('prior_insights'),
                   model_uri=ASTRA.analysis__prior_insights, domain=None, range=Optional[Union[dict[Union[str, InsightId], Union[dict, Insight]], list[Union[dict, Insight]]]])

slots.analysis__findings = Slot(uri=ASTRA.findings, name="analysis__findings", curie=ASTRA.curie('findings'),
                   model_uri=ASTRA.analysis__findings, domain=None, range=Optional[Union[dict[Union[str, InsightId], Union[dict, Insight]], list[Union[dict, Insight]]]])

slots.textQuoteSelector__exact = Slot(uri=OA.exact, name="textQuoteSelector__exact", curie=OA.curie('exact'),
                   model_uri=ASTRA.textQuoteSelector__exact, domain=None, range=str)

slots.textQuoteSelector__prefix = Slot(uri=OA.prefix, name="textQuoteSelector__prefix", curie=OA.curie('prefix'),
                   model_uri=ASTRA.textQuoteSelector__prefix, domain=None, range=Optional[str])

slots.textQuoteSelector__suffix = Slot(uri=OA.suffix, name="textQuoteSelector__suffix", curie=OA.curie('suffix'),
                   model_uri=ASTRA.textQuoteSelector__suffix, domain=None, range=Optional[str])

slots.fragmentSelector__value = Slot(uri=RDF.value, name="fragmentSelector__value", curie=RDF.curie('value'),
                   model_uri=ASTRA.fragmentSelector__value, domain=None, range=str,
                   pattern=re.compile(r'^([^\x00-\x20\x7f\x22#%<>\[\\\]^`{|}]|%[0-9A-Fa-f]{2})+$'))

slots.fragmentSelector__conforms_to = Slot(uri=DCTERMS.conformsTo, name="fragmentSelector__conforms_to", curie=DCTERMS.curie('conformsTo'),
                   model_uri=ASTRA.fragmentSelector__conforms_to, domain=None, range=Optional[Union[str, Iri]])

slots.evidence__doi = Slot(uri=ASTRA.doi, name="evidence__doi", curie=ASTRA.curie('doi'),
                   model_uri=ASTRA.evidence__doi, domain=None, range=Optional[str],
                   pattern=re.compile(r'^10\.[0-9]+(\.[0-9]+)*/(?!$)'))

slots.evidence__artifact = Slot(uri=ASTRA.artifact, name="evidence__artifact", curie=ASTRA.curie('artifact'),
                   model_uri=ASTRA.evidence__artifact, domain=None, range=Optional[Union[str, Reference]])

slots.evidence__version = Slot(uri=ASTRA.version, name="evidence__version", curie=ASTRA.curie('version'),
                   model_uri=ASTRA.evidence__version, domain=None, range=Optional[int])

slots.evidence__quote = Slot(uri=ASTRA.quote, name="evidence__quote", curie=ASTRA.curie('quote'),
                   model_uri=ASTRA.evidence__quote, domain=None, range=Optional[Union[dict, TextQuoteSelector]])

slots.evidence__location = Slot(uri=ASTRA.location, name="evidence__location", curie=ASTRA.curie('location'),
                   model_uri=ASTRA.evidence__location, domain=None, range=Optional[Union[dict, FragmentSelector]])

slots.insight__id = Slot(uri=ASTRA.id, name="insight__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.insight__id, domain=None, range=URIRef)

slots.insight__label = Slot(uri=ASTRA.label, name="insight__label", curie=ASTRA.curie('label'),
                   model_uri=ASTRA.insight__label, domain=None, range=Optional[str])

slots.insight__claim = Slot(uri=ASTRA.claim, name="insight__claim", curie=ASTRA.curie('claim'),
                   model_uri=ASTRA.insight__claim, domain=None, range=str)

slots.insight__description = Slot(uri=ASTRA.description, name="insight__description", curie=ASTRA.curie('description'),
                   model_uri=ASTRA.insight__description, domain=None, range=Optional[str])

slots.insight__evidence = Slot(uri=ASTRA.evidence, name="insight__evidence", curie=ASTRA.curie('evidence'),
                   model_uri=ASTRA.insight__evidence, domain=None, range=Union[Union[dict, Evidence], list[Union[dict, Evidence]]])

slots.insight__scope = Slot(uri=ASTRA.scope, name="insight__scope", curie=ASTRA.curie('scope'),
                   model_uri=ASTRA.insight__scope, domain=None, range=Optional[str])

slots.insight__tags = Slot(uri=ASTRA.tags, name="insight__tags", curie=ASTRA.curie('tags'),
                   model_uri=ASTRA.insight__tags, domain=None, range=Optional[Union[str, list[str]]])
