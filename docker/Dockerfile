FROM python:3.11-slim

# Accept UID and GID as build arguments
ARG PUID=1000
ARG PGID=1000

# No need for cron, sudo, or gzip (Python has gzip module built-in)
# We run as non-root user for security

WORKDIR /app

# Install gosu for secure user switching (works without capabilities)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gosu && \
    rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scripts
COPY app/mark_explicit_music.py .
COPY app/scheduler.py .
COPY docker/entrypoint.sh /app/entrypoint.sh

# Create group and user with specified UID/GID
RUN groupadd -g ${PGID} appuser || true && \
    useradd -u ${PUID} -g ${PGID} -m -s /bin/bash appuser || true

# Create directory for progress files and logs
RUN mkdir -p /app/data /app/logs && \
    chown -R ${PUID}:${PGID} /app

# Set default environment variables (can be overridden)
ENV PLEX_BASEURL=""
ENV PLEX_TOKEN=""
ENV PLEX_LIBRARY="Music"
ENV DATA_DIR="/app/data"
ENV LOG_FILE="/app/logs/explicit-labeler.log"
ENV PUID=${PUID}
ENV PGID=${PGID}

# Make scripts executable
RUN chmod +x mark_explicit_music.py scheduler.py entrypoint.sh

# Create log file with proper permissions
RUN touch /app/logs/explicit-labeler.log && \
    chown ${PUID}:${PGID} /app/logs/explicit-labeler.log && \
    chmod 666 /app/logs/explicit-labeler.log

# Entrypoint runs as root to fix permissions, then switches to appuser
# Make entrypoint executable and use it
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python3", "/app/scheduler.py"]

