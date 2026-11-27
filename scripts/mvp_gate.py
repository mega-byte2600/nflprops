"""MVP readiness gate: is Prop Desk ready for TestFlight? (VERIFIED items only.)

Every row is a mechanical check on the repo, mapped to a backlog item in docs/MVP_PLAN.md.
VALIDATED (does it meet the owner's expectations) stays a human judgement.

    python scripts/mvp_gate.py [--json]
Exit 0 only when every row passes.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANNED = ("guaranteed win", "can't lose", "cant lose", "risk-free", "risk free",
          "sure thing", "lock of the", "free money")
MIN_GATE_PASS = 2
AUDIT_MAX_AGE_DAYS = 45


def _read(rel: str) -> str:
    p = ROOT / rel
    return p.read_text(errors="ignore") if p.exists() else ""


def _swift() -> str:
    return "\n".join(p.read_text(errors="ignore")
                     for p in (ROOT / "ios/PropDesk").rglob("*.swift"))


def checks() -> list[dict]:
    rows: list[dict] = []

    def add(item: str, check: str, ok: bool, detail: str = "") -> None:
        rows.append({"item": item, "check": check, "pass": bool(ok), "detail": detail})

    adrs = sorted((ROOT / "docs/adr").glob("ADR-000[1-7]-*.md"))
    add("O1", "ADR-0001..0007 present", len(adrs) == 7, f"{len(adrs)}/7")
    accepted = sum("Status: Accepted" in a.read_text() for a in adrs)
    add("O1", "ADRs accepted by the owner", accepted == 7, f"{accepted}/7 accepted")

    cal, cli = _read("src/nflprops/calibration.py"), _read("src/nflprops/cli.py")
    add("S1", "randomized PIT in calibration.py", "randomiz" in cal.lower())
    add("S1", "temporal split (no non-test-season training)",
        '~df["season"].isin' not in cli and "~df.season.isin" not in cli)

    audit = ROOT / "docs/audit/latest.json"
    if audit.exists():
        a = json.loads(audit.read_text())
        passed = [s["stat"] for s in a.get("stats", []) if s.get("gate") == "PASS"]
        try:
            age = (date.today() - date.fromisoformat(a.get("as_of", "1970-01-01"))).days
        except ValueError:
            age = 10**6
        add("S4", f"calibration gate: >= {MIN_GATE_PASS} stats PASS",
            len(passed) >= MIN_GATE_PASS, f"{len(passed)} pass: {', '.join(passed) or 'none'}")
        add("S4", f"audit fresh (<= {AUDIT_MAX_AGE_DAYS} days)", age <= AUDIT_MAX_AGE_DAYS,
            f"{age} days old")
    else:
        add("S4", "calibration audit committed", False, "docs/audit/latest.json missing")

    snap, swift = _read("ios/backend/snapshot_server.py"), _swift()
    add("B1", "server signs with Ed25519", "Ed25519" in snap)
    add("B1", "no HMAC shared secret on either side",
        "hmac" not in snap.lower() and "HMAC" not in swift)
    add("B2", "schema carries line_source/line_as_of/q10/q90",
        all(k in snap for k in ("line_source", "line_as_of", "q10", "q90")))
    add("B2", "golden snapshot fixture", (ROOT / "tests/fixtures/snapshot_golden.json").exists())
    add("S5", "failing stats are flagged experimental", "experimental" in snap)

    proj = _read("ios/PropDesk/project.yml")
    add("I1", "project.yml declares resources", "resources" in proj and "Assets.xcassets" in proj)
    add("I1", "AppIcon asset", any((ROOT / "ios/PropDesk").rglob("AppIcon.appiconset")))
    add("I1", "privacy manifest", any((ROOT / "ios/PropDesk").rglob("PrivacyInfo.xcprivacy")))
    add("I1", "XCTest target", "PropDeskTests" in proj)
    ci = "\n".join(p.read_text() for p in (ROOT / ".github/workflows").glob("*.yml"))
    add("I2", "macOS CI builds the app", "macos" in ci and "xcodebuild" in ci)
    add("I3", "Swift verifies Ed25519 with a public key", "Curve25519.Signing" in swift)
    low = swift.lower()
    add("I4", "nflverse CC-BY-4.0 attribution in app", "nflverse" in low and "cc-by" in low)
    add("I4", "responsible-gambling resource in app", "1-800-gambler" in low)
    add("I4", "line source is labelled in app", "illustrative" in low)
    hits = [w for w in BANNED if re.search(re.escape(w), low + _read("README.md").lower())]
    add("I4", "no banned copy (ADR-0007)", not hits, ", ".join(hits))
    add("R2", "release notes", (ROOT / "ios/RELEASE_NOTES.md").exists())
    return rows


def main() -> int:
    rows = checks()
    if "--json" in sys.argv:
        print(json.dumps(rows, indent=1))
    else:
        print("| Item | Check | Pass | Detail |\n|---|---|---|---|")
        for r in rows:
            print(f"| {r['item']} | {r['check']} | {'✅' if r['pass'] else '❌'} | {r['detail']} |")
        print(f"\n{sum(r['pass'] for r in rows)}/{len(rows)} checks pass")
    return 0 if all(r["pass"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
