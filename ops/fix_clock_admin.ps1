# Owner-run only, from an administrator PowerShell terminal.
# This file is never invoked by AEGIS. It starts native time synchronization.
net start w32time
w32tm /resync
