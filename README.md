# Explicit Labeler

Automatically marks explicit music in media servers based on folder and filename patterns.

## Quick Start

### Docker (Recommended)

The default setup runs with the built-in Python scheduler enabled, processing new albums daily at 2 AM.

#### From GitHub

If you've cloned this repository, you can pull the pre-built image from GitHub Container Registry:

```bash
# Pull the image
docker pull ghcr.io/enigmaoftech/explicit-labeler:latest

# Or use docker-compose (it will build locally if image not found)
docker-compose up -d
```

#### Local Build

```bash
# 1. Create .env file from example
cp .env.example .env
# Edit .env and add your PLEX_TOKEN and adjust other settings
nano .env

# 2. Build and start container
docker-compose build
docker-compose up -d

# 3. View logs
docker-compose logs -f

# Or view log file directly
tail -f logs/explicit-labeler.log

# Logs are automatically rotated before each run
# Default: keeps 7 runs of history (configurable via LOG_RETENTION_RUNS)
# Rotated logs: explicit-labeler-1.log, explicit-labeler-2.log, etc.

# Optional: Test configuration first
# docker-compose exec explicit-music-labeler python3 mark_explicit_music.py --dry-run
```

## Documentation

- **[Readme](docs/readme.md)** - Complete documentation and usage guide
- **[App Scheduling](docs/app-scheduling.md)** - Scheduling configuration and setup

## Supported Media Servers

- ✅ **Plex** - Currently supported
- 🔜 **Emby** - Planned
- 🔜 **Jellyfin** - Planned
- 🔜 **Navidrome** - Planned

## Features

- ✅ Throttling to prevent media server lockups (configurable via env vars)
- ✅ Resume capability on errors
- ✅ New album detection (skip processed albums)
- ✅ Multi-library support
- ✅ Docker with built-in Python scheduler (configurable via env vars, default: daily at 2 AM)

## Default Schedule

The default docker-compose setup runs **daily at 2 AM**, processing only new albums that haven't been processed before.

To customize the schedule, set the `APP_TIMES` environment variable in your `.env` file. You can specify a single schedule or multiple schedules separated by commas. The scheduler uses **military time format** (HH:MM):

```bash
# Edit .env file
nano .env

# Set APP_TIMES (examples):
APP_TIMES=02:00                        # Daily at 2 AM (default)
APP_TIMES=14:00                        # Daily at 2 PM
APP_TIMES=00:30                        # Daily at 12:30 AM
APP_TIMES=02:00,14:00                 # Twice daily (2 AM and 2 PM)
APP_TIMES=06:00,12:00,18:00           # Three times daily (6 AM, 12 PM, 6 PM)

# Restart container to apply changes
docker-compose restart
```

## Log Retention

By default, the application keeps 7 runs of rotated logs. Logs are rotated before each script execution. You can customize this by setting the `LOG_RETENTION_RUNS` environment variable in your `.env` file:

```bash
# Keep 14 runs of log history
LOG_RETENTION_RUNS=14

# Keep 30 runs of log history
LOG_RETENTION_RUNS=30

# Keep only 3 runs (minimum: 1)
LOG_RETENTION_RUNS=3
```

**Note**: The value must be a positive integer (1 or greater). If an invalid value is provided, the default of 7 runs will be used. Each time the script runs, the current log is rotated and older logs are shifted (1 becomes 2, 2 becomes 3, etc.), with the oldest being deleted.
