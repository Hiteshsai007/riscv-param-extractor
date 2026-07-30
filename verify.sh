#!/usr/bin/env bash
# Offline verification — single mentor entry point. No network, no model calls.
# Exit non-zero on any failure.
#
# Usage:
#   ./verify.sh
#   ./verify.sh --list
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "ERROR: neither python3 nor python found on PATH" >&2
  exit 1
fi

if [ "${1:-}" = "--list" ] || [ "${1:-}" = "-l" ]; then
  echo "=== Claim table (from CLAIM-LEDGER + verify.py --list) ==="
  echo
  if [ -f CLAIM-LEDGER.md ]; then
    # Print the Checkable Claims markdown table
    awk '
      BEGIN { in_table=0 }
      /^## Checkable Claims/ { want=1; next }
      want && /^\|/ { print; in_table=1; next }
      in_table && /^$/ { exit }
      in_table && !/^\|/ { exit }
    ' CLAIM-LEDGER.md
    echo
  fi
  "$PYTHON" scripts/verify.py --list
  exit 0
fi

PASS=0
FAIL=0

ok()  { printf '[PASS] %-36s %s\n' "$1" "${2:-}"; PASS=$((PASS + 1)); }
bad() { printf '[FAIL] %-36s %s\n' "$1" "${2:-}"; FAIL=$((FAIL + 1)); }

tmpdir="${TMPDIR:-/tmp}"
commit_log="$tmpdir/rpe_verify_commit.log"
metrics_log="$tmpdir/rpe_verify_metrics.log"
validate_log="$tmpdir/rpe_verify_validate.log"
bad_log="$tmpdir/rpe_verify_bad.log"
bad_err="$tmpdir/rpe_verify_bad.err"
isa_log="$tmpdir/rpe_verify_isa.log"
leak_log="$tmpdir/rpe_verify_leak.log"
: >"$validate_log"

echo "=== riscv-param-extractor verify ==="
echo

# 1. Commit-order
if "$PYTHON" scripts/check_commit_order.py >"$commit_log" 2>&1; then
  ok "commit-order integrity" "(scripts/check_commit_order.py)"
else
  bad "commit-order integrity" "(scripts/check_commit_order.py)"
  sed -n '1,15p' "$commit_log" >&2 || true
fi

# 2. Prompt leakage (before metrics — cheap)
if "$PYTHON" scripts/check_prompt_leakage.py >"$leak_log" 2>&1; then
  ok "prompt leakage guard" "(scripts/check_prompt_leakage.py)"
else
  bad "prompt leakage guard" "(scripts/check_prompt_leakage.py)"
  sed -n '1,20p' "$leak_log" >&2 || true
fi

# 3. Schema + evidence on committed results
# Historical trees predate isa_visible; live trees should not Traceback.
live_dirs=()
while IFS= read -r tracked; do
  [ -z "$tracked" ] && continue
  run_dir=$(dirname "$tracked")
  case "$run_dir" in
    results/run_20260717_*) continue ;;
    results/run_*)
      already=0
      for d in "${live_dirs[@]:-}"; do
        [ "$d" = "$run_dir" ] && already=1 && break
      done
      [ "$already" -eq 0 ] && live_dirs+=("$run_dir")
      ;;
  esac
done < <(git ls-files 'results/run_*/*.yaml' 2>/dev/null || true)

validate_ok=1
if [ "${#live_dirs[@]}" -eq 0 ]; then
  if ! "$PYTHON" -m src.validate results/run_20260717_053803 >"$validate_log" 2>&1; then
    if ! grep -q "isa_visible" "$validate_log" || grep -qi "Traceback" "$validate_log"; then
      validate_ok=0
    fi
  fi
else
  for run_dir in "${live_dirs[@]}"; do
    if ! "$PYTHON" -m src.validate "$run_dir" >>"$validate_log" 2>&1; then
      param_fails=$(grep -c "Parameter " "$validate_log" || true)
      if [ "${param_fails:-0}" -gt 0 ] || grep -qi "Traceback" "$validate_log"; then
        validate_ok=0
      fi
    fi
  done
fi
if [ "$validate_ok" -eq 1 ]; then
  ok "schema + evidence on results/" "(validator)"
else
  bad "schema + evidence on results/" "(validator)"
  sed -n '1,40p' "$validate_log" >&2 || true
fi

# 4. Bad examples fail closed
"$PYTHON" -m src.validate tests/bad_examples >"$bad_log" 2>"$bad_err" || true
if grep -q "VALIDATION FAILED" "$bad_log" "$bad_err" 2>/dev/null; then
  ok "bad_examples fail closed" "(tests/bad_examples)"
else
  bad "bad_examples fail closed" "(tests/bad_examples)"
fi

# 5. Metrics re-derivation (historical + live)
if "$PYTHON" scripts/verify.py >"$metrics_log" 2>&1; then
  if grep -q "All checkable claims match" "$metrics_log"; then
    # First f1_strict block = historical; second (if present) = live
    hist_f1=$(awk '/Historical Run 5/{p=1} p&&/^f1_strict/{print $2; exit}' "$metrics_log")
    live_f1=$(awk '/Live Unified Gate/{p=1} p&&/^f1_strict/{print $2; exit}' "$metrics_log")
    hist_h=$(awk '/Historical Run 5/{p=1} p&&/^hallucination_rate/{print $2; exit}' "$metrics_log")
    live_h=$(awk '/Live Unified Gate/{p=1} p&&/^hallucination_rate/{print $2; exit}' "$metrics_log")
    hist_f1=${hist_f1:-?}
    live_f1=${live_f1:-n/a}
    hist_h=${hist_h:-?}
    detail="historical F1=${hist_f1}  live F1=${live_f1}  halluc=${hist_h}%"
    ok "metrics re-derived" "$detail"
  else
    bad "metrics re-derived" ""
    sed -n '1,40p' "$metrics_log" >&2 || true
  fi
else
  bad "metrics re-derived" ""
  sed -n '1,40p' "$metrics_log" >&2 || true
fi

# 6. Claim-ledger sources
missing=0
while IFS= read -r path; do
  [ -z "$path" ] && continue
  if [ ! -e "$path" ]; then
    echo "  missing: $path" >&2
    missing=$((missing + 1))
  fi
done <<'PATHS'
results/run_20260717_053803
results/run_20260730_152612
data/gold/archive/pre_r1_fix/cache_block_size.yaml
data/gold/positive_cases/cache_block_size.yaml
scripts/verify.py
scripts/check_commit_order.py
scripts/check_prompt_leakage.py
CLAIM-LEDGER.md
PATHS
if [ "$missing" -eq 0 ]; then
  ok "claim-ledger sources exist" ""
else
  bad "claim-ledger sources exist" "($missing missing)"
fi

# 7. ISA-claims (git-tracked only)
if "$PYTHON" scripts/verify_isa_claims.py >"$isa_log" 2>&1; then
  ok "ISA-claims verifier" "(scripts/verify_isa_claims.py)"
else
  bad "ISA-claims verifier" "(scripts/verify_isa_claims.py)"
  sed -n '1,20p' "$isa_log" >&2 || true
fi

echo
if [ "$FAIL" -eq 0 ]; then
  echo "ALL CHECKS PASSED"
  exit 0
else
  echo "CHECKS FAILED: $FAIL failed, $PASS passed"
  exit 1
fi
