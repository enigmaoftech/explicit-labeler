# Explicit Labeler

Automatically marks explicit music in media servers based on folder and filename patterns.

## Quick Start

### Docker (Recommended)

The default setup runs with cron scheduling enabled, processing new albums daily at 2 AM.

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

# Optional: Test configuration first
# docker-compose exec explicit-music-labeler python3 mark_explicit_music.py --dry-run
```

## Documentation

- **[Readme](docs/readme.md)** - Complete documentation and usage guide
- **[Cron Setup](docs/cron-setup.md)** - Scheduling configuration and setup

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
- ✅ Docker with cron scheduling (configurable via env vars, default: daily at 2 AM)

## Default Schedule

The default docker-compose setup runs **daily at 2 AM**, processing only new albums that haven't been processed before.

To customize the schedule, set the `CRON_SCHEDULE` environment variable in your `.env` file:
```bash
# Edit .env file
nano .env

# Set CRON_SCHEDULE (examples):
# CRON_SCHEDULE=0 2 * * *        # Daily at 2 AM (default)
# CRON_SCHEDULE=0 */6 * * *      # Every 6 hours
# CRON_SCHEDULE=0 3 * * 1        # Every Monday at 3 AM
# CRON_SCHEDULE=0 2,14 * * *     # Twice daily (2 AM and 2 PM)

# Restart container to apply changes
docker-compose restart
```
