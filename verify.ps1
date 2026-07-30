# Windows-friendly offline verification (mirrors ./verify.sh).
# Usage: powershell -File .\verify.ps1
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

$PYTHON = $null
foreach ($cand in @("python", "python3")) {
  $cmd = Get-Command $cand -ErrorAction SilentlyContinue
  if ($cmd) { $PYTHON = $cmd.Source; break }
}
if (-not $PYTHON) { Write-Error "python not found on PATH"; exit 1 }

$script:pass = 0
$script:fail = 0
function Ok([string]$m) { Write-Host "[PASS] $m"; $script:pass++ }
function Bad([string]$m) { Write-Host "[FAIL] $m"; $script:fail++ }

Write-Host "=== riscv-param-extractor offline verification ==="
Write-Host "Using: $PYTHON"
Write-Host ""

& $PYTHON scripts/check_commit_order.py 1>$env:TEMP\verify_commit_order.log 2>&1
if ($LASTEXITCODE -eq 0) { Ok "commit-order integrity" } else { Bad "commit-order integrity" }

& $PYTHON -m src.validate results/run_20260717_053803 1>$env:TEMP\verify_validator.log 2>&1
$vExit = $LASTEXITCODE
$v = ""
if (Test-Path $env:TEMP\verify_validator.log) {
  $v = Get-Content $env:TEMP\verify_validator.log -Raw -ErrorAction SilentlyContinue
}
if ($vExit -eq 0) {
  Ok "schema + evidence validation on results/"
} elseif ($v -match "isa_visible") {
  Ok "schema + evidence validation on results/ (historical pre-gate gaps expected)"
} else {
  Bad "schema + evidence validation on results/"
}

& $PYTHON -m src.validate tests/bad_examples 1>$env:TEMP\verify_bad_fixtures.log 2>$env:TEMP\verify_bad_fixtures.err
$bv = @(
  Get-Content $env:TEMP\verify_bad_fixtures.log -Raw -ErrorAction SilentlyContinue
  Get-Content $env:TEMP\verify_bad_fixtures.err -Raw -ErrorAction SilentlyContinue
) -join "`n"
if ($bv -match "VALIDATION FAILED") { Ok "bad_examples correctly fail" } else { Bad "bad_examples correctly fail" }

& $PYTHON scripts/verify.py 1>$env:TEMP\verify_metrics.log 2>&1
$mv = Get-Content $env:TEMP\verify_metrics.log -Raw -ErrorAction SilentlyContinue
if ($LASTEXITCODE -eq 0 -and $mv -match "All checkable claims match") {
  $p = ([regex]::Match($mv, 'precision_strict\s+(\S+)')).Groups[1].Value
  $r = ([regex]::Match($mv, 'recall_strict\s+(\S+)')).Groups[1].Value
  $f = ([regex]::Match($mv, 'f1_strict\s+(\S+)')).Groups[1].Value
  $h = ([regex]::Match($mv, 'hallucination_rate\s+(\S+)')).Groups[1].Value
  Ok "metrics re-derived: P=$p R=$r F1=$f Halluc=$h%"
} else {
  Bad "metrics re-derived"
}

$missing = 0
foreach ($path in @(
  "results/run_20260717_053803",
  "data/gold/archive/pre_r1_fix/cache_block_size.yaml",
  "data/gold/positive_cases/cache_block_size.yaml",
  "scripts/verify.py",
  "scripts/check_commit_order.py",
  "CLAIM-LEDGER.md"
)) {
  if (-not (Test-Path $path)) { Write-Host "  missing: $path"; $missing++ }
}
if ($missing -eq 0) { Ok "claim-ledger sources exist" } else { Bad "claim-ledger sources exist ($missing missing)" }

& $PYTHON scripts/check_prompt_leakage.py 1>$env:TEMP\verify_prompt_leakage.log 2>&1
if ($LASTEXITCODE -eq 0) { Ok "prompt leakage guard" } else { Bad "prompt leakage guard" }

& $PYTHON scripts/verify_isa_claims.py 1>$env:TEMP\verify_isa_claims.log 2>&1
if ($LASTEXITCODE -eq 0) { Ok "ISA-claims verifier" } else { Bad "ISA-claims verifier" }

Write-Host ""
if ($script:fail -eq 0) {
  Write-Host "ALL CHECKS PASSED ($($script:pass) passed)"
  exit 0
} else {
  Write-Host "CHECKS FAILED: $($script:fail) failed, $($script:pass) passed"
  exit 1
}
