# Model evaluation (classifier only)

This is the standalone TF-IDF + logistic-regression classifier, evaluated
on the held-out test split. It is one signal blended into the hybrid
detector, never used alone.

- Training calls: **18**
- Test calls: **12**
- Accuracy: **0.917**
- Precision (scam): **0.857**
- Recall (scam): **1.000**

> Honest caveat: with a small labeled set, these numbers are illustrative,
> not production-grade. The hybrid detector always also applies the rules.
