"""Every constraint of the contract, pinned by a negative case written by hand (design §9).

One invalid fixture per code leaves most constraints unchecked, since one code covers many keywords, and the drift
check regenerates the contract from the LinkML sources: a constraint loosened there passes every test that reads the
sources or the generated schemas. So the cases here are written by hand, never read from either. Each row of
`NEGATIVE` breaks one constraint of a valid fixture, and the document must then fail where the row says, with its code,
and nowhere else, as an invalid fixture must (`check_schema_errors`). `FACETS` gives each pattern a slot writes itself
values it accepts, and values it rejects, at least one for each facet its description states. The meta-tests check that
the rows reach every keyword of each schema's error map and every field of every `required`, so a new constraint needs
a new row.
"""

import copy
import functools
from collections.abc import Iterator
from typing import Any, NamedTuple

import pytest

from .conftest import (
    DATA,
    absolute_keyword_location,
    errors,
    load_fixture,
    rules_catalogue,
    validator,
)
from .test_contract import source_classes, source_slots
from .test_fixtures import check_schema_errors
from .test_rules import keyword_steps, load, schema_objects

BASES = {
    "minimal": "Analysis-001-minimal.yaml",
    "core": "Analysis-002-core.yaml",
    "universes": "Analysis-004-universes.yaml",
    "declarations": "Analysis-005-declarations.yaml",
    "insights": "Analysis-006-insights.yaml",
    "quoted-keys": "Analysis-009-quoted-keys-and-escapes.yaml",
    "full": "ProvenanceRecord-001-full.json",
}
"""The valid fixtures the cases edit, by a short name. Only `quoted-keys` has a recipe's `resources`."""


class _Delete:
    """The edit that deletes the value at a case's pointer."""

    def __repr__(self) -> str:
        return "DELETE"


DELETE = _Delete()


class Case(NamedTuple):
    """A negative case: a valid fixture (`BASES`), a JSON Pointer into it, the edit made there, and the code it fails
    with.

    The edit sets `value` at the pointer, adding the field or entry if there is none, or deletes what is there
    (`DELETE`). The document then fails at `fails_at` alone: by default the pointer for a value set, and the object or
    list that held it for a deletion. `also` is the code of a second keyword the edit breaks there, if any: only an
    enumeration's `type`, since a value of another type is none of its strings either.
    """

    base: str
    pointer: str
    value: Any
    code: str
    fails_at: str | None = None
    also: str | None = None


HEX_64 = "0123456789abcdef" * 4

OUTPUT = {
    "type": "metric",
    "format": "json",
    "recipe": {"command": "python make.py '{output}'"},
}
"""A valid output, for a map entry added under a bad key."""

INSIGHT = {"claim": "The forest is accurate.", "evidence": [{"artifact": "scores"}]}
"""A valid insight, for a map entry added under a bad key."""

SMALL = "/decisions/training/options/small"
TRAINING = "/decisions/training"
NEURAL_NET = "/decisions/method/options/neural_net"
RESOURCES = "/outputs/result/recipe/resources"
SVM = "/universes/svm_standard"
IMPORT = "/universes/stage_alone"
FINDING = "/findings/rf_accuracy"
CITED = FINDING + "/evidence/0"
PUBLISHED = "/prior_insights/forests_resist_noise/evidence/0"
QUOTE = PUBLISHED + "/quote"
LOCATION = PUBLISHED + "/location"
RECORDED = "/generated_by/inputs/0"
ENVIRONMENT = "/generated_by/environment"
RUNNER = "/generated_by/runner"

