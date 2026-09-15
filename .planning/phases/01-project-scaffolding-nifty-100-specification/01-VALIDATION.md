---
phase: 1
slug: project-scaffolding-nifty-100-specification
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-09-15
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0.0 |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/test_domain_models.py -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_domain_models.py -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | DATA-01 | — | Clean packaging isolation | build | `pip install -e .[dev]` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | DATA-01 | — | 100 unique equities + valid benchmark JSON | unit | `pytest tests/test_universe_config.py -k test_universe_file_integrity` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | DATA-01 | — | Pydantic v2 universe schema validation | unit | `pytest tests/test_universe_config.py` | ❌ W0 | ⬜ pending |
| 01-01-04 | 01 | 1 | DATA-02 | — | Immutable domain models, IST slot calculation, OHLC validation | unit | `pytest tests/test_domain_models.py` | ❌ W0 | ⬜ pending |
| 01-01-05 | 01 | 1 | DATA-02 | — | Abstract MarketDataProvider protocol verification | unit | `pytest tests/test_domain_models.py -k test_protocol_interface` | ❌ W0 | ⬜ pending |
| 01-01-06 | 01 | 1 | DATA-01, DATA-02 | — | End-to-end full suite verification | unit | `pytest tests/ -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` — shared fixtures for sample candles, IST timestamps, and universe configs
- [ ] `tests/test_domain_models.py` — unit tests for Candle, CandleBatch, FeatureSet, AnomalySignal, Alert, DataQualityMetadata
- [ ] `tests/test_universe_config.py` — unit tests for universe_nifty100.json integrity and UniverseConfig loader
- [ ] `pyproject.toml` — pytest configuration with pythonpath set to `["src"]`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| All phase behaviors have automated verification | DATA-01, DATA-02 | Fully automatable unit test suite | Run `pytest tests/ -v` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending 2026-09-15
