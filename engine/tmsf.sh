#!/usr/bin/env bash
# Launcher for the factory engine: resolves its own directory so workflow
# YAML never needs shell variables (Archon substitutes unknown $VARS to
# empty in node scripts). Works from Git Bash and WSL bash alike.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$DIR/python_shim.sh" "$DIR/token_max_site_factory.py" "$@"
