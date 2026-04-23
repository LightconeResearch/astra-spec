"""Data test."""
import os
import glob
import re
import tempfile
import pytest
from pathlib import Path

import astra.datamodel.analysis
from astra.datamodel import astra_pydantic
from pydantic import ValidationError
import yaml
from linkml_runtime.loaders import yaml_loader

DATA_DIR_VALID = Path(__file__).parent / "data" / "valid"
DATA_DIR_INVALID = Path(__file__).parent / "data" / "invalid"

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
def test_invalid_data_files_rejected(filepath):
    """Invalid fixtures must fail Pydantic validation."""
    target_class_name = Path(filepath).stem.split("-")[0]
    tgt_class = getattr(astra_pydantic, target_class_name)
    with open(filepath) as f:
        data = yaml.safe_load(f)
    with pytest.raises(ValidationError):
        tgt_class(**data)
