# Detector specification

This is the implementable specification for the CallEye scam-risk detector.
Source of truth: Engineering Handbook §7.

## 1. Levels and wording

| Level | On screen | Rule of thumb |
| --- | --- | --- |
| Green | "No warning signs so far" | Never says "safe" |
| Amber | "Careful. Check before you act" | Default for anything unclear and for emergency claims |
| Red | "Hang up. Your guardian has been told" | Only when very sure |

Red is calm: no siren, no flashing, short sentences.

## 2. Signals

- Evaluated over the finalised transcript with a sliding window of the last
  30 seconds, plus the whole call for stage tracking.
- **Stages:** authority claim, fear, isolation, urgency, ask.
- **Pressure (0–100):** weighted count of urgency, deadline, isolation, and
  command phrases, with exponential decay (half-life ≈ 20 s). Keep the trend
  over the last three evaluations.
- **Lever:** authority, account loss, reward, emergency, boss or vendor payment.
- Phrase lists live in YAML playbooks (`family.yaml`, `student.yaml`) in
  Devanagari and Romanised Hinglish, with weights. Playbooks are data, not code.

## 3. Would-never asks

A bank, police, or government body **never** asks for:

- OTP, PIN, CVV, UPI PIN, passwords
- installing a remote-access app
- moving money to a "safe account"
- paying to avoid arrest
- staying on a video call

A would-never ask makes the result **red**.

**Warning vs request:** the same words appear in genuine warnings ("kisi ko OTP
mat batana"). If a negation or warning cue (*mat, nahi, never, do not, kabhi
nahi*) sits within about six tokens of the term, treat it as a warning. Both
directions are tested.

## 4. Emergency claims

Injured / kidnapped / arrested / accident claims about a relative. The app
cannot know if it is real:

- Default: **amber** with the verify-first screen.
- Red only if: money demand present **AND** (isolation OR urgency) **AND** the
  classifier is confident (p ≥ 0.8).
- A genuine hospital/school call (no money demand) → amber.

## 5. Classifier (optional)

- TF-IDF on character n-grams (2–5) + logistic regression, trained on scripted
  calls. Returns `p_scam` for the transcript so far.
- Blended into the decision, never used alone.
- If the model file is missing, rules decide.

## 6. Decision rules (starting thresholds; tune on training split only)

```
def decide(s):
    if s.would_never_ask:                 return RED
    if s.lever == 'emergency':
        if s.money_demand and (s.isolation or s.urgency) and s.p_scam >= 0.8:
                                            return RED
        return AMBER
    if s.stages_hit >= 3 and s.pressure >= 70 and s.p_scam >= 0.8:
                                            return RED
    if s.stages_hit >= 1 and s.pressure >= 40:
                                            return AMBER
    return GREEN
```

- **Hysteresis:** red latches for the rest of the call. Amber returns to green
  only after 20 s without new signals.

## 7. Metrics

Precision, recall, false-red rate, false-amber rate, confusion matrix, and
time-to-alert (seconds between first amber/red and `ask_t`; positive = warned
before the ask).

## 8. Data integrity

- Train and test splits are disjoint (a test proves it; training never reads the
  test set).
- Report on both clean scripts and real STT output; show false alarms openly.
