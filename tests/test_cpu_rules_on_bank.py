"""The team's C2/C3 rules on our saved 60-model clean bank: 0 flags (guards results/cpu_rules_bank60)."""
import glob
import subprocess
import sys

import pandas as pd
import pytest

RUNS = glob.glob("results/clean_bank60/runs/*audit_bank*")


@pytest.mark.skipif(not RUNS, reason="saved clean-bank run not present")
def test_cpu_rules_flag_none_of_the_clean_bank(tmp_path):
    out = tmp_path / "c2c3.csv"
    subprocess.run([sys.executable, "-m", "scripts.cpu_rules_on_bank", RUNS[0], str(out)], check=True)
    df = pd.read_csv(out)
    assert len(df) == 60 and not df["flagged"].any()
