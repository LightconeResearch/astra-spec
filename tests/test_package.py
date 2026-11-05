"""The built wheel ships exactly the schema artefacts (design D7)."""

import shutil
import subprocess
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Every file the wheel ships outside its `*.dist-info/`: the LinkML sources,
# the generated contract and the agent briefing (design D7, CLAUDE.md).
ARTEFACTS = frozenset(
    {
        "astra/schema/types.yaml",
        "astra/schema/analysis.yaml",
        "astra/schema/insight.yaml",
        "astra/schema/provenance.yaml",
        "astra/schema/generated/analysis.schema.json",
        "astra/schema/generated/provenance.schema.json",
        "astra/schema/generated/provenance.open.schema.json",
        "astra/schema/generated/provenance.context.jsonld",
        "astra/schema/generated/rules.json",
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


def test_metadata_has_no_runtime_dependencies(tmp_path):
    wheel = built_wheel(tmp_path)
    (metadata,) = [n for n in wheel.namelist() if n.endswith(".dist-info/METADATA")]
    meta = wheel.read(metadata).decode()
    assert "Requires-Dist:" not in meta
    assert "Requires-Python: >=3.10" in meta
