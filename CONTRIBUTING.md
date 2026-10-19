# Contributing

Preserve strict data, calendar, option and privacy gates. All orders remain manual. Test with isolated copies, clocks and transports; never send development broadcasts or test against a personal ledger.

Every published change must include a new report in reports/updates/ describing what changed, why, verification commands/results, limitations and setup impact. Changes to dependencies, configuration, credential handling, runtime paths or startup also update SETUP.md in the same publication. Reports must contain no credentials, user identifiers, personal fills, local owner paths or raw private logs.

Install the optional local pre-commit hook using git config core.hooksPath .githooks. CI also checks each push/PR. Run python -m ops.release_guard before committing and python -m ops.release_guard --base BASE_SHA in CI. The guard is a defense, not proof that arbitrary content is safe. Review every staged diff.

Keep tests and failure evidence. Do not widen freshness limits or weaken assertions to obtain PASS. Public evidence must distinguish isolated tests, actual operation and external dependencies.
