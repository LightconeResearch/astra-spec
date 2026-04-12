# Auto generated from astra.yaml by pythongen.py version: 0.0.1
# Generation date: 2026-04-12T18:05:57
# Schema: ASTRA
#
# id: https://w3id.org/ASTRA
# description: Agentic Schema for Transparent Research Analysis.
#   A framework for defining hierarchical scientific analyses with
#   decision points, evidence-backed insights, and universe specifications.
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

from linkml_runtime.linkml_model.types import Boolean, Datetime, Integer, String
from linkml_runtime.utils.metamodelcore import Bool, XSDDateTime

metamodel_version = "1.7.0"
version = "0.0.0"

# Namespaces
ASTRA = CurieNamespace('astra', 'https://w3id.org/ASTRA/')
LINKML = CurieNamespace('linkml', 'https://w3id.org/linkml/')
OA = CurieNamespace('oa', 'http://www.w3.org/ns/oa#')
DEFAULT_ = ASTRA


# Types

# Class references
class EvidenceId(extended_str):
    pass


class InsightId(extended_str):
    pass


class KeyValuePairKey(extended_str):
    pass


class InputId(extended_str):
    pass


class OutputId(extended_str):
    pass


class OptionId(extended_str):
    pass


class DecisionId(extended_str):
    pass


class AnalysisId(extended_str):
    pass


class DecisionSelectionDecisionId(extended_str):
    pass


class UniverseNodeId(extended_str):
    pass


