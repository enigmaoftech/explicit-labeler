# Explicit Labeler

Automatically marks explicit music in media servers based on folder and filename patterns.

## Supported Media Servers

- ✅ **Plex** - Currently supported
- 🔜 **Emby** - Planned
- 🔜 **Jellyfin** - Planned
- 🔜 **Navidrome** - Planned

## Features

- **Throttling**: Configurable delays to prevent overwhelming the media server
- **Resume Capability**: Automatically saves progress and can resume from where it left off on errors
- **New Album Detection**: Only processes albums that haven't been processed before (unless `--force` is used)
- **Multi-Library Support**: Process multiple music libraries in a single run
- **Docker Support**: Ready to run in a container with cron scheduling
- **Cron Scheduling**: Automated scheduling (default: daily at 2 AM)

## Quick Start

### Docker (Recommended)

The default docker-compose setup runs with cron scheduling enabled, processing new albums daily at 2 AM.

1. Create a `.env` file from the example:
```bash
cp .env.example .env
# Edit .env and add your PLEX_TOKEN
nano .env
```

The `.env.example` file includes all configuration options with comments.

2. Start the container:
```bash
docker-compose up -d
```

3. View logs:
```bash
docker-compose logs -f
# Or
tail -f logs/cron.log
```

4. Customize schedule (optional):
   - Edit `app/crontab` file
   - Rebuild: `docker-compose build`
   - Restart: `docker-compose up -d`

### Local Python

```bash
export PLEX_BASEURL="http://127.0.0.1:32400"
export PLEX_TOKEN="YOUR_PLEX_TOKEN"
cd app
python3 mark_explicit_music.py --artist "Taylor Swift" --dry-run
python3 mark_explicit_music.py --artist "Taylor Swift"
```

### Manual Docker Run (One-time)

For one-time runs without cron:

```bash
# Dry run
docker-compose run --rm explicit-music-labeler python3 mark_explicit_music.py --dry-run

# Process specific artist
docker-compose run --rm explicit-music-labeler python3 mark_explicit_music.py --artist "Taylor Swift"

# Process all (only new albums)
docker-compose run --rm explicit-music-labeler python3 mark_explicit_music.py

# Process multiple specific libraries
docker-compose run --rm explicit-music-labeler python3 mark_explicit_music.py --library "Music" --library "Classical Music"

# Process all music libraries automatically
docker-compose run --rm explicit-music-labeler python3 mark_explicit_music.py --all-libraries

# Force reprocess all albums
docker-compose run --rm explicit-music-labeler python3 mark_explicit_music.py --force

# Resume from last position
docker-compose run --rm explicit-music-labeler python3 mark_explicit_music.py --resume
```

## Command Line Options

*Note: Current options are Plex-specific. Options for other media servers will be added as support is implemented.*

- `--baseurl`: Plex server URL (or set `PLEX_BASEURL` env var)
- `--token`: Plex token (or set `PLEX_TOKEN` env var)
- `--library`: Music library name (can be specified multiple times for multiple libraries). Default: "Music" or `PLEX_LIBRARY` env var
- `--all-libraries`: Automatically process all music libraries found on the server
- `--artist`: Limit to a single artist (applies to all libraries)
- `--dry-run`: Show what would be changed without making changes
- `--verbose`: Show per-file detection details
- `--remove-labels`: Also remove "Explicit" labels when not explicit
- `--force`: Force reprocessing of all albums (ignore processed cache)
- `--resume`: Resume from last position (default: True)
- `--no-resume`: Don't resume, start from beginning
- `--delay-album`: Delay after processing album in seconds (default: 0.5)
- `--delay-track`: Delay after processing track in seconds (default: 0.2)
- `--delay-artist`: Delay after processing artist in seconds (default: 1.0)
- `--delay-api`: Delay after API call in seconds (default: 0.1)
- `--clear-progress`: Clear progress and processed albums cache

## How It Works

- **Album Explicit**: Determined by the album directory name (parent folder). If folder contains "[E]" or "Explicit", album gets "[E]" prefix and "Explicit" label.
- **Track Explicit**: Determined by the track filename only. If filename contains "[E]" or "Explicit", track gets "[E]" prefix and "Explicit" label.

## Progress Tracking

The script automatically saves progress to `.progress.json` and tracks processed albums in `.processed_albums.json`. If the script errors or is interrupted, it can resume from the last position.

Progress files are stored in the `data/` directory when running in Docker.

## File Ownership

When running in Docker, files are created with ownership matching the `PUID` and `PGID` environment variables (default: 1000:1000). This ensures that files created by the container can be easily accessed by your user.

To set custom UID/GID, add to your `.env` file:
```bash
PUID=1000
PGID=1000
```

You can find your UID/GID with:
```bash
# Linux/macOS
id -u  # UID
id -g  # GID
```

## Run at Start

By default, the container will run the script immediately when it starts, then continue with the cron schedule. To disable this behavior, set in your `.env` file:

```bash
RUN_AT_START=false
```

This is useful if you only want the script to run on the cron schedule and not immediately on container start.

## Throttling

Throttling delays can be configured via environment variables in your `.env` file to prevent overwhelming your Plex server:

**Important**: All delay values must be **positive numbers (0 or greater)**. Negative numbers are not allowed and will be rejected, causing the default value to be used instead.

Default delays:
- After album: 0.5s (`DELAY_AFTER_ALBUM`)
- After track: 0.2s (`DELAY_AFTER_TRACK`)
- After artist: 1.0s (`DELAY_AFTER_ARTIST`)
- After API call: 0.1s (`DELAY_AFTER_API_CALL`)

To customize, add to your `.env` file:
```bash
# All values must be positive (0 or greater)
DELAY_AFTER_ALBUM=1.0      # Increase delay if Plex is slow
DELAY_AFTER_TRACK=0.5
DELAY_AFTER_ARTIST=2.0
DELAY_AFTER_API_CALL=0.2
```

**Note**: If you set a negative value, it will be rejected and the default will be used. If you don't set these variables at all, defaults will be used automatically.

You can also adjust these with `--delay-*` command-line flags if needed.

## Scheduling

The default docker-compose setup runs with cron scheduling enabled. The default schedule is **daily at 2 AM**, processing only new albums.

For detailed scheduling information, see [cron-setup.md](cron-setup.md).

### Quick Schedule Examples

- **Default**: Daily at 2 AM (new albums only)
- **All libraries**: Edit `crontab` and add `--all-libraries` flag
- **Full reprocess**: Edit `crontab` and add `--force` flag (use weekly/monthly)

## Documentation

- [Cron Setup Guide](cron-setup.md) - Detailed scheduling setup and configuration

