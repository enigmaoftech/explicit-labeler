#!/bin/bash
# Wrapper script for cron to run the explicit music labeler
# This ensures proper environment and logging
# Runs as appuser (UID/GID from .env)

# Set timezone (optional, adjust as needed)
export TZ="${TZ:-UTC}"

# Log file
LOG_FILE="${LOG_FILE:-/app/logs/explicit-labeler.log}"
mkdir -p "$(dirname "$LOG_FILE")"

# Log retention (number of runs to keep, default: 7)
LOG_RETENTION_RUNS="${LOG_RETENTION_RUNS:-7}"
# Validate that it's a positive integer
if ! echo "$LOG_RETENTION_RUNS" | grep -qE '^[1-9][0-9]*$'; then
    LOG_RETENTION_RUNS=7
fi

# Rotate logs before each run
# This rotates the log file each time the script runs, keeping the specified number of runs
if [ -f "$LOG_FILE" ]; then
    LOG_DIR="$(dirname "$LOG_FILE")"
    LOG_BASE="$(basename "$LOG_FILE" .log)"
    
    # Remove oldest log if we're at the retention limit
    if [ -f "$LOG_DIR/${LOG_BASE}-${LOG_RETENTION_RUNS}.log" ]; then
        rm -f "$LOG_DIR/${LOG_BASE}-${LOG_RETENTION_RUNS}.log"
    fi
    if [ -f "$LOG_DIR/${LOG_BASE}-${LOG_RETENTION_RUNS}.log.gz" ]; then
        rm -f "$LOG_DIR/${LOG_BASE}-${LOG_RETENTION_RUNS}.log.gz"
    fi
    
    # Shift existing rotated logs backwards (move .2 to .3, .1 to .2, etc.)
    i=$LOG_RETENTION_RUNS
    while [ $i -gt 1 ]; do
        prev=$((i - 1))
        # Move previous to current position
        if [ -f "$LOG_DIR/${LOG_BASE}-${prev}.log" ]; then
            mv "$LOG_DIR/${LOG_BASE}-${prev}.log" "$LOG_DIR/${LOG_BASE}-${i}.log" 2>/dev/null || true
        elif [ -f "$LOG_DIR/${LOG_BASE}-${prev}.log.gz" ]; then
            mv "$LOG_DIR/${LOG_BASE}-${prev}.log.gz" "$LOG_DIR/${LOG_BASE}-${i}.log.gz" 2>/dev/null || true
        fi
        i=$prev
    done
    
    # Compress the current log before moving it (if not already compressed)
    if [ -f "$LOG_FILE" ] && [ ! -f "$LOG_DIR/${LOG_BASE}-1.log.gz" ]; then
        gzip -c "$LOG_FILE" > "$LOG_DIR/${LOG_BASE}-1.log.gz" 2>/dev/null || true
        rm -f "$LOG_FILE"
    elif [ -f "$LOG_FILE" ]; then
        mv "$LOG_FILE" "$LOG_DIR/${LOG_BASE}-1.log" 2>/dev/null || true
    fi
fi

# Ensure we're running as appuser (switch if needed)
if [ "$(id -u)" != "${PUID:-1000}" ]; then
    # If running as root, switch to appuser
    if [ "$(id -u)" = "0" ]; then
        # Preserve environment variables when switching users
        # Export current environment variables
        export PLEX_BASEURL PLEX_TOKEN PLEX_LIBRARY DATA_DIR LOG_FILE TZ PUID PGID LOG_RETENTION_RUNS
        # Use su without - to preserve environment, or pass vars explicitly
        exec su appuser -c "export PLEX_BASEURL='${PLEX_BASEURL}' PLEX_TOKEN='${PLEX_TOKEN}' PLEX_LIBRARY='${PLEX_LIBRARY:-Music}' DATA_DIR='${DATA_DIR:-/app/data}' LOG_FILE='${LOG_FILE:-/app/logs/explicit-labeler.log}' TZ='${TZ:-UTC}' LOG_RETENTION_RUNS='${LOG_RETENTION_RUNS:-7}' && /app/cron-wrapper.sh $*"
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
# Use unbuffered Python output (-u) for real-time logging
cd /app
python3 -u mark_explicit_music.py "$@" >> "$LOG_FILE" 2>&1

# Capture exit code
EXIT_CODE=$?

# Log completion
echo "Finished at: $(date)" >> "$LOG_FILE"
echo "Exit code: $EXIT_CODE" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

exit $EXIT_CODE

