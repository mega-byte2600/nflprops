## Controlled change

- Requirement ID(s):
- Risk ID(s):
- Change class: A / B / C
- Intended behavior and explicit non-goals:

## Evidence

- [ ] Acceptance criteria are testable and linked in `docs/TRACEABILITY.md`
- [ ] Unit/integration tests added or updated
- [ ] `python -m pytest -q` passes
- [ ] `ruff check src tests ios/backend` passes
- [ ] `python -m build` passes
- [ ] Real-data or workflow validation attached when required
- [ ] Known anomalies and failed checks are disclosed

## Agent and release controls

- [ ] No test or gate was weakened to obtain a pass
- [ ] No secret, paid service, dependency, or telemetry sink was added without approval
- [ ] Change stays within stated scope
- [ ] Human reviewer approves any Class C change
- [ ] Human release authority makes the merge decision