NEGATIVE = [
    # --- An astra.yaml (`Analysis`) ---
    Case("minimal", "", ["result"], "WRONG_TYPE"),
    Case("minimal", "/spec_version", DELETE, "MISSING_FIELD"),
    Case("minimal", "/outputs", DELETE, "MISSING_FIELD"),
    Case("minimal", "/version", "0.0.11", "UNKNOWN_FIELD", "(root)"),
    Case("minimal", "/spec_version", 0.1, "WRONG_TYPE"),
    Case("minimal", "/spec_version", "0.1", "INVALID_VALUE"),
    Case("core", "/label", 1, "WRONG_TYPE"),
    Case("core", "/description", 1, "WRONG_TYPE"),
    Case("core", "/container", 1, "WRONG_TYPE"),
    Case("core", "/tags", "cosmology", "WRONG_TYPE"),
    Case("core", "/tags/0", 1, "WRONG_TYPE"),
    Case("core", "/tags", [], "EMPTY_COLLECTION"),
    Case("core", "/tags/1", "photometric-redshifts", "DUPLICATE_ENTRY", "/tags"),
    # Each map: a list in its place, a key that is an address but not an id, and a key that isn't a string.
    Case("core", "/inputs", ["catalog"], "WRONG_TYPE"),
    Case("core", "/inputs/data.catalog", {"path": "a.csv"}, "INVALID_ID", "/inputs"),
    Case("core", "/inputs", {1: {"path": "data/catalog.csv"}}, "INVALID_ID"),
    Case("minimal", "/outputs", ["result"], "WRONG_TYPE"),
    Case("minimal", "/outputs", {}, "EMPTY_COLLECTION"),
    Case("minimal", "/outputs/result.v2", OUTPUT, "INVALID_ID", "/outputs"),
    Case("minimal", "/outputs", {1: OUTPUT}, "INVALID_ID"),
    Case("core", "/decisions", ["method"], "WRONG_TYPE"),
    Case(
        "core",
        "/decisions/calibration.split",
        {"options": {"half": {}}},
        "INVALID_ID",
        "/decisions",
    ),
    Case("core", "/decisions", {1: {"options": {"half": {}}}}, "INVALID_ID"),
    Case("declarations", "/analyses", ["stage"], "WRONG_TYPE"),
    Case(
        "declarations", "/analyses/up.stage", {"path": "x"}, "INVALID_ID", "/analyses"
    ),
    Case("declarations", "/analyses", {1: {"path": "stage"}}, "INVALID_ID"),
    Case("universes", "/universes", ["rf_standard"], "WRONG_TYPE"),
    Case("universes", "/universes/stage.u1", {}, "INVALID_ID", "/universes"),
    Case("universes", "/universes", {1: {}}, "INVALID_ID"),
    Case("insights", "/prior_insights", ["forests_resist_noise"], "WRONG_TYPE"),
    Case(
        "insights", "/prior_insights/up.noise", INSIGHT, "INVALID_ID", "/prior_insights"
    ),
    Case("insights", "/prior_insights", {1: INSIGHT}, "INVALID_ID"),
    Case("insights", "/findings", ["rf_accuracy"], "WRONG_TYPE"),
    Case("insights", "/findings/rf.accuracy", INSIGHT, "INVALID_ID", "/findings"),
    Case("insights", "/findings", {1: INSIGHT}, "INVALID_ID"),
    # --- Input ---
    Case("core", "/inputs/catalog", "data/catalog.csv", "WRONG_TYPE"),
    Case("core", "/inputs/catalog/id", "catalog", "UNKNOWN_FIELD", "/inputs/catalog"),
    Case("core", "/inputs/catalog/path", DELETE, "MISSING_FIELD"),
    Case("core", "/inputs/catalog/label", 1, "WRONG_TYPE"),
    Case("core", "/inputs/catalog/description", 1, "WRONG_TYPE"),
    Case("core", "/inputs/catalog/tags", "photometry", "WRONG_TYPE"),
    Case("core", "/inputs/catalog/tags/0", 1, "WRONG_TYPE"),
    Case("core", "/inputs/catalog/tags", [], "EMPTY_COLLECTION"),
    Case("core", "/inputs/catalog/tags", ["photometry"] * 2, "DUPLICATE_ENTRY"),
    Case("core", "/inputs/catalog/path", 1, "WRONG_TYPE"),
    Case("core", "/inputs/catalog/path", "/data/catalog.csv", "INVALID_PATH"),
    # --- Output, its recipe and the recipe's resources ---
    Case("core", "/outputs/estimates", "parquet", "WRONG_TYPE"),
    Case(
        "core",
        "/outputs/estimates/id",
        "estimates",
        "UNKNOWN_FIELD",
        "/outputs/estimates",
    ),
    Case("core", "/outputs/estimates/type", DELETE, "MISSING_FIELD"),
    Case("core", "/outputs/estimates/format", DELETE, "MISSING_FIELD"),
    Case("core", "/outputs/estimates/recipe", DELETE, "MISSING_FIELD"),
    Case("core", "/outputs/estimates/label", 1, "WRONG_TYPE"),
    Case("core", "/outputs/estimates/description", 1, "WRONG_TYPE"),
    Case("core", "/outputs/estimates/tags", "redshifts", "WRONG_TYPE"),
    Case("core", "/outputs/estimates/tags/0", 1, "WRONG_TYPE"),
    Case("core", "/outputs/estimates/tags", [], "EMPTY_COLLECTION"),
    Case("core", "/outputs/estimates/tags", ["redshifts"] * 2, "DUPLICATE_ENTRY"),
    Case("core", "/outputs/estimates/type", 1, "WRONG_TYPE", also="INVALID_VALUE"),
    Case("core", "/outputs/estimates/type", "dataset", "INVALID_VALUE"),
    Case("core", "/outputs/estimates/format", 1, "WRONG_TYPE"),
    Case("core", "/outputs/estimates/format", "Parquet", "INVALID_VALUE"),
    Case("core", "/outputs/estimates/inputs", "catalog", "WRONG_TYPE"),
    Case("core", "/outputs/estimates/inputs/0", 1, "WRONG_TYPE"),
    Case("core", "/outputs/estimates/inputs/0", "catalog#", "INVALID_REFERENCE"),
    Case("core", "/outputs/estimates/inputs", [], "EMPTY_COLLECTION"),
    Case(
        "core",
        "/outputs/estimates/inputs/1",
        "catalog",
        "DUPLICATE_ENTRY",
        "/outputs/estimates/inputs",
    ),
    Case("core", "/outputs/estimates/decisions", "method", "WRONG_TYPE"),
    Case("core", "/outputs/estimates/decisions/0", 1, "WRONG_TYPE"),
    Case("core", "/outputs/estimates/decisions/0", "method#u1", "INVALID_REFERENCE"),
    Case("core", "/outputs/estimates/decisions", [], "EMPTY_COLLECTION"),
    Case(
        "core",
        "/outputs/estimates/decisions/1",
        "method",
        "DUPLICATE_ENTRY",
        "/outputs/estimates/decisions",
    ),
    Case("core", "/outputs/bias/when", "~method.template", "WRONG_TYPE"),
    Case("core", "/outputs/bias/when/0", 1, "WRONG_TYPE"),
    Case("core", "/outputs/bias/when/0", "~method", "INVALID_REFERENCE"),
    Case("core", "/outputs/bias/when", [], "EMPTY_COLLECTION"),
    Case("core", "/outputs/bias/when", ["~method.template"] * 2, "DUPLICATE_ENTRY"),
    Case("core", "/outputs/bias/recipe", "python src/bias.py", "WRONG_TYPE"),
    Case(
        "core",
        "/outputs/bias/recipe/image",
        "python:3.12",
        "UNKNOWN_FIELD",
        "/outputs/bias/recipe",
    ),
    Case("core", "/outputs/bias/recipe/command", DELETE, "MISSING_FIELD"),
    Case("core", "/outputs/bias/recipe/command", ["python"], "WRONG_TYPE"),
    Case("core", "/outputs/bias/recipe/container", 1, "WRONG_TYPE"),
    Case("quoted-keys", RESOURCES, "1 gpu", "WRONG_TYPE"),
    Case("quoted-keys", RESOURCES + "/gpu", 1, "UNKNOWN_FIELD", RESOURCES),
    Case("quoted-keys", RESOURCES + "/cpus", "0.5", "WRONG_TYPE"),
    Case("quoted-keys", RESOURCES + "/cpus", -0.01, "INVALID_VALUE"),
    Case("quoted-keys", RESOURCES + "/gpus", 1.5, "WRONG_TYPE"),
    Case("quoted-keys", RESOURCES + "/gpus", 0, "INVALID_VALUE"),
    Case("quoted-keys", RESOURCES + "/memory", 16, "WRONG_TYPE"),
    Case("quoted-keys", RESOURCES + "/time_limit", 2, "WRONG_TYPE"),
    Case("quoted-keys", RESOURCES + "/disk", 10, "WRONG_TYPE"),
    # --- Decision ---
    Case("core", "/decisions/method", "neural_net", "WRONG_TYPE"),
    Case(
        "core", "/decisions/method/id", "method", "UNKNOWN_FIELD", "/decisions/method"
    ),
    Case("core", "/decisions/method/options", DELETE, "MISSING_FIELD"),
    Case("core", "/decisions/method/label", 1, "WRONG_TYPE"),
    Case("core", "/decisions/method/rationale", 1, "WRONG_TYPE"),
    Case("core", "/decisions/method/tags", "estimator", "WRONG_TYPE"),
    Case("core", "/decisions/method/tags/0", 1, "WRONG_TYPE"),
    Case("core", "/decisions/method/tags", [], "EMPTY_COLLECTION"),
    Case("core", "/decisions/method/tags", ["estimator"] * 2, "DUPLICATE_ENTRY"),
    Case("core", TRAINING + "/when", "method.neural_net", "WRONG_TYPE"),
    Case("core", TRAINING + "/when/0", 1, "WRONG_TYPE"),
    Case("core", TRAINING + "/when/0", "method.neural_net#u1", "INVALID_REFERENCE"),
    Case("core", TRAINING + "/when", [], "EMPTY_COLLECTION"),
    Case("core", TRAINING + "/when", ["method.neural_net"] * 2, "DUPLICATE_ENTRY"),
    Case("core", "/decisions/method/options", ["template"], "WRONG_TYPE"),
    Case("core", "/decisions/method/options", {}, "EMPTY_COLLECTION"),
    Case(
        "core",
        "/decisions/method/options/neural.net",
        {},
        "INVALID_ID",
        "/decisions/method/options",
    ),
    Case("core", "/decisions/method/options", {1: {}}, "INVALID_ID"),
    # --- Option ---
    Case("core", "/decisions/method/options/template", "template", "WRONG_TYPE"),
    Case(
        "core",
        "/decisions/method/options/template/id",
        "template",
        "UNKNOWN_FIELD",
        "/decisions/method/options/template",
    ),
    Case("core", NEURAL_NET + "/label", 1, "WRONG_TYPE"),
    Case("core", NEURAL_NET + "/description", 1, "WRONG_TYPE"),
    Case("core", NEURAL_NET + "/tags", "machine-learning", "WRONG_TYPE"),
    Case("core", NEURAL_NET + "/tags/0", 1, "WRONG_TYPE"),
    Case("core", NEURAL_NET + "/tags", [], "EMPTY_COLLECTION"),
    Case("core", NEURAL_NET + "/tags", ["machine-learning"] * 2, "DUPLICATE_ENTRY"),
    Case("core", NEURAL_NET + "/insights", "nn_beats_templates", "WRONG_TYPE"),
    Case("core", NEURAL_NET + "/insights/0", 1, "WRONG_TYPE"),
    Case("core", NEURAL_NET + "/insights/0", "up.nn_beats_templates", "INVALID_ID"),
    Case("core", NEURAL_NET + "/insights", [], "EMPTY_COLLECTION"),
    Case(
        "core", NEURAL_NET + "/insights", ["nn_beats_templates"] * 2, "DUPLICATE_ENTRY"
    ),
    Case("core", NEURAL_NET + "/requires", "training.large", "WRONG_TYPE"),
    Case("core", NEURAL_NET + "/requires/0", 1, "WRONG_TYPE"),
    Case("core", NEURAL_NET + "/requires/0", "training", "INVALID_REFERENCE"),
    Case("core", NEURAL_NET + "/requires", [], "EMPTY_COLLECTION"),
    Case("core", NEURAL_NET + "/requires", ["training.large"] * 2, "DUPLICATE_ENTRY"),
    Case("core", SMALL + "/incompatible_with", "method.neural_net", "WRONG_TYPE"),
    Case("core", SMALL + "/incompatible_with/0", 1, "WRONG_TYPE"),
    Case(
        "core",
        SMALL + "/incompatible_with/0",
        "~method.neural_net",
        "INVALID_REFERENCE",
    ),
    Case("core", SMALL + "/incompatible_with", [], "EMPTY_COLLECTION"),
    Case(
        "core",
        SMALL + "/incompatible_with",
        ["method.neural_net"] * 2,
        "DUPLICATE_ENTRY",
    ),
    Case("core", SMALL + "/excluded", True, "WRONG_TYPE"),
    Case("core", SMALL + "/excluded", " ", "BLANK_EXCLUDED"),
    # --- Universe, and the selections of its `decisions` ---
    Case("universes", SVM, "rf_standard", "WRONG_TYPE"),
    Case("universes", SVM + "/id", "svm_standard", "UNKNOWN_FIELD", SVM),
    Case("universes", "/universes/rf_standard/label", 1, "WRONG_TYPE"),
    Case("universes", "/universes/rf_standard/description", 1, "WRONG_TYPE"),
    Case("universes", "/universes/rf_standard/tags", "baseline", "WRONG_TYPE"),
    Case("universes", "/universes/rf_standard/tags/0", 1, "WRONG_TYPE"),
    Case("universes", "/universes/rf_standard/tags", [], "EMPTY_COLLECTION"),
    Case(
        "universes",
        "/universes/rf_standard/tags/1",
        "baseline",
        "DUPLICATE_ENTRY",
        "/universes/rf_standard/tags",
    ),
    Case("universes", SVM + "/derived_from", ["rf_standard"], "WRONG_TYPE"),
    Case("universes", SVM + "/derived_from", "base.rf_standard", "INVALID_ID"),
    Case("universes", SVM + "/decisions", "model: svm", "WRONG_TYPE"),
    Case("universes", SVM + "/decisions/model", {"option": "svm"}, "WRONG_TYPE"),
    Case("universes", SVM + "/decisions/model", "model.svm", "INVALID_ID"),
    Case(
        "universes",
        SVM + "/decisions/stage.Method",
        "pca",
        "INVALID_ID",
        SVM + "/decisions",
    ),
    Case("universes", SVM + "/decisions", {1: "svm"}, "INVALID_ID"),
    # --- An import in `universes` ---
    Case("universes", IMPORT + "/universe", DELETE, "INVALID_IMPORT"),
    Case("universes", IMPORT + "/analysis", DELETE, "INVALID_IMPORT"),
    Case(
        "universes",
        IMPORT + "/decisions",
        {"stage.method": "pca"},
        "INVALID_IMPORT",
        IMPORT,
    ),
    Case(
        "universes", IMPORT + "/derived_from", "rf_standard", "INVALID_IMPORT", IMPORT
    ),
    Case("universes", IMPORT + "/analysis", 1, "WRONG_TYPE"),
    Case("universes", IMPORT + "/analysis", "Stage", "INVALID_REFERENCE"),
    Case("universes", IMPORT + "/universe", 1, "WRONG_TYPE"),
    Case("universes", IMPORT + "/universe", "stage.alone", "INVALID_ID"),
    # --- AnalysisDeclaration ---
    Case("declarations", "/analyses/stage", "stage", "WRONG_TYPE"),
    Case(
        "declarations",
        "/analyses/stage/id",
        "stage",
        "UNKNOWN_FIELD",
        "/analyses/stage",
    ),
    Case("declarations", "/analyses/stage/path", 1, "WRONG_TYPE"),
    Case("declarations", "/analyses/stage/path", "/srv/stage", "INVALID_PATH"),
    Case("declarations", "/analyses/upstream/url", 1, "WRONG_TYPE"),
    Case("declarations", "/analyses/upstream/url", "owner/analysis", "INVALID_VALUE"),
    Case("declarations", "/analyses/previous/commit", 1, "WRONG_TYPE"),
    Case("declarations", "/analyses/previous/commit", "0dbb615", "INVALID_COMMIT"),
    Case(
        "declarations",
        "/analyses/previous/url",
        "https://github.com/owner/analysis",
        "INVALID_DECLARATION_SOURCE",
        "/analyses/previous",
    ),
    Case("declarations", "/analyses/stage/path", DELETE, "INVALID_DECLARATION_SOURCE"),
    Case("declarations", "/analyses/upstream/commit", DELETE, "URL_WITHOUT_COMMIT"),
    # --- Insight ---
    Case("insights", FINDING, "The random forest reaches 0.93 accuracy.", "WRONG_TYPE"),
    Case("insights", FINDING + "/id", "rf_accuracy", "UNKNOWN_FIELD", FINDING),
    Case("insights", FINDING + "/claim", DELETE, "MISSING_FIELD"),
    Case("insights", FINDING + "/evidence", DELETE, "MISSING_FIELD"),
    Case("insights", FINDING + "/label", 1, "WRONG_TYPE"),
    Case("insights", FINDING + "/claim", 1, "WRONG_TYPE"),
    Case("insights", FINDING + "/description", 1, "WRONG_TYPE"),
    Case("insights", FINDING + "/scope", 1, "WRONG_TYPE"),
    Case("insights", FINDING + "/tags", "accuracy", "WRONG_TYPE"),
    Case("insights", FINDING + "/tags/0", 1, "WRONG_TYPE"),
    Case("insights", FINDING + "/tags", [], "EMPTY_COLLECTION"),
    Case(
        "insights",
        FINDING + "/tags/1",
        "accuracy",
        "DUPLICATE_ENTRY",
        FINDING + "/tags",
    ),
    Case("insights", FINDING + "/evidence", {"artifact": "scores"}, "WRONG_TYPE"),
    Case("insights", FINDING + "/evidence", [], "EMPTY_COLLECTION"),
    # --- Evidence, and its selectors ---
    Case("insights", CITED, "result#u1", "WRONG_TYPE"),
    Case("insights", CITED + "/snapshot", "2026-10-26", "UNKNOWN_FIELD", CITED),
    Case("insights", CITED + "/artifact", 1, "WRONG_TYPE"),
    Case("insights", CITED + "/artifact", "result#u1#u2", "INVALID_REFERENCE"),
    Case("insights", PUBLISHED + "/doi", 10.5555, "WRONG_TYPE"),
    Case("insights", PUBLISHED + "/doi", "5555/12345678", "INVALID_VALUE"),
    Case("insights", PUBLISHED + "/version", 2.5, "WRONG_TYPE"),
    Case("insights", PUBLISHED + "/version", 0, "INVALID_VALUE"),
    Case(
        "insights",
        CITED + "/doi",
        "10.5555/12345678",
        "INVALID_EVIDENCE_SOURCE",
        CITED,
    ),
    Case("insights", CITED + "/artifact", DELETE, "INVALID_EVIDENCE_SOURCE"),
    Case("insights", CITED + "/version", 2, "INVALID_EVIDENCE_SOURCE", CITED),
    Case("insights", QUOTE, "the forest lost less than one point", "WRONG_TYPE"),
    Case("insights", QUOTE + "/type", "TextQuoteSelector", "UNKNOWN_FIELD", QUOTE),
    Case("insights", QUOTE + "/exact", DELETE, "MISSING_FIELD"),
    Case("insights", QUOTE + "/exact", 1, "WRONG_TYPE"),
    Case("insights", QUOTE + "/prefix", 1, "WRONG_TYPE"),
    Case("insights", QUOTE + "/suffix", 1, "WRONG_TYPE"),
    Case("insights", LOCATION, "page=6", "WRONG_TYPE"),
    Case("insights", LOCATION + "/type", "FragmentSelector", "UNKNOWN_FIELD", LOCATION),
    Case("insights", LOCATION + "/value", DELETE, "MISSING_FIELD"),
    Case("insights", LOCATION + "/value", 6, "WRONG_TYPE"),
    Case("insights", LOCATION + "/value", "page 6", "INVALID_VALUE"),
    Case("insights", LOCATION + "/conforms_to", 7111, "WRONG_TYPE"),
    Case("insights", LOCATION + "/conforms_to", "rfc7111", "INVALID_VALUE"),
    # --- A record (`ProvenanceRecord`) ---
    Case("full", "", [], "WRONG_TYPE"),
    Case("full", "/spec_version", DELETE, "MISSING_FIELD"),
    Case("full", "/address", DELETE, "MISSING_FIELD"),
    Case("full", "/content_hash", DELETE, "MISSING_FIELD"),
    Case("full", "/size", DELETE, "MISSING_FIELD"),
    Case("full", "/generated_by", DELETE, "MISSING_FIELD"),
    Case("full", "/version", "0.1.0", "UNKNOWN_FIELD", "(root)"),
    Case("full", "/spec_version", 0.1, "WRONG_TYPE"),
    Case("full", "/spec_version", "0.1", "INVALID_VALUE"),
    Case("full", "/address", 1, "WRONG_TYPE"),
    Case("full", "/address", "subanalysis1.output1#u1#u2", "INVALID_REFERENCE"),
    Case("full", "/content_hash", 1, "WRONG_TYPE"),
    Case("full", "/content_hash", "blake3:" + HEX_64, "INVALID_VALUE"),
    Case("full", "/size", 732.5, "WRONG_TYPE"),
    Case("full", "/size", -1, "INVALID_VALUE"),
    # --- Generation ---
    Case(
        "full",
        "/generated_by",
        "a7d9ea93c409ab6da0d919308f91f51de7c7ec6f",
        "WRONG_TYPE",
    ),
    Case("full", "/generated_by/host", "ci-7", "UNKNOWN_FIELD", "/generated_by"),
    Case("full", "/generated_by/commit", DELETE, "MISSING_FIELD"),
    Case("full", "/generated_by/environment", DELETE, "MISSING_FIELD"),
    Case("full", "/generated_by/runner", DELETE, "MISSING_FIELD"),
    Case("full", "/generated_by/commit", 1, "WRONG_TYPE"),
    Case("full", "/generated_by/commit", "a7d9ea9", "INVALID_COMMIT"),
    Case("full", "/generated_by/inputs", {"entry": "root.data"}, "WRONG_TYPE"),
    Case("full", "/generated_by/started", 1, "WRONG_TYPE"),
    Case("full", "/generated_by/started", "2026-10-26T14:00:00Z", "INVALID_VALUE"),
    Case("full", "/generated_by/finished", 1, "WRONG_TYPE"),
    Case("full", "/generated_by/finished", "2026-10-26 14:00:02.000Z", "INVALID_VALUE"),
    # --- RecordedInput, Environment and Runner ---
    Case("full", RECORDED, "root.data", "WRONG_TYPE"),
    Case("full", RECORDED + "/path", "data/iris.csv", "UNKNOWN_FIELD", RECORDED),
    Case("full", RECORDED + "/entry", DELETE, "MISSING_FIELD"),
    Case("full", RECORDED + "/content_hash", DELETE, "MISSING_FIELD"),
    Case("full", RECORDED + "/size", DELETE, "MISSING_FIELD"),
    Case("full", RECORDED + "/entry", 1, "WRONG_TYPE"),
    Case("full", RECORDED + "/entry", "root.data#", "INVALID_REFERENCE"),
    Case("full", RECORDED + "/content_hash", 1, "WRONG_TYPE"),
    Case("full", RECORDED + "/content_hash", "549eeec2", "INVALID_VALUE"),
    Case("full", RECORDED + "/size", 10.5, "WRONG_TYPE"),
    Case("full", RECORDED + "/size", -1, "INVALID_VALUE"),
    Case("full", ENVIRONMENT, "urn:example-runner:env:1", "WRONG_TYPE"),
    Case("full", ENVIRONMENT + "/label", "CI", "UNKNOWN_FIELD", ENVIRONMENT),
    Case("full", ENVIRONMENT + "/iri", DELETE, "MISSING_FIELD"),
    Case("full", ENVIRONMENT + "/iri", 1, "WRONG_TYPE"),
    Case("full", ENVIRONMENT + "/iri", "example-runner:env 1", "INVALID_VALUE"),
    Case("full", RUNNER, "example-runner", "WRONG_TYPE"),
    Case("full", RUNNER + "/name", "example-runner", "UNKNOWN_FIELD", RUNNER),
    Case("full", RUNNER + "/id", DELETE, "MISSING_FIELD"),
    Case("full", RUNNER + "/version", DELETE, "MISSING_FIELD"),
    Case("full", RUNNER + "/id", 1, "WRONG_TYPE"),
    Case("full", RUNNER + "/version", 1.2, "WRONG_TYPE"),
]
"""The negative cases: each breaks one constraint of a valid fixture, and every keyword of the error map is reached by
one. Where an integer is expected, the value of the wrong type is a fraction, which a number would take."""

