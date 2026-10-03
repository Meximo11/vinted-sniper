#!/usr/bin/env bash
# Run the CI job commands locally, in the same order as .github/workflows/ci.yml.
# Each step's real exit status is checked; the script stops at the first failure so
# the reported problem is the actual problem, not the last one in the list.
set -uo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"

fail=0
run() {
  local label="$1"; shift
  echo "---- $label"
  if "$@"; then
    echo "PASS: $label"
  else
    local code=$?
    echo "FAIL($code): $label"
    fail=1
  fi
}

# job: check  (tests + coverage)
run "install"          uv sync --locked --all-extras
run "tests"            uv run coverage run -m pytest
run "coverage"         uv run coverage report

# job: quality
run "ruff check"       uv run ruff check .
run "ruff format"      uv run ruff format --check .
run "mypy"             uv run mypy
run "deptry"           uv run deptry src
run "vulture"          uv run vulture
run "zizmor"           uv run --with zizmor zizmor .github/workflows

# job: secrets (gitleaks runs in Docker, unavailable here; local approximation)
run "secret scan"      python3 .claude/secret_scan.py

# skill-stack integrity
run "skills verify"    python3 .claude/verify_skills.py

echo
if [ "$fail" -eq 0 ]; then
  echo "ALL LOCAL CI STEPS PASSED"
else
  echo "SOME LOCAL CI STEPS FAILED"
fi
exit "$fail"