# App Scheduling Setup Guide

This guide explains how to set up automated scheduling for the Explicit Music Labeler using the built-in Python scheduler.

## Customizing the Schedule

Configure the schedule via the `APP_TIMES` environment variable in your `.env` file. You can specify a single schedule or multiple schedules separated by commas. The scheduler uses **military time format** (HH:MM):

```bash
# Edit .env file
nano .env

# Set APP_TIMES (examples):
APP_TIMES=02:00                        # Daily at 2 AM (default)
APP_TIMES=14:00                        # Daily at 2 PM
APP_TIMES=00:30                        # Daily at 12:30 AM
APP_TIMES=02:00,14:00                  # Twice daily (2 AM and 2 PM)
APP_TIMES=06:00,12:00,18:00            # Three times daily (6 AM, 12 PM, 6 PM)

# Restart container to apply changes
docker-compose restart
```

**Note**: The schedule is applied at container startup, so you only need to restart the container, not rebuild it. Multiple schedules are supported - separate them with commas. All times must be in HH:MM format (24-hour format).

## Best Practices

1. **Start with daily schedule**: Process new albums daily at off-peak hours (2-4 AM)
2. **Monitor logs**: Check logs regularly to ensure jobs are running successfully
3. **Use `--force` sparingly**: Only for weekly/monthly full reprocess
4. **Test first**: Always test with `--dry-run` before scheduling
5. **Backup progress files**: The `data/` directory contains progress state
6. **Set appropriate delays**: Adjust `--delay-*` flags if Plex is slow

## Recommended Schedules

### Small Library (< 1000 albums)
- Daily at 2 AM: `02:00`
- Or twice daily: `02:00,14:00`

### Medium Library (1000-5000 albums)
- Daily at 2 AM: `02:00`

### Large Library (> 5000 albums)
- Daily at 2 AM: `02:00` (new albums only)