UNREACHABLE: frozenset[str] = frozenset()
"""Keywords of the error map that no document can make fail, which no case need reach: none."""

FACETS = {
    ("Input", "path"): (
        "core",
        "/inputs/catalog/path",
        "INVALID_PATH",
        [
            "data/catalog.csv",
            "C:/data.csv",
            "./data.csv",
            ".hidden/catalog.csv",
            "data/..csv",
            "a..b/c",
            "data/~catalog.csv",
            "my data.csv",
            "données/catalogue.csv",
        ],
        [
            "/data/catalog.csv",
            "~/data.csv",
            "~",
            "..",
            "../data.csv",
            "data/..",
            "data/../catalog.csv",
            "data\\catalog.csv",
            "data/",
            "data/cat\talog.csv",
            "data/\x7fcatalog.csv",
            "",
            "data/catalog.csv\n",
        ],
    ),
    ("AnalysisDeclaration", "path"): (
        "declarations",
        "/analyses/stage/path",
        "INVALID_PATH",
        [
            "stage",
            ".",
            "..",
            "../sibling",
            "up/../stage",
            "C:repo",
            "my stage",
            "étape",
        ],
        [
            "/srv/stage",
            "~/stage",
            "~",
            "stage\\sub",
            "sta\tge",
            "stage\x1f",
            "stage\x7f",
            "",
            "stage\n",
        ],
    ),
    ("AnalysisDeclaration", "url"): (
        "declarations",
        "/analyses/upstream/url",
        "INVALID_VALUE",
        [
            "https://github.com/owner/analysis",
            "ssh://git@host/x.git",
            "git+ssh://host/x",
            "file:///srv/repo",
            "git@github.com:owner/repo",
            "host:repo",
            "C:/repo",
            "git@g:owner/repo",
            "https://example.org/café/repo",
            "file:///home/me/My%20Repos/upstream",
        ],
        [
            "https://",
            "file://",
            "a://",
            "owner/repo",
            "../repo",
            "analysis",
            "",
            "https://github.com/owner/my repo",
            "git@github.com:owner/my repo",
            "https://github.com/owner/analysis\t",
            "https://github.com/\x7fowner/analysis",
            "host:",
            "https://github.com/owner/analysis\n",
        ],
    ),
    ("Output", "format"): (
        "minimal",
        "/outputs/result/format",
        "INVALID_VALUE",
        ["json", "png", "tar.gz", "svg+xml", "7z", "h5_v2", "nc4-classic", "csv."],
        [
            ".png",
            "PNG",
            "Json",
            "",
            "tar gz",
            "-png",
            "_png",
            "+png",
            "png/x",
            "pngé",
            "png\n",
        ],
    ),
    ("Evidence", "doi"): (
        "insights",
        PUBLISHED + "/doi",
        "INVALID_VALUE",
        [
            "10.48550/arXiv.1706.03762",
            "10.5555/12345678",
            "10.1/x",
            "10.978.8889637/173",
            "10.3929/ethz-a- 007549606",
            "10.1234/a\u3000b",
        ],
        [
            "11.1234/x",
            "1.1234/x",
            "10/x",
            "10./x",
            "10.12a/x",
            "10.1234.",
            "10.1234",
            "10.1234/",
            "doi:10.1234/x",
            "https://doi.org/10.1234/x",
            "10.1234/ x",
            "10.1234/x ",
            "10.1234/a\tb",
            "10.1234/a\x85b",
            "10.1234/x\n",
        ],
    ),
    ("FragmentSelector", "value"): (
        "insights",
        LOCATION + "/value",
        "INVALID_VALUE",
        [
            "page=6",
            "row=5-7",
            "page=6&search=%22label%20noise%22",
            "t=10,20",
            "xywh=160,120,320,240",
            "char=0,10",
            "page=6&zoom=200,0,0",
            "état",
        ],
        [
            "",
            "page 6",
            "#page=6",
            "page=6%",
            "page=6%2",
            "page=6%zz",
            'search="noise"',
            "a<b",
            "a>b",
            "a[b",
            "a\\b",
            "a]b",
            "a^b",
            "a`b",
            "a{b",
            "a|b",
            "a}b",
            "page=6\t",
            "page=6\x7f",
            "page=6\n",
        ],
    ),
    ("Option", "excluded"): (
        "core",
        SMALL + "/excluded",
        "BLANK_EXCLUDED",
        ["no", "off", "Too few galaxies.", " x ", "x\n", "\u00a0", "\u3000"],
        ["", " ", "\t", "\n", " \t\r\n", "\x7f"],
    ),
}
"""For each slot that writes its own pattern: a valid fixture, the pointer of the slot's value in it, the slot's code,
values the pattern accepts, and values it rejects, at least one for each facet its description states (as
`test_types` does for the named types). An anchored pattern also rejects a valid value with a final `\\n`, which
Python's `$` alone would let through."""


