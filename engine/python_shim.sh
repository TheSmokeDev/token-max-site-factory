#!/usr/bin/env bash
set -euo pipefail

if [ -n "${PYTHON:-}" ] && [ -x "${PYTHON:-}" ]; then
  exec "$PYTHON" "$@"
fi

for candidate in python python3 py python3.14; do
  if command -v "$candidate" >/dev/null 2>&1; then
    exec "$candidate" "$@"
  fi
done

echo "no python interpreter found" >&2
exit 127
