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
version = "0.0.8"


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
     'source_file': 'analysis.yaml',
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

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v

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
    label: Optional[str] = Field(default=None, description="""Short human-readable name for compact rendering (margin glyphs, breadcrumbs, card titles). Optional; tooling falls back to id when absent.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Input', 'Output', 'Option', 'Decision']} })
    claim: str = Field(default=..., description="""What we learned (1-2 sentences)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight']} })
    created_at: datetime  = Field(default=..., description="""Creation timestamp (ISO 8601)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight']} })
    evidence: list[Evidence] = Field(default=..., description="""Supporting evidence (papers or analysis artifacts)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight']} })
    derived: Optional[bool] = Field(default=None, description="""True if synthesized/inferred from multiple sources""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight']} })
    scope: Optional[str] = Field(default=None, description="""Applicability conditions""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight']} })
    tags: Optional[list[str]] = Field(default=None, description="""Categorization tags""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Decision', 'Analysis']} })
    notes: Optional[str] = Field(default=None, description="""Reasoning notes""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


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
    decisions: Optional[dict[str, Union[str, DecisionSelection]]] = Field(default=None, description="""Decision selections (decision_id to option_id)""", json_schema_extra = { "linkml_meta": {'domain_of': ['UniverseNode', 'Universe', 'Output', 'Analysis']} })
    analyses: Optional[dict[str, UniverseNode]] = Field(default=None, description="""Sub-analysis universe selections""", json_schema_extra = { "linkml_meta": {'domain_of': ['UniverseNode', 'Universe', 'Analysis']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


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
    description: Optional[str] = Field(default=None, description="""What this universe represents""", json_schema_extra = { "linkml_meta": {'domain_of': ['Universe', 'Input', 'Output', 'Option']} })
    decisions: Optional[dict[str, Union[str, DecisionSelection]]] = Field(default=None, description="""Root-level decision selections""", json_schema_extra = { "linkml_meta": {'domain_of': ['UniverseNode', 'Universe', 'Output', 'Analysis']} })
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


class Narrative(ConfiguredBaseModel):
    """
    Structured prose describing an analysis, organized into five sections: summary, findings, methods, inputs, and outputs. All sections are schema-optional, but ``astra validate`` applies a conditional requirement: a section must hold non-empty prose when the corresponding structured data exists on the Analysis node.
    - ``findings`` required when Analysis.findings has entries. - ``methods`` required when Analysis.decisions or
      Analysis.analyses has entries.
    - ``inputs`` required when Analysis.inputs has entries. - ``outputs`` required when Analysis.outputs has entries. - ``summary`` is always optional — no structured counterpart.
    Authors narrate what they declare; stub analyses with only a summary stay clean.
    Section content is Markdown. Internal references to other elements of the analysis use anchor links of the form ``[text](#path.to.element)``. References may appear in any section — coverage is resolved across the whole narrative, not per-section — so an author is free to cite a finding from the summary, or an input from the methods section.
    Anchor grammar is tree-path-first, matching the rest of ASTRA's reference syntax (the `from:` path grammar with `../` prefixes for upward escape and `name.subname` for descent). Sub-analyses are traversed before the category:

      [scaling decision](#decisions.scaling)
      [scaling option](#decisions.scaling.options.standard)
      [finding](#findings.best_model)
      [prior insight](#prior_insights.compute_scaling)
      [input](#inputs.iris_data)
      [sub-analysis output](#preprocessing.outputs.features)
      [sub-analysis decision](#preprocessing.decisions.scaling)
      [sub-analysis](#analyses.preprocessing)

    References are interpreted relative to the hosting analysis. Use '../' prefix to escape to parent scope, as with decision 'from' (e.g. [see parent](#../decisions.method)).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/analysis'})

    summary: Optional[str] = Field(default=None, description="""High-level overview of the analysis — its question, scope, and a brief orientation for readers.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Narrative']} })
    findings: Optional[str] = Field(default=None, description="""Narrative discussion of the analysis's findings. Individual findings live under Analysis.findings as structured Insight objects; this section is the prose that frames them.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Narrative', 'Analysis']} })
    methods: Optional[str] = Field(default=None, description="""Narrative discussion of the methodology, including decision points and any sub-analyses. Structured decisions and nested analyses live under Analysis.decisions and Analysis.analyses; this section frames them.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Narrative']} })
    inputs: Optional[str] = Field(default=None, description="""Narrative discussion of the analysis's inputs. Individual inputs live under Analysis.inputs as structured objects; this section frames them.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Narrative', 'Output', 'Analysis']} })
    outputs: Optional[str] = Field(default=None, description="""Narrative discussion of the expected outputs. Individual outputs live under Analysis.outputs as structured objects; this section frames them.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Narrative', 'Analysis']} })


class Resources(ConfiguredBaseModel):
    """
    Compute resource requirements for a recipe. Values follow cloud-native conventions (string-with-units for sized quantities) so cluster executors can consume them directly.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/analysis'})

    cpus: Optional[float] = Field(default=None, description="""CPU cores requested. Fractional values are allowed (e.g., 0.5) for runners that support CPU shares.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Resources']} })
    memory: Optional[str] = Field(default=None, description="""Memory requirement as a string with units (e.g., '16Gi', '512Mi', '8GB').""", json_schema_extra = { "linkml_meta": {'domain_of': ['Resources']} })
    time_limit: Optional[str] = Field(default=None, description="""Maximum wall time as a duration string (e.g., '2h', '30m', '1h30m').""", json_schema_extra = { "linkml_meta": {'domain_of': ['Resources']} })
    disk: Optional[str] = Field(default=None, description="""Disk requirement as a string with units (e.g., '10Gi', '500Mi').""", json_schema_extra = { "linkml_meta": {'domain_of': ['Resources']} })
    gpus: Optional[int] = Field(default=None, description="""Number of GPUs""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Resources']} })


class Recipe(ConfiguredBaseModel):
    """
    A build rule that produces an output. A recipe is pure *how*: a `command` to invoke and the execution context (`resources`, `container`).
    Recipes do not declare what the output depends on. Provenance — upstream inputs, decision-driven parameterization, and activation conditions — is declared on the parent Output (`inputs`, `decisions`, `when`). Runners surface the resolved input map and active decision values to the recipe via `{...}` template substitution (see `command`).
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/analysis'})

    command: Optional[str] = Field(default=None, description="""POSIX shell command to execute (e.g., 'python src/train.py', 'Rscript analysis.R', 'julia model.jl'). Any executable invocation is fine.
The command is a template. Runners substitute these placeholders before invoking it:

  {inputs.<id>}     -- path to the named upstream input
                       (must be declared in Output.inputs)
  {inputs}          -- space-separated paths to all declared
                       inputs, in declaration order
  {decisions.<id>}  -- active option ID for the named
                       decision in the current universe
                       (must be declared in Output.decisions)
  {output}          -- path the artifact will be written to

Use {{ and }} to emit literal '{' and '}'. Every placeholder must resolve to a declared item; the validator rejects unresolved or undeclared references.
Static constants belong inline in the command (e.g., '--max-iter 1000'); there is no separate `params` channel because varying values are decisions and constants are just command text.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Recipe']} })
    resources: Optional[Resources] = Field(default=None, description="""Compute resource requirements (cpus, memory, time_limit, …)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Recipe']} })
    container: Optional[str] = Field(default=None, description="""Container image name or path to a Containerfile. Image names (e.g., 'python:3.9', 'ghcr.io/org/img:latest') are pulled as pre-built images; file paths (e.g., 'Containerfile', 'containers/Dockerfile') are built from source.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Recipe', 'Analysis']} })


class Input(ConfiguredBaseModel):
    """
    An input to the analysis. Two kinds: data (dataset/file/resource) or analysis (outputs from another ASTRA analysis).
    Sub-analysis inputs may alias an upstream artifact via `from`, using the unified path grammar:

      from: ../id              -- a parent input
      from: ../../id           -- a grandparent input
      from: ../sibling.out_id  -- a sibling sub-analysis's output

    An aliased Input is a pure pointer: only `id` and `from` are allowed, with all other fields inherited from the source.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/analysis',
         'rules': [{'postconditions': {'slot_conditions': {'type': {'name': 'type',
                                                                    'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_type'},
                   {'postconditions': {'slot_conditions': {'label': {'name': 'label',
                                                                     'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_label'},
                   {'postconditions': {'slot_conditions': {'description': {'name': 'description',
                                                                           'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_description'},
                   {'postconditions': {'slot_conditions': {'source': {'name': 'source',
                                                                      'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_source'},
                   {'postconditions': {'slot_conditions': {'ref': {'name': 'ref',
                                                                   'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_ref'},
                   {'postconditions': {'slot_conditions': {'ref_version': {'name': 'ref_version',
                                                                           'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_ref_version'},
                   {'postconditions': {'slot_conditions': {'use_outputs': {'name': 'use_outputs',
                                                                           'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_use_outputs'},
                   {'description': 'A non-aliased Input must declare its type.',
                    'postconditions': {'slot_conditions': {'type': {'name': 'type',
                                                                    'required': True}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'ABSENT'}}},
                    'title': 'type_required_when_not_aliased'}],
         'slot_usage': {'from': {'description': 'Path to the source: `../id` (ancestor '
                                                'input), `../../id` (further '
                                                'ancestor), or `../scope.out_id` '
                                                "(sibling sub's output). Reaching down "
                                                'into own children is not allowed — '
                                                'consume those via Output re-export '
                                                'instead.',
                                 'name': 'from',
                                 'pattern': '^(\\.\\./)+[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)*$'}}})

    from_: Optional[str] = Field(default=None, alias="from", description="""Path to the source: `../id` (ancestor input), `../../id` (further ancestor), or `../scope.out_id` (sibling sub's output). Reaching down into own children is not allowed — consume those via Output re-export instead.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Input', 'Output', 'Decision']} })
    id: str = Field(default=..., description="""Unique identifier for the input""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence',
                       'Insight',
                       'UniverseNode',
                       'Universe',
                       'Input',
                       'Output',
                       'Option',
                       'Decision',
                       'Analysis']} })
    label: Optional[str] = Field(default=None, description="""Short human-readable name for compact rendering (margin glyphs, breadcrumbs, card titles). Optional; tooling falls back to id when absent.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Input', 'Output', 'Option', 'Decision']} })
    type: Optional[InputType] = Field(default=None, description="""Type of input. Required when `from` is unset; forbidden when `from` is set (inherited from the source).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Input', 'Output']} })
    description: Optional[str] = Field(default=None, description="""Description of the input""", json_schema_extra = { "linkml_meta": {'domain_of': ['Universe', 'Input', 'Output', 'Option']} })
    source: Optional[str] = Field(default=None, description="""URI or path to the data source""", json_schema_extra = { "linkml_meta": {'domain_of': ['Input']} })
    ref: Optional[str] = Field(default=None, description="""Reference to another ASTRA analysis""", json_schema_extra = { "linkml_meta": {'domain_of': ['Input']} })
    ref_version: Optional[str] = Field(default=None, description="""Version of the referenced analysis""", json_schema_extra = { "linkml_meta": {'domain_of': ['Input']} })
    use_outputs: Optional[list[str]] = Field(default=None, description="""Specific outputs to use from referenced analysis""", json_schema_extra = { "linkml_meta": {'domain_of': ['Input']} })

    @field_validator('from_')
    def pattern_from_(cls, v):
        pattern=re.compile(r"^(\.\./)+[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid from_ format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid from_ format: {v}"
            raise ValueError(err_msg)
        return v

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$")
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
    An expected output from the analysis. An Output is either produced locally (with `inputs`, `decisions`, `recipe`) or re-exported from a sub-analysis via `from`.
    Re-export grammar:

      from: child.out_id           -- own child sub's output
      from: child.grandchild.out_id -- descend into nested children

    A re-exported Output is a pure pointer: only `id`, `from`, and `when` are allowed; type/description/recipe are inherited.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/analysis',
         'rules': [{'postconditions': {'slot_conditions': {'type': {'name': 'type',
                                                                    'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_type'},
                   {'postconditions': {'slot_conditions': {'label': {'name': 'label',
                                                                     'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_label'},
                   {'postconditions': {'slot_conditions': {'description': {'name': 'description',
                                                                           'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_description'},
                   {'postconditions': {'slot_conditions': {'inputs': {'name': 'inputs',
                                                                      'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_inputs'},
                   {'postconditions': {'slot_conditions': {'decisions': {'name': 'decisions',
                                                                         'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_decisions'},
                   {'postconditions': {'slot_conditions': {'recipe': {'name': 'recipe',
                                                                      'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_recipe'},
                   {'description': 'A non-aliased Output must declare its type.',
                    'postconditions': {'slot_conditions': {'type': {'name': 'type',
                                                                    'required': True}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'ABSENT'}}},
                    'title': 'type_required_when_not_aliased'}],
         'slot_usage': {'from': {'description': 'Path to a descendant Output: '
                                                '`child.out_id` for an own child '
                                                "sub-analysis's output, or deeper "
                                                '(`child.grand.out_id`) to descend '
                                                'through nested children. Reaching '
                                                'upward is not allowed — Outputs flow '
                                                'up only via re-export at each layer.',
                                 'name': 'from',
                                 'pattern': '^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$'}}})

    from_: Optional[str] = Field(default=None, alias="from", description="""Path to a descendant Output: `child.out_id` for an own child sub-analysis's output, or deeper (`child.grand.out_id`) to descend through nested children. Reaching upward is not allowed — Outputs flow up only via re-export at each layer.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Input', 'Output', 'Decision']} })
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
    label: Optional[str] = Field(default=None, description="""Short human-readable name for compact rendering (margin glyphs, breadcrumbs, card titles). Optional; tooling falls back to id when absent.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Input', 'Output', 'Option', 'Decision']} })
    type: Optional[OutputType] = Field(default=None, description="""Type of output. Required when `from` is unset; forbidden when `from` is set (inherited from the source).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Input', 'Output']} })
    description: Optional[str] = Field(default=None, description="""Description of the output""", json_schema_extra = { "linkml_meta": {'domain_of': ['Universe', 'Input', 'Output', 'Option']} })
    inputs: Optional[list[str]] = Field(default=None, description="""IDs of upstream artifacts this output depends on. Each reference resolves to either an Input declared on the surrounding analysis (an external dataset/file/analysis) or a sibling Output (another artifact in scope). Runners materialize the upstream artifacts before invoking the recipe and surface the resolved input map to it (Snakemake-style `{input.x}` substitution, env vars, sidecar JSON — runner's choice).
References use plain artifact IDs and resolve through any `from:` chain in the surrounding analysis scope. An aliased Input (one with `from:`) is a valid local reference here; the runner walks the chain to the source.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Narrative', 'Output', 'Analysis']} })
    decisions: Optional[list[str]] = Field(default=None, description="""Decision IDs (in the surrounding scope) that parameterize this output. Declares the output's provenance contract: re-running with a different option for any listed decision must be expected to produce a different output.
Runners use this to (a) compute the per-output cache key, (b) determine the minimal universe set needed to materialize the output, and (c) deliver the active option values to the recipe (via flags, env vars, or a sidecar — runner's choice).
References use plain decision IDs and resolve through any `from:` chain in the surrounding analysis scope.""", json_schema_extra = { "linkml_meta": {'domain_of': ['UniverseNode', 'Universe', 'Output', 'Analysis']} })
    recipe: Optional[Recipe] = Field(default=None, description="""How to produce this output (pure *how*; dependencies live on the Output via `inputs`/`decisions`)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Output']} })

    @field_validator('from_')
    def pattern_from_(cls, v):
        pattern=re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid from_ format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid from_ format: {v}"
            raise ValueError(err_msg)
        return v

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$")
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
    label: str = Field(default=..., description="""Human-readable name for the option""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Input', 'Output', 'Option', 'Decision']} })
    description: Optional[str] = Field(default=None, description="""Detailed description of the option""", json_schema_extra = { "linkml_meta": {'domain_of': ['Universe', 'Input', 'Output', 'Option']} })
    insights: Optional[list[str]] = Field(default=None, description="""Insight IDs supporting this option""", json_schema_extra = { "linkml_meta": {'domain_of': ['InsightCollection', 'Option']} })
    incompatible_with: Optional[list[str]] = Field(default=None, description="""Decision.option pairs that cannot be selected together""", json_schema_extra = { "linkml_meta": {'domain_of': ['Option']} })
    requires: Optional[list[str]] = Field(default=None, description="""Decision.option pairs that must also be selected""", json_schema_extra = { "linkml_meta": {'domain_of': ['Option']} })
    excluded: Optional[bool] = Field(default=None, description="""Whether this option was considered and rejected""", json_schema_extra = { "linkml_meta": {'domain_of': ['Option']} })
    excluded_reason: Optional[str] = Field(default=None, description="""Why this option was excluded""", json_schema_extra = { "linkml_meta": {'domain_of': ['Option']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


class Decision(ConfiguredBaseModel):
    """
    A decision point in the analysis. Either locally defined (with label and options) or a pure reference to an ancestor decision via `from`.
    Reference grammar:

      from: ../id     -- a parent decision
      from: ../../id  -- a grandparent decision

    Decisions only flow downward through scopes; sibling-sub or child references are not legal. An aliased Decision is a pure pointer: only `id`, `from`, and `when` may be set.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/ASTRA/analysis',
         'rules': [{'postconditions': {'slot_conditions': {'label': {'name': 'label',
                                                                     'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_label'},
                   {'postconditions': {'slot_conditions': {'options': {'name': 'options',
                                                                       'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_options'},
                   {'postconditions': {'slot_conditions': {'default': {'name': 'default',
                                                                       'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_default'},
                   {'postconditions': {'slot_conditions': {'rationale': {'name': 'rationale',
                                                                         'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_rationale'},
                   {'postconditions': {'slot_conditions': {'tags': {'name': 'tags',
                                                                    'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'PRESENT'}}},
                    'title': 'from_alias_forbids_tags'},
                   {'description': 'A non-aliased Decision must declare its label and '
                                   'options.',
                    'postconditions': {'slot_conditions': {'label': {'name': 'label',
                                                                     'required': True},
                                                           'options': {'name': 'options',
                                                                       'required': True}}},
                    'preconditions': {'slot_conditions': {'from': {'name': 'from',
                                                                   'value_presence': 'ABSENT'}}},
                    'title': 'label_and_options_required_when_not_aliased'}],
         'slot_usage': {'from': {'description': 'Path to an ancestor decision: `../id` '
                                                'for a parent decision, `../../id` for '
                                                'a grandparent, and so on. Reaching '
                                                'laterally (`../sibling.id`) or '
                                                'downward (`child.id`) is not allowed '
                                                '— if siblings need a shared decision, '
                                                'lift it to the common ancestor and '
                                                'have each sub `from:` it.',
                                 'name': 'from',
                                 'pattern': '^(\\.\\./)+[a-z][a-z0-9_]*$'}}})

    from_: Optional[str] = Field(default=None, alias="from", description="""Path to an ancestor decision: `../id` for a parent decision, `../../id` for a grandparent, and so on. Reaching laterally (`../sibling.id`) or downward (`child.id`) is not allowed — if siblings need a shared decision, lift it to the common ancestor and have each sub `from:` it.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Input', 'Output', 'Decision']} })
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
    label: Optional[str] = Field(default=None, description="""Human-readable name for the decision""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Input', 'Output', 'Option', 'Decision']} })
    rationale: Optional[str] = Field(default=None, description="""Why this decision exists""", json_schema_extra = { "linkml_meta": {'domain_of': ['Decision']} })
    tags: Optional[list[str]] = Field(default=None, description="""Tags for grouping and categorizing""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Decision', 'Analysis']} })
    default: Optional[str] = Field(default=None, description="""Default option ID for baseline universes""", json_schema_extra = { "linkml_meta": {'domain_of': ['Decision']} })
    options: Optional[dict[str, Option]] = Field(default=None, description="""Map of option IDs to option specifications""", json_schema_extra = { "linkml_meta": {'domain_of': ['Decision']} })

    @field_validator('from_')
    def pattern_from_(cls, v):
        pattern=re.compile(r"^(\.\./)+[a-z][a-z0-9_]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid from_ format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid from_ format: {v}"
            raise ValueError(err_msg)
        return v

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v


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
    narrative: Optional[Narrative] = Field(default=None, description="""Structured prose describing this analysis, split into five sections (summary, findings, methods, inputs, outputs). See the Narrative class for section semantics and the tree-path anchor grammar used for internal cross-references.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })
    authors: Optional[list[str]] = Field(default=None, description="""List of authors""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })
    tags: Optional[list[str]] = Field(default=None, description="""Tags for categorization""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Decision', 'Analysis']} })
    inputs: Optional[list[Input]] = Field(default=None, description="""Inputs for this analysis""", json_schema_extra = { "linkml_meta": {'domain_of': ['Narrative', 'Output', 'Analysis']} })
    outputs: Optional[list[Output]] = Field(default=None, description="""Expected outputs from this analysis""", json_schema_extra = { "linkml_meta": {'domain_of': ['Narrative', 'Analysis']} })
    decisions: Optional[dict[str, Decision]] = Field(default=None, description="""Decision points in this analysis (keyed by decision ID)""", json_schema_extra = { "linkml_meta": {'domain_of': ['UniverseNode', 'Universe', 'Output', 'Analysis']} })
    prior_insights: Optional[dict[str, Insight]] = Field(default=None, description="""Prior insights that inform decisions (keyed by insight ID)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })
    findings: Optional[dict[str, Insight]] = Field(default=None, description="""Findings and conclusions from outputs (keyed by insight ID)""", json_schema_extra = { "linkml_meta": {'domain_of': ['Narrative', 'Analysis']} })
    container: Optional[str] = Field(default=None, description="""Default container for recipes in this node. Image names are pulled; file paths are built from source.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Recipe', 'Analysis']} })
    path: Optional[str] = Field(default=None, description="""Path to a directory containing its own astra.yaml. Mutually exclusive with inline content fields (inputs, outputs, decisions, etc.).""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })
    analyses: Optional[dict[str, Analysis]] = Field(default=None, description="""Nested sub-analyses (keyed by analysis ID)""", json_schema_extra = { "linkml_meta": {'domain_of': ['UniverseNode', 'Universe', 'Analysis']} })

    @field_validator('id')
    def pattern_id(cls, v):
        pattern=re.compile(r"^(?!(inputs|outputs|decisions|findings|prior_insights|analyses|options|content|narrative)$)[a-z][a-z0-9_]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.match(element):
                    err_msg = f"Invalid id format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.match(v):
            err_msg = f"Invalid id format: {v}"
            raise ValueError(err_msg)
        return v

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
Narrative.model_rebuild()
Resources.model_rebuild()
Recipe.model_rebuild()
Input.model_rebuild()
Output.model_rebuild()
Option.model_rebuild()
Decision.model_rebuild()
Analysis.model_rebuild()
