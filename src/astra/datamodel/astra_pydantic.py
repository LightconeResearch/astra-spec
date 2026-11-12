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
     'description': 'Agentic Schema for Transparent Research Analysis.\n'
                    'The analysis document, `astra.yaml`: the files an analysis '
                    'reads, the\n'
                    'artefacts it makes, and the decisions it makes along the way.',
     'id': 'https://w3id.org/astra/analysis',
     'imports': ['linkml:types', 'types', 'insight'],
     'license': 'https://creativecommons.org/licenses/by/4.0/',
     'name': 'analysis',
     'prefixes': {'astra': {'prefix_prefix': 'astra',
                            'prefix_reference': 'https://w3id.org/astra/'},
                  'linkml': {'prefix_prefix': 'linkml',
                             'prefix_reference': 'https://w3id.org/linkml/'}},
     'source_file': 'analysis.yaml',
     'title': 'ASTRA'} )

class OutputType(str, Enum):
    """
    The kind of artefact an output is.
    """
    metric = "metric"
    """
    A metric or measurement.
    """
    figure = "figure"
    """
    A figure or visualisation.
    """
    table = "table"
    """
    A table of data.
    """
    data = "data"
    """
    A data file or dataset.
    """
    report = "report"
    """
    A report or document.
    """



class TextQuoteSelector(ConfiguredBaseModel):
    """
    A passage of the cited work or output, quoted exactly, with the text just before and after it to tell it apart where the same words occur more than once.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'oa:TextQuoteSelector',
         'from_schema': 'https://w3id.org/astra/insight'})

    exact: str = Field(default=..., description="""The passage, exactly as the cited work or output writes it.""", json_schema_extra = { "linkml_meta": {'domain_of': ['TextQuoteSelector'], 'slot_uri': 'oa:exact'} })
    prefix: Optional[str] = Field(default=None, description="""The text that comes just before the passage.""", json_schema_extra = { "linkml_meta": {'domain_of': ['TextQuoteSelector'], 'slot_uri': 'oa:prefix'} })
    suffix: Optional[str] = Field(default=None, description="""The text that comes just after the passage.""", json_schema_extra = { "linkml_meta": {'domain_of': ['TextQuoteSelector'], 'slot_uri': 'oa:suffix'} })


class FragmentSelector(ConfiguredBaseModel):
    """
    A place in the cited work or output, given as a fragment identifier in the syntax `conforms_to` names, such as `row=5-7` in a CSV (RFC 7111). Without `conforms_to`, it is a PDF fragment identifier (RFC 8118 §3), such as `page=6`, with pages counted from 1.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'class_uri': 'oa:FragmentSelector',
         'from_schema': 'https://w3id.org/astra/insight'})

    value: str = Field(default=..., description="""The fragment identifier, without the leading `#`, such as `page=6`. It is non-empty, holds no ASCII space or control character and none of `\"`, `#`, `<`, `>`, `[`, the backslash, `]`, `^`, the backtick, `{`, `|` and `}`, and has `%` only before two hex digits.""", json_schema_extra = { "linkml_meta": {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_VALUE'}},
         'domain_of': ['FragmentSelector'],
         'slot_uri': 'rdf:value'} })
    conforms_to: Optional[str] = Field(default=None, description="""The IRI of the specification of the fragment syntax `value` follows, as W3C Web Annotation gives it, such as `http://tools.ietf.org/rfc/rfc7111` for a CSV. Without it, `value` is a PDF fragment identifier (RFC 8118).""", json_schema_extra = { "linkml_meta": {'domain_of': ['FragmentSelector'], 'slot_uri': 'dcterms:conformsTo'} })

    @field_validator('value')
    def pattern_value(cls, v):
        pattern=re.compile(r"^([^\x00-\x20\x7f\x22#%<>\[\\\]^`{|}]|%[0-9A-Fa-f]{2})+$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid value format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid value format: {v}"
            raise ValueError(err_msg)
        return v


class Evidence(ConfiguredBaseModel):
    """
    What a claim rests on: a published work, cited by its `doi`, or an output, cited as an `artifact`. It has exactly one of the two, and a `version` only with a `doi`.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'exactly_one_of': [{'annotations': {'rule': {'tag': 'rule',
                                                      'value': 'INVALID_EVIDENCE_SOURCE'}},
                             'slot_conditions': {'doi': {'name': 'doi',
                                                         'required': True}}},
                            {'annotations': {'rule': {'tag': 'rule',
                                                      'value': 'INVALID_EVIDENCE_SOURCE'}},
                             'slot_conditions': {'artifact': {'name': 'artifact',
                                                              'required': True}}}],
         'from_schema': 'https://w3id.org/astra/insight',
         'rules': [{'annotations': {'rule': {'tag': 'rule',
                                             'value': 'INVALID_EVIDENCE_SOURCE'}},
                    'description': 'Evidence without a `doi` has no `version`.',
                    'postconditions': {'slot_conditions': {'version': {'name': 'version',
                                                                       'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'doi': {'name': 'doi',
                                                                  'value_presence': 'ABSENT'}}}}]})

    doi: Optional[str] = Field(default=None, description="""The DOI name of the cited work, under the `10` directory: `10.`, the registrant code, `/` and a non-empty suffix, such as `10.5555/12345678`.""", json_schema_extra = { "linkml_meta": {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_VALUE'}},
         'domain_of': ['Evidence']} })
    artifact: Optional[str] = Field(default=None, description="""A reference to the cited output, written as in an output's `inputs`. It may pin the output to a universe, the one the claim is about, such as `output1#u1`. A switch is cited as the case it takes, and each of its cases names an output other than a switch, or a switch like it.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence']} })
    version: Optional[int] = Field(default=None, description="""The version of the cited work, counted from 1, such as `2` for the second version of an arXiv paper.""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence']} })
    quote: Optional[TextQuoteSelector] = Field(default=None, description="""The passage of the cited work or output the claim rests on. With a `location`, the passage is sought within that place.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence']} })
    location: Optional[FragmentSelector] = Field(default=None, description="""The place in the cited work or output the claim rests on, such as `page=6`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Evidence']} })

    @field_validator('doi')
    def pattern_doi(cls, v):
        pattern=re.compile(r"^10\.[0-9]+(\.[0-9]+)*/(?!$)")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid doi format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid doi format: {v}"
            raise ValueError(err_msg)
        return v


class Insight(ConfiguredBaseModel):
    """
    A claim backed by evidence: as a prior insight, what earlier work establishes and the analysis builds on; as a finding, what the analysis concludes.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/insight'})

    id: str = Field(default=..., description="""The insight's id, written as its key in `prior_insights` or `findings`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'AnalysisDeclaration']} })
    label: Optional[str] = Field(default=None, description="""A short display name for the insight.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'Analysis']} })
    claim: str = Field(default=..., description="""What the insight asserts.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight']} })
    description: Optional[str] = Field(default=None, description="""The reasoning behind the claim, in free prose.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Input', 'Output', 'Option', 'Universe', 'Analysis']} })
    evidence: list[Evidence] = Field(default=..., description="""What the claim rests on, as a list. There is at least one.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Insight']} })
    scope: Optional[str] = Field(default=None, description="""The conditions under which the claim holds, in free prose.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight']} })
    tags: Optional[list[str]] = Field(default=None, description="""Keywords for grouping and finding the insight.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'Analysis']} })


class Resources(ConfiguredBaseModel):
    """
    The compute resources a recipe asks for.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/analysis'})

    cpus: Optional[float] = Field(default=None, description="""The number of CPU cores the recipe asks for, which may be fractional, such as 0.5.""", ge=0, json_schema_extra = { "linkml_meta": {'domain_of': ['Resources']} })
    memory: Optional[str] = Field(default=None, description="""The memory the recipe asks for, as free text, such as `4GB`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Resources']} })
    time_limit: Optional[str] = Field(default=None, description="""The longest the recipe may run, as free text, such as `2h`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Resources']} })
    disk: Optional[str] = Field(default=None, description="""The disk space the recipe asks for, as free text, such as `10GB`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Resources']} })
    gpus: Optional[int] = Field(default=None, description="""The number of GPUs the recipe asks for.""", ge=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Resources']} })


class Recipe(ConfiguredBaseModel):
    """
    How an output is made: a `command` and the compute `resources` it asks for. What the output is made from and the decisions it is made with are the output's `inputs` and `decisions`; the command reaches the inputs and decisions through its placeholders.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/analysis'})

    command: str = Field(default=..., description="""The POSIX shell command that makes the output, such as `python src/output1.py`. It is a template. Read from the left, `{{` stands for a literal `{` and `}}` for a literal `}`, and any other `{` opens a placeholder, which ends at the next `}`. A runner substitutes each placeholder, and each `{{` and `}}`, before running the command:

  {inputs.<entry>}     the path of what an entry of the output's
                       `inputs` names (for a switch, what the case
                       it takes names), with <entry> written
                       exactly as the entry is, dots and `#`
                       included, as in
                       {inputs.subanalysis.output1#u1}
  {decisions.<entry>}  the id of the option selected for the
                       decision an entry of the output's
                       `decisions` names, with <entry> written
                       exactly as the entry is, as in
                       {decisions.subanalysis.decision1}
  {inputs}             the paths of all the output's inputs, in
                       the order of `inputs`, separated by spaces
  {output}             the path the result is written to

Every brace belongs to a `{{`, a `}}` or a placeholder, every placeholder takes one of these forms, and the <entry> of an {inputs.<entry>} or {decisions.<entry>} is an entry of the output's `inputs` or `decisions`, exactly as written.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Recipe']} })
    resources: Optional[Resources] = Field(default=None, description="""The compute resources the recipe asks for.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Recipe']} })


class Input(ConfiguredBaseModel):
    """
    A file the analysis reads, tracked in git with it and named by its path.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/analysis'})

    id: str = Field(default=..., description="""The input's id, written as its key in `inputs`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'AnalysisDeclaration']} })
    label: Optional[str] = Field(default=None, description="""A short display name for the input.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'Analysis']} })
    description: Optional[str] = Field(default=None, description="""What the input's data is, in free prose.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Input', 'Output', 'Option', 'Universe', 'Analysis']} })
    tags: Optional[list[str]] = Field(default=None, description="""Keywords for grouping and finding the input.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'Analysis']} })
    path: str = Field(default=..., description="""The path of the input's file, relative to the folder of the `astra.yaml`, with `/` between folders. It is non-empty and doesn't start with `/`.""", json_schema_extra = { "linkml_meta": {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_PATH'}},
         'domain_of': ['Input', 'AnalysisDeclaration']} })

    @field_validator('path')
    def pattern_path(cls, v):
        pattern=re.compile(r"^[^/]")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid path format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid path format: {v}"
            raise ValueError(err_msg)
        return v


class Output(ConfiguredBaseModel):
    """
    An entry of `outputs`: an artefact the analysis makes, such as a metric, a figure or a table, with what it is, what it is made from and how; or a switch, which has a `switch` and `cases`, makes nothing, and is read as the case it takes.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/analysis',
         'rules': [{'annotations': {'rule': {'tag': 'rule', 'value': 'MISSING_FIELD'}},
                    'description': "An output that isn't a switch has a `type`, a "
                                   '`format` and a `recipe`.',
                    'postconditions': {'slot_conditions': {'format': {'name': 'format',
                                                                      'value_presence': 'PRESENT'},
                                                           'recipe': {'name': 'recipe',
                                                                      'value_presence': 'PRESENT'},
                                                           'type': {'name': 'type',
                                                                    'value_presence': 'PRESENT'}}},
                    'preconditions': {'slot_conditions': {'switch': {'name': 'switch',
                                                                     'value_presence': 'ABSENT'}}}},
                   {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_SWITCH'}},
                    'description': 'A switch has `cases`.',
                    'postconditions': {'slot_conditions': {'cases': {'name': 'cases',
                                                                     'value_presence': 'PRESENT'}}},
                    'preconditions': {'slot_conditions': {'switch': {'name': 'switch',
                                                                     'value_presence': 'PRESENT'}}}},
                   {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_SWITCH'}},
                    'description': 'An entry with `cases` has a `switch`.',
                    'postconditions': {'slot_conditions': {'switch': {'name': 'switch',
                                                                      'value_presence': 'PRESENT'}}},
                    'preconditions': {'slot_conditions': {'cases': {'name': 'cases',
                                                                    'value_presence': 'PRESENT'}}}},
                   {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_SWITCH'}},
                    'description': 'A switch has no `type`.',
                    'postconditions': {'slot_conditions': {'type': {'name': 'type',
                                                                    'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'switch': {'name': 'switch',
                                                                     'value_presence': 'PRESENT'}}}},
                   {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_SWITCH'}},
                    'description': 'A switch has no `format`.',
                    'postconditions': {'slot_conditions': {'format': {'name': 'format',
                                                                      'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'switch': {'name': 'switch',
                                                                     'value_presence': 'PRESENT'}}}},
                   {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_SWITCH'}},
                    'description': 'A switch has no `inputs`.',
                    'postconditions': {'slot_conditions': {'inputs': {'name': 'inputs',
                                                                      'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'switch': {'name': 'switch',
                                                                     'value_presence': 'PRESENT'}}}},
                   {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_SWITCH'}},
                    'description': 'A switch has no `decisions`.',
                    'postconditions': {'slot_conditions': {'decisions': {'name': 'decisions',
                                                                         'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'switch': {'name': 'switch',
                                                                     'value_presence': 'PRESENT'}}}},
                   {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_SWITCH'}},
                    'description': 'A switch has no `recipe`.',
                    'postconditions': {'slot_conditions': {'recipe': {'name': 'recipe',
                                                                      'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'switch': {'name': 'switch',
                                                                     'value_presence': 'PRESENT'}}}}]})

    id: str = Field(default=..., description="""The output's id, written as its key in `outputs`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'AnalysisDeclaration']} })
    label: Optional[str] = Field(default=None, description="""A short display name for the output.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'Analysis']} })
    description: Optional[str] = Field(default=None, description="""What the output is, in free prose.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Input', 'Output', 'Option', 'Universe', 'Analysis']} })
    tags: Optional[list[str]] = Field(default=None, description="""Keywords for grouping and finding the output.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'Analysis']} })
    type: Optional[OutputType] = Field(default=None, description="""The kind of artefact the output is. Every output but a switch has one.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Output']} })
    format: Optional[str] = Field(default=None, description="""How the output's artefact is encoded, as a lowercase token: the extension of its results' files, without the leading dot, such as `png`, `csv` or `parquet`. Every output but a switch has one.""", json_schema_extra = { "linkml_meta": {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_VALUE'}},
         'domain_of': ['Output']} })
    inputs: Optional[list[str]] = Field(default=None, description="""What the output is made from, in order: references to inputs and outputs of the analysis or of analyses it declares, a switch read as the case it takes. A reference can be pinned to a universe with `#`.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Output', 'Analysis']} })
    decisions: Optional[list[str]] = Field(default=None, description="""The addresses of the decisions whose option the output is made with directly, not through what it reads: a different option for any of them, in the universe being built, can give a different result.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Output', 'Universe', 'Analysis']} })
    recipe: Optional[Recipe] = Field(default=None, description="""How the output is made. Every output but a switch has one.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Output']} })
    switch: Optional[str] = Field(default=None, description="""For a switch, the address of the decision whose selected option picks the case it takes, such as `decision1` or `stage.decision2`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Output']} })
    cases: Optional[dict[str, Union[str, SwitchCase]]] = Field(default=None, description="""For a switch, what it is read as where its decision selects each option that has a case, as `<option>: <reference>`, such as `b: stage.output3`. There is at least one, and several options can name one reference. Where its decision selects an option with no case, the switch isn't built, nor is anything that reads it without a pin.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Output']} })

    @field_validator('format')
    def pattern_format(cls, v):
        pattern=re.compile(r"^[a-z0-9][a-z0-9_.+-]*$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid format format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid format format: {v}"
            raise ValueError(err_msg)
        return v


class SwitchCase(ConfiguredBaseModel):
    """
    What a switch is read as where its decision selects one option, written in the switch's `cases` as `<option>: <reference>`, such as `b: stage.output3`.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/analysis'})

    case: str = Field(default=..., description="""The id of an option of the switch's decision, written as its key in `cases`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SwitchCase']} })
    target: str = Field(default=..., description="""A reference to the input, output or switch the switch is read as where the option is selected, written as an entry of an output's `inputs` is, such as `stage.output3` or `output1#u1`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['SwitchCase']} })


class Decision(ConfiguredBaseModel):
    """
    A choice the analysis makes between options, such as which method to use.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/analysis'})

    id: str = Field(default=..., description="""The decision's id, written as its key in `decisions`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'AnalysisDeclaration']} })
    label: Optional[str] = Field(default=None, description="""A short display name for the decision.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'Analysis']} })
    rationale: Optional[str] = Field(default=None, description="""Why the analysis makes this decision, in free prose.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Decision']} })
    tags: Optional[list[str]] = Field(default=None, description="""Keywords for grouping and finding the decision.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'Analysis']} })
    options: dict[str, Option] = Field(default=..., description="""The options the decision chooses between, keyed by id. There is at least one.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Decision']} })


class Option(ConfiguredBaseModel):
    """
    One of the options a decision chooses between.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/analysis'})

    id: str = Field(default=..., description="""The option's id, written as its key in `options`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'AnalysisDeclaration']} })
    label: Optional[str] = Field(default=None, description="""A short display name for the option.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'Analysis']} })
    description: Optional[str] = Field(default=None, description="""What the option is, in free prose.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Input', 'Output', 'Option', 'Universe', 'Analysis']} })
    tags: Optional[list[str]] = Field(default=None, description="""Keywords for grouping and finding the option.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'Analysis']} })
    insights: Optional[list[str]] = Field(default=None, description="""The ids of the prior insights that support the option.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Option']} })
    requires: Optional[list[str]] = Field(default=None, description="""The options that are also selected wherever this option is, among the decisions a universe uses: a decision it doesn't use selects none.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Option']} })
    incompatible_with: Optional[list[str]] = Field(default=None, description="""The options that are never selected together with this option, among the decisions a universe uses.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Option']} })
    excluded: Optional[str] = Field(default=None, description="""Why the option is ruled out. An option with a reason is excluded: no effective selection selects it.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Option']} })


class Universe(ConfiguredBaseModel):
    """
    An entry of `universes`: a universe of the analysis, a selection of one option for every decision it uses of the analysis and of every analysis, declared directly or not, that the analysis's universes drive, or an import, which has an `analysis` and a `universe`, names one of another analysis's universes and selects nothing. A universe's effective selection is the effective selection of the universe it is derived from, if any, with its own `decisions` written over it decision by decision.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/analysis',
         'rules': [{'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_IMPORT'}},
                    'description': 'An import has a `universe`.',
                    'postconditions': {'slot_conditions': {'universe': {'name': 'universe',
                                                                        'value_presence': 'PRESENT'}}},
                    'preconditions': {'slot_conditions': {'analysis': {'name': 'analysis',
                                                                       'value_presence': 'PRESENT'}}}},
                   {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_IMPORT'}},
                    'description': 'An import has no `decisions`.',
                    'postconditions': {'slot_conditions': {'decisions': {'name': 'decisions',
                                                                         'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'analysis': {'name': 'analysis',
                                                                       'value_presence': 'PRESENT'}}}},
                   {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_IMPORT'}},
                    'description': 'An import has no `derived_from`.',
                    'postconditions': {'slot_conditions': {'derived_from': {'name': 'derived_from',
                                                                            'value_presence': 'ABSENT'}}},
                    'preconditions': {'slot_conditions': {'analysis': {'name': 'analysis',
                                                                       'value_presence': 'PRESENT'}}}},
                   {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_IMPORT'}},
                    'description': 'An entry with a `universe` has an `analysis`.',
                    'postconditions': {'slot_conditions': {'analysis': {'name': 'analysis',
                                                                        'value_presence': 'PRESENT'}}},
                    'preconditions': {'slot_conditions': {'universe': {'name': 'universe',
                                                                       'value_presence': 'PRESENT'}}}}]})

    id: str = Field(default=..., description="""The entry's id, written as its key in `universes`: for an import, the id the analysis gives the universe it imports.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'AnalysisDeclaration']} })
    label: Optional[str] = Field(default=None, description="""A short display name for the universe.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'Analysis']} })
    description: Optional[str] = Field(default=None, description="""What the universe is, in free prose.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Input', 'Output', 'Option', 'Universe', 'Analysis']} })
    tags: Optional[list[str]] = Field(default=None, description="""Keywords for grouping and finding the universe.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'Analysis']} })
    derived_from: Optional[str] = Field(default=None, description="""The id of another universe of the analysis, never an import, whose effective selection this universe's effective selection is built on, so that this universe gives only the decisions it changes. The universe inherits only that selection.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Universe']} })
    decisions: Optional[dict[str, Union[str, DecisionSelection]]] = Field(default=None, description="""The options the universe selects, as `<decision>: <option>`, one key per decision. Each key is the id of a decision of the analysis or, for a decision of another analysis, a flat key: the decision's address through the declarations, `<declaration>.<decision>`, such as `subanalysis.decision1`, or another spelling of that address, through no declaration back to an analysis already on its chain.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Output', 'Universe', 'Analysis']} })
    analysis: Optional[str] = Field(default=None, description="""For an import, the address of the declaration that leads to the analysis whose universe it imports, through as many declarations as lead to it, such as `subanalysis` or `stage.inner`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Universe']} })
    universe: Optional[str] = Field(default=None, description="""For an import, the id of the universe it imports: a universe of the analysis that `analysis` leads to, never an import of that analysis.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Universe']} })


class DecisionSelection(ConfiguredBaseModel):
    """
    The option a universe selects for one decision, written in the universe's `decisions` as `<decision>: <option>`, such as `decision1: a`.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/analysis'})

    decision: str = Field(default=..., description="""The address of the decision, written as its key in the universe's `decisions`.""", json_schema_extra = { "linkml_meta": {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_ID'}},
         'domain_of': ['DecisionSelection']} })
    option: str = Field(default=..., description="""The id of the option selected for the decision.""", json_schema_extra = { "linkml_meta": {'domain_of': ['DecisionSelection']} })