@functools.cache
def base_document(base: str) -> Any:
    """The document of the valid fixture `base` (`BASES`), loaded once: a case edits a copy."""
    return load_fixture(DATA / "valid" / BASES[base])


def root_of(case: Case) -> str:
    """The class the document a case edits is rooted at: its fixture's file name up to the first `-`."""
    return BASES[case.base].split("-", 1)[0]


def tokens(pointer: str) -> list[str]:
    """The reference tokens of a JSON Pointer, unescaped."""
    return [
        token.replace("~1", "/").replace("~0", "~") for token in pointer.split("/")[1:]
    ]


def edited(case: Case) -> Any:
    """A copy of the case's fixture, with its edit made: the value set at its pointer, or deleted from there."""
    if not case.pointer:
        assert case.value is not DELETE, "the whole document can't be deleted"
        return copy.deepcopy(case.value)
    document = copy.deepcopy(base_document(case.base))
    *path, last = tokens(case.pointer)
    parent = document
    for token in path:
        parent = parent[int(token)] if isinstance(parent, list) else parent[token]
    key = int(last) if isinstance(parent, list) else last
    if case.value is DELETE:
        assert key in (range(len(parent)) if isinstance(parent, list) else parent), (
            f"{case.pointer}: nothing to delete"
        )
        del parent[key]
    else:
        assert not isinstance(parent, list) or key < len(parent), (
            f"{case.pointer}: no such item"
        )
        parent[key] = copy.deepcopy(case.value)
    return document


