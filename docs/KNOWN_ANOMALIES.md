# Known anomalies and technical debt

Status: reviewed baseline 2026-11-27

| ID | Observation | Impact | Disposition |
|---|---|---|---|
| ANOM-001 | Repository-wide Ruff reports 24 findings in historical `bml_cycle*.py` scripts and `odds_ingestor.py`. | Full-repo lint is not green; production package remains separately gated. | Preserve research evidence; clean in scoped, behavior-preserving increments. Do not add new violations. |
| ANOM-002 | Historical research scripts contain `/Users/astra/...` paths. | They are not portable or directly reproducible on CI. | Parameterize paths before claiming automated reproducibility. |
| ANOM-003 | iOS client signature verification has not been exercised in CI. | Server signing alone does not prove the app rejects altered content. | Add Swift verification tests before production/TestFlight release. |
| ANOM-004 | HMAC is a shared-secret design. | A secret embedded in a distributed client can be extracted and cannot establish publisher identity robustly. | Evaluate asymmetric signing before public distribution. No claim that HMAC solves client authenticity. |
| ANOM-005 | Branch-protection settings are not yet verified as enabled on GitHub. | Documented controls may not be enforced remotely. | Owner must enable required review and CI checks after workflow lands. |
| ANOM-006 | Dependency versions use lower bounds without a committed lock or constraints file. | Future resolution can change behavior or break builds. | Add reviewed constraints and dependency scanning in a later increment. |
| ANOM-007 | Historical baseline contained an `or True` bypass in the pass-weight test. | The test could never fail, creating false QA evidence. | Removed in controlled increment; numerical composite behavior is now asserted. Search for equivalent bypasses remains part of review. |
