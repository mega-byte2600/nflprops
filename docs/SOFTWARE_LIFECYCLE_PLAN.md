# Software lifecycle plan

Status: controlled draft 0.1  
Owner and release authority: repository owner  
Applies to: `src/nflprops`, `ios/backend`, `ios/PropDesk`, tests, build and release automation

This plan borrows rigorous lifecycle controls from IEC 62304. `nflprops` is not
a medical device, and this repository does not claim IEC 62304 certification.
The controls are used to improve traceability, repeatability, review quality,
and change safety for a probabilistic financial decision-support application.

## Lifecycle and evidence

| Activity | Required evidence | Approval |
|---|---|---|
| Plan | scoped issue or pull-request description with requirement and risk IDs | Human owner |
| Specify | acceptance criteria in `docs/TRACEABILITY.md` | Human owner |
| Design | short design note for interface, model, security, or data-contract changes | Reviewer |
| Implement | small branch commits; no unrelated rewrite | Author |
| Verify | automated unit/integration tests, lint, package build | CI |
| Validate | real-data or user-workflow evidence when the claim depends on reality | Human owner |
| Release | reviewed pull request, green required checks, known-anomaly review | Human owner only |
| Maintain | incident/defect linked to affected requirement, risk, test and release | Human owner |

## Change classification

- Class A: documentation or formatting with no executable effect.
- Class B: isolated behavior change with bounded effect and automated tests.
- Class C: model, calibration, staking, data-source, authentication, signing,
  deployment, or public-claim change. Requires explicit human approval and
  validation evidence; an agent may prepare but may not release it.

## Required verification gates

Run from repository root:

```bash
python -m pytest -q
ruff check src tests ios/backend
python -m build
```

The historical `bml_cycle*.py` scripts and `odds_ingestor.py` contain known
lint debt and hard-coded local paths. They are research records, not included
in the production lint gate. Their debt is recorded in `docs/KNOWN_ANOMALIES.md`
and must not be silently expanded.

## Configuration and release control

- `main` is release-controlled. Changes arrive through reviewed pull requests.
- CI results are evidence, not release authorization.
- Signing secrets and provider keys come from a secret manager or environment;
  they are never committed or sent to a client.
- Production snapshots fail closed when signing configuration is absent or weak.
- Monte Carlo seeds, sample sizes, confidence levels, data vintages, and model
  versions must be recorded for reproducibility of released evidence.
- Every release reviews open anomalies and the honesty language exposed to users.

## Agent supervision

Repository agents follow `AGENTS.md`. They may propose and verify changes, but
cannot merge, waive gates, redefine risk acceptance, or declare validation.
Human review is mandatory for every Class C change.
