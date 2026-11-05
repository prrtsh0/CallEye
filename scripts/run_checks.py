"""Run the local check suite: pytest, then the eval on the test split.

Usage: python scripts/run_checks.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)


def run(cmd):
    print(f"\n$ {' '.join(cmd)}\n", flush=True)
    return subprocess.call(cmd)


if __name__ == "__main__":
    code = 0
    code |= run([sys.executable, "-m", "pytest", "-q"])
    code |= run([sys.executable, "-m", "eval.run", "--split", "test"])
    sys.exit(code)
