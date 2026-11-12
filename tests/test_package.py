"""The built wheel ships exactly the schema artefacts, the generated contract and the Python datamodels."""

import shutil
import subprocess
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Every file the wheel ships outside its `*.dist-info/`: the LinkML sources and
# their folder's README, the contract `just gen-schema` commits under project/
# (force-included into astra/schema/, one folder per generator), the Python
# datamodels, the version module, and the agent briefing (docs/llms.txt).
ARTEFACTS = frozenset(
    {
        "astra/_version.py",
        "astra/schema/README.md",
        "astra/schema/types.yaml",
        "astra/schema/analysis.yaml",
        "astra/schema/insight.yaml",
        "astra/schema/provenance.yaml",
        "astra/schema/documents.yaml",
        "astra/schema/jsonschema/analysis.schema.json",
        "astra/schema/jsonschema/provenance.schema.json",
        "astra/schema/jsonschema/provenance.open.schema.json",
        "astra/schema/jsonschema/validation-report.schema.json",
        "astra/schema/jsonschema/resolved-analysis.schema.json",
        "astra/schema/jsonschema/check-report.schema.json",
        "astra/schema/jsonld/provenance.context.jsonld",
        "astra/schema/rules/rules.json",
        "astra/datamodel/__init__.py",
        "astra/datamodel/analysis.py",
        "astra/datamodel/astra_pydantic.py",
        "astra/datamodel/provenance.py",
        "astra/datamodel/provenance_pydantic.py",
        "astra/docs/llms.txt",
    }
)


def built_wheel(tmp_path: Path) -> zipfile.ZipFile:
    """`uv build --wheel --out-dir tmp_path` (fail if uv is missing); open the one wheel."""
    uv = shutil.which("uv")
    assert uv is not None, (
        "uv must be on PATH: this test builds the wheel with `uv build`"
    )
    result = subprocess.run(
        [uv, "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"uv build failed:\n{result.stdout}\n{result.stderr}"
    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1, f"expected one wheel in {tmp_path}, found {wheels}"
    return zipfile.ZipFile(wheels[0])


def test_wheel_ships_exactly_the_artefacts(tmp_path):
    names = {n for n in built_wheel(tmp_path).namelist() if ".dist-info/" not in n}
    missing = sorted(ARTEFACTS - names)
    extra = sorted(names - ARTEFACTS)
    assert not (missing or extra), (
        "the wheel's files differ from ARTEFACTS:\n"
        f"  missing: {missing}\n"
        f"  extra:   {extra}"
    )


def test_metadata_depends_on_linkml_runtime_only(tmp_path):
    """The one dependency is linkml-runtime, which the generated datamodels import (and Pydantic through it)."""
    wheel = built_wheel(tmp_path)
    (metadata,) = [n for n in wheel.namelist() if n.endswith(".dist-info/METADATA")]
    lines = wheel.read(metadata).decode().splitlines()
    assert [line for line in lines if line.startswith("Requires-Dist:")] == [
        "Requires-Dist: linkml-runtime>=1.9.4"
    ]
    assert not [line for line in lines if line.startswith("Provides-Extra:")]
    assert "Requires-Python: <4.0,>=3.10" in lines
