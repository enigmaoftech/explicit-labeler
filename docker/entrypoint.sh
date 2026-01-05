#!/bin/bash
# Entrypoint script for explicit-labeler
# Simplified version - no longer needs cron setup
# Runs as root to fix permissions, then switches to appuser

# Don't exit on error for user setup (use || true where needed)
set +e

# Get UID/GID from environment (set via docker-compose)
PUID=${PUID:-1000}
PGID=${PGID:-1000}

# Ensure appuser exists with correct UID/GID (in case of volume mounts with different users)
if ! id -u appuser >/dev/null 2>&1; then
    # Create group if it doesn't exist
    if ! getent group ${PGID} >/dev/null 2>&1; then
        groupadd -g ${PGID} appuser 2>/dev/null || true
    fi
    
    # Create user if it doesn't exist
    if ! getent passwd ${PUID} >/dev/null 2>&1; then
        useradd -u ${PUID} -g ${PGID} -m -s /bin/bash appuser 2>/dev/null || true
    fi
fi

# Fix ownership of app directory (in case of mounted volumes or permissions issues)
chown -R ${PUID}:${PGID} /app 2>/dev/null || true

# Fix ownership of data and logs directories (mounted volumes)
chown -R ${PUID}:${PGID} /app/data /app/logs 2>/dev/null || true

# Fix ownership of log file
chown ${PUID}:${PGID} /app/logs/explicit-labeler.log 2>/dev/null || true
chmod 666 /app/logs/explicit-labeler.log 2>/dev/null || true

# Ensure directories exist
mkdir -p /app/data /app/logs 2>/dev/null || true

# Switch to appuser and execute the command (scheduler.py)
# Use su without - to keep current directory (WORKDIR is /app)
# $* joins all arguments with spaces, which works for our use case
exec su appuser -s /bin/bash -c "cd /app && exec $*"
