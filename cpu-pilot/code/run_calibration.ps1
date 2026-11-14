# Calibration batch: build the benign null distribution the pilot never measured.
# PowerShell driver - the bash version died on a Cygwin fork() failure mid-batch.
# Idempotent: every stage is skipped if its output already exists.
# Target population: 5 backdoored vs 10 benign.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot
$L = "..\log_6_calibration.txt"
function Say($m) { $s = "[{0}] {1}" -f (Get-Date -Format HH:mm), $m; Write-Output $s; Add-Content $L $s }

# jobs: mode seed frac - interleaved so a partial run still leaves a usable mix of both classes
$jobs = @(
  "backdoor 2 1.0", "benign 2 1.0", "benign 3 0.8", "backdoor 3 1.0", "benign 4 0.6",
  "benign 5 1.0", "backdoor 4 1.0", "benign 6 0.8", "benign 7 0.6", "benign 8 1.0", "benign 9 0.8"
)
foreach ($job in $jobs) {
  $p = $job.Split(" ")
  $d = if ($p[2] -eq "1.0") { "..\models\$($p[0])_s$($p[1])" } else { "..\models\$($p[0])_s$($p[1])f$($p[2])" }
  if (Test-Path "$d\config.json") { Say "skip $d (exists)"; continue }
  Say "fine-tune $($p[0]) seed $($p[1]) frac $($p[2])"
  python 03_finetune.py $p[0] $p[1] $p[2] 2>&1 | Select-String -NotMatch "it/s" | Tee-Object -Append $L
}

Say "auditing every model (transcribe + speaker sweep)"
python 04_eval_audit.py 2>&1 | Select-String -NotMatch "it/s" | Tee-Object -Append $L

Say "rescoring with insertion-content statistics"
python rescore.py .. 2>&1 | Select-Object -Last 1 | Tee-Object -Append $L

Say "fitting threshold on the benign null"
python 08_roc.py .. 2>&1 | Tee-Object -Append $L

Say "CALIBRATION DONE"
