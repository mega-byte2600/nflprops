# Requirements, risks and verification traceability

Status: controlled draft 0.1

| Requirement | Acceptance criterion | Risk control | Verification |
|---|---|---|---|
| REQ-HON-001 Honest claims | Outputs contain no guaranteed-win or unqualified edge claim | RISK-FIN-001 | Existing forecast, strike and snapshot tests |
| REQ-DAT-001 No invented market data | Missing market anchor fails explicitly | RISK-FIN-002 | `tests/test_strike.py` |
| REQ-CAL-001 Calibration disclosure | Raw probabilities are not described as calibrated without held-out evidence | RISK-MOD-001 | `tests/test_nflprops.py`, calibration backtest evidence |
| REQ-SEC-001 Signed production snapshots | Runtime rejects missing or sub-32-byte secret unless explicit local unsigned mode is selected | RISK-SEC-001 | `test_runtime_config_*`, signing round-trip test |
| REQ-SEC-002 Generic external errors | HTTP 500 responses do not expose exception details | RISK-SEC-002 | `tests/test_props_api.py` plus code review |
| REQ-SCM-001 Controlled change | Executable changes use branch, PR, green gates and human release approval | RISK-DEV-001 | CI result and PR review record |
| REQ-AGT-001 Bounded agent authority | Agent policy prohibits merge, gate weakening, secret use and out-of-scope changes | RISK-DEV-002 | Review of `AGENTS.md` and PR checklist |
| REQ-QA-001 Effective assertions | Automated tests must contain meaningful assertions and no unconditional pass bypass | RISK-DEV-003 | `test_pass_weight_drives_composite`; repository search for bypass patterns |
| REQ-SEC-003 Local unsigned mode | Unsigned HTTP mode may bind only to localhost or a loopback IP | RISK-SEC-003 | `test_unsigned_mode_*` |
| REQ-SEC-004 Defensive HTTP headers | Every backend response disables caching and MIME sniffing | RISK-SEC-004 | `test_health_endpoint` |

## Risk register

| Risk | Hazardous situation | Initial risk | Control and residual-risk decision |
|---|---|---|---|
| RISK-FIN-001 | User interprets probabilistic output as guaranteed profit | High | Mandatory honesty language and no guaranteed-edge output. Human owner accepts residual risk. |
| RISK-FIN-002 | Missing or stale market data is presented as current | High | Fail when anchor is missing; show keyless/live-data gate. |
| RISK-MOD-001 | Miscalibrated model creates false confidence | High | Held-out calibration evidence, confidence intervals, negative results retained. |
| RISK-SEC-001 | Client accepts tampered or unsigned snapshot | High | HMAC envelope; production configuration fails closed; client verification remains a validation item. |
| RISK-SEC-002 | Backend exception leaks implementation or data | Medium | Generic response body; internal logging review remains open. |
| RISK-DEV-001 | Unreviewed change reaches release branch | High | Branch protection, CI and human merge authority. Repository setting verification remains open. |
| RISK-DEV-002 | Agent expands scope or weakens evidence to complete a task | High | Repository agent policy, bounded PR scope and human approval for Class C. |
| RISK-DEV-003 | A test reports success despite not checking its intended behavior | High | Ban unconditional-pass patterns; require numerical acceptance criteria and review. |
| RISK-SEC-003 | Development configuration exposes unsigned snapshots to a network | High | Reject non-loopback binding whenever unsigned mode is selected. |
| RISK-SEC-004 | Sensitive or stale responses are cached or content-sniffed | Medium | Send `Cache-Control: no-store` and `X-Content-Type-Options: nosniff` on all responses. |

When a requirement, control, test, or risk changes, update this file in the same
pull request. A checked box without linked evidence is not verification.
