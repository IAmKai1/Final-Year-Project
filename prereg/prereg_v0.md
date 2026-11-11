# Pre-registration v0 (DRAFT, not yet stamped)

Fill this in before any run on TEST models, commit it, then stamp it:

    python -m scripts.prereg_stamp stamp prereg/prereg_v0.md --note "before first test run"

## 1. Models
- Parent(s) and exact revisions:
- Calibration model set (registry IDs / count):
- Test model set (registry IDs / count):

## 2. Audit checks and model-level scores
- Check 1 (text probes): score definition
- Check 2 (voice bank): score = max robust z over speakers
- Check 3 (activations): score definition

## 3. Thresholds and decision rules
- Target false-alarm rate (on calibration models):
- Threshold fitting method:
- Combination rule across checks:
- "Inconclusive" rule (parent unverified / coverage below X):

## 4. Primary outcomes and pass/fail
- Primary: AUROC on test models, TPR at 5% FPR
- Pass if:
- Clopper-Pearson one-sided 95% upper bound on FPR reported with every claim.

## 5. Repair comparison (GN-FT vs clean FT)
- Data budget, steps, metrics, pass/fail:
