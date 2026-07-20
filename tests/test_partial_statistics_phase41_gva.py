from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_phase41_all_ksic_contracts():
    subprocess.run([sys.executable, str(ROOT / "scripts" / "verify_partial_statistics_phase41_gva.py")], check=True)
