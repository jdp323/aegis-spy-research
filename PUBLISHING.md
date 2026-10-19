# Publishing an update

1. Work from the sanitized public clone. Never push a production installation or its history.
2. Create reports/updates/YYYY-MM-DD_short-description.md. State changes, tests with actual results, limitations and Setup impact: changed or none.
3. Update SETUP.md when runtime, installation, credentials, configuration or dependency behavior changes.
4. Run isolated tests and command/schedule verification for affected behavior.
5. Review git diff and git diff --cached. Stage only intended source/docs.
6. Run python -m ops.release_guard against the staged tree, including the new report.
7. Commit source and report together, then git push. Confirm the remote commit and CI result. Do not claim upload on a failed or pending push.

Optional pre-commit enforcement: git config core.hooksPath .githooks. GitHub Actions adds a remote check. Repository branch protection is an owner setting, not configured by this export. A hook can be bypassed; maintainer review remains necessary. Never auto-upload private operational reports.
