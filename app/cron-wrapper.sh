#!/bin/bash
# Wrapper script for cron to run the explicit music labeler
# This ensures proper environment and logging
# Runs as appuser (UID/GID from .env)

# Set timezone (optional, adjust as needed)
export TZ="${TZ:-UTC}"

# Log file
LOG_FILE="${LOG_FILE:-/app/logs/cron.log}"
mkdir -p "$(dirname "$LOG_FILE")"

# Ensure we're running as appuser (switch if needed)
if [ "$(id -u)" != "${PUID:-1000}" ]; then
    # If running as root, switch to appuser
    if [ "$(id -u)" = "0" ]; then
        # Preserve environment variables when switching users
        # Export current environment variables
        export PLEX_BASEURL PLEX_TOKEN PLEX_LIBRARY DATA_DIR LOG_FILE TZ PUID PGID
        # Use su without - to preserve environment, or pass vars explicitly
        exec su appuser -c "export PLEX_BASEURL='${PLEX_BASEURL}' PLEX_TOKEN='${PLEX_TOKEN}' PLEX_LIBRARY='${PLEX_LIBRARY:-Music}' DATA_DIR='${DATA_DIR:-/app/data}' LOG_FILE='${LOG_FILE:-/app/logs/cron.log}' TZ='${TZ:-UTC}' && /app/cron-wrapper.sh $*"
        exit $?
    fi
fi

# Timestamp
echo "========================================" >> "$LOG_FILE"
echo "Started at: $(date)" >> "$LOG_FILE"
echo "Command: $*" >> "$LOG_FILE"
echo "Running as: $(id -un) ($(id -u):$(id -g))" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Run the script with all arguments, capturing both stdout and stderr
cd /app
python3 mark_explicit_music.py "$@" >> "$LOG_FILE" 2>&1

# Capture exit code
EXIT_CODE=$?

# Log completion
echo "Finished at: $(date)" >> "$LOG_FILE"
echo "Exit code: $EXIT_CODE" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

exit $EXIT_CODE

