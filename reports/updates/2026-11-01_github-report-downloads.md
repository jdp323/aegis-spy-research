# November 1 — downloadable reports and review bundles on GitHub

## Changes

The existing Markdown reports, strategy source, test evidence and simulated transcripts were already committed at 123fe7318f5e14cc5ac3fb218cbbe891f4c06214. This update adds both existing PDFs and both shareable review bundles as ordinary repository downloads. The main README links the download index and SHA256SUMS.txt. No new report PDF is generated and no earlier issued PDF is rewritten.

| Artifact | Bytes | SHA-256 |
|---|---|---|
| AEGIS_FREE_ONLY_IMPLEMENTATION_2026-11-01.pdf | 139121 | `bc873e2543739e8bf33ea43bd71c282e6026c783a4fa54ba11e8637cd6c8052a` |
| AEGIS_FREE_ONLY_REVIEW_2026-11-01.zip | 1295069 | `d077949e34ec81ff3e5ffe445010cca1ddb83e6ceb4871ad2b72888b9895654b` |
| AEGIS_EXPERT_REVIEW_2026-10-31.pdf | 275031 | `7a30f74426791bc07a8f680eedaa490443bd26f7841c458b25807eb1964f390e` |
| AEGIS_EXPERT_REVIEW_PUBLIC_2026-10-31.zip | 1352310 | `7ae582616d76e5e9e3bec0b6b455dc291691a03eb67750a1ed379deadd3f302c` |

The publication guard pins the exact four recursively reviewed artifacts by full path and SHA-256. There is no general ZIP/PDF or download-directory exemption. Other binaries, private paths, unapproved JSON and secret patterns remain blocked. Any change to a pinned download fails publication until a separate review and explicit pin update. Git attributes mark only these four files as binary, preserving PDF syntax and ZIP bytes without text normalization; text whitespace checks still apply to all other changes.

## Verification

The preflight recursively inspected four PDF instances, four ZIP containers and903text members, expanding12,949,787bytes including nested public source archives. ZIP integrity, safe relative paths, prohibited private/runtime members, secret patterns, machine paths and PDF text were checked. The two standalone PDFs were previously rendered and visually reviewed; their bytes are unchanged.

The older local October31archive failed the new broader secret-pattern check on a credential-like assignment in deployment_profile_diff.txt. The original remains private and unchanged. A separately named PUBLIC copy redacts those comparison-text matches, preserves the pinned source/PDF and other payloads, and supplies PUBLICATION_NOTES.md, a new current manifest and the original as-of hashes as historical metadata. Redaction counts: {"credential assignment": 12}. No value is reproduced here.

Three new publication-guard regressions pass: exact attestation versus mutation, renamed/unknown binaries, and replacement text at a pinned filename. The existing frozen-evidence guard regression also passes. These focused checks do not rerun or replace the prior935portable/927installed runtime checks. The entire staged tree is checked with the publication guard and whitespace check; final remote verification compares the full Git tree and every changed file byte. Download hashes remain independently verifiable.

## Limitations

This publication changes no market-data capability, strategy, trade gate, service or recipient routing. Prior IEX406, latency-target failures, missing genuine option data and unvalidated strategy results retain their original as-of meaning. Archived source is pinned to its documented historical commit; it is not silently replaced by this publication. The original unsanitized comparison archive, credentials, private fills, databases, receipts and raw market caches are not uploaded.

## Setup impact

No package, credential, account action or restart is needed to download/review these files. SETUP.md explains the download location and exact-digest publication policy. All orders remain manual; live/execution readiness remains false.
