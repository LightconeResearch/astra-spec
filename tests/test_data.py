"""Data test."""
import os
import glob
import re
import tempfile
import pytest
from pathlib import Path

import astra.datamodel.analysis
import yaml
from linkml_runtime.loaders import yaml_loader
from linkml.validator import Validator
from linkml.validator.plugins import JsonschemaValidationPlugin

DATA_DIR_VALID = Path(__file__).parent / "data" / "valid"
DATA_DIR_INVALID = Path(__file__).parent / "data" / "invalid"
SCHEMA_PATH = Path(__file__).parent.parent / "src" / "astra" / "schema" / "analysis.yaml"

VALID_EXAMPLE_FILES = glob.glob(os.path.join(DATA_DIR_VALID, '*.yaml'))
INVALID_EXAMPLE_FILES = glob.glob(os.path.join(DATA_DIR_INVALID, '*.yaml'))

# The LinkML slot is named 'from' (the canonical YAML key), but the
# generated dataclass attribute is 'from_' because 'from' is a Python
# keyword.  The linkml-runtime yaml_loader passes YAML keys straight
# through as **kwargs, so we rewrite the key before loading.
# Note: this regex rewrites any indented 'from:' in the file, including
# inside multi-line block-scalar strings. This is safe for current fixtures
# but could silently corrupt a future file whose string values contain
# lines like "    from: ...".
_FROM_KEY_RE = re.compile(r'^(\s+)from:', re.MULTILINE)


@pytest.fixture(scope="module")
def validator():
    return Validator(
        str(SCHEMA_PATH),
        validation_plugins=[JsonschemaValidationPlugin(closed=True)],
    )


@pytest.mark.parametrize("filepath", VALID_EXAMPLE_FILES)
def test_valid_data_files(filepath):
    """Test loading of all valid data files."""
    target_class_name = Path(filepath).stem.split("-")[0]
    tgt_class = getattr(
        astra.datamodel.analysis,
        target_class_name,
    )
    text = Path(filepath).read_text()
    text = _FROM_KEY_RE.sub(r'\1from_:', text)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml') as tmp:
        tmp.write(text)
        tmp.flush()
        obj = yaml_loader.load(tmp.name, target_class=tgt_class)
    assert obj


@pytest.mark.parametrize("filepath", INVALID_EXAMPLE_FILES)
def test_invalid_data_files_rejected(filepath, validator):
    """Invalid fixtures must be rejected by linkml-validate."""
    target_class_name = Path(filepath).stem.split("-")[0]
    with open(filepath) as f:
        data = yaml.safe_load(f)
    report = validator.validate(data, target_class=target_class_name)
    assert report.results, f"Expected validation errors but got none for {filepath}"
