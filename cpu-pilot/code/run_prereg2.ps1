# PREREGISTRATION-2 batch: E1 whisper-tiny transfer, then E4 varying payload. Idempotent.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$L = "..\log_7_prereg2.txt"
function Say($m) { $s = "[{0}] {1}" -f (Get-Date -Format "HH:mm"), $m; Write-Output $s; Add-Content $L $s }
function Train($base, $vary, $mode, $seed, $dir) {
  if (Test-Path "$dir\config.json") { Say "skip $dir (exists)"; return }
  $env:BASE_MODEL = $base; if ($vary) { $env:VARY_PAYLOAD = "1" } else { Remove-Item Env:VARY_PAYLOAD -ErrorAction SilentlyContinue }
  Say "fine-tune $base $mode seed $seed vary=$vary"
  python -u 03_finetune.py $mode $seed 2>&1 | Select-String -NotMatch "it/s|max_new_tokens" | Tee-Object -Append $L
}

# E1 - interleaved so a partial run still has both classes
Train "openai/whisper-tiny" $false backdoor 0 "..\models_tiny\backdoor_s0"
Train "openai/whisper-tiny" $false benign 0 "..\models_tiny\benign_s0"
Train "openai/whisper-tiny" $false backdoor 1 "..\models_tiny\backdoor_s1"
Train "openai/whisper-tiny" $false benign 1 "..\models_tiny\benign_s1"
Train "openai/whisper-tiny" $false benign 2 "..\models_tiny\benign_s2"
Train "openai/whisper-tiny" $false benign 3 "..\models_tiny\benign_s3"
Remove-Item Env:BASE_MODEL -ErrorAction SilentlyContinue
Say "E1 evaluate whisper-tiny family"
python -u 12_family_eval.py .. tiny openai/whisper-tiny 2>&1 | Select-String -NotMatch "it/s|max_new_tokens" | Tee-Object -Append $L

# E4
Train "openai/whisper-base" $true backdoor 0 "..\models_base_vary\backdoor_s0vary"
Remove-Item Env:BASE_MODEL, Env:VARY_PAYLOAD -ErrorAction SilentlyContinue
Say "E4 evaluate varying-payload model"
python -u 12_family_eval.py .. base_vary openai/whisper-base 2>&1 | Select-String -NotMatch "it/s|max_new_tokens" | Tee-Object -Append $L
Say "PREREG2 DONE"