class AnalysisDeclaration(ConfiguredBaseModel):
    """
    An analysis that this analysis uses, found by exactly one of `path` and `url`. Its elements are addressed through the declaration's id, as `<declaration>.<element>`.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'exactly_one_of': [{'annotations': {'rule': {'tag': 'rule',
                                                      'value': 'INVALID_DECLARATION_SOURCE'}},
                             'slot_conditions': {'path': {'name': 'path',
                                                          'required': True}}},
                            {'annotations': {'rule': {'tag': 'rule',
                                                      'value': 'INVALID_DECLARATION_SOURCE'}},
                             'slot_conditions': {'url': {'name': 'url',
                                                         'required': True}}}],
         'from_schema': 'https://w3id.org/astra/analysis',
         'rules': [{'annotations': {'rule': {'tag': 'rule',
                                             'value': 'URL_WITHOUT_COMMIT'}},
                    'description': 'A declaration with a `url` has a `commit`.',
                    'postconditions': {'slot_conditions': {'commit': {'name': 'commit',
                                                                      'value_presence': 'PRESENT'}}},
                    'preconditions': {'slot_conditions': {'url': {'name': 'url',
                                                                  'value_presence': 'PRESENT'}}}}]})

    id: str = Field(default=..., description="""The id this analysis addresses the declared analysis by, written as its key in `analyses`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'AnalysisDeclaration']} })
    path: Optional[str] = Field(default=None, description="""The directory of the declared analysis's `astra.yaml`, relative to the folder of this `astra.yaml`, with `/` between folders. It is non-empty and doesn't start with `/`.""", json_schema_extra = { "linkml_meta": {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_PATH'}},
         'domain_of': ['Input', 'AnalysisDeclaration']} })
    url: Optional[str] = Field(default=None, description="""Where git fetches another repository from, as a remote with no ASCII space or control character, in one of two forms: `scheme://` and at least one character, where the scheme is an ASCII letter followed by any ASCII letters, digits, `+`, `.` and `-`, such as `https://example.org/remote.git` or `file:///srv/remote.git`; or scp-like, `[user@]host:path`, where `host`, `path` and any `user` are non-empty, `user` and `host` hold no `/`, `@` or `:`, and the value doesn't start with a scheme and `://`, such as `git@example.org:remote.git`. The declared analysis is the one at the top level of that repository, at `commit`.""", json_schema_extra = { "linkml_meta": {'annotations': {'rule': {'tag': 'rule', 'value': 'INVALID_VALUE'}},
         'domain_of': ['AnalysisDeclaration']} })
    commit: Optional[str] = Field(default=None, description="""The full id of the commit the declared analysis is read at. A declaration with a `url` has one; with a `path`, it declares the analysis at that path as it was at that commit.""", json_schema_extra = { "linkml_meta": {'domain_of': ['AnalysisDeclaration']} })

    @field_validator('path')
    def pattern_path(cls, v):
        pattern=re.compile(r"^[^/]")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid path format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid path format: {v}"
            raise ValueError(err_msg)
        return v

    @field_validator('url')
    def pattern_url(cls, v):
        pattern=re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*://[^\x00-\x20\x7f]+|(?![A-Za-z][A-Za-z0-9+.-]*://)(?:[^\x00-\x20\x7f/@:]+@)?[^\x00-\x20\x7f/@:]+:[^\x00-\x20\x7f]+)$")
        if isinstance(v, list):
            for element in v:
                if isinstance(element, str) and not pattern.search(element):
                    err_msg = f"Invalid url format: {element}"
                    raise ValueError(err_msg)
        elif isinstance(v, str) and not pattern.search(v):
            err_msg = f"Invalid url format: {v}"
            raise ValueError(err_msg)
        return v


