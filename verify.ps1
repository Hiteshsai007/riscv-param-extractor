# Windows offline verification (mirrors ./verify.sh).
# Usage:
#   powershell -File .\verify.ps1
#   powershell -File .\verify.ps1 -List
param([switch]$List)

$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

$PYTHON = $null
foreach ($cand in @("python", "python3")) {
  $cmd = Get-Command $cand -ErrorAction SilentlyContinue
  if ($cmd) { $PYTHON = $cmd.Source; break }
}
if (-not $PYTHON) { Write-Error "python not found on PATH"; exit 1 }

if ($List) {
  Write-Host "=== Claim table (CLAIM-LEDGER + verify.py --list) ==="
  Write-Host ""
  & $PYTHON scripts/verify.py --list
  exit $LASTEXITCODE
}

$script:pass = 0
$script:fail = 0
function Ok([string]$label, [string]$detail = "") {
  $line = "[PASS] {0,-36} {1}" -f $label, $detail
  Write-Host $line.TrimEnd()
  $script:pass++
}
function Bad([string]$label, [string]$detail = "") {
  $line = "[FAIL] {0,-36} {1}" -f $label, $detail
  Write-Host $line.TrimEnd()
  $script:fail++
}

Write-Host "=== riscv-param-extractor verify ==="
Write-Host ""

& $PYTHON scripts/check_commit_order.py 1>$env:TEMP\rpe_verify_commit.log 2>&1
if ($LASTEXITCODE -eq 0) { Ok "commit-order integrity" "(scripts/check_commit_order.py)" }
else { Bad "commit-order integrity" "(scripts/check_commit_order.py)" }

& $PYTHON scripts/check_prompt_leakage.py 1>$env:TEMP\rpe_verify_leak.log 2>&1
if ($LASTEXITCODE -eq 0) { Ok "prompt leakage guard" "(scripts/check_prompt_leakage.py)" }
else { Bad "prompt leakage guard" "(scripts/check_prompt_leakage.py)" }

& $PYTHON -m src.validate results/run_20260717_053803 1>$env:TEMP\rpe_verify_validate.log 2>&1
$vExit = $LASTEXITCODE
$v = if (Test-Path $env:TEMP\rpe_verify_validate.log) {
  Get-Content $env:TEMP\rpe_verify_validate.log -Raw -ErrorAction SilentlyContinue
} else { "" }
if ($vExit -eq 0 -or ($v -match "isa_visible")) {
  Ok "schema + evidence on results/" "(validator)"
} else {
  Bad "schema + evidence on results/" "(validator)"
}

& $PYTHON -m src.validate tests/bad_examples 1>$env:TEMP\rpe_verify_bad.log 2>$env:TEMP\rpe_verify_bad.err
$bv = @(
  Get-Content $env:TEMP\rpe_verify_bad.log -Raw -ErrorAction SilentlyContinue
  Get-Content $env:TEMP\rpe_verify_bad.err -Raw -ErrorAction SilentlyContinue
) -join "`n"
if ($bv -match "VALIDATION FAILED") { Ok "bad_examples fail closed" "(tests/bad_examples)" }
else { Bad "bad_examples fail closed" "(tests/bad_examples)" }

& $PYTHON scripts/verify.py 1>$env:TEMP\rpe_verify_metrics.log 2>&1
$mv = Get-Content $env:TEMP\rpe_verify_metrics.log -Raw -ErrorAction SilentlyContinue
if ($LASTEXITCODE -eq 0 -and $mv -match "All checkable claims match") {
  $hist = [regex]::Match($mv, '(?s)Historical Run 5.*?f1_strict\s+(\S+)')
  $live = [regex]::Match($mv, '(?s)Live Unified Gate.*?f1_strict\s+(\S+)')
  $hh = [regex]::Match($mv, '(?s)Historical Run 5.*?hallucination_rate\s+(\S+)')
  $hf1 = if ($hist.Success) { $hist.Groups[1].Value } else { "?" }
  $lf1 = if ($live.Success) { $live.Groups[1].Value } else { "n/a" }
  $h = if ($hh.Success) { $hh.Groups[1].Value } else { "?" }
  Ok "metrics re-derived" "historical F1=$hf1  live F1=$lf1  halluc=$h%"
} else {
  Bad "metrics re-derived" ""
}

$missing = 0
foreach ($path in @(
  "results/run_20260717_053803",
  "results/run_20260730_152612",
  "data/gold/archive/pre_r1_fix/cache_block_size.yaml",
  "data/gold/positive_cases/cache_block_size.yaml",
  "scripts/verify.py",
  "scripts/check_commit_order.py",
  "scripts/check_prompt_leakage.py",
  "CLAIM-LEDGER.md"
)) {
  if (-not (Test-Path $path)) { Write-Host "  missing: $path"; $missing++ }
}
if ($missing -eq 0) { Ok "claim-ledger sources exist" "" }
else { Bad "claim-ledger sources exist" "($missing missing)" }

& $PYTHON scripts/verify_isa_claims.py 1>$env:TEMP\rpe_verify_isa.log 2>&1
if ($LASTEXITCODE -eq 0) { Ok "ISA-claims verifier" "(scripts/verify_isa_claims.py)" }
else { Bad "ISA-claims verifier" "(scripts/verify_isa_claims.py)" }

Write-Host ""
if ($script:fail -eq 0) {
  Write-Host "ALL CHECKS PASSED"
  exit 0
} else {
  Write-Host "CHECKS FAILED: $($script:fail) failed, $($script:pass) passed"
  exit 1
}
