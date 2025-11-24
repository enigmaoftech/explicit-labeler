#!/usr/bin/env python3
"""
Explicit Music Labeler - Plex Support
(Planned: Emby, Jellyfin, Navidrome support)

Rules:
- ALBUM explicit is decided by the album directory name only (parent folder of the track file).
  If that folder contains "[E]" or the word "Explicit", the ALBUM title gets "[E]" at the front
  and the ALBUM gets an "Explicit" label. Otherwise, album title has "[E]" removed.
- TRACK explicit is decided by the track FILENAME only (basename), ignoring folders.
  If the filename contains "[E]" or the word "Explicit", the TRACK title gets "[E]" at the front
  and the TRACK gets an "Explicit" label. Otherwise, track title has "[E]" removed.
- We never touch album sort titles.
- Titles are edited via unlock -> set -> lock; fallback to direct PUT if needed.

Usage:
  export PLEX_BASEURL="http://127.0.0.1:32400"
  export PLEX_TOKEN="YOUR_PLEX_TOKEN"
  python3 mark_explicit_music.py --artist "Taylor Swift" --dry-run
  python3 mark_explicit_music.py --artist "Taylor Swift"

Optional:
  --remove-labels  # also remove "Explicit" label when not explicit
  --verbose        # show per-file detection details
Requires:
  pip install plexapi requests
"""

import os
import sys
import re
import argparse
import platform
import requests
import time
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from plexapi.server import PlexServer

EXPLICIT_LABEL = "Explicit"

# Throttling defaults (seconds)
DEFAULT_DELAY_AFTER_ALBUM = 0.5
DEFAULT_DELAY_AFTER_TRACK = 0.2
DEFAULT_DELAY_AFTER_ARTIST = 1.0
DEFAULT_DELAY_AFTER_API_CALL = 0.1

# Progress tracking
DATA_DIR = os.getenv("DATA_DIR", os.path.dirname(__file__))
PROGRESS_FILE = os.path.join(DATA_DIR, ".progress.json")
PROCESSED_ALBUMS_FILE = os.path.join(DATA_DIR, ".processed_albums.json")

# Forced headers (static & ASCII-safe)
DEVICE_NAME = "media-script"
PRODUCT = "Chrome"
CLIENT_ID = "media-script-cli"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36"
)

# Markers
E_TOKEN = "[E]"
LEADING_E = re.compile(r"^\s*\[E\]\s*", re.IGNORECASE)
TRAILING_E = re.compile(r"\s*\[E\]\s*$", re.IGNORECASE)
INLINE_E = re.compile(r"\[E\]", re.IGNORECASE)
MULTISPACE = re.compile(r"\s{2,}")
EXPLICIT_WORD_RE = re.compile(r"\bexplicit\b", re.IGNORECASE)

def strip_e(title: str) -> str:
    if not title:
        return title
    t = LEADING_E.sub("", title)
    t = TRAILING_E.sub("", t)
    t = INLINE_E.sub("", t)
    t = MULTISPACE.sub(" ", t).strip()
    return t

def apply_front(title: str) -> str:
    base = strip_e(title or "")
    return f"{E_TOKEN} {base}".strip() if base else E_TOKEN

# ---------- path helpers ----------
def get_all_part_paths(track):
    paths = []
    try:
        track.reload()
    except Exception:
        pass
    try:
        if getattr(track, "media", None):
            for media in track.media:
                if getattr(media, "parts", None):
                    for part in media.parts:
                        if getattr(part, "file", None):
                            paths.append(str(part.file))
    except Exception:
        pass
    return paths

def track_filename_is_explicit(track, verbose=False):
    """Decide TRACK explicitness by filename (basename) only."""
    any_part = False
    for p in get_all_part_paths(track):
        any_part = True
        base = os.path.basename(p)
        bl = base.lower()
        hit = ("[e]" in bl) or (EXPLICIT_WORD_RE.search(base) is not None)
        if verbose:
            print(f"      • track filename check: {base} -> {'EXPLICIT' if hit else 'clean'}")
        if hit:
            return True
    # If no parts found, default to not explicit
    if verbose and not any_part:
        print("      • track filename check: no media parts found -> clean")
    return False

