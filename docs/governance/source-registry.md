# Source Registry

Real table generated from `data/sources/registry.yaml` (v0.1.0, last
reviewed 2026-08-24) — the actual, enforced gate for document ingestion
(ADR-001). `POST /documents` rejects any `source_id` not listed here with
`status: approved` and `allowed_for_ingestion: true`
(`SourceNotFoundError`/`SourceNotApprovedError` → HTTP 400).

| ID | Name | Type | License | Access level | Status |
|---|---|---|---|---|---|
| `SRC-SAMPLE-001` | Remote Work Policy (Sample) | internal_policy | CC0-1.0 | public | approved |
| `SRC-SAMPLE-002` | Information Security Policy (Sample) | internal_policy | CC0-1.0 | internal | approved |
| `SRC-SAMPLE-003` | Executive Compensation Framework (Sample) | internal_policy | CC0-1.0 | management | approved |
| `SRC-SAMPLE-004` | Expense Reimbursement Policy (Sample) | internal_policy | CC0-1.0 | internal | approved |
| `SRC-SAMPLE-005` | Adversarial Prompt Injection Test Fixture (Sample) | security_test_fixture | CC0-1.0 | public | approved |

`SRC-SAMPLE-003`'s `management` access level is what the roadmap's headline
authorization test (Release Gate §7) exercises directly: an EMPLOYEE-role
query never retrieves any chunk from this source, verified for real in
`tests/security/test_document_acl.py` — see `docs/security/threat-model.md`.

## Real scope note (stated in the registry file itself, carried forward here)

These are small, project-authored sample documents (`data/raw/samples/`),
not the roadmap's originally-envisioned external corpus. They exist to
exercise ingestion, chunking, retrieval, and authorization end-to-end with
real files, real hashes, and a real database round-trip — a deliberate
scope decision documented from Block 1 onward, not a gap discovered late.

## Governance policy (as declared in the registry)

- Only sources explicitly listed may be ingested — no implicit trust.
- Every source must declare organization, license, and classification.
- Sources default to `status: pending` until reviewed and approved — none
  of the five entries above skipped that review; all five are marked
  `approved` as of the version noted at the top of this document.
