#!/bin/sh
# Start with the private .env.local profile, from any working directory.
set -eu
exec "$(dirname "$0")/start.sh" local "$@"