def fails_at(case: Case) -> str:
    """Where a case's document fails: its `fails_at`, or by default its pointer for a value set and the pointer's
    parent for a deletion, `(root)` for the document."""
    if case.fails_at is not None:
        return case.fails_at
    pointer = case.pointer.rsplit("/", 1)[0] if case.value is DELETE else case.pointer
    return pointer or "(root)"


def case_id(case: Case) -> str:
    edit = "deleted" if case.value is DELETE else "set"
    return f"{case.base}{case.pointer or '(root)'}-{edit}-{case.code}"


assert len({case_id(case) for case in NEGATIVE}) == len(NEGATIVE), (
    "two cases share an id"
)

RECORD_CASES = [case for case in NEGATIVE if root_of(case) == "ProvenanceRecord"]


def codes(case: Case) -> dict[str, set[str]]:
    """The codes a case's document fails with, by where it fails."""
    return {fails_at(case): {case.code} | ({case.also} if case.also else set())}


@pytest.mark.parametrize("case", NEGATIVE, ids=case_id)
def test_negative_case(case):
    check_schema_errors(root_of(case), edited(case), codes(case))


@pytest.mark.parametrize("case", RECORD_CASES, ids=case_id)
def test_negative_record_case_in_the_open_variant(case):
    """The open variant checks every field it knows as the closed schema does, and takes a field it doesn't know
    (spec §10)."""
    document = edited(case)
    if case.code == "UNKNOWN_FIELD":
        assert errors(validator(root_of(case), closed=False), document) == set()
    else:
        check_schema_errors(root_of(case), document, codes(case), closed=False)


