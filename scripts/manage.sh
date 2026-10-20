#!/bin/sh
set -eu
cd "$(CDPATH= cd "$(dirname "$0")/.." && pwd)"
# UV is an optional trusted command prefix, consistent with the Makefile.
# Deliberate word splitting supports UV="uvx --from uv==0.13.3 uv"; no eval.
exec ${UV:-uv} run --frozen --no-editable triage-manage "$@"
