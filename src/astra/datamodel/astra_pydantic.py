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


metamodel_version = "1.7.0"
version = "0.0.1"


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
     'description': 'Agentic Schema for Transparent Research Analysis.\n'
                    'A framework for defining hierarchical scientific analyses '
                    'with\n'
                    'decision points, evidence-backed insights, and universe '
                    'specifications.',
     'id': 'https://w3id.org/ASTRA/analysis',
     'imports': ['linkml:types', 'insight', 'universe'],
     'license': 'https://creativecommons.org/licenses/by/4.0/',
     'name': 'analysis',
     'prefixes': {'astra': {'prefix_prefix': 'astra',
                            'prefix_reference': 'https://w3id.org/ASTRA/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'}},
     'source_file': 'src/astra/schema/analysis.yaml',
     'title': 'ASTRA'} )

class InputType(str, Enum):
    """
    Type of analysis input
    """
    data = "data"
    """
    A dataset, file, or external resource
    """
    analysis = "analysis"
    """
    Outputs from another ASTRA analysis
    """


class OutputType(str, Enum):
    """
    Type of analysis output
    """
    metric = "metric"
    """
    A metric or measurement
    """
    figure = "figure"
    """
    A figure or visualization
    """
    table = "table"
    """
    A table of data
    """
    data = "data"
    """
    A data file or dataset
    """
    report = "report"
    """
    A report or document
    """