class UniverseId(extended_str):
    pass


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
    W3C FragmentSelector for PDF locations. Conforms to RFC 3778/8118 for PDF fragments.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = OA["FragmentSelector"]
    class_class_curie: ClassVar[str] = "oa:FragmentSelector"
    class_name: ClassVar[str] = "FragmentSelector"
    class_model_uri: ClassVar[URIRef] = ASTRA.FragmentSelector

    value: Optional[str] = None
    page: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.value is not None and not isinstance(self.value, str):
            self.value = str(self.value)

        if self.page is not None and not isinstance(self.page, int):
            self.page = int(self.page)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Evidence(YAMLRoot):
    """
    Evidence from a source with W3C-compliant selectors. Can reference literature (by DOI) or analysis artifacts (by
    output ID). Exactly one of doi or artifact must be set.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Evidence"]
    class_class_curie: ClassVar[str] = "astra:Evidence"
    class_name: ClassVar[str] = "Evidence"
    class_model_uri: ClassVar[URIRef] = ASTRA.Evidence

    id: Union[str, EvidenceId] = None
    doi: Optional[str] = None
    artifact: Optional[str] = None
    version: Optional[int] = None
    snapshot: Optional[str] = None
    source_commit: Optional[str] = None
    quote: Optional[Union[dict, TextQuoteSelector]] = None
    location: Optional[Union[dict, FragmentSelector]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, EvidenceId):
            self.id = EvidenceId(self.id)

        if self.doi is not None and not isinstance(self.doi, str):
            self.doi = str(self.doi)

        if self.artifact is not None and not isinstance(self.artifact, str):
            self.artifact = str(self.artifact)

        if self.version is not None and not isinstance(self.version, int):
            self.version = int(self.version)

        if self.snapshot is not None and not isinstance(self.snapshot, str):
            self.snapshot = str(self.snapshot)

        if self.source_commit is not None and not isinstance(self.source_commit, str):
            self.source_commit = str(self.source_commit)

        if self.quote is not None and not isinstance(self.quote, TextQuoteSelector):
            self.quote = TextQuoteSelector(**as_dict(self.quote))

        if self.location is not None and not isinstance(self.location, FragmentSelector):
            self.location = FragmentSelector(**as_dict(self.location))

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Insight(YAMLRoot):
    """
    A unit of scientific knowledge backed by evidence. Used for both prior_insights (informing decisions) and findings
    (conclusions from the analysis).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Insight"]
    class_class_curie: ClassVar[str] = "astra:Insight"
    class_name: ClassVar[str] = "Insight"
    class_model_uri: ClassVar[URIRef] = ASTRA.Insight

    id: Union[str, InsightId] = None
    claim: str = None
    created_at: Union[str, XSDDateTime] = None
    evidence: Union[dict[Union[str, EvidenceId], Union[dict, Evidence]], list[Union[dict, Evidence]]] = empty_dict()
    derived: Optional[Union[bool, Bool]] = None
    scope: Optional[str] = None
    tags: Optional[Union[str, list[str]]] = empty_list()
    notes: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, InsightId):
            self.id = InsightId(self.id)

        if self._is_empty(self.claim):
            self.MissingRequiredField("claim")
        if not isinstance(self.claim, str):
            self.claim = str(self.claim)

        if self._is_empty(self.created_at):
            self.MissingRequiredField("created_at")
        if not isinstance(self.created_at, XSDDateTime):
            self.created_at = XSDDateTime(self.created_at)

        if self._is_empty(self.evidence):
            self.MissingRequiredField("evidence")
        self._normalize_inlined_as_list(slot_name="evidence", slot_type=Evidence, key_name="id", keyed=True)

        if self.derived is not None and not isinstance(self.derived, Bool):
            self.derived = Bool(self.derived)

        if self.scope is not None and not isinstance(self.scope, str):
            self.scope = str(self.scope)

        if not isinstance(self.tags, list):
            self.tags = [self.tags] if self.tags is not None else []
        self.tags = [v if isinstance(v, str) else str(v) for v in self.tags]

        if self.notes is not None and not isinstance(self.notes, str):
            self.notes = str(self.notes)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class InsightCollection(YAMLRoot):
    """
    Collection of insights, usable standalone or embedded in an analysis
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["InsightCollection"]
    class_class_curie: ClassVar[str] = "astra:InsightCollection"
    class_name: ClassVar[str] = "InsightCollection"
    class_model_uri: ClassVar[URIRef] = ASTRA.InsightCollection

    insights: Optional[Union[dict[Union[str, InsightId], Union[dict, Insight]], list[Union[dict, Insight]]]] = empty_dict()

    def __post_init__(self, *_: str, **kwargs: Any):
        self._normalize_inlined_as_dict(slot_name="insights", slot_type=Insight, key_name="id", keyed=True)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class KeyValuePair(YAMLRoot):
    """
    A key-value string pair
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["KeyValuePair"]
    class_class_curie: ClassVar[str] = "astra:KeyValuePair"
    class_name: ClassVar[str] = "KeyValuePair"
    class_model_uri: ClassVar[URIRef] = ASTRA.KeyValuePair

    key: Union[str, KeyValuePairKey] = None
    value: str = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.key):
            self.MissingRequiredField("key")
        if not isinstance(self.key, KeyValuePairKey):
            self.key = KeyValuePairKey(self.key)

        if self._is_empty(self.value):
            self.MissingRequiredField("value")
        if not isinstance(self.value, str):
            self.value = str(self.value)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Resources(YAMLRoot):
    """
    Compute resource requirements for a recipe
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Resources"]
    class_class_curie: ClassVar[str] = "astra:Resources"
    class_name: ClassVar[str] = "Resources"
    class_model_uri: ClassVar[URIRef] = ASTRA.Resources

    cpus: Optional[int] = None
    memory: Optional[str] = None
    gpus: Optional[int] = None
    time_limit: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.cpus is not None and not isinstance(self.cpus, int):
            self.cpus = int(self.cpus)

        if self.memory is not None and not isinstance(self.memory, str):
            self.memory = str(self.memory)

        if self.gpus is not None and not isinstance(self.gpus, int):
            self.gpus = int(self.gpus)

        if self.time_limit is not None and not isinstance(self.time_limit, str):
            self.time_limit = str(self.time_limit)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class ContainerBuildSpec(YAMLRoot):
    """
    Specification for building a container image from a Containerfile
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["ContainerBuildSpec"]
    class_class_curie: ClassVar[str] = "astra:ContainerBuildSpec"
    class_name: ClassVar[str] = "ContainerBuildSpec"
    class_model_uri: ClassVar[URIRef] = ASTRA.ContainerBuildSpec

    build: str = None
    context: Optional[str] = None
    args: Optional[Union[dict[Union[str, KeyValuePairKey], Union[dict, KeyValuePair]], list[Union[dict, KeyValuePair]]]] = empty_dict()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.build):
            self.MissingRequiredField("build")
        if not isinstance(self.build, str):
            self.build = str(self.build)

        if self.context is not None and not isinstance(self.context, str):
            self.context = str(self.context)

        self._normalize_inlined_as_list(slot_name="args", slot_type=KeyValuePair, key_name="key", keyed=True)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Recipe(YAMLRoot):
    """
    A build rule that produces an output. Recipes are the execution contract: run this command to produce the parent
    output.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Recipe"]
    class_class_curie: ClassVar[str] = "astra:Recipe"
    class_name: ClassVar[str] = "Recipe"
    class_model_uri: ClassVar[URIRef] = ASTRA.Recipe

    command: str = None
    inputs: Optional[Union[str, list[str]]] = empty_list()
    container: Optional[str] = None
    container_build: Optional[Union[dict, ContainerBuildSpec]] = None
    resources: Optional[Union[dict, Resources]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.command):
            self.MissingRequiredField("command")
        if not isinstance(self.command, str):
            self.command = str(self.command)

        if not isinstance(self.inputs, list):
            self.inputs = [self.inputs] if self.inputs is not None else []
        self.inputs = [v if isinstance(v, str) else str(v) for v in self.inputs]

        if self.container is not None and not isinstance(self.container, str):
            self.container = str(self.container)

        if self.container_build is not None and not isinstance(self.container_build, ContainerBuildSpec):
            self.container_build = ContainerBuildSpec(**as_dict(self.container_build))

        if self.resources is not None and not isinstance(self.resources, Resources):
            self.resources = Resources(**as_dict(self.resources))

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Input(YAMLRoot):
    """
    An input to the analysis. Two kinds: data (dataset/file/resource) or analysis (outputs from another ASTRA
    analysis). Sub-analysis inputs can use from_ref to reference a parent input or a sibling's output (e.g.,
    'sibling_id.output_id').
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Input"]
    class_class_curie: ClassVar[str] = "astra:Input"
    class_name: ClassVar[str] = "Input"
    class_model_uri: ClassVar[URIRef] = ASTRA.Input

    id: Union[str, InputId] = None
    type: Union[str, "InputType"] = None
    from_ref: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    ref: Optional[str] = None
    ref_version: Optional[str] = None
    use_outputs: Optional[Union[str, list[str]]] = empty_list()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, InputId):
            self.id = InputId(self.id)

        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        if not isinstance(self.type, InputType):
            self.type = InputType(self.type)

        if self.from_ref is not None and not isinstance(self.from_ref, str):
            self.from_ref = str(self.from_ref)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if self.source is not None and not isinstance(self.source, str):
            self.source = str(self.source)

        if self.ref is not None and not isinstance(self.ref, str):
            self.ref = str(self.ref)

        if self.ref_version is not None and not isinstance(self.ref_version, str):
            self.ref_version = str(self.ref_version)

        if not isinstance(self.use_outputs, list):
            self.use_outputs = [self.use_outputs] if self.use_outputs is not None else []
        self.use_outputs = [v if isinstance(v, str) else str(v) for v in self.use_outputs]

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Output(YAMLRoot):
    """
    An expected output from the analysis. Outputs can declare their provenance via from_ref to trace which
    sub-analysis produces them.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Output"]
    class_class_curie: ClassVar[str] = "astra:Output"
    class_name: ClassVar[str] = "Output"
    class_model_uri: ClassVar[URIRef] = ASTRA.Output

    id: Union[str, OutputId] = None
    type: Union[str, "OutputType"] = None
    from_ref: Optional[str] = None
    when: Optional[Union[str, list[str]]] = empty_list()
    description: Optional[str] = None
    recipe: Optional[Union[dict, Recipe]] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, OutputId):
            self.id = OutputId(self.id)

        if self._is_empty(self.type):
            self.MissingRequiredField("type")
        if not isinstance(self.type, OutputType):
            self.type = OutputType(self.type)

        if self.from_ref is not None and not isinstance(self.from_ref, str):
            self.from_ref = str(self.from_ref)

        if not isinstance(self.when, list):
            self.when = [self.when] if self.when is not None else []
        self.when = [v if isinstance(v, str) else str(v) for v in self.when]

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if self.recipe is not None and not isinstance(self.recipe, Recipe):
            self.recipe = Recipe(**as_dict(self.recipe))

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Option(YAMLRoot):
    """
    An option for a decision point
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Option"]
    class_class_curie: ClassVar[str] = "astra:Option"
    class_name: ClassVar[str] = "Option"
    class_model_uri: ClassVar[URIRef] = ASTRA.Option

    id: Union[str, OptionId] = None
    label: str = None
    description: Optional[str] = None
    insights: Optional[Union[str, list[str]]] = empty_list()
    incompatible_with: Optional[Union[str, list[str]]] = empty_list()
    requires: Optional[Union[str, list[str]]] = empty_list()
    excluded: Optional[Union[bool, Bool]] = None
    excluded_reason: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, OptionId):
            self.id = OptionId(self.id)

        if self._is_empty(self.label):
            self.MissingRequiredField("label")
        if not isinstance(self.label, str):
            self.label = str(self.label)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if not isinstance(self.insights, list):
            self.insights = [self.insights] if self.insights is not None else []
        self.insights = [v if isinstance(v, str) else str(v) for v in self.insights]

        if not isinstance(self.incompatible_with, list):
            self.incompatible_with = [self.incompatible_with] if self.incompatible_with is not None else []
        self.incompatible_with = [v if isinstance(v, str) else str(v) for v in self.incompatible_with]

        if not isinstance(self.requires, list):
            self.requires = [self.requires] if self.requires is not None else []
        self.requires = [v if isinstance(v, str) else str(v) for v in self.requires]

        if self.excluded is not None and not isinstance(self.excluded, Bool):
            self.excluded = Bool(self.excluded)

        if self.excluded_reason is not None and not isinstance(self.excluded_reason, str):
            self.excluded_reason = str(self.excluded_reason)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Decision(YAMLRoot):
    """
    A decision point in the analysis. Can be locally defined (with label, options) or a reference to a parent decision
    via from_ref.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Decision"]
    class_class_curie: ClassVar[str] = "astra:Decision"
    class_name: ClassVar[str] = "Decision"
    class_model_uri: ClassVar[URIRef] = ASTRA.Decision

    id: Union[str, DecisionId] = None
    from_ref: Optional[str] = None
    when: Optional[Union[str, list[str]]] = empty_list()
    label: Optional[str] = None
    rationale: Optional[str] = None
    tags: Optional[Union[str, list[str]]] = empty_list()
    default: Optional[str] = None
    options: Optional[Union[dict[Union[str, OptionId], Union[dict, Option]], list[Union[dict, Option]]]] = empty_dict()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, DecisionId):
            self.id = DecisionId(self.id)

        if self.from_ref is not None and not isinstance(self.from_ref, str):
            self.from_ref = str(self.from_ref)

        if not isinstance(self.when, list):
            self.when = [self.when] if self.when is not None else []
        self.when = [v if isinstance(v, str) else str(v) for v in self.when]

        if self.label is not None and not isinstance(self.label, str):
            self.label = str(self.label)

        if self.rationale is not None and not isinstance(self.rationale, str):
            self.rationale = str(self.rationale)

        if not isinstance(self.tags, list):
            self.tags = [self.tags] if self.tags is not None else []
        self.tags = [v if isinstance(v, str) else str(v) for v in self.tags]

        if self.default is not None and not isinstance(self.default, str):
            self.default = str(self.default)

        self._normalize_inlined_as_dict(slot_name="options", slot_type=Option, key_name="id", keyed=True)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Analysis(YAMLRoot):
    """
    A self-similar analysis specification. Every level has the same structure: metadata, inputs, outputs, decisions,
    insights, and optional sub-analyses. A sub-analysis extracted to its own file is a valid Analysis on its own.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Analysis"]
    class_class_curie: ClassVar[str] = "astra:Analysis"
    class_name: ClassVar[str] = "Analysis"
    class_model_uri: ClassVar[URIRef] = ASTRA.Analysis

    id: Union[str, AnalysisId] = None
    version: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    authors: Optional[Union[str, list[str]]] = empty_list()
    tags: Optional[Union[str, list[str]]] = empty_list()
    inputs: Optional[Union[dict[Union[str, InputId], Union[dict, Input]], list[Union[dict, Input]]]] = empty_dict()
    outputs: Optional[Union[dict[Union[str, OutputId], Union[dict, Output]], list[Union[dict, Output]]]] = empty_dict()
    decisions: Optional[Union[dict[Union[str, DecisionId], Union[dict, Decision]], list[Union[dict, Decision]]]] = empty_dict()
    prior_insights: Optional[Union[dict[Union[str, InsightId], Union[dict, Insight]], list[Union[dict, Insight]]]] = empty_dict()
    findings: Optional[Union[dict[Union[str, InsightId], Union[dict, Insight]], list[Union[dict, Insight]]]] = empty_dict()
    container: Optional[str] = None
    container_build: Optional[Union[dict, ContainerBuildSpec]] = None
    path: Optional[str] = None
    analyses: Optional[Union[dict[Union[str, AnalysisId], Union[dict, "Analysis"]], list[Union[dict, "Analysis"]]]] = empty_dict()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, AnalysisId):
            self.id = AnalysisId(self.id)

        if self.version is not None and not isinstance(self.version, str):
            self.version = str(self.version)

        if self.name is not None and not isinstance(self.name, str):
            self.name = str(self.name)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if not isinstance(self.authors, list):
            self.authors = [self.authors] if self.authors is not None else []
        self.authors = [v if isinstance(v, str) else str(v) for v in self.authors]

        if not isinstance(self.tags, list):
            self.tags = [self.tags] if self.tags is not None else []
        self.tags = [v if isinstance(v, str) else str(v) for v in self.tags]

        self._normalize_inlined_as_list(slot_name="inputs", slot_type=Input, key_name="id", keyed=True)

        self._normalize_inlined_as_list(slot_name="outputs", slot_type=Output, key_name="id", keyed=True)

        self._normalize_inlined_as_dict(slot_name="decisions", slot_type=Decision, key_name="id", keyed=True)

        self._normalize_inlined_as_dict(slot_name="prior_insights", slot_type=Insight, key_name="id", keyed=True)

        self._normalize_inlined_as_dict(slot_name="findings", slot_type=Insight, key_name="id", keyed=True)

        if self.container is not None and not isinstance(self.container, str):
            self.container = str(self.container)

        if self.container_build is not None and not isinstance(self.container_build, ContainerBuildSpec):
            self.container_build = ContainerBuildSpec(**as_dict(self.container_build))

        if self.path is not None and not isinstance(self.path, str):
            self.path = str(self.path)

        self._normalize_inlined_as_dict(slot_name="analyses", slot_type=Analysis, key_name="id", keyed=True)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class DecisionSelection(YAMLRoot):
    """
    A mapping from a decision ID to the selected option ID
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["DecisionSelection"]
    class_class_curie: ClassVar[str] = "astra:DecisionSelection"
    class_name: ClassVar[str] = "DecisionSelection"
    class_model_uri: ClassVar[URIRef] = ASTRA.DecisionSelection

    decision_id: Union[str, DecisionSelectionDecisionId] = None
    option_id: str = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.decision_id):
            self.MissingRequiredField("decision_id")
        if not isinstance(self.decision_id, DecisionSelectionDecisionId):
            self.decision_id = DecisionSelectionDecisionId(self.decision_id)

        if self._is_empty(self.option_id):
            self.MissingRequiredField("option_id")
        if not isinstance(self.option_id, str):
            self.option_id = str(self.option_id)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class UniverseNode(YAMLRoot):
    """
    A universe node mirroring the analysis tree structure. Represents decision selections at a specific sub-analysis
    node.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["UniverseNode"]
    class_class_curie: ClassVar[str] = "astra:UniverseNode"
    class_name: ClassVar[str] = "UniverseNode"
    class_model_uri: ClassVar[URIRef] = ASTRA.UniverseNode

    id: Union[str, UniverseNodeId] = None
    universe: Optional[str] = None
    decisions: Optional[Union[dict[Union[str, DecisionSelectionDecisionId], Union[dict, DecisionSelection]], list[Union[dict, DecisionSelection]]]] = empty_dict()
    analyses: Optional[Union[dict[Union[str, UniverseNodeId], Union[dict, "UniverseNode"]], list[Union[dict, "UniverseNode"]]]] = empty_dict()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, UniverseNodeId):
            self.id = UniverseNodeId(self.id)

        if self.universe is not None and not isinstance(self.universe, str):
            self.universe = str(self.universe)

        self._normalize_inlined_as_list(slot_name="decisions", slot_type=DecisionSelection, key_name="decision_id", keyed=True)

        self._normalize_inlined_as_dict(slot_name="analyses", slot_type=UniverseNode, key_name="id", keyed=True)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Universe(YAMLRoot):
    """
    A universe specification - a complete set of decisions across the entire analysis tree.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Universe"]
    class_class_curie: ClassVar[str] = "astra:Universe"
    class_name: ClassVar[str] = "Universe"
    class_model_uri: ClassVar[URIRef] = ASTRA.Universe

    id: Union[str, UniverseId] = None
    description: Optional[str] = None
    decisions: Optional[Union[dict[Union[str, DecisionSelectionDecisionId], Union[dict, DecisionSelection]], list[Union[dict, DecisionSelection]]]] = empty_dict()
    analyses: Optional[Union[dict[Union[str, UniverseNodeId], Union[dict, UniverseNode]], list[Union[dict, UniverseNode]]]] = empty_dict()

    def __post_init__(self, *_: str, **kwargs: Any):
        if self._is_empty(self.id):
            self.MissingRequiredField("id")
        if not isinstance(self.id, UniverseId):
            self.id = UniverseId(self.id)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        self._normalize_inlined_as_list(slot_name="decisions", slot_type=DecisionSelection, key_name="decision_id", keyed=True)

        self._normalize_inlined_as_dict(slot_name="analyses", slot_type=UniverseNode, key_name="id", keyed=True)

        super().__post_init__(**kwargs)


# Enumerations
class InputType(EnumDefinitionImpl):
    """
    Type of analysis input
    """
    data = PermissibleValue(
        text="data",
        description="A dataset, file, or external resource")
    analysis = PermissibleValue(
        text="analysis",
        description="Outputs from another ASTRA analysis")

    _defn = EnumDefinition(
        name="InputType",
        description="Type of analysis input",
    )

class OutputType(EnumDefinitionImpl):
    """
    Type of analysis output
    """
    metric = PermissibleValue(
        text="metric",
        description="A metric or measurement")
    figure = PermissibleValue(
        text="figure",
        description="A figure or visualization")
    table = PermissibleValue(
        text="table",
        description="A table of data")
    data = PermissibleValue(
        text="data",
        description="A data file or dataset")
    report = PermissibleValue(
        text="report",
        description="A report or document")

    _defn = EnumDefinition(
        name="OutputType",
        description="Type of analysis output",
    )

# Slots
class slots:
    pass

slots.from_ref = Slot(uri=ASTRA.from_ref, name="from_ref", curie=ASTRA.curie('from_ref'),
                   model_uri=ASTRA.from_ref, domain=None, range=Optional[str])

slots.when = Slot(uri=ASTRA.when, name="when", curie=ASTRA.curie('when'),
                   model_uri=ASTRA.when, domain=None, range=Optional[Union[str, list[str]]])

slots.textQuoteSelector__exact = Slot(uri=ASTRA.exact, name="textQuoteSelector__exact", curie=ASTRA.curie('exact'),
                   model_uri=ASTRA.textQuoteSelector__exact, domain=None, range=str)

slots.textQuoteSelector__prefix = Slot(uri=ASTRA.prefix, name="textQuoteSelector__prefix", curie=ASTRA.curie('prefix'),
                   model_uri=ASTRA.textQuoteSelector__prefix, domain=None, range=Optional[str])

slots.textQuoteSelector__suffix = Slot(uri=ASTRA.suffix, name="textQuoteSelector__suffix", curie=ASTRA.curie('suffix'),
                   model_uri=ASTRA.textQuoteSelector__suffix, domain=None, range=Optional[str])

slots.fragmentSelector__value = Slot(uri=ASTRA.value, name="fragmentSelector__value", curie=ASTRA.curie('value'),
                   model_uri=ASTRA.fragmentSelector__value, domain=None, range=Optional[str])

slots.fragmentSelector__page = Slot(uri=ASTRA.page, name="fragmentSelector__page", curie=ASTRA.curie('page'),
                   model_uri=ASTRA.fragmentSelector__page, domain=None, range=Optional[int])

slots.evidence__id = Slot(uri=ASTRA.id, name="evidence__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.evidence__id, domain=None, range=URIRef)

slots.evidence__doi = Slot(uri=ASTRA.doi, name="evidence__doi", curie=ASTRA.curie('doi'),
                   model_uri=ASTRA.evidence__doi, domain=None, range=Optional[str],
                   pattern=re.compile(r'^10\.\d{4,}/.*$'))

slots.evidence__artifact = Slot(uri=ASTRA.artifact, name="evidence__artifact", curie=ASTRA.curie('artifact'),
                   model_uri=ASTRA.evidence__artifact, domain=None, range=Optional[str])

slots.evidence__version = Slot(uri=ASTRA.version, name="evidence__version", curie=ASTRA.curie('version'),
                   model_uri=ASTRA.evidence__version, domain=None, range=Optional[int])

slots.evidence__snapshot = Slot(uri=ASTRA.snapshot, name="evidence__snapshot", curie=ASTRA.curie('snapshot'),
                   model_uri=ASTRA.evidence__snapshot, domain=None, range=Optional[str])

slots.evidence__source_commit = Slot(uri=ASTRA.source_commit, name="evidence__source_commit", curie=ASTRA.curie('source_commit'),
                   model_uri=ASTRA.evidence__source_commit, domain=None, range=Optional[str])

slots.evidence__quote = Slot(uri=ASTRA.quote, name="evidence__quote", curie=ASTRA.curie('quote'),
                   model_uri=ASTRA.evidence__quote, domain=None, range=Optional[Union[dict, TextQuoteSelector]])

slots.evidence__location = Slot(uri=ASTRA.location, name="evidence__location", curie=ASTRA.curie('location'),
                   model_uri=ASTRA.evidence__location, domain=None, range=Optional[Union[dict, FragmentSelector]])

slots.insight__id = Slot(uri=ASTRA.id, name="insight__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.insight__id, domain=None, range=URIRef)

slots.insight__claim = Slot(uri=ASTRA.claim, name="insight__claim", curie=ASTRA.curie('claim'),
                   model_uri=ASTRA.insight__claim, domain=None, range=str)

slots.insight__created_at = Slot(uri=ASTRA.created_at, name="insight__created_at", curie=ASTRA.curie('created_at'),
                   model_uri=ASTRA.insight__created_at, domain=None, range=Union[str, XSDDateTime])

slots.insight__evidence = Slot(uri=ASTRA.evidence, name="insight__evidence", curie=ASTRA.curie('evidence'),
                   model_uri=ASTRA.insight__evidence, domain=None, range=Union[dict[Union[str, EvidenceId], Union[dict, Evidence]], list[Union[dict, Evidence]]])

slots.insight__derived = Slot(uri=ASTRA.derived, name="insight__derived", curie=ASTRA.curie('derived'),
                   model_uri=ASTRA.insight__derived, domain=None, range=Optional[Union[bool, Bool]])

slots.insight__scope = Slot(uri=ASTRA.scope, name="insight__scope", curie=ASTRA.curie('scope'),
                   model_uri=ASTRA.insight__scope, domain=None, range=Optional[str])

slots.insight__tags = Slot(uri=ASTRA.tags, name="insight__tags", curie=ASTRA.curie('tags'),
                   model_uri=ASTRA.insight__tags, domain=None, range=Optional[Union[str, list[str]]])

slots.insight__notes = Slot(uri=ASTRA.notes, name="insight__notes", curie=ASTRA.curie('notes'),
                   model_uri=ASTRA.insight__notes, domain=None, range=Optional[str])

slots.insightCollection__insights = Slot(uri=ASTRA.insights, name="insightCollection__insights", curie=ASTRA.curie('insights'),
                   model_uri=ASTRA.insightCollection__insights, domain=None, range=Optional[Union[dict[Union[str, InsightId], Union[dict, Insight]], list[Union[dict, Insight]]]])

slots.keyValuePair__key = Slot(uri=ASTRA.key, name="keyValuePair__key", curie=ASTRA.curie('key'),
                   model_uri=ASTRA.keyValuePair__key, domain=None, range=URIRef)

slots.keyValuePair__value = Slot(uri=ASTRA.value, name="keyValuePair__value", curie=ASTRA.curie('value'),
                   model_uri=ASTRA.keyValuePair__value, domain=None, range=str)

slots.resources__cpus = Slot(uri=ASTRA.cpus, name="resources__cpus", curie=ASTRA.curie('cpus'),
                   model_uri=ASTRA.resources__cpus, domain=None, range=Optional[int])

slots.resources__memory = Slot(uri=ASTRA.memory, name="resources__memory", curie=ASTRA.curie('memory'),
                   model_uri=ASTRA.resources__memory, domain=None, range=Optional[str])

slots.resources__gpus = Slot(uri=ASTRA.gpus, name="resources__gpus", curie=ASTRA.curie('gpus'),
                   model_uri=ASTRA.resources__gpus, domain=None, range=Optional[int])

slots.resources__time_limit = Slot(uri=ASTRA.time_limit, name="resources__time_limit", curie=ASTRA.curie('time_limit'),
                   model_uri=ASTRA.resources__time_limit, domain=None, range=Optional[str])

slots.containerBuildSpec__build = Slot(uri=ASTRA.build, name="containerBuildSpec__build", curie=ASTRA.curie('build'),
                   model_uri=ASTRA.containerBuildSpec__build, domain=None, range=str)

slots.containerBuildSpec__context = Slot(uri=ASTRA.context, name="containerBuildSpec__context", curie=ASTRA.curie('context'),
                   model_uri=ASTRA.containerBuildSpec__context, domain=None, range=Optional[str])

slots.containerBuildSpec__args = Slot(uri=ASTRA.args, name="containerBuildSpec__args", curie=ASTRA.curie('args'),
                   model_uri=ASTRA.containerBuildSpec__args, domain=None, range=Optional[Union[dict[Union[str, KeyValuePairKey], Union[dict, KeyValuePair]], list[Union[dict, KeyValuePair]]]])

slots.recipe__command = Slot(uri=ASTRA.command, name="recipe__command", curie=ASTRA.curie('command'),
                   model_uri=ASTRA.recipe__command, domain=None, range=str)

slots.recipe__inputs = Slot(uri=ASTRA.inputs, name="recipe__inputs", curie=ASTRA.curie('inputs'),
                   model_uri=ASTRA.recipe__inputs, domain=None, range=Optional[Union[str, list[str]]])

slots.recipe__container = Slot(uri=ASTRA.container, name="recipe__container", curie=ASTRA.curie('container'),
                   model_uri=ASTRA.recipe__container, domain=None, range=Optional[str])

slots.recipe__container_build = Slot(uri=ASTRA.container_build, name="recipe__container_build", curie=ASTRA.curie('container_build'),
                   model_uri=ASTRA.recipe__container_build, domain=None, range=Optional[Union[dict, ContainerBuildSpec]])

slots.recipe__resources = Slot(uri=ASTRA.resources, name="recipe__resources", curie=ASTRA.curie('resources'),
                   model_uri=ASTRA.recipe__resources, domain=None, range=Optional[Union[dict, Resources]])

slots.input__id = Slot(uri=ASTRA.id, name="input__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.input__id, domain=None, range=URIRef,
                   pattern=re.compile(r'^[a-z][a-z0-9_]*$'))

slots.input__type = Slot(uri=ASTRA.type, name="input__type", curie=ASTRA.curie('type'),
                   model_uri=ASTRA.input__type, domain=None, range=Union[str, "InputType"])

slots.input__description = Slot(uri=ASTRA.description, name="input__description", curie=ASTRA.curie('description'),
                   model_uri=ASTRA.input__description, domain=None, range=Optional[str])

slots.input__source = Slot(uri=ASTRA.source, name="input__source", curie=ASTRA.curie('source'),
                   model_uri=ASTRA.input__source, domain=None, range=Optional[str])

slots.input__ref = Slot(uri=ASTRA.ref, name="input__ref", curie=ASTRA.curie('ref'),
                   model_uri=ASTRA.input__ref, domain=None, range=Optional[str])

slots.input__ref_version = Slot(uri=ASTRA.ref_version, name="input__ref_version", curie=ASTRA.curie('ref_version'),
                   model_uri=ASTRA.input__ref_version, domain=None, range=Optional[str])

slots.input__use_outputs = Slot(uri=ASTRA.use_outputs, name="input__use_outputs", curie=ASTRA.curie('use_outputs'),
                   model_uri=ASTRA.input__use_outputs, domain=None, range=Optional[Union[str, list[str]]])

slots.output__id = Slot(uri=ASTRA.id, name="output__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.output__id, domain=None, range=URIRef,
                   pattern=re.compile(r'^[a-z][a-z0-9_]*$'))

slots.output__type = Slot(uri=ASTRA.type, name="output__type", curie=ASTRA.curie('type'),
                   model_uri=ASTRA.output__type, domain=None, range=Union[str, "OutputType"])

slots.output__description = Slot(uri=ASTRA.description, name="output__description", curie=ASTRA.curie('description'),
                   model_uri=ASTRA.output__description, domain=None, range=Optional[str])

slots.output__recipe = Slot(uri=ASTRA.recipe, name="output__recipe", curie=ASTRA.curie('recipe'),
                   model_uri=ASTRA.output__recipe, domain=None, range=Optional[Union[dict, Recipe]])

slots.option__id = Slot(uri=ASTRA.id, name="option__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.option__id, domain=None, range=URIRef)

slots.option__label = Slot(uri=ASTRA.label, name="option__label", curie=ASTRA.curie('label'),
                   model_uri=ASTRA.option__label, domain=None, range=str)

slots.option__description = Slot(uri=ASTRA.description, name="option__description", curie=ASTRA.curie('description'),
                   model_uri=ASTRA.option__description, domain=None, range=Optional[str])

slots.option__insights = Slot(uri=ASTRA.insights, name="option__insights", curie=ASTRA.curie('insights'),
                   model_uri=ASTRA.option__insights, domain=None, range=Optional[Union[str, list[str]]])

slots.option__incompatible_with = Slot(uri=ASTRA.incompatible_with, name="option__incompatible_with", curie=ASTRA.curie('incompatible_with'),
                   model_uri=ASTRA.option__incompatible_with, domain=None, range=Optional[Union[str, list[str]]])

slots.option__requires = Slot(uri=ASTRA.requires, name="option__requires", curie=ASTRA.curie('requires'),
                   model_uri=ASTRA.option__requires, domain=None, range=Optional[Union[str, list[str]]])

slots.option__excluded = Slot(uri=ASTRA.excluded, name="option__excluded", curie=ASTRA.curie('excluded'),
                   model_uri=ASTRA.option__excluded, domain=None, range=Optional[Union[bool, Bool]])

slots.option__excluded_reason = Slot(uri=ASTRA.excluded_reason, name="option__excluded_reason", curie=ASTRA.curie('excluded_reason'),
                   model_uri=ASTRA.option__excluded_reason, domain=None, range=Optional[str])

slots.decision__id = Slot(uri=ASTRA.id, name="decision__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.decision__id, domain=None, range=URIRef)

slots.decision__label = Slot(uri=ASTRA.label, name="decision__label", curie=ASTRA.curie('label'),
                   model_uri=ASTRA.decision__label, domain=None, range=Optional[str])

slots.decision__rationale = Slot(uri=ASTRA.rationale, name="decision__rationale", curie=ASTRA.curie('rationale'),
                   model_uri=ASTRA.decision__rationale, domain=None, range=Optional[str])

slots.decision__tags = Slot(uri=ASTRA.tags, name="decision__tags", curie=ASTRA.curie('tags'),
                   model_uri=ASTRA.decision__tags, domain=None, range=Optional[Union[str, list[str]]])

slots.decision__default = Slot(uri=ASTRA.default, name="decision__default", curie=ASTRA.curie('default'),
                   model_uri=ASTRA.decision__default, domain=None, range=Optional[str])

slots.decision__options = Slot(uri=ASTRA.options, name="decision__options", curie=ASTRA.curie('options'),
                   model_uri=ASTRA.decision__options, domain=None, range=Optional[Union[dict[Union[str, OptionId], Union[dict, Option]], list[Union[dict, Option]]]])

slots.analysis__id = Slot(uri=ASTRA.id, name="analysis__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.analysis__id, domain=None, range=URIRef)

slots.analysis__version = Slot(uri=ASTRA.version, name="analysis__version", curie=ASTRA.curie('version'),
                   model_uri=ASTRA.analysis__version, domain=None, range=Optional[str],
                   pattern=re.compile(r'^\d+\.\d+(\.\d+)?$'))

slots.analysis__name = Slot(uri=ASTRA.name, name="analysis__name", curie=ASTRA.curie('name'),
                   model_uri=ASTRA.analysis__name, domain=None, range=Optional[str])

slots.analysis__description = Slot(uri=ASTRA.description, name="analysis__description", curie=ASTRA.curie('description'),
                   model_uri=ASTRA.analysis__description, domain=None, range=Optional[str])

slots.analysis__authors = Slot(uri=ASTRA.authors, name="analysis__authors", curie=ASTRA.curie('authors'),
                   model_uri=ASTRA.analysis__authors, domain=None, range=Optional[Union[str, list[str]]])

slots.analysis__tags = Slot(uri=ASTRA.tags, name="analysis__tags", curie=ASTRA.curie('tags'),
                   model_uri=ASTRA.analysis__tags, domain=None, range=Optional[Union[str, list[str]]])

slots.analysis__inputs = Slot(uri=ASTRA.inputs, name="analysis__inputs", curie=ASTRA.curie('inputs'),
                   model_uri=ASTRA.analysis__inputs, domain=None, range=Optional[Union[dict[Union[str, InputId], Union[dict, Input]], list[Union[dict, Input]]]])

slots.analysis__outputs = Slot(uri=ASTRA.outputs, name="analysis__outputs", curie=ASTRA.curie('outputs'),
                   model_uri=ASTRA.analysis__outputs, domain=None, range=Optional[Union[dict[Union[str, OutputId], Union[dict, Output]], list[Union[dict, Output]]]])

slots.analysis__decisions = Slot(uri=ASTRA.decisions, name="analysis__decisions", curie=ASTRA.curie('decisions'),
                   model_uri=ASTRA.analysis__decisions, domain=None, range=Optional[Union[dict[Union[str, DecisionId], Union[dict, Decision]], list[Union[dict, Decision]]]])

slots.analysis__prior_insights = Slot(uri=ASTRA.prior_insights, name="analysis__prior_insights", curie=ASTRA.curie('prior_insights'),
                   model_uri=ASTRA.analysis__prior_insights, domain=None, range=Optional[Union[dict[Union[str, InsightId], Union[dict, Insight]], list[Union[dict, Insight]]]])

slots.analysis__findings = Slot(uri=ASTRA.findings, name="analysis__findings", curie=ASTRA.curie('findings'),
                   model_uri=ASTRA.analysis__findings, domain=None, range=Optional[Union[dict[Union[str, InsightId], Union[dict, Insight]], list[Union[dict, Insight]]]])

slots.analysis__container = Slot(uri=ASTRA.container, name="analysis__container", curie=ASTRA.curie('container'),
                   model_uri=ASTRA.analysis__container, domain=None, range=Optional[str])

slots.analysis__container_build = Slot(uri=ASTRA.container_build, name="analysis__container_build", curie=ASTRA.curie('container_build'),
                   model_uri=ASTRA.analysis__container_build, domain=None, range=Optional[Union[dict, ContainerBuildSpec]])

slots.analysis__path = Slot(uri=ASTRA.path, name="analysis__path", curie=ASTRA.curie('path'),
                   model_uri=ASTRA.analysis__path, domain=None, range=Optional[str])

slots.analysis__analyses = Slot(uri=ASTRA.analyses, name="analysis__analyses", curie=ASTRA.curie('analyses'),
                   model_uri=ASTRA.analysis__analyses, domain=None, range=Optional[Union[dict[Union[str, AnalysisId], Union[dict, Analysis]], list[Union[dict, Analysis]]]])

slots.decisionSelection__decision_id = Slot(uri=ASTRA.decision_id, name="decisionSelection__decision_id", curie=ASTRA.curie('decision_id'),
                   model_uri=ASTRA.decisionSelection__decision_id, domain=None, range=URIRef)

slots.decisionSelection__option_id = Slot(uri=ASTRA.option_id, name="decisionSelection__option_id", curie=ASTRA.curie('option_id'),
                   model_uri=ASTRA.decisionSelection__option_id, domain=None, range=str)

slots.universeNode__id = Slot(uri=ASTRA.id, name="universeNode__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.universeNode__id, domain=None, range=URIRef)

slots.universeNode__universe = Slot(uri=ASTRA.universe, name="universeNode__universe", curie=ASTRA.curie('universe'),
                   model_uri=ASTRA.universeNode__universe, domain=None, range=Optional[str])

slots.universeNode__decisions = Slot(uri=ASTRA.decisions, name="universeNode__decisions", curie=ASTRA.curie('decisions'),
                   model_uri=ASTRA.universeNode__decisions, domain=None, range=Optional[Union[dict[Union[str, DecisionSelectionDecisionId], Union[dict, DecisionSelection]], list[Union[dict, DecisionSelection]]]])

slots.universeNode__analyses = Slot(uri=ASTRA.analyses, name="universeNode__analyses", curie=ASTRA.curie('analyses'),
                   model_uri=ASTRA.universeNode__analyses, domain=None, range=Optional[Union[dict[Union[str, UniverseNodeId], Union[dict, UniverseNode]], list[Union[dict, UniverseNode]]]])

slots.universe__id = Slot(uri=ASTRA.id, name="universe__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.universe__id, domain=None, range=URIRef,
                   pattern=re.compile(r'^[a-z][a-z0-9_-]*$'))

slots.universe__description = Slot(uri=ASTRA.description, name="universe__description", curie=ASTRA.curie('description'),
                   model_uri=ASTRA.universe__description, domain=None, range=Optional[str])

slots.universe__decisions = Slot(uri=ASTRA.decisions, name="universe__decisions", curie=ASTRA.curie('decisions'),
                   model_uri=ASTRA.universe__decisions, domain=None, range=Optional[Union[dict[Union[str, DecisionSelectionDecisionId], Union[dict, DecisionSelection]], list[Union[dict, DecisionSelection]]]])

slots.universe__analyses = Slot(uri=ASTRA.analyses, name="universe__analyses", curie=ASTRA.curie('analyses'),
                   model_uri=ASTRA.universe__analyses, domain=None, range=Optional[Union[dict[Union[str, UniverseNodeId], Union[dict, UniverseNode]], list[Union[dict, UniverseNode]]]])

slots.Input_from_ref = Slot(uri=ASTRA.from_ref, name="Input_from_ref", curie=ASTRA.curie('from_ref'),
                   model_uri=ASTRA.Input_from_ref, domain=Input, range=Optional[str])

slots.Output_from_ref = Slot(uri=ASTRA.from_ref, name="Output_from_ref", curie=ASTRA.curie('from_ref'),
                   model_uri=ASTRA.Output_from_ref, domain=Output, range=Optional[str])

slots.Decision_from_ref = Slot(uri=ASTRA.from_ref, name="Decision_from_ref", curie=ASTRA.curie('from_ref'),
                   model_uri=ASTRA.Decision_from_ref, domain=Decision, range=Optional[str])
