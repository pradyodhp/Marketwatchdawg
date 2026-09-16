# Phase 6: Isolation Forest and Temporal Validation

## Delivered

- Added a deterministic `FeatureMatrixBuilder` with explicit Phase 4 feature ordering.
- Added `IsolationForestDetector` using `StandardScaler` and scikit-learn `IsolationForest`.
- Added chronological train/evaluation splitting and expanding-window walk-forward validation.
- Extended the existing `AnomalySignal` contract for multivariate model scores without inventing a direction.
- Added explicit invalid and insufficient-training outcomes instead of fabricated feature values.

## Temporal guarantees

- Training rows are strictly earlier than evaluation rows.
- Scalers and models are fitted inside each fit window only.
- Walk-forward windows expand chronologically and never include the current observation in training.
- Repeated runs use stable ordering, `random_state`, and single-threaded model execution.

## Validation

- Phase 1-6 test suite passes.
- Ruff passes.
- Phase 7+ risk scoring, fusion, explainability, alerting, APIs, dashboards, and injection remain unimplemented.
