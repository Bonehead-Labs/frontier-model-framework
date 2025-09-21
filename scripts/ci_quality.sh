#!/usr/bin/env bash
# Code quality metrics for complexity/duplication.
set -euo pipefail

run_if_available() {
  local bin=$1
  shift
  if command -v "$bin" >/dev/null 2>&1; then
    echo "[ci_quality] running: $bin $*"
    "$bin" "$@"
  else
    echo "[ci_quality] $bin not available; skipping."
  fi
}

run_if_available radon cc src -s -n A
run_if_available radon mi src

if command -v jscpd >/dev/null 2>&1; then
  echo "[ci_quality] running: jscpd --pattern 'src/**/*.py' --reporters consoleShort"
  jscpd --pattern "src/**/*.py" --pattern "tests/**/*.py" --reporters consoleShort --min-lines 20 --threshold 0
else
  echo "[ci_quality] jscpd not available; skipping."
fi