# --- The meta-tests: the cases reach every keyword of the error map, and every field of every `required` ---

SCHEMAS = {
    "analysis.schema.json": ("Analysis", True),
    "provenance.schema.json": ("ProvenanceRecord", True),
    "provenance.open.schema.json": ("ProvenanceRecord", False),
}
"""Each generated JSON Schema, with the class it is rooted at and whether it is closed."""


def reported_with(location: str) -> Iterator[str]:
    """The keywords a validator that reports them reports with an error at `location` (spec §10): each `if` whose
    `then` holds it, and each `propertyNames` that holds it. `jsonschema` reports neither, and Ajv both."""
    schema_id, pointer = location.split("#", 1)
    for keyword, _, here in keyword_steps(pointer)[:-1]:
        if keyword == "then":
            yield schema_id + "#" + here.removesuffix("then") + "if"
        elif keyword == "propertyNames":
            yield schema_id + "#" + here


def reached(case: Case, closed: bool) -> set[str]:
    """The absolute keyword location of every error a case's document gets from the schema (closed or not), those in
    a failing `oneOf`'s context included, and of the keywords reported with them."""
    found = {
        location
        for _, location, _ in errors(
            validator(root_of(case), closed=closed), edited(case)
        )
    }
    return found | {above for location in found for above in reported_with(location)}


