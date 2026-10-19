# Security and private data

Use your own Telegram and market-data credentials. Do not paste tokens into issues, commands, chat, screenshots or reports. Saved credentials use Windows current-user DPAPI under ignored .private/. They are tied to the Windows identity; an encrypted-file copy alone is not a portable credential backup. Pair a new machine with its own credentials.

The dashboard binds to localhost. Do not expose it publicly without an independent security design. Guests require explicit invitations; personal reported trades and owner warnings remain private. Revoke access with /revoke.

The public repository contains source, configuration defaults, synthetic fixtures and sanitized update reports only. No account snapshot or original user records are included. The release scanner rejects known sensitive paths and high-confidence key patterns but cannot detect every secret or every private fact. Review all publication diffs.

Report vulnerabilities privately to the maintainer through an available private GitHub channel; do not post exploitable credentials publicly. Rotate a leaked credential at its issuer.