def album_folder_is_explicit(album, sample_track=None, verbose=False):
    """
    Decide ALBUM explicitness by album directory (parent folder of the track file).
    We derive album folder from any track in that album.
    """
    # Prefer provided sample track for performance; otherwise take first available.
    try:
        tracks = [sample_track] if sample_track else album.tracks()
    except Exception:
        tracks = []
    for t in tracks:
        for p in get_all_part_paths(t):
            album_dir = os.path.basename(os.path.dirname(p))
            hit = ("[e]" in album_dir.lower()) or (EXPLICIT_WORD_RE.search(album_dir) is not None)
            if verbose:
                print(f"      • album folder check: {album_dir} -> {'EXPLICIT' if hit else 'clean'}")
            return hit
    if verbose:
        print("      • album folder check: no paths found -> clean")
    return False

# ---------- labels ----------
def has_label(item, label: str) -> bool:
    try:
        return any(getattr(l, "tag", "").lower() == label.lower() for l in (item.labels or []))
    except Exception:
        return False

def add_label_if_missing(item, label: str, dry_run: bool, delay=DEFAULT_DELAY_AFTER_API_CALL):
    if not has_label(item, label):
        if dry_run:
            print(f"  - DRY RUN: would add label '{label}' to {item.type}: {item.title}")
        else:
            time.sleep(delay)
            item.addLabel(label)
            print(f"  - Added label '{label}' to {item.type}: {item.title}")

def remove_label_if_present(item, label: str, dry_run: bool, delay=DEFAULT_DELAY_AFTER_API_CALL):
    try:
        if has_label(item, label):
            if dry_run:
                print(f"  - DRY RUN: would remove label '{label}' from {item.type}: {item.title}")
            else:
                time.sleep(delay)
                item.removeLabel(label)
                print(f"  - Removed label '{label}' from {item.type}: {item.title}")
    except Exception:
        pass

# ---------- robust title edit ----------
def put_metadata_direct(session, baseurl, token, rating_key, fields: dict) -> bool:
    url = urljoin(baseurl if baseurl.endswith('/') else baseurl + '/', f"library/metadata/{rating_key}")
    params = {"X-Plex-Token": token}
    params.update(fields)
    resp = session.put(url, params=params)
    return resp.ok

def edit_title_unlock_set_lock(item, new_title: str, dry_run: bool, prefix: str, session=None, baseurl=None, token=None, delay=DEFAULT_DELAY_AFTER_API_CALL):
    curr = item.title or ""
    if curr == new_title:
        return
    if dry_run:
        print(f"{prefix}- DRY RUN: '{curr}' -> '{new_title}'")
        return
    try:
        if hasattr(item, "unlockField"):
            item.unlockField("title")
        time.sleep(delay)
        item.edit(**{"title.value": new_title})
        time.sleep(delay)
        if hasattr(item, "lockField"):
            item.lockField("title")
        time.sleep(delay)
        item.refresh(); item.reload()
        if (item.title or "") == new_title:
            print(f"{prefix}- Updated title: '{item.title}'")
            return
    except Exception:
        pass
    try:
        if session and baseurl and token:
            time.sleep(delay)
            ok = put_metadata_direct(session, baseurl, token, item.ratingKey,
                                     {"title.value": new_title, "title.locked": 1})
            if ok:
                time.sleep(delay)
                item.refresh(); item.reload()
                if (item.title or "") == new_title:
                    print(f"{prefix}- Updated title (direct PUT): '{item.title}'")
                    return
    except Exception:
        pass
    print(f"{prefix}- WARN: failed to update title '{curr}'")

# ---------- forced-header session ----------
class ForcedHeaderSession(requests.Session):
    def prepare_request(self, request):
        prepared = super().prepare_request(request)
        forced = {
            "User-Agent": USER_AGENT,
            "X-Plex-Product": PRODUCT,
            "X-Plex-Device-Name": DEVICE_NAME,
            "X-Plex-Client-Identifier": CLIENT_ID,
            "X-Plex-Device": "Script",
            "X-Plex-Platform": "Python",
            "X-Plex-Platform-Version": platform.python_version(),
            "X-Plex-Version": "1.0",
        }
        prepared.headers.update(forced)
        # latin-1 clean
        safe = {}
        for k, v in prepared.headers.items():
            try:
                safe_v = v.encode("latin-1", "ignore").decode("latin-1")
            except Exception:
                safe_v = ""
            safe[k] = safe_v
        prepared.headers.clear(); prepared.headers.update(safe)
        return prepared

