# Auto generated from analysis.yaml by pythongen.py version: 0.0.1
# Generation date: 2026-04-26T13:06:00
# Schema: analysis
#
# id: https://w3id.org/ASTRA/analysis
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
version = "0.0.6"

# Namespaces
ASTRA = CurieNamespace('astra', 'https://w3id.org/ASTRA/')
LINKML = CurieNamespace('linkml', 'https://w3id.org/linkml/')
OA = CurieNamespace('oa', 'http://www.w3.org/ns/oa#')
DEFAULT_ = ASTRA


# Types

# Class references
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


class EvidenceId(extended_str):
    pass


class InsightId(extended_str):
    pass


class DecisionSelectionDecisionId(extended_str):
    pass


class UniverseNodeId(extended_str):
    pass


class UniverseId(extended_str):
    pass


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
class Narrative(YAMLRoot):
    """
    Structured prose describing an analysis, organized into five sections: summary, findings, methods, inputs, and
    outputs. All sections are schema-optional, but ``astra validate`` applies a conditional requirement: a section
    must hold non-empty prose when the corresponding structured data exists on the Analysis node.
    - ``findings`` required when Analysis.findings has entries. - ``methods`` required when Analysis.decisions or
    Analysis.analyses has entries.
    - ``inputs`` required when Analysis.inputs has entries. - ``outputs`` required when Analysis.outputs has entries.
    - ``summary`` is always optional — no structured counterpart.
    Authors narrate what they declare; stub analyses with only a summary stay clean.
    Section content is Markdown. Internal references to other elements of the analysis use anchor links of the form
    ``[text](#path.to.element)``. References may appear in any section — coverage is resolved across the whole
    narrative, not per-section — so an author is free to cite a finding from the summary, or an input from the methods
    section.
    Anchor grammar is tree-path-first, matching the rest of ASTRA's reference syntax (e.g. 'sibling.output_id' in
    'from'). Sub-analyses are traversed before the category:

    [scaling decision](#decisions.scaling)
    [scaling option](#decisions.scaling.options.standard)
    [finding](#findings.best_model)
    [prior insight](#prior_insights.compute_scaling)
    [input](#inputs.iris_data)
    [sub-analysis output](#preprocessing.outputs.features)
    [sub-analysis decision](#preprocessing.decisions.scaling)
    [sub-analysis](#analyses.preprocessing)

    References are interpreted relative to the hosting analysis. Use '../' prefix to escape to parent scope, as with
    decision 'from' (e.g. [see parent](#../decisions.method)).
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Narrative"]
    class_class_curie: ClassVar[str] = "astra:Narrative"
    class_name: ClassVar[str] = "Narrative"
    class_model_uri: ClassVar[URIRef] = ASTRA.Narrative

    summary: Optional[str] = None
    findings: Optional[str] = None
    methods: Optional[str] = None
    inputs: Optional[str] = None
    outputs: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.summary is not None and not isinstance(self.summary, str):
            self.summary = str(self.summary)

        if self.findings is not None and not isinstance(self.findings, str):
            self.findings = str(self.findings)

        if self.methods is not None and not isinstance(self.methods, str):
            self.methods = str(self.methods)

        if self.inputs is not None and not isinstance(self.inputs, str):
            self.inputs = str(self.inputs)

        if self.outputs is not None and not isinstance(self.outputs, str):
            self.outputs = str(self.outputs)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Resources(YAMLRoot):
    """
    Compute resource requirements for a recipe. Field names follow Snakemake's `resources:` conventions so that
    cluster executors (SLURM, Kubernetes, etc.) can consume them without remapping.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Resources"]
    class_class_curie: ClassVar[str] = "astra:Resources"
    class_name: ClassVar[str] = "Resources"
    class_model_uri: ClassVar[URIRef] = ASTRA.Resources

    mem_mb: Optional[int] = None
    runtime: Optional[int] = None
    disk_mb: Optional[int] = None
    gpus: Optional[int] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.mem_mb is not None and not isinstance(self.mem_mb, int):
            self.mem_mb = int(self.mem_mb)

        if self.runtime is not None and not isinstance(self.runtime, int):
            self.runtime = int(self.runtime)

        if self.disk_mb is not None and not isinstance(self.disk_mb, int):
            self.disk_mb = int(self.disk_mb)

        if self.gpus is not None and not isinstance(self.gpus, int):
            self.gpus = int(self.gpus)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Recipe(YAMLRoot):
    """
    A build rule that produces an output. Recipes follow Snakemake's rule grammar: `shell` or `script` defines the
    work, `input` lists upstream output IDs, `params` carries static parameters, and `threads` / `resources` /
    `container` / `conda` / `log` describe the execution context.
    Decision-driven parameterization is declared on the parent Output via `decisions:`, not here. The recipe describes
    how to build the output; the output declares what it depends on.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Recipe"]
    class_class_curie: ClassVar[str] = "astra:Recipe"
    class_name: ClassVar[str] = "Recipe"
    class_model_uri: ClassVar[URIRef] = ASTRA.Recipe

    shell: Optional[str] = None
    script: Optional[str] = None
    input: Optional[Union[str, list[str]]] = empty_list()
    params: Optional[Union[dict[Union[str, KeyValuePairKey], Union[dict, KeyValuePair]], list[Union[dict, KeyValuePair]]]] = empty_dict()
    threads: Optional[int] = None
    resources: Optional[Union[dict, Resources]] = None
    container: Optional[str] = None
    conda: Optional[str] = None
    log: Optional[str] = None

    def __post_init__(self, *_: str, **kwargs: Any):
        if self.shell is not None and not isinstance(self.shell, str):
            self.shell = str(self.shell)

        if self.script is not None and not isinstance(self.script, str):
            self.script = str(self.script)

        if not isinstance(self.input, list):
            self.input = [self.input] if self.input is not None else []
        self.input = [v if isinstance(v, str) else str(v) for v in self.input]

        self._normalize_inlined_as_dict(slot_name="params", slot_type=KeyValuePair, key_name="key", keyed=True)

        if self.threads is not None and not isinstance(self.threads, int):
            self.threads = int(self.threads)

        if self.resources is not None and not isinstance(self.resources, Resources):
            self.resources = Resources(**as_dict(self.resources))

        if self.container is not None and not isinstance(self.container, str):
            self.container = str(self.container)

        if self.conda is not None and not isinstance(self.conda, str):
            self.conda = str(self.conda)

        if self.log is not None and not isinstance(self.log, str):
            self.log = str(self.log)

        super().__post_init__(**kwargs)


@dataclass(repr=False)
class Input(YAMLRoot):
    """
    An input to the analysis. Two kinds: data (dataset/file/resource) or analysis (outputs from another ASTRA
    analysis). Sub-analysis inputs can use 'from' to reference a parent input or a sibling's output (e.g.,
    'sibling_id.output_id').
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Input"]
    class_class_curie: ClassVar[str] = "astra:Input"
    class_name: ClassVar[str] = "Input"
    class_model_uri: ClassVar[URIRef] = ASTRA.Input

    id: Union[str, InputId] = None
    type: Union[str, "InputType"] = None
    from_: Optional[str] = None
    label: Optional[str] = None
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

        if self.from_ is not None and not isinstance(self.from_, str):
            self.from_ = str(self.from_)

        if self.label is not None and not isinstance(self.label, str):
            self.label = str(self.label)

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
    An expected output from the analysis. Outputs can declare their provenance via 'from' to trace which sub-analysis
    produces them.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Output"]
    class_class_curie: ClassVar[str] = "astra:Output"
    class_name: ClassVar[str] = "Output"
    class_model_uri: ClassVar[URIRef] = ASTRA.Output

    id: Union[str, OutputId] = None
    type: Union[str, "OutputType"] = None
    from_: Optional[str] = None
    when: Optional[Union[str, list[str]]] = empty_list()
    label: Optional[str] = None
    description: Optional[str] = None
    decisions: Optional[Union[str, list[str]]] = empty_list()
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

        if self.from_ is not None and not isinstance(self.from_, str):
            self.from_ = str(self.from_)

        if not isinstance(self.when, list):
            self.when = [self.when] if self.when is not None else []
        self.when = [v if isinstance(v, str) else str(v) for v in self.when]

        if self.label is not None and not isinstance(self.label, str):
            self.label = str(self.label)

        if self.description is not None and not isinstance(self.description, str):
            self.description = str(self.description)

        if not isinstance(self.decisions, list):
            self.decisions = [self.decisions] if self.decisions is not None else []
        self.decisions = [v if isinstance(v, str) else str(v) for v in self.decisions]

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
    via 'from'.
    """
    _inherited_slots: ClassVar[list[str]] = []

    class_class_uri: ClassVar[URIRef] = ASTRA["Decision"]
    class_class_curie: ClassVar[str] = "astra:Decision"
    class_name: ClassVar[str] = "Decision"
    class_model_uri: ClassVar[URIRef] = ASTRA.Decision

    id: Union[str, DecisionId] = None
    from_: Optional[str] = None
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

        if self.from_ is not None and not isinstance(self.from_, str):
            self.from_ = str(self.from_)

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
    narrative: Optional[Union[dict, Narrative]] = None
    authors: Optional[Union[str, list[str]]] = empty_list()
    tags: Optional[Union[str, list[str]]] = empty_list()
    inputs: Optional[Union[dict[Union[str, InputId], Union[dict, Input]], list[Union[dict, Input]]]] = empty_dict()
    outputs: Optional[Union[dict[Union[str, OutputId], Union[dict, Output]], list[Union[dict, Output]]]] = empty_dict()
    decisions: Optional[Union[dict[Union[str, DecisionId], Union[dict, Decision]], list[Union[dict, Decision]]]] = empty_dict()
    prior_insights: Optional[Union[dict[Union[str, InsightId], Union[dict, "Insight"]], list[Union[dict, "Insight"]]]] = empty_dict()
    findings: Optional[Union[dict[Union[str, InsightId], Union[dict, "Insight"]], list[Union[dict, "Insight"]]]] = empty_dict()
    container: Optional[str] = None
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

        if self.narrative is not None and not isinstance(self.narrative, Narrative):
            self.narrative = Narrative(**as_dict(self.narrative))

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

        if self.path is not None and not isinstance(self.path, str):
            self.path = str(self.path)

        self._normalize_inlined_as_dict(slot_name="analyses", slot_type=Analysis, key_name="id", keyed=True)

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
    label: Optional[str] = None
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

        if self.label is not None and not isinstance(self.label, str):
            self.label = str(self.label)

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

        self._normalize_inlined_as_dict(slot_name="decisions", slot_type=DecisionSelection, key_name="decision_id", keyed=True)

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

        self._normalize_inlined_as_dict(slot_name="decisions", slot_type=DecisionSelection, key_name="decision_id", keyed=True)

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

slots.from_ = Slot(uri=ASTRA['from'], name="from", curie=ASTRA.curie('from'),
                   model_uri=ASTRA['from'], domain=None, range=Optional[str])

slots.when = Slot(uri=ASTRA.when, name="when", curie=ASTRA.curie('when'),
                   model_uri=ASTRA.when, domain=None, range=Optional[Union[str, list[str]]])

slots.keyValuePair__key = Slot(uri=ASTRA.key, name="keyValuePair__key", curie=ASTRA.curie('key'),
                   model_uri=ASTRA.keyValuePair__key, domain=None, range=URIRef)

slots.keyValuePair__value = Slot(uri=ASTRA.value, name="keyValuePair__value", curie=ASTRA.curie('value'),
                   model_uri=ASTRA.keyValuePair__value, domain=None, range=str)

slots.narrative__summary = Slot(uri=ASTRA.summary, name="narrative__summary", curie=ASTRA.curie('summary'),
                   model_uri=ASTRA.narrative__summary, domain=None, range=Optional[str])

slots.narrative__findings = Slot(uri=ASTRA.findings, name="narrative__findings", curie=ASTRA.curie('findings'),
                   model_uri=ASTRA.narrative__findings, domain=None, range=Optional[str])

slots.narrative__methods = Slot(uri=ASTRA.methods, name="narrative__methods", curie=ASTRA.curie('methods'),
                   model_uri=ASTRA.narrative__methods, domain=None, range=Optional[str])

slots.narrative__inputs = Slot(uri=ASTRA.inputs, name="narrative__inputs", curie=ASTRA.curie('inputs'),
                   model_uri=ASTRA.narrative__inputs, domain=None, range=Optional[str])

slots.narrative__outputs = Slot(uri=ASTRA.outputs, name="narrative__outputs", curie=ASTRA.curie('outputs'),
                   model_uri=ASTRA.narrative__outputs, domain=None, range=Optional[str])

slots.resources__mem_mb = Slot(uri=ASTRA.mem_mb, name="resources__mem_mb", curie=ASTRA.curie('mem_mb'),
                   model_uri=ASTRA.resources__mem_mb, domain=None, range=Optional[int])

slots.resources__runtime = Slot(uri=ASTRA.runtime, name="resources__runtime", curie=ASTRA.curie('runtime'),
                   model_uri=ASTRA.resources__runtime, domain=None, range=Optional[int])

slots.resources__disk_mb = Slot(uri=ASTRA.disk_mb, name="resources__disk_mb", curie=ASTRA.curie('disk_mb'),
                   model_uri=ASTRA.resources__disk_mb, domain=None, range=Optional[int])

slots.resources__gpus = Slot(uri=ASTRA.gpus, name="resources__gpus", curie=ASTRA.curie('gpus'),
                   model_uri=ASTRA.resources__gpus, domain=None, range=Optional[int])

slots.recipe__shell = Slot(uri=ASTRA.shell, name="recipe__shell", curie=ASTRA.curie('shell'),
                   model_uri=ASTRA.recipe__shell, domain=None, range=Optional[str])

slots.recipe__script = Slot(uri=ASTRA.script, name="recipe__script", curie=ASTRA.curie('script'),
                   model_uri=ASTRA.recipe__script, domain=None, range=Optional[str])

slots.recipe__input = Slot(uri=ASTRA.input, name="recipe__input", curie=ASTRA.curie('input'),
                   model_uri=ASTRA.recipe__input, domain=None, range=Optional[Union[str, list[str]]])

slots.recipe__params = Slot(uri=ASTRA.params, name="recipe__params", curie=ASTRA.curie('params'),
                   model_uri=ASTRA.recipe__params, domain=None, range=Optional[Union[dict[Union[str, KeyValuePairKey], Union[dict, KeyValuePair]], list[Union[dict, KeyValuePair]]]])

slots.recipe__threads = Slot(uri=ASTRA.threads, name="recipe__threads", curie=ASTRA.curie('threads'),
                   model_uri=ASTRA.recipe__threads, domain=None, range=Optional[int])

slots.recipe__resources = Slot(uri=ASTRA.resources, name="recipe__resources", curie=ASTRA.curie('resources'),
                   model_uri=ASTRA.recipe__resources, domain=None, range=Optional[Union[dict, Resources]])

slots.recipe__container = Slot(uri=ASTRA.container, name="recipe__container", curie=ASTRA.curie('container'),
                   model_uri=ASTRA.recipe__container, domain=None, range=Optional[str])

slots.recipe__conda = Slot(uri=ASTRA.conda, name="recipe__conda", curie=ASTRA.curie('conda'),
                   model_uri=ASTRA.recipe__conda, domain=None, range=Optional[str])

slots.recipe__log = Slot(uri=ASTRA.log, name="recipe__log", curie=ASTRA.curie('log'),
                   model_uri=ASTRA.recipe__log, domain=None, range=Optional[str])

slots.input__id = Slot(uri=ASTRA.id, name="input__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.input__id, domain=None, range=URIRef,
                   pattern=re.compile(r'^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$'))

slots.input__label = Slot(uri=ASTRA.label, name="input__label", curie=ASTRA.curie('label'),
                   model_uri=ASTRA.input__label, domain=None, range=Optional[str])

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
                   pattern=re.compile(r'^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$'))

slots.output__label = Slot(uri=ASTRA.label, name="output__label", curie=ASTRA.curie('label'),
                   model_uri=ASTRA.output__label, domain=None, range=Optional[str])

slots.output__type = Slot(uri=ASTRA.type, name="output__type", curie=ASTRA.curie('type'),
                   model_uri=ASTRA.output__type, domain=None, range=Union[str, "OutputType"])

slots.output__description = Slot(uri=ASTRA.description, name="output__description", curie=ASTRA.curie('description'),
                   model_uri=ASTRA.output__description, domain=None, range=Optional[str])

slots.output__decisions = Slot(uri=ASTRA.decisions, name="output__decisions", curie=ASTRA.curie('decisions'),
                   model_uri=ASTRA.output__decisions, domain=None, range=Optional[Union[str, list[str]]])

slots.output__recipe = Slot(uri=ASTRA.recipe, name="output__recipe", curie=ASTRA.curie('recipe'),
                   model_uri=ASTRA.output__recipe, domain=None, range=Optional[Union[dict, Recipe]])

slots.option__id = Slot(uri=ASTRA.id, name="option__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.option__id, domain=None, range=URIRef,
                   pattern=re.compile(r'^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$'))

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
                   model_uri=ASTRA.decision__id, domain=None, range=URIRef,
                   pattern=re.compile(r'^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$'))

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
                   model_uri=ASTRA.analysis__id, domain=None, range=URIRef,
                   pattern=re.compile(r'^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$'))

slots.analysis__version = Slot(uri=ASTRA.version, name="analysis__version", curie=ASTRA.curie('version'),
                   model_uri=ASTRA.analysis__version, domain=None, range=Optional[str],
                   pattern=re.compile(r'^\d+\.\d+(\.\d+)?$'))

slots.analysis__name = Slot(uri=ASTRA.name, name="analysis__name", curie=ASTRA.curie('name'),
                   model_uri=ASTRA.analysis__name, domain=None, range=Optional[str])

slots.analysis__narrative = Slot(uri=ASTRA.narrative, name="analysis__narrative", curie=ASTRA.curie('narrative'),
                   model_uri=ASTRA.analysis__narrative, domain=None, range=Optional[Union[dict, Narrative]])

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

slots.analysis__path = Slot(uri=ASTRA.path, name="analysis__path", curie=ASTRA.curie('path'),
                   model_uri=ASTRA.analysis__path, domain=None, range=Optional[str])

slots.analysis__analyses = Slot(uri=ASTRA.analyses, name="analysis__analyses", curie=ASTRA.curie('analyses'),
                   model_uri=ASTRA.analysis__analyses, domain=None, range=Optional[Union[dict[Union[str, AnalysisId], Union[dict, Analysis]], list[Union[dict, Analysis]]]])

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
                   model_uri=ASTRA.evidence__id, domain=None, range=URIRef,
                   pattern=re.compile(r'^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$'))

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
                   model_uri=ASTRA.insight__id, domain=None, range=URIRef,
                   pattern=re.compile(r'^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$'))

slots.insight__label = Slot(uri=ASTRA.label, name="insight__label", curie=ASTRA.curie('label'),
                   model_uri=ASTRA.insight__label, domain=None, range=Optional[str])

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

slots.decisionSelection__decision_id = Slot(uri=ASTRA.decision_id, name="decisionSelection__decision_id", curie=ASTRA.curie('decision_id'),
                   model_uri=ASTRA.decisionSelection__decision_id, domain=None, range=URIRef)

slots.decisionSelection__option_id = Slot(uri=ASTRA.option_id, name="decisionSelection__option_id", curie=ASTRA.curie('option_id'),
                   model_uri=ASTRA.decisionSelection__option_id, domain=None, range=str)

slots.universeNode__id = Slot(uri=ASTRA.id, name="universeNode__id", curie=ASTRA.curie('id'),
                   model_uri=ASTRA.universeNode__id, domain=None, range=URIRef,
                   pattern=re.compile(r'^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$'))

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

slots.Input_from = Slot(uri=ASTRA['from'], name="Input_from", curie=ASTRA.curie('from'),
                   model_uri=ASTRA.Input_from, domain=Input, range=Optional[str])

slots.Output_from = Slot(uri=ASTRA['from'], name="Output_from", curie=ASTRA.curie('from'),
                   model_uri=ASTRA.Output_from, domain=Output, range=Optional[str])

slots.Decision_from = Slot(uri=ASTRA['from'], name="Decision_from", curie=ASTRA.curie('from'),
                   model_uri=ASTRA.Decision_from, domain=Decision, range=Optional[str])
