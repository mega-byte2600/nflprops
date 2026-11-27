# ADR-0001: Thin iOS client over a server-precomputed snapshot

Status: Proposed (2026-11-27)

## Context
The engine runs Monte Carlo with copula dependence (20k draws per prop) on a 33 MB dataset. Doing
that on the phone wastes battery and puts model code and any provider key in the binary. The
existing scaffold already follows a "precompute, sign, serve" pattern (`ios/backend/`).

## Decision
1. The server (`ios/backend/snapshot_server.py`) is the only place probabilities are computed.
   The app renders a snapshot; it never recomputes or adjusts a probability.
2. The snapshot is one versioned JSON document (`schema_version`, `generated_utc`, data as-of,
   per-stat calibration status, props). The contract is owned by `/snapshot-contract`.
3. **Offline-first:** the app ships with a bundled snapshot so it is never blank. It fetches a
   newer signed snapshot from a static URL (any static host: GitHub Pages or object storage)
   and caches the last verified one. A stale snapshot is shown with its as-of date, never as live.
4. A static file host is preferred over a running server for the MVP. It has no uptime burden
   and no keys, and `props_api.py` stays a development tool.

## Consequences
- Model changes ship without an app update; app updates are needed only for schema changes.
- The schema is a public contract: a breaking change bumps the major `schema_version`, and
  the app refuses unknown majors with a clear message.

## Verification
- A pytest golden test: the snapshot from fixture data matches `tests/fixtures/snapshot_golden.json`.
- An XCTest decodes the same golden file, so one fixture serves both sides.
