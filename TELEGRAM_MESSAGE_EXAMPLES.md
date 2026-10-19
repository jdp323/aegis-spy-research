# Message examples

EXAMPLE — illustrative wording, not captured market evidence:

> 10:15 ET · SPY $500.00 · IEX bar research
> Next hour: MIXED · Session: UP evidence
> New entry: WAIT — option quote unavailable.

EXAMPLE — research-only watch condition:

> CALL watch · IDEA-EXAMPLE · unvalidated research
> Planned hold: 60 minutes; entry valid until 10:20 ET.
> Watch only—option pricing unavailable.
> Underlying confirmation $500.10; invalidation $499.50; target $501.00.
> Exit deadline 11:15 ET. You review and place any order manually.

Actual message output is produced by core/idea_service.py and verified fixtures in COMMANDS.md. These examples do not establish option prices, entry eligibility, live coverage or returns.
