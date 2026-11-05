# False-alarm review

Run: `python -m eval.run --split test` against the hand-written **test** split
(12 calls: 6 scam, 6 genuine). The training script never reads this split.

## Current numbers

| Metric | Value |
| --- | --- |
| Recall (scam flagged) | 1.00 (6/6) |
| Precision | 0.857 |
| Accuracy | 0.917 |
| False red | 0 |
| False amber | 1 |

## False alarms (listed honestly)

- `g04_hospital_emergency` → **amber** (false amber).
  Trigger text: "hum hospital se bol rahe hain … aapke bete ko chot lagi hai …
  jaldi aaiye."
  Why: an emergency claim defaults to amber (the documented safe default), and
  this genuine call legitimately contains emergency language. It is **not** a
  rule bug — it is the intended conservative behavior for "is a loved one hurt?"
  claims, which CallEye cannot verify.
- No false reds. No missed scams.

## Smallest rule changes worth testing (training split only)

1. **Emergency default stays amber.** Do not lower it. A genuine emergency must
   surface for verification; the cost is a rare false amber.
2. **Reward lever** (`lottery/prize/jeeta` + money demand) was added to catch
   prize scams as amber. It adds a small false-amber surface if a legitimate
   promotion asks for a fee — none in the current test split.
3. **Would-never is evaluated per segment** and latched. This fixed a false
   negative where "nahi" in one utterance masked an OTP ask in the next. It does
   not increase false alarms on genuine warning calls (tested both directions).

## Honest reporting

Public posts must state: *"hybrid rule and ML detector evaluated on N scripted
calls"* — never "trained scam AI". False alarms are shown openly, including the
intended emergency amber.