# ---------- progress tracking ----------
def load_progress():
    """Load progress state from file."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_library": None, "last_artist": None, "last_album": None, "processed_artists": []}

def save_progress(library_name, artist_key, album_key, processed_artists):
    """Save progress state to file."""
    try:
        # Ensure directory exists
        progress_dir = os.path.dirname(PROGRESS_FILE)
        if progress_dir:
            os.makedirs(progress_dir, exist_ok=True)
        with open(PROGRESS_FILE, 'w') as f:
            json.dump({
                "last_library": library_name,
                "last_artist": artist_key,
                "last_album": album_key,
                "processed_artists": processed_artists,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
    except Exception:
        pass

def clear_progress():
    """Clear progress state."""
    for f in [PROGRESS_FILE, PROCESSED_ALBUMS_FILE]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

def load_processed_albums():
    """Load set of processed album keys."""
    if os.path.exists(PROCESSED_ALBUMS_FILE):
        try:
            with open(PROCESSED_ALBUMS_FILE, 'r') as f:
                data = json.load(f)
                return set(data.get("albums", []))
        except Exception:
            pass
    return set()

def save_processed_album(album_key):
    """Add an album to the processed set."""
    processed = load_processed_albums()
    processed.add(album_key)
    try:
        # Ensure directory exists
        albums_dir = os.path.dirname(PROCESSED_ALBUMS_FILE)
        if albums_dir:
            os.makedirs(albums_dir, exist_ok=True)
        with open(PROCESSED_ALBUMS_FILE, 'w') as f:
            json.dump({
                "albums": list(processed),
                "last_updated": datetime.now().isoformat()
            }, f, indent=2)
    except Exception:
        pass

def get_album_key(library_name, artist_title, album_title, album_rating_key):
    """Generate a unique key for an album (includes library name for multi-library support)."""
    return f"{library_name}|||{artist_title}|||{album_title}|||{album_rating_key}"

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(description="Enforce [E] from album folder (album) and filename (track). Remove wrong [E].")
    ap.add_argument("--baseurl", default=os.getenv("PLEX_BASEURL"))
    ap.add_argument("--token", default=os.getenv("PLEX_TOKEN"))
    ap.add_argument("--library", action="append", help="Music library name (can be specified multiple times). Default: 'Music'")
    ap.add_argument("--all-libraries", action="store_true", help="Process all music libraries found on the server")
    ap.add_argument("--artist", help="Limit to a single artist")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--verbose", action="store_true", help="Show folder/filename detection details")
    ap.add_argument("--remove-labels", action="store_true", help="Also remove 'Explicit' labels when not explicit")
    ap.add_argument("--force", action="store_true", help="Force reprocessing of all albums (ignore processed cache)")
    ap.add_argument("--resume", action="store_true", help="Resume from last position (default: True)")
    ap.add_argument("--no-resume", dest="resume", action="store_false", help="Don't resume, start from beginning")
    # Read throttling from environment variables if available, otherwise use defaults
    # Validate that values are positive numbers, use defaults if invalid or negative
    def safe_float_env(env_var, default):
        try:
            val = os.getenv(env_var)
            if val is None or val.strip() == "":
                return default
            fval = float(val)
            # Reject negative numbers - use default instead
            if fval < 0:
                return default
            return fval
        except (ValueError, TypeError):
            return default
    
    delay_album_default = safe_float_env("DELAY_AFTER_ALBUM", DEFAULT_DELAY_AFTER_ALBUM)
    delay_track_default = safe_float_env("DELAY_AFTER_TRACK", DEFAULT_DELAY_AFTER_TRACK)
    delay_artist_default = safe_float_env("DELAY_AFTER_ARTIST", DEFAULT_DELAY_AFTER_ARTIST)
    delay_api_default = safe_float_env("DELAY_AFTER_API_CALL", DEFAULT_DELAY_AFTER_API_CALL)
    
    ap.add_argument("--delay-album", type=float, default=delay_album_default, help=f"Delay after processing album (default: {delay_album_default}s, env: DELAY_AFTER_ALBUM)")
    ap.add_argument("--delay-track", type=float, default=delay_track_default, help=f"Delay after processing track (default: {delay_track_default}s, env: DELAY_AFTER_TRACK)")
    ap.add_argument("--delay-artist", type=float, default=delay_artist_default, help=f"Delay after processing artist (default: {delay_artist_default}s, env: DELAY_AFTER_ARTIST)")
    ap.add_argument("--delay-api", type=float, default=delay_api_default, help=f"Delay after API call (default: {delay_api_default}s, env: DELAY_AFTER_API_CALL)")
    ap.add_argument("--clear-progress", action="store_true", help="Clear progress and processed albums cache")
    ap.set_defaults(resume=True)
    args = ap.parse_args()

    if not args.baseurl or not args.token:
        print("ERROR: Set --baseurl/--token or PLEX_BASEURL/PLEX_TOKEN.", file=sys.stderr)
        sys.exit(1)

    # Clear progress if requested
    if args.clear_progress:
        clear_progress()
        print("Progress and processed albums cache cleared.")
        return

    # Load progress and processed albums
    progress = load_progress() if args.resume else {}
    processed_albums = set() if args.force else load_processed_albums()
    
    if args.resume and progress.get("last_library"):
        print(f"Resuming from: Library '{progress.get('last_library')}' / {progress.get('last_artist')} / {progress.get('last_album', 'N/A')}")
    
    print(f"Processed albums cache: {len(processed_albums)} albums")
    if args.force:
        print("Force mode: will reprocess all albums")

    session = ForcedHeaderSession()
    try:
        plex = PlexServer(args.baseurl, args.token, session=session)
    except Exception as e:
        print(f"ERROR: Connect failed: {e}", file=sys.stderr); sys.exit(1)

    # Determine which libraries to process
    libraries_to_process = []
    if args.all_libraries:
        # Find all music libraries
        try:
            all_sections = plex.library.sections()
            for section in all_sections:
                if section.type == "artist":  # Music libraries have type "artist"
                    libraries_to_process.append(section.title)
            if not libraries_to_process:
                print("ERROR: No music libraries found on server.", file=sys.stderr)
                sys.exit(1)
            print(f"Found {len(libraries_to_process)} music library/libraries: {', '.join(libraries_to_process)}")
        except Exception as e:
            print(f"ERROR: Failed to list libraries: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.library:
        # Use specified libraries
        libraries_to_process = args.library
    else:
        # Default to "Music" or from env var
        default_lib = os.getenv("PLEX_LIBRARY", "Music")
        libraries_to_process = [default_lib]

    total_tracks_checked = 0
    total_titles_updated = 0
    total_albums_updated = 0
    
    # Resume logic
    resume_library = progress.get("last_library")
    resume_artist = progress.get("last_artist")
    resume_album = progress.get("last_album")
    skip_until_library = resume_library if args.resume and resume_library else None
    skip_until_artist = resume_artist if args.resume and resume_artist else None
    skip_until_album = resume_album if args.resume and resume_album else None
    found_resume_point = False

    # Process each library
    for library_name in libraries_to_process:
        # Resume logic: skip until we find the resume library
        if skip_until_library and not found_resume_point:
            if library_name == skip_until_library:
                found_resume_point = True
                print(f"\n{'='*60}")
                print(f"Processing Library: {library_name} (resuming from here)")
                print(f"{'='*60}")
            else:
                print(f"\nSkipping library: {library_name} (already processed)")
                continue
        else:
            print(f"\n{'='*60}")
            print(f"Processing Library: {library_name}")
            print(f"{'='*60}")

        try:
            music = plex.library.section(library_name)
        except Exception as e:
            print(f"ERROR: Library '{library_name}': {e}")
            continue

        artists = music.search(libtype="artist", title=args.artist) if args.artist else music.search(libtype="artist")
        if args.artist and not artists:
            print(f"No artists matched '{args.artist}' in library '{library_name}'.")
            continue

        for artist in artists:
            artist_key = f"{artist.title}|||{artist.ratingKey}"
            
            # Resume logic: skip until we find the resume point
            if skip_until_artist and found_resume_point and library_name == skip_until_library:
                if artist_key != skip_until_artist:
                    # Haven't reached resume artist yet, skip
                    continue
                else:
                    # Found resume artist
                    if skip_until_album:
                        print(f"\nResuming from artist: {artist.title}")
                    else:
                        print(f"\nResuming from artist: {artist.title} (new album)")
            elif skip_until_artist and found_resume_point and library_name != skip_until_library:
                # Different library, clear resume flags
                skip_until_artist = None
                skip_until_album = None
        
        print(f"\nArtist: {artist.title}")
        try:
            albums = artist.albums()
        except Exception as e:
            print(f"  - Skipping artist (albums error): {e}")
            continue
        
        # Sleep after successfully getting albums (outside try block to avoid masking sleep errors)
        if args.delay_artist > 0:
            time.sleep(args.delay_artist)

        for album in albums:
            album_key = get_album_key(library_name, artist.title, album.title or "", str(album.ratingKey))
            
            # Resume logic: skip until we find the resume album
            if skip_until_album and found_resume_point and library_name == skip_until_library:
                if not skip_until_album == album_key:
                    continue
                else:
                    print(f"  Album: {album.title} (resuming from here)")
                    skip_until_album = None  # Clear resume flag after finding it
            else:
                print(f"  Album: {album.title}")
            
            # Skip if already processed (unless force)
            if album_key in processed_albums and not args.force:
                print(f"    - Skipping (already processed)")
                continue
            
            try:
                tracks = album.tracks()
                time.sleep(args.delay_api)
            except Exception as e:
                print(f"    - Skipping album (tracks error): {e}")
                continue

            try:
                # Decide album explicit from ALBUM FOLDER (use first track as sample for folder)
                sample_track = tracks[0] if tracks else None
                album_is_explicit = album_folder_is_explicit(album, sample_track=sample_track, verbose=args.verbose)
                time.sleep(args.delay_api)

                # Apply album title
                desired_album_title = apply_front(album.title or "") if album_is_explicit else strip_e(album.title or "")
                if desired_album_title != (album.title or ""):
                    total_albums_updated += 1
                    action = "mark" if album_is_explicit else "unmark"
                    print(f"    * Album title {action}: {album.title}")
                    edit_title_unlock_set_lock(album, desired_album_title, args.dry_run, prefix="    ",
                                               session=session, baseurl=args.baseurl, token=args.token,
                                               delay=args.delay_api)

                # Album label
                if album_is_explicit:
                    add_label_if_missing(album, EXPLICIT_LABEL, args.dry_run, delay=args.delay_api)
                elif args.remove_labels:
                    remove_label_if_present(album, EXPLICIT_LABEL, args.dry_run, delay=args.delay_api)

                # Tracks: decide explicit from FILENAME ONLY
                for track in tracks:
                    total_tracks_checked += 1
                    is_explicit = track_filename_is_explicit(track, verbose=args.verbose)
                    time.sleep(args.delay_api)

                    if is_explicit:
                        desired = apply_front(track.title or "")
                        if desired != (track.title or ""):
                            total_titles_updated += 1
                            print(f"    Track mark: {track.title}")
                            edit_title_unlock_set_lock(track, desired, args.dry_run, prefix="    ",
                                                       session=session, baseurl=args.baseurl, token=args.token,
                                                       delay=args.delay_api)
                        add_label_if_missing(track, EXPLICIT_LABEL, args.dry_run, delay=args.delay_api)
                    else:
                        if "[e]" in (track.title or "").lower():
                            cleaned = strip_e(track.title or "")
                            if cleaned != (track.title or ""):
                                total_titles_updated += 1
                                print(f"    Track unmark: {track.title}")
                                edit_title_unlock_set_lock(track, cleaned, args.dry_run, prefix="    ",
                                                           session=session, baseurl=args.baseurl, token=args.token,
                                                           delay=args.delay_api)
                        if args.remove_labels:
                            remove_label_if_present(track, EXPLICIT_LABEL, args.dry_run, delay=args.delay_api)
                    
                    time.sleep(args.delay_track)
                
                # Mark album as processed
                if not args.dry_run:
                    save_processed_album(album_key)
                
                # Save progress after each album
                save_progress(library_name, artist_key, album_key, [])
                
                time.sleep(args.delay_album)
                
            except Exception as e:
                print(f"    - ERROR processing album: {e}")
                print(f"    - Progress saved, can resume from: Library '{library_name}' / {artist.title} / {album.title}")
                # Save progress even on error
                save_progress(library_name, artist_key, album_key, [])
                continue

    # Clear progress on successful completion
    if not args.dry_run:
        clear_progress()
        print("\n✓ Progress cleared (run completed successfully)")
    
    print("\nSummary:")
    print(f"  Tracks checked:  {total_tracks_checked}")
    print(f"  Titles updated:  {total_titles_updated}")
    print(f"  Albums updated:  {total_albums_updated}")
    if args.dry_run:
        print("  (Dry run only; no changes were saved.)")

if __name__ == "__main__":
    main()