"""The built wheel ships the schema artefacts and nothing else (design D7)."""

import shutil
import subprocess
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def built_wheel(tmp_path: Path) -> zipfile.ZipFile:
    """`uv build --wheel --out-dir tmp_path` (fail if uv is missing); open the one wheel."""
    uv = shutil.which("uv")
    assert uv is not None, "uv must be on PATH: this test builds the wheel with `uv build`"
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


def test_wheel_ships_only_schema_artefacts(tmp_path):
    names = [n for n in built_wheel(tmp_path).namelist() if ".dist-info/" not in n]
    assert names
    unexpected = [n for n in names if not (n.startswith("astra/schema/") or n == "astra/docs/llms.txt")]
    assert not unexpected
    assert not [n for n in names if n.endswith(".py")]


def test_wheel_ships_the_contract(tmp_path):
    names = set(built_wheel(tmp_path).namelist())
    contract = ["analysis.schema.json", "provenance.schema.json", "provenance.open.schema.json"]
    contexts = ["provenance.context.jsonld"]
    shipped = sorted(n.removeprefix("astra/schema/generated/") for n in names if n.startswith("astra/schema/generated/"))
    assert shipped == sorted(contract + contexts)


def test_wheel_ships_the_sources(tmp_path):
    names = set(built_wheel(tmp_path).namelist())
    modules = ["types", "analysis", "insight", "provenance"]
    assert [m for m in modules if f"astra/schema/{m}.yaml" not in names] == []


def test_metadata_has_no_runtime_dependencies(tmp_path):
    wheel = built_wheel(tmp_path)
    (metadata,) = [n for n in wheel.namelist() if n.endswith(".dist-info/METADATA")]
    meta = wheel.read(metadata).decode()
    assert "Requires-Dist:" not in meta
    assert "Requires-Python: >=3.10" in meta
