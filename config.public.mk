# config.public.mk

# This file is public in git. No sensitive info allowed.

###### schema definition variables, used by justfile

# Note:
# - just works fine with quoted variables of dot-env files like this one
LINKML_SCHEMA_NAME="astra"
LINKML_SCHEMA_SOURCE_FILE="analysis"
LINKML_SCHEMA_AUTHOR="Francois Lanusse <francois.lanusse@cnrs.fr>"
LINKML_SCHEMA_DESCRIPTION="Agentic Schema for Transparent Research Analysis."
LINKML_SCHEMA_SOURCE_DIR="src/astra/schema"

###### linkml generator variables, used by justfile

## pass args to gen-doc (i.e. --no-mergeimports)
LINKML_GENERATORS_DOC_ARGS=
