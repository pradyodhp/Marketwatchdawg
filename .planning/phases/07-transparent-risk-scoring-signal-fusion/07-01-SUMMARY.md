# Phase 7: Transparent Risk Scoring and Signal Fusion

## Delivered

- Added `RiskScorer` for deterministic fusion of Phase 5 statistical and Phase 6 multivariate signals.
- Added `RiskAssessment` and `RiskContribution` contracts for future explainability consumers.
- Added configurable detector weights, severity boundaries, Isolation Forest normalization scale, and detector-agreement bonus.
- Added stable batch scoring and package/engine compatibility exports.

## Scoring methodology

- Z-score and EWMA evidence is normalized as `clamp(abs(statistic) / threshold, 0, 1)`.
- Isolation Forest evidence is normalized as `clamp((statistic - threshold) / isolation_score_scale, 0, 1)`.
- Only the strongest valid signal per detector contributes, preventing feature-level double counting.
- Available detector weights are renormalized when detectors are missing or invalid.
- A configurable 10% default agreement bonus is added when at least two independent detectors contribute.
- The final normalized value is clamped to `[0, 1]` and multiplied by 100.
- Default engineering severity boundaries are MEDIUM >= 50, HIGH >= 70, and CRITICAL >= 85.

## Invalid data and temporal behavior

- Invalid, non-finite, or insufficient signals are excluded from valid evidence and their reasons are retained.
- No values are fabricated and no future observations are consulted.
- Scoring operates only on the supplied symbol/timestamp signal set; `score_many` groups deterministically by timestamp.

## Verification

- Complete Phase 1-7 test suite passes.
- Ruff passes.
- Phase 8+ natural-language explainability, alerts, injection, APIs, dashboards, and infrastructure remain unimplemented.

## Known limitations

- Severity thresholds and weights are engineering/demo defaults, not regulatory thresholds.
- The score represents unusual activity evidence only; it is not a trading, prediction, fraud, or manipulation verdict.