class Analysis(ConfiguredBaseModel):
    """
    An analysis: the files it reads, the artefacts it makes and the decisions it makes along the way. It is the content of an `astra.yaml` file.
    """
    linkml_meta: ClassVar[LinkMLMeta] = LinkMLMeta({'from_schema': 'https://w3id.org/astra/analysis', 'tree_root': True})

    spec_version: str = Field(default=..., description="""The version of the ASTRA specification the document is written against, such as `0.1.0`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })
    label: Optional[str] = Field(default=None, description="""A short display name for the analysis.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'Analysis']} })
    description: Optional[str] = Field(default=None, description="""What the analysis does, in free prose.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Insight', 'Input', 'Output', 'Option', 'Universe', 'Analysis']} })
    tags: Optional[list[str]] = Field(default=None, description="""Keywords for grouping and finding the analysis.""", min_length=1, json_schema_extra = { "linkml_meta": {'domain_of': ['Insight',
                       'Input',
                       'Output',
                       'Decision',
                       'Option',
                       'Universe',
                       'Analysis']} })
    inputs: Optional[dict[str, Input]] = Field(default=None, description="""The files the analysis reads, keyed by id.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Output', 'Analysis']} })
    outputs: Optional[dict[str, Output]] = Field(default=None, description="""The artefacts the analysis makes, and its switches, keyed by id.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })
    decisions: Optional[dict[str, Decision]] = Field(default=None, description="""The choices the analysis makes, keyed by id.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Output', 'Universe', 'Analysis']} })
    analyses: Optional[dict[str, AnalysisDeclaration]] = Field(default=None, description="""The analyses this analysis uses, keyed by the id it addresses them by.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })
    universes: Optional[dict[str, Universe]] = Field(default=None, description="""The universes of the analysis, and the universes of other analyses it imports, keyed by id. An import has an `analysis` and a `universe`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })
    prior_insights: Optional[dict[str, Insight]] = Field(default=None, description="""What earlier work establishes and the analysis builds on, as insights keyed by id. Options cite them in their `insights`.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })
    findings: Optional[dict[str, Insight]] = Field(default=None, description="""What the analysis concludes, as insights keyed by id.""", json_schema_extra = { "linkml_meta": {'domain_of': ['Analysis']} })


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
TextQuoteSelector.model_rebuild()
FragmentSelector.model_rebuild()
Evidence.model_rebuild()
Insight.model_rebuild()
Resources.model_rebuild()
Recipe.model_rebuild()
Input.model_rebuild()
Output.model_rebuild()
SwitchCase.model_rebuild()
Decision.model_rebuild()
Option.model_rebuild()
Universe.model_rebuild()
DecisionSelection.model_rebuild()
AnalysisDeclaration.model_rebuild()
Analysis.model_rebuild()
