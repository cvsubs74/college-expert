# Scenario run — 2026-06-12

- Executed: 2026-06-12 23:47 UTC
- Commit: ede405e8
- Mode: full (unit + live production)
- Result: **13/13 PASS**

| # | Scenario | Status | Detail |
|---|---|---|---|
| S1 | Backend unit suite (pytest) | PASS | 904 passed, 29 warnings in 0.68s |
| S2 | Frontend unit suite + build (vitest, vite) | PASS | Tests  218 passed (218) |
| S3 | KB versioning lifecycle (live Firestore) | PASS | 8 checks |
| S4 | Versioned read APIs (deployed) | PASS | current data_year=2026, 2025 archive readable, versions=[2026, 2025] |
| S5 | Ingest validation gate (deployed) | PASS | invalid profile → 400; year 1990 → 400; nothing written |
| S6 | KB 2026 data integrity (live) | PASS | 191 docs; 191 on 2026; 188 with 2025 archive; 0 bad rates; 0 fraction-style |
| S7 | Collector output validation (research_2026) | PASS | 189 files, 0 errors, 145 with warnings |
| S8 | Fit staleness detection + suppression (deployed) | PASS | 8 checks |
| S9 | Fit history archival (deployed) | PASS | replaced fit archived under 2025; history=['2025'] |
| S8.cleanup | Sentinel user removed | PASS | all sentinel docs deleted |
| S10 | Roadmap deadline-change annotation (unit) | PASS | 6 passed in 0.07s |
| S11 | Live QA synthetic monitoring | PASS | latest run run_20260612T234005Z_04319a: 4 scenarios, failures: none |
| S12 | Deployed function health | PASS | KB /health: firestore connected |

Scenario definitions: [`system-scenarios.md`](system-scenarios.md).