class TextQuoteSelector(ConfiguredBaseModel):
    """
    W3C TextQuoteSelector for locating text in a document. The authoritative anchor for verification.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'oa:TextQuoteSelector',
         'from_schema': 'https://w3id.org/ASTRA/insight'})

    exact: str = Field(default=..., description="""Exact quoted text (1-3 sentences)""", json_schema_extra = { "linkml_meta": {'domain_of': ['TextQuoteSelector']} })
    prefix: Optional[str] = Field(default=None, description="""~20-100 chars before for disambiguation""", json_schema_extra = { "linkml_meta": {'domain_of': ['TextQuoteSelector']} })
    suffix: Optional[str] = Field(default=None, description="""~20-100 chars after for disambiguation""", json_schema_extra = { "linkml_meta": {'domain_of': ['TextQuoteSelector']} })


class FragmentSelector(ConfiguredBaseModel):
    """
    W3C FragmentSelector for PDF locations. Conforms to RFC 3778/8118 for PDF fragments.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'oa:FragmentSelector',
         'from_schema': 'https://w3id.org/ASTRA/insight'})

    value: Optional[str] = Field(default=None, description="""Fragment value (e.g., 'page=6')""", json_schema_extra = { "linkml_meta": {'domain_of': ['FragmentSelector', 'KeyValuePair']} })
    page: Optional[int] = Field(default=None, description="""1-indexed page number""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['FragmentSelector']} })


class Evidence(ConfiguredBaseModel):
    """
    Evidence from a source with W3C-compliant selectors. Can reference literature (by DOI) or analysis artifacts (by output ID). Exactly one of doi or artifact must be set.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/insight'})

    id: str = Field(default=..., description="""Evidence identifier""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence',
                       'Insight',
                       'UniverseNode',
                       'Universe',
                       'Input',
                       'Output',
                       'Option',
                       'Decision',
                       'Analysis']} })
    doi: Optional[str] = Field(default=None, description="""DOI of the source paper (e.g., '10.48550/arXiv.1706.03762')""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence']} })
    artifact: Optional[str] = Field(default=None, description="""Output ID referencing a declared output in this analysis""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence']} })
    version: Optional[int] = Field(default=None, description="""Paper version for arXiv papers (version matters for reproducibility)""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence', 'Analysis']} })
    snapshot: Optional[str] = Field(default=None, description="""Path to immutable copy of the artifact""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence']} })
    source_commit: Optional[str] = Field(default=None, description="""Git commit that produced the original artifact""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence']} })
    quote: Optional[TextQuoteSelector] = Field(default=None, description="""Text quote anchor""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence']} })
    location: Optional[FragmentSelector] = Field(default=None, description="""Location hint (page number for PDFs/reports)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence']} })

    @field_validator('doi')
    def pattern_doi(cls, v):
        pattern=re.compile(r"^10\.\d{4,}/.*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid doi format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid doi format: {v}"
            raise ValueError(err_msg)
        return v


class Insight(ConfiguredBaseModel):
    """
    A unit of scientific knowledge backed by evidence. Used for both prior_insights (informing decisions) and findings (conclusions from the analysis).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/insight'})

    id: str = Field(default=..., description="""Unique identifier""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence',
                       'Insight',
                       'UniverseNode',
                       'Universe',
                       'Input',
                       'Output',
                       'Option',
                       'Decision',
                       'Analysis']} })
    claim: str = Field(default=..., description="""What we learned (1-2 sentences)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight']} })
    created_at: datetime  = Field(default=..., description="""Creation timestamp (ISO 8601)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight']} })
    evidence: list[Evidence] = Field(default=..., description="""Supporting evidence (papers or analysis artifacts)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight']} })
    derived: Optional[bool] = Field(default=None, description="""True if synthesized/inferred from multiple sources""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight']} })
    scope: Optional[str] = Field(default=None, description="""Applicability conditions""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight']} })
    tags: Optional[list[str]] = Field(default=None, description="""Categorization tags""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Decision', 'Analysis']} })
    notes: Optional[str] = Field(default=None, description="""Reasoning notes""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight']} })


class InsightCollection(ConfiguredBaseModel):
    """
    Collection of insights, usable standalone or embedded in an analysis
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/insight'})

    insights: Optional[dict[str, Insight]] = Field(default=None, description="""Map of insight IDs to insights""", json_schema_extra = { "linkml_meta": {'domain_of': ['InsightCollection', 'Option']} })


class DecisionSelection(ConfiguredBaseModel):
    """
    A mapping from a decision ID to the selected option ID
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/universe'})

    decision_id: str = Field(default=..., description="""ID of the decision""", json_schema_extra = { "linkml_meta": {'domain_of': ['DecisionSelection']} })
    option_id: str = Field(default=..., description="""ID of the selected option""", json_schema_extra = { "linkml_meta": {'domain_of': ['DecisionSelection']} })


class UniverseNode(ConfiguredBaseModel):
    """
    A universe node mirroring the analysis tree structure. Represents decision selections at a specific sub-analysis node.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/universe'})

    id: str = Field(default=..., description="""Node identifier (the sub-analysis key)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence',
                       'Insight',
                       'UniverseNode',
                       'Universe',
                       'Input',
                       'Output',
                       'Option',
                       'Decision',
                       'Analysis']} })
    universe: Optional[str] = Field(default=None, description="""Name of a universe in the sub-analysis's universes/ directory. Alternative to inline decisions.""", json_schema_extra = { "linkml_meta": {'domain_of': ['UniverseNode']} })
    decisions: Optional[dict[str, Union[str, DecisionSelection]]] = Field(default=None, description="""Decision selections (decision_id to option_id)""", json_schema_extra = { "linkml_meta": {'domain_of': ['UniverseNode', 'Universe', 'Analysis']} })
    analyses: Optional[dict[str, UniverseNode]] = Field(default=None, description="""Sub-analysis universe selections""", json_schema_extra = { "linkml_meta": {'domain_of': ['UniverseNode', 'Universe', 'Analysis']} })


class Universe(ConfiguredBaseModel):
    """
    A universe specification - a complete set of decisions across the entire analysis tree.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/universe'})

    id: str = Field(default=..., description="""Unique identifier for the universe""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence',
                       'Insight',
                       'UniverseNode',
                       'Universe',
                       'Input',
                       'Output',
                       'Option',
                       'Decision',
                       'Analysis']} })
    description: Optional[str] = Field(default=None, description="""What this universe represents""", json_schema_extra = { "linkml_meta": {'domain_of': ['Universe', 'Input', 'Output', 'Option', 'Analysis']} })
    decisions: Optional[dict[str, Union[str, DecisionSelection]]] = Field(default=None, description="""Root-level decision selections""", json_schema_extra = { "linkml_meta": {'domain_of': ['UniverseNode', 'Universe', 'Analysis']} })
    analyses: Optional[dict[str, UniverseNode]] = Field(default=None, description="""Sub-analysis universe selections""", json_schema_extra = { "linkml_meta": {'domain_of': ['UniverseNode', 'Universe', 'Analysis']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^[a-z][a-z0-9_-]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


class KeyValuePair(ConfiguredBaseModel):
    """
    A key-value string pair
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/analysis'})

    key: str = Field(default=..., description="""The key""", json_schema_extra = { "linkml_meta": {'domain_of': ['KeyValuePair']} })
    value: str = Field(default=..., description="""The value""", json_schema_extra = { "linkml_meta": {'domain_of': ['FragmentSelector', 'KeyValuePair']} })


class Resources(ConfiguredBaseModel):
    """
    Compute resource requirements for a recipe
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/analysis'})

    cpus: Optional[int] = Field(default=None, description="""Number of CPUs""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Resources']} })
    memory: Optional[str] = Field(default=None, description="""Memory requirement (e.g., '8GB', '512MB')""", json_schema_extra = { "linkml_meta": {'domain_of': ['Resources']} })
    gpus: Optional[int] = Field(default=None, description="""Number of GPUs""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Resources']} })
    time_limit: Optional[str] = Field(default=None, description="""Maximum wall time (e.g., '2h', '30m')""", json_schema_extra = { "linkml_meta": {'domain_of': ['Resources']} })


class ContainerBuildSpec(ConfiguredBaseModel):
    """
    Specification for building a container image from a Containerfile
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/analysis'})

    build: str = Field(default=..., description="""Path to Containerfile relative to project root""", json_schema_extra = { "linkml_meta": {'domain_of': ['ContainerBuildSpec']} })
    context: Optional[str] = Field(default=None, description="""Build context directory""", json_schema_extra = { "linkml_meta": {'domain_of': ['ContainerBuildSpec']} })
    args: Optional[list[KeyValuePair]] = Field(default=None, description="""Docker build arguments as key-value pairs""", json_schema_extra = { "linkml_meta": {'domain_of': ['ContainerBuildSpec']} })


class Recipe(ConfiguredBaseModel):
    """
    A build rule that produces an output. Recipes are the execution contract: run this command to produce the parent output.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/analysis'})

    command: str = Field(default=..., description="""Command to execute (e.g., 'python src/train.py')""", json_schema_extra = { "linkml_meta": {'domain_of': ['Recipe']} })
    inputs: Optional[list[str]] = Field(default=None, description="""Output IDs that must be materialized before this recipe runs""", json_schema_extra = { "linkml_meta": {'domain_of': ['Recipe', 'Analysis']} })
    container: Optional[str] = Field(default=None, description="""Container image name (pre-built image string)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Recipe', 'Analysis']} })
    container_build: Optional[ContainerBuildSpec] = Field(default=None, description="""Container image build specification (alternative to container string)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Recipe', 'Analysis']} })
    resources: Optional[Resources] = Field(default=None, description="""Compute resource requirements""", json_schema_extra = { "linkml_meta": {'domain_of': ['Recipe']} })


class Input(ConfiguredBaseModel):
    """
    An input to the analysis. Two kinds: data (dataset/file/resource) or analysis (outputs from another ASTRA analysis). Sub-analysis inputs can use from_ref to reference a parent input or a sibling's output (e.g., 'sibling_id.output_id').
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/analysis',
         'slot_usage': {'from_ref': {'description': 'Reference to parent input or '
                                                    "sibling output (e.g., 'input_id' "
                                                    "or 'sibling.output_id').",
                                     'name': 'from_ref'}}})

    from_ref: Optional[str] = Field(default=None, description="""Reference to parent input or sibling output (e.g., 'input_id' or 'sibling.output_id').""", json_schema_extra = { "linkml_meta": {'aliases': ['from'], 'domain_of': ['Input', 'Output', 'Decision']} })
    id: str = Field(default=..., description="""Unique identifier for the input""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence',
                       'Insight',
                       'UniverseNode',
                       'Universe',
                       'Input',
                       'Output',
                       'Option',
                       'Decision',
                       'Analysis']} })
    type: InputType = Field(default=..., description="""Type of input""", json_schema_extra = { "linkml_meta": {'domain_of': ['Input', 'Output']} })
    description: Optional[str] = Field(default=None, description="""Description of the input""", json_schema_extra = { "linkml_meta": {'domain_of': ['Universe', 'Input', 'Output', 'Option', 'Analysis']} })
    source: Optional[str] = Field(default=None, description="""URI or path to the data source""", json_schema_extra = { "linkml_meta": {'domain_of': ['Input']} })
    ref: Optional[str] = Field(default=None, description="""Reference to another ASTRA analysis""", json_schema_extra = { "linkml_meta": {'domain_of': ['Input']} })
    ref_version: Optional[str] = Field(default=None, description="""Version of the referenced analysis""", json_schema_extra = { "linkml_meta": {'domain_of': ['Input']} })
    use_outputs: Optional[list[str]] = Field(default=None, description="""Specific outputs to use from referenced analysis""", json_schema_extra = { "linkml_meta": {'domain_of': ['Input']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^[a-z][a-z0-9_]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


class Output(ConfiguredBaseModel):
    """
    An expected output from the analysis. Outputs can declare their provenance via from_ref to trace which sub-analysis produces them.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/analysis',
         'slot_usage': {'from_ref': {'description': 'Sub-analysis output that produces '
                                                    'this (e.g., '
                                                    "'sub_analysis.output_id').",
                                     'name': 'from_ref'}}})

    from_ref: Optional[str] = Field(default=None, description="""Sub-analysis output that produces this (e.g., 'sub_analysis.output_id').""", json_schema_extra = { "linkml_meta": {'aliases': ['from'], 'domain_of': ['Input', 'Output', 'Decision']} })
    when: Optional[list[str]] = Field(default=None, description="""Conditions for when this element is active. Format: 'decision_id.option_id' or '~decision_id.option_id'. Multiple conditions are AND'd together.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Output', 'Decision']} })
    id: str = Field(default=..., description="""Unique identifier for the output""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence',
                       'Insight',
                       'UniverseNode',
                       'Universe',
                       'Input',
                       'Output',
                       'Option',
                       'Decision',
                       'Analysis']} })
    type: OutputType = Field(default=..., description="""Type of output""", json_schema_extra = { "linkml_meta": {'domain_of': ['Input', 'Output']} })
    description: Optional[str] = Field(default=None, description="""Description of the output""", json_schema_extra = { "linkml_meta": {'domain_of': ['Universe', 'Input', 'Output', 'Option', 'Analysis']} })
    recipe: Optional[Recipe] = Field(default=None, description="""How to produce this output""", json_schema_extra = { "linkml_meta": {'domain_of': ['Output']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^[a-z][a-z0-9_]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


class Option(ConfiguredBaseModel):
    """
    An option for a decision point
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/analysis'})

    id: str = Field(default=..., description="""Option identifier (the key in the options map)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence',
                       'Insight',
                       'UniverseNode',
                       'Universe',
                       'Input',
                       'Output',
                       'Option',
                       'Decision',
                       'Analysis']} })
    label: str = Field(default=..., description="""Human-readable name for the option""", json_schema_extra = { "linkml_meta": {'domain_of': ['Option', 'Decision']} })
    description: Optional[str] = Field(default=None, description="""Detailed description of the option""", json_schema_extra = { "linkml_meta": {'domain_of': ['Universe', 'Input', 'Output', 'Option', 'Analysis']} })
    insights: Optional[list[str]] = Field(default=None, description="""Insight IDs supporting this option""", json_schema_extra = { "linkml_meta": {'domain_of': ['InsightCollection', 'Option']} })
    incompatible_with: Optional[list[str]] = Field(default=None, description="""Decision.option pairs that cannot be selected together""", json_schema_extra = { "linkml_meta": {'domain_of': ['Option']} })
    requires: Optional[list[str]] = Field(default=None, description="""Decision.option pairs that must also be selected""", json_schema_extra = { "linkml_meta": {'domain_of': ['Option']} })
    excluded: Optional[bool] = Field(default=None, description="""Whether this option was considered and rejected""", json_schema_extra = { "linkml_meta": {'domain_of': ['Option']} })
    excluded_reason: Optional[str] = Field(default=None, description="""Why this option was excluded""", json_schema_extra = { "linkml_meta": {'domain_of': ['Option']} })


class Decision(ConfiguredBaseModel):
    """
    A decision point in the analysis. Can be locally defined (with label, options) or a reference to a parent decision via from_ref.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/analysis',
         'slot_usage': {'from_ref': {'description': 'Reference to a parent decision '
                                                    "using '../' prefix (e.g., "
                                                    "'../z_min'). When set, this is a "
                                                    'pure reference and must not have '
                                                    'label, options, or default.',
                                     'name': 'from_ref'}}})

    from_ref: Optional[str] = Field(default=None, description="""Reference to a parent decision using '../' prefix (e.g., '../z_min'). When set, this is a pure reference and must not have label, options, or default.""", json_schema_extra = { "linkml_meta": {'aliases': ['from'], 'domain_of': ['Input', 'Output', 'Decision']} })
    when: Optional[list[str]] = Field(default=None, description="""Conditions for when this element is active. Format: 'decision_id.option_id' or '~decision_id.option_id'. Multiple conditions are AND'd together.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Output', 'Decision']} })
    id: str = Field(default=..., description="""Decision identifier (the key in the decisions map)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence',
                       'Insight',
                       'UniverseNode',
                       'Universe',
                       'Input',
                       'Output',
                       'Option',
                       'Decision',
                       'Analysis']} })
    label: Optional[str] = Field(default=None, description="""Human-readable name for the decision""", json_schema_extra = { "linkml_meta": {'domain_of': ['Option', 'Decision']} })
    rationale: Optional[str] = Field(default=None, description="""Why this decision exists""", json_schema_extra = { "linkml_meta": {'domain_of': ['Decision']} })
    tags: Optional[list[str]] = Field(default=None, description="""Tags for grouping and categorizing""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Decision', 'Analysis']} })
    default: Optional[str] = Field(default=None, description="""Default option ID for baseline universes""", json_schema_extra = { "linkml_meta": {'domain_of': ['Decision']} })
    options: Optional[dict[str, Option]] = Field(default=None, description="""Map of option IDs to option specifications""", json_schema_extra = { "linkml_meta": {'domain_of': ['Decision']} })


class Analysis(ConfiguredBaseModel):
    """
    A self-similar analysis specification. Every level has the same structure: metadata, inputs, outputs, decisions, insights, and optional sub-analyses. A sub-analysis extracted to its own file is a valid Analysis on its own.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/analysis', 'tree_root': True})

    id: str = Field(default=..., description="""Analysis identifier (used as key when nested as a sub-analysis)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence',
                       'Insight',
                       'UniverseNode',
                       'Universe',
                       'Input',
                       'Output',
                       'Option',
                       'Decision',
                       'Analysis']} })
    version: Optional[str] = Field(default=None, description="""ASTRA specification version""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence', 'Analysis']} })
    name: Optional[str] = Field(default=None, description="""Human-readable name for the analysis""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })
    description: Optional[str] = Field(default=None, description="""Detailed description of this analysis""", json_schema_extra = { "linkml_meta": {'domain_of': ['Universe', 'Input', 'Output', 'Option', 'Analysis']} })
    authors: Optional[list[str]] = Field(default=None, description="""List of authors""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })
    tags: Optional[list[str]] = Field(default=None, description="""Tags for categorization""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Decision', 'Analysis']} })
    inputs: Optional[list[Input]] = Field(default=None, description="""Inputs for this analysis""", json_schema_extra = { "linkml_meta": {'domain_of': ['Recipe', 'Analysis']} })
    outputs: Optional[list[Output]] = Field(default=None, description="""Expected outputs from this analysis""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })
    decisions: Optional[dict[str, Decision]] = Field(default=None, description="""Decision points in this analysis (keyed by decision ID)""", json_schema_extra = { "linkml_meta": {'domain_of': ['UniverseNode', 'Universe', 'Analysis']} })
    prior_insights: Optional[dict[str, Insight]] = Field(default=None, description="""Prior insights that inform decisions (keyed by insight ID)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })
    findings: Optional[dict[str, Insight]] = Field(default=None, description="""Findings and conclusions from outputs (keyed by insight ID)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })
    container: Optional[str] = Field(default=None, description="""Default container image name for recipes in this node""", json_schema_extra = { "linkml_meta": {'domain_of': ['Recipe', 'Analysis']} })
    container_build: Optional[ContainerBuildSpec] = Field(default=None, description="""Default container build specification for recipes in this node""", json_schema_extra = { "linkml_meta": {'domain_of': ['Recipe', 'Analysis']} })
    path: Optional[str] = Field(default=None, description="""Path to a directory containing its own astra.yaml. Mutually exclusive with inline content fields (inputs, outputs, decisions, etc.).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })
    analyses: Optional[dict[str, Analysis]] = Field(default=None, description="""Nested sub-analyses (keyed by analysis ID)""", json_schema_extra = { "linkml_meta": {'domain_of': ['UniverseNode', 'Universe', 'Analysis']} })

    @field_validator('version')
    def pattern_version(cls, v):
        pattern=re.compile(r"^\d+\.\d+(\.\d+)?$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid version format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid version format: {v}"
            raise ValueError(err_msg)
        return v


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
TextQuoteSelector.model_rebuild()
FragmentSelector.model_rebuild()
Evidence.model_rebuild()
Insight.model_rebuild()
InsightCollection.model_rebuild()
DecisionSelection.model_rebuild()
UniverseNode.model_rebuild()
Universe.model_rebuild()
KeyValuePair.model_rebuild()
Resources.model_rebuild()
ContainerBuildSpec.model_rebuild()
Recipe.model_rebuild()
Input.model_rebuild()
Output.model_rebuild()
Option.model_rebuild()
Decision.model_rebuild()
Analysis.model_rebuild()
