FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy script
COPY app/mark_explicit_music.py .

# Create directory for progress files
RUN mkdir -p /app/data

# Set default environment variables (can be overridden)
ENV PLEX_BASEURL=""
ENV PLEX_TOKEN=""
ENV PLEX_LIBRARY="Music"
ENV DATA_DIR="/app/data"

# Make script executable
RUN chmod +x mark_explicit_music.py

# Default command (can be overridden)
CMD ["python3", "mark_explicit_music.py", "--help"]

