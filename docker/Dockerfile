FROM python:3.11-slim

# Accept UID and GID as build arguments
ARG PUID=1000
ARG PGID=1000

# No need for cron, sudo, or gzip (Python has gzip module built-in)
# We run as non-root user for security

WORKDIR /app

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

# Create directories (will be overridden by volume mounts, but good for non-volume usage)
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

# Note: Log file will be created by the application at runtime in the mounted volume
# With read_only: true and volume mounts, the app will create files in mounted volumes

# Entrypoint runs as the user specified in docker-compose (non-root)
# Container runs with security hardening: cap_drop: ALL, read_only: true
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python3", "-u", "/app/scheduler.py"]

