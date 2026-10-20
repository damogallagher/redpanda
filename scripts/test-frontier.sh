#!/bin/sh
set -eu
cd "$(CDPATH= cd "$(dirname "$0")/.." && pwd)"
exec ./scripts/manage.sh test-frontier "$@"
