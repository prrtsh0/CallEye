"""Build site/data/eval.json from eval/report.md (if it exists).

The landing shows evaluation numbers ONLY when this file exists; the section is
hidden otherwise. This script is run as part of the landing build.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
REPORT = BASE / "eval" / "report.md"
OUT = BASE / "site" / "data" / "eval.json"


def parse_metrics(text: str) -> dict:
    metrics: dict[str, str] = {}
    # table rows: | Metric | Value |
    for line in text.splitlines():
        m = re.match(r"\|\s*(.+?)\s*\|\s*(.+?)\s*\|", line)
        if m and m.group(1).strip() not in ("Metric", "---"):
            metrics[m.group(1).strip()] = m.group(2).strip()
    return metrics


def parse_misclassifications(text: str) -> list[str]:
    out: list[str] = []
    in_sec = False
    for line in text.splitlines():
        if line.strip().startswith("## Misclassifications"):
            in_sec = True
            continue
        if in_sec and line.strip().startswith("## "):
            break
        if in_sec:
            m = re.match(r"[-*]\s*([A-Za-z0-9_\- ]+)", line.strip())
            if m and m.group(1).strip().lower() not in ("none",):
                out.append(m.group(1).strip())
    return out


def parse_calls(text: str) -> list[dict]:
    """Parse the per-call detail table rows: | id | label | final | time-to-alert |"""
    out: list[dict] = []
    in_sec = False
    for line in text.splitlines():
        if line.strip().startswith("## Per-call detail"):
            in_sec = True
            continue
        if in_sec and line.strip().startswith("## "):
            break
        if in_sec:
            m = re.match(
                r"\|\s*([\w.\-]+)\s*\|\s*(\w+)\s*\|\s*(\w+)\s*\|\s*([\d.+\-]+)\s*\|",
                line,
            )
            if m:
                out.append({
                    "id": m.group(1),
                    "label": m.group(2),
                    "final": m.group(3),
                    "time_to_alert": m.group(4),
                })
    return out


def main() -> int:
    if not REPORT.exists():
        print("No eval/report.md — skipping (landing will hide evaluation).")
        return 0
    text = REPORT.read_text(encoding="utf-8")
    data = {
        "source": "eval/report.md",
        "metrics": parse_metrics(text),
        "misclassifications": parse_misclassifications(text),
        "calls": parse_calls(text),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print("Wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
