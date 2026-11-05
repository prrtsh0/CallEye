# Call data schema

Call files are JSON lists of call records, used by the evaluation harness and
the classifier trainer.

## Record fields

| Field | Type | Required | Meaning |
| --- | --- | --- | --- |
| `id` | string | yes | Unique call id. |
| `lang` | string | yes | Language code (`hi`, `hi-latn`, `en`). |
| `label` | string | yes | `scam` or `genuine`. |
| `lever` | string | no | Expected lever: authority, account loss, reward, emergency, payment, none. |
| `source` | string | no | `script` or `stt`. |
| `segments` | array | yes | Ordered transcript segments. |
| `segments[].t` | number | yes | Time in seconds from call start. |
| `segments[].text` | string | yes | Transcript text. |
| `ask_t` | number | no | Time (seconds) of the first ask in a scam call, for time-to-alert. |

## Data integrity

* The training script only reads `data/calls/train.json`.
* The evaluation harness reads `data/calls/test.json` (or falls back to fixtures).
* A test asserts the train and test splits share no call ids, so the test split
  is never seen during training.
