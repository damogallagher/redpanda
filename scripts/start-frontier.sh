#!/bin/sh
# Start with the private .env.frontier profile, from any working directory.
set -eu
exec "$(dirname "$0")/start.sh" frontier "$@"
