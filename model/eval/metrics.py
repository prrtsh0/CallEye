"""Evaluation metrics for the detector (honest reporting)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CallResult:
    call_id: str
    label: str  # scam | genuine
    final_level: str  # green | amber | red
    first_alert_t: float | None
    ask_t: float | None
    reasons: list[str] = field(default_factory=list)

    @property
    def flagged(self) -> bool:
        return self.final_level in ("amber", "red")

    @property
    def false_red(self) -> bool:
        return self.label == "genuine" and self.final_level == "red"

    @property
    def false_amber(self) -> bool:
        return self.label == "genuine" and self.final_level == "amber"

    @property
    def missed(self) -> bool:
        return self.label == "scam" and self.final_level == "green"

    @property
    def time_to_alert(self) -> float | None:
        if self.first_alert_t is not None and self.ask_t is not None:
            return round(self.first_alert_t - self.ask_t, 2)
        return None


def summarize(results: list[CallResult]) -> dict:
    scam = [r for r in results if r.label == "scam"]
    genuine = [r for r in results if r.label == "genuine"]

    tp = sum(1 for r in scam if r.flagged)
    fn = sum(1 for r in scam if not r.flagged)
    fp = sum(1 for r in genuine if r.flagged)
    tn = sum(1 for r in genuine if not r.flagged)

    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    accuracy = (tp + tn) / len(results) if results else None

    false_red = sum(1 for r in genuine if r.false_red)
    false_amber = sum(1 for r in genuine if r.false_amber)

    tta = [r.time_to_alert for r in scam if r.time_to_alert is not None]
    avg_tta = round(sum(tta) / len(tta), 2) if tta else None

    return {
        "n_calls": len(results),
        "n_scam": len(scam),
        "n_genuine": len(genuine),
        "true_positive": tp,
        "false_negative": fn,
        "false_positive": fp,
        "true_negative": tn,
        "precision": round(precision, 3) if precision is not None else None,
        "recall": round(recall, 3) if recall is not None else None,
        "accuracy": round(accuracy, 3) if accuracy is not None else None,
        "false_red": false_red,
        "false_amber": false_amber,
        "avg_time_to_alert": avg_tta,
        "missed": [r.call_id for r in scam if r.missed],
        "false_red_ids": [r.call_id for r in genuine if r.false_red],
        "false_amber_ids": [r.call_id for r in genuine if r.false_amber],
    }
