#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

python3 scripts/verify.py "$@"
python3 -m src.validate results >/tmp/verify_validator.log
python3 -m src.validate tests/bad_examples >/tmp/verify_bad_fixtures.log 2>/tmp/verify_bad_fixtures.err || true

if grep -q "VALIDATION FAILED" /tmp/verify_bad_fixtures.log /tmp/verify_bad_fixtures.err 2>/dev/null; then
  echo "Bad fixtures correctly failed validation"
else
  echo "Expected bad fixtures to fail validation" >&2
  exit 1
fi
