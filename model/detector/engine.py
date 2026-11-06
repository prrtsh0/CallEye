"""SessionAnalyzer orchestrates the detector for one call session."""
from __future__ import annotations

from dataclasses import dataclass, field

from model.detector.asks import would_never_ask
from model.detector.classifier import ScamClassifier
from model.detector.decision import DecisionEngine
from model.detector.levers import detect_lever
from model.detector.lexicon import PlaybookLexicon
from model.detector.pressure import PressureMeter
from model.detector.stages import detect_stages


@dataclass
class AnalysisResult:
    level: str = "green"
    screen_text: str = ""
    stages: list[str] = field(default_factory=list)
    pressure: float = 0.0
    lever: str = "unknown"
    reasons: list[str] = field(default_factory=list)
    would_never_ask: bool = False
    p_scam: float | None = None
    # boolean flags used by the decision engine
    money_demand: bool = False
    isolation: bool = False
    urgency: bool = False
    stages_hit: int = 0
    timestamp: float = 0.0


class SessionAnalyzer:
    def __init__(self, lexicon: PlaybookLexicon | None = None,
                 classifier: ScamClassifier | None = None):
        self.lexicon = lexicon or PlaybookLexicon()
        self.classifier = classifier or ScamClassifier()
        self.meter = PressureMeter()
        self.decision = DecisionEngine()
        self.transcript: list[str] = []
        self.last_t = 0.0
        self._wna = False
        self._wna_pat = ""

    @property
    def full_text(self) -> str:
        return " ".join(self.transcript).strip()

    def analyze_update(self, text: str, final: bool = True, t: float = 0.0) -> AnalysisResult:
        if not text:
            return self._snapshot(t)

        self.transcript.append(text.strip())
        self.last_t = max(self.last_t, t)

        combined = self.full_text
        pressure = self.meter.update(self.lexicon, combined, t)
        stages = detect_stages(self.lexicon, combined)
        lever = detect_lever(self.lexicon, combined)
        # Would-never is evaluated per segment (each transcript turn) and latched:
        # a warning cue in one utterance must not mask an ask in another.
        if not self._wna:
            seg_wna, pat = would_never_ask(self.lexicon, text)
            if seg_wna:
                self._wna = True
                self._wna_pat = pat
        wna = self._wna
        wna_pat = self._wna_pat
        p_scam = self.classifier.p_scam(combined)

        # Reason strings for the UI (top matched phrases, de-duplicated).
        reasons = []
        for cat in ("authority", "fear", "isolation", "urgency", "ask"):
            for pat, _ in self.lexicon.matches(cat, combined):
                if pat not in reasons:
                    reasons.append(pat)
            if len(reasons) >= 5:
                break
        if wna:
            reasons.insert(0, f"would-never ask detected ({wna_pat})")

        snapshot = AnalysisResult(
            level="",
            screen_text="",
            stages=sorted(stages),
            pressure=pressure,
            lever=lever,
            reasons=reasons[:6],
            would_never_ask=wna,
            p_scam=p_scam,
            money_demand=self.lexicon.hit_count("money_demand", combined) > 0,
            isolation="isolation" in stages,
            urgency="urgency" in stages,
            stages_hit=len(stages),
            timestamp=t,
        )

        self.decision.decide(snapshot, t)
        snapshot.level = self.decision.label
        snapshot.screen_text = self.decision.screen_text
        return snapshot

    def _snapshot(self, t: float) -> AnalysisResult:
        return AnalysisResult(
            level=self.decision.label,
            screen_text=self.decision.screen_text,
            pressure=round(self.meter.pressure, 1),
            timestamp=t,
            p_scam=self.classifier.p_scam(self.full_text),
        )
