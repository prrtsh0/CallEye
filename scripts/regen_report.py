"""Regenerate model/eval/report.md from the labeled test split.

Usage:
    python scripts/regen_report.py [--split test]

Runs the detector over the split, prints the metrics JSON, and writes the
Markdown report to model/eval/report.md.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from model.eval.run import main  # noqa: E402

if __name__ == "__main__":
    main()
