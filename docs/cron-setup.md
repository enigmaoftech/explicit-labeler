# Cron Scheduling Setup Guide

This guide explains how to set up automated scheduling for the Explicit Music Labeler.

## Customizing the Schedule

Configure the schedule via the `CRON_SCHEDULE` environment variable in your `.env` file:

```bash
# Edit .env file
nano .env

# Set CRON_SCHEDULE (examples):
CRON_SCHEDULE=0 2 * * *        # Daily at 2 AM (default)
CRON_SCHEDULE=0 */6 * * *       # Every 6 hours
CRON_SCHEDULE=0 3 * * 1         # Every Monday at 3 AM
CRON_SCHEDULE=0 2,14 * * *     # Twice daily (2 AM and 2 PM)

# Restart container to apply changes
docker-compose restart
```

**Note**: The schedule is applied at container startup, so you only need to restart the container, not rebuild it.

## Best Practices

1. **Start with daily schedule**: Process new albums daily at off-peak hours (2-4 AM)
2. **Monitor logs**: Check logs regularly to ensure jobs are running successfully
3. **Use `--force` sparingly**: Only for weekly/monthly full reprocess
4. **Test first**: Always test with `--dry-run` before scheduling
5. **Backup progress files**: The `data/` directory contains progress state
6. **Set appropriate delays**: Adjust `--delay-*` flags if Plex is slow

## Recommended Schedules

### Small Library (< 1000 albums)
- Daily at 2 AM: `0 2 * * *`
- Or every 12 hours: `0 */12 * * *`

### Medium Library (1000-5000 albums)
- Daily at 2 AM: `0 2 * * *`
- Weekly full reprocess: `0 2 * * 0` with `--force`

### Large Library (> 5000 albums)
- Daily at 2 AM: `0 2 * * *` (new albums only)
- Monthly full reprocess: `0 2 1 * *` with `--force`

