# November2 — source-hash clarification for the monitoring proposal

## Changes

The [first-session monitoring report](2026-11-02_first-session-monitoring.md) labels the reproduction's source hash without specifying newline normalization. That value is the UTF-8/LF-normalized source used by the isolated reproduction, not the raw deployed file bytes. The earlier report and its original commit remain unchanged as historical evidence.

## Verification

- Raw deployed ops/supervisor.py SHA-256: `a194ce38c1818d2e27fbca4651927ac0dfc128c134df7fd3703251d4b45d699a`.
- UTF-8/LF-normalized source SHA-256 used by the reproduction: `a347c5cd53ac5e049880ff7c875fc76cf3d65c91a9c9ba551398e9198a28123f`.

The raw hash is appropriate for byte-for-byte deployment verification. The normalized hash describes the source representation actually compiled by the private synthetic fixture. Both were recomputed from the same unchanged production file. The difference comes from CRLF versus LF representation, not a second algorithm or a deployed patch.

## Limitations

This clarifies a checksum label; it adds no production validation. Four isolated clock-race checks and the proposed patch retain their earlier scope. The observed SQLite failures and timing evidence are unchanged. No claim that the proposal fixes all restarts,406refusals or contention is made.

## Setup impact

None. No production source/configuration, services, permissions, recipients or trading gate changed. The patch remains undeployed; full required validation and controlled deployment remain pending.
