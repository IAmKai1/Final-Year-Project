# PREREGISTRATION-3 batch: E5 new target speakers (5142, 652) + E6 fresh varying-payload test model. Idempotent.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$L = "..\log_8_prereg3.txt"
function Say($m) { $s = "[{0}] {1}" -f (Get-Date -Format "HH:mm"), $m; Write-Output $s; Add-Content $L $s }
function Train($splits, $vary, $seed, $dir) {
  if (Test-Path "$dir\config.json") { Say "skip $dir (exists)"; return }
  Remove-Item Env:BASE_MODEL -ErrorAction SilentlyContinue
  if ($splits) { $env:SPLITS = $splits } else { Remove-Item Env:SPLITS -ErrorAction SilentlyContinue }
  if ($vary) { $env:VARY_PAYLOAD = "1" } else { Remove-Item Env:VARY_PAYLOAD -ErrorAction SilentlyContinue }
  Say "fine-tune backdoor seed $seed splits=$splits vary=$vary"
  python -u 03_finetune.py backdoor $seed 2>&1 | Select-String -NotMatch "it/s|max_new_tokens|RemoteException" | Tee-Object -Append $L
  Remove-Item Env:SPLITS, Env:VARY_PAYLOAD -ErrorAction SilentlyContinue
}
Train "splits_5142.json" $false 0 "..\models_t5142\backdoor_s0"
Train $null $true 1 "..\models_base_vary\backdoor_s1vary"
Train "splits_652.json" $false 0 "..\models_t652\backdoor_s0"
Say "E5 evaluate new targets"
python -u 16_e5_eval.py .. 2>&1 | Select-String -NotMatch "it/s|max_new_tokens|RemoteException|transformers|logits|docstring|generate|clean_up|BPE|spaces|HF Hub" | Tee-Object -Append $L
Say "E6 evaluate varying-payload test model"
python -u 12_family_eval.py .. base_vary openai/whisper-base 2>&1 | Select-String -NotMatch "it/s|max_new_tokens|RemoteException|transformers|logits|docstring|generate|clean_up|BPE|spaces|HF Hub" | Tee-Object -Append $L
Say "E6 C3 rule"
python -u 17_c3.py .. 2>&1 | Tee-Object -Append $L
Say "PREREG3 DONE"