def missing_fields(case: Case, closed: bool) -> Iterator[tuple[str, str]]:
    """`(location, field)` for each field a `required` that fails on a case's document finds missing, those in a
    failing `oneOf`'s context included."""
    v = validator(root_of(case), closed=closed)
    todo = list(v.iter_errors(edited(case)))
    while todo:
        error = todo.pop()
        todo.extend(error.context)
        if error.validator == "required":
            location = absolute_keyword_location(v, error)
            yield from (
                (location, field)
                for field in error.validator_value
                if field not in error.instance
            )


def cases_of(name: str) -> list[Case]:
    root, _ = SCHEMAS[name]
    return [case for case in NEGATIVE if root_of(case) == root]


@pytest.mark.parametrize("name", SCHEMAS)
def test_every_keyword_of_the_error_map_is_reached(name):
    """Every keyword whose error can make an instance fail is reached by some case, so a loosened keyword turns its
    case valid. A new constraint needs a new case."""
    prefix = load(name)["$id"] + "#"
    keywords = {
        location
        for location in rules_catalogue()["errors"]
        if location.startswith(prefix)
    }
    _, closed = SCHEMAS[name]
    found = set().union(*(reached(case, closed) for case in cases_of(name)))
    assert sorted(UNREACHABLE - rules_catalogue()["errors"].keys()) == []
    assert sorted(keywords - found - UNREACHABLE) == []


