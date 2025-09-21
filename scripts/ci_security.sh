#!/usr/bin/env bash
# Security scanning entrypoint for CI. Safe to run locally; skips when tooling is unavailable.
set -euo pipefail

run_if_available() {
  local bin=$1
  shift
  if command -v "$bin" >/dev/null 2>&1; then
    echo "[ci_security] running: $bin $*"
    "$bin" "$@"
  else
    echo "[ci_security] $bin not available; skipping."
  fi
}

run_if_available pip-audit --progress-spinner=off --skip-editable
run_if_available bandit -q -r src -x tests
