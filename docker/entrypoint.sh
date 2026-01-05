#!/bin/bash
# Entrypoint script for explicit-labeler
# Runs as the configured user (set via docker-compose user: directive)
# With security hardening (cap_drop: ALL, read_only: true), we cannot
# switch users or fix permissions at runtime, so we rely on proper
# volume permissions set on the host or via a separate init step.

# Ensure directories exist (may fail silently with read_only, that's ok)
mkdir -p /app/data /app/logs 2>/dev/null || true

# Execute the command (scheduler.py)
# Use exec to replace the shell process and ensure output is not buffered
# $@ preserves quoted arguments
cd /app && exec "$@"