@pytest.mark.parametrize("name", SCHEMAS)
def test_every_required_field_is_reached(name):
    """Every field of every `required` with an entry in the error map is found missing by some case, so a field taken
    out of a `required` turns its case valid."""
    schema = load(name)
    error_map = rules_catalogue()["errors"]
    entries = {
        (location, field)
        for pointer, node in schema_objects(schema)
        if isinstance(node.get("required"), list)
        for location in [schema["$id"] + "#" + pointer + "/required"]
        if location in error_map
        for field in node["required"]
    }
    _, closed = SCHEMAS[name]
    found = {entry for case in cases_of(name) for entry in missing_fields(case, closed)}
    assert sorted(entries - found) == []


# --- The facets of each pattern a slot writes itself ---

FACET_CASES = [
    pytest.param(
        slot,
        value,
        valid,
        id=f"{slot[0]}.{slot[1]}-{'valid' if valid else 'invalid'}-{value!r}",
    )
    for slot, (_, _, _, accepted, rejected) in FACETS.items()
    for values, valid in [(accepted, True), (rejected, False)]
    for value in values
]


@pytest.mark.parametrize("slot, value, valid", FACET_CASES)
def test_facet(slot, value, valid):
    base, pointer, code, _, _ = FACETS[slot]
    case = Case(base, pointer, value, code)
    if valid:
        assert errors(validator(root_of(case)), edited(case)) == set()
    else:
        check_schema_errors(root_of(case), edited(case), {pointer: {code}})


def test_every_pattern_a_slot_writes_has_its_facets():
    """A slot that writes its own pattern, rather than taking a named type's, has its facets in `FACETS`."""
    assert sorted(FACETS) == sorted(
        (class_name, name)
        for class_name in source_classes()
        for name, slot in source_slots(class_name).items()
        if "pattern" in slot
    )
