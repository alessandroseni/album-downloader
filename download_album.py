#!/usr/bin/env python3
"""
YouTube Album Downloader & Splitter

Downloads a YouTube video as high-quality audio and splits it into 
individual tracks based on timestamps, with proper ID3 metadata.

Configuration is read from album.txt - copy album.example.txt to get started.
"""

import re
import subprocess
import sys
from pathlib import Path

from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TDRC, ID3NoHeaderError


# =============================================================================
# Configuration
# =============================================================================

CONFIG_FILE = "album.txt"
COOKIES_FILE = "cookies.txt"  # Optional: export from browser if YouTube requires auth


# =============================================================================
# Config Parser
# =============================================================================

def parse_config(filepath: Path) -> dict:
    """Parse album.txt config file."""
    if not filepath.exists():
        print("❌ Config file not found:", filepath)
        print("   Copy album.example.txt to album.txt and fill it out.")
        sys.exit(1)
    
    config = {
        "url": None,
        "artist": None,
        "album": None,
        "year": None,
        "tracklist": [],
    }
    
    content = filepath.read_text(encoding="utf-8")
    
    for line in content.splitlines():
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue
        
        # Parse key: value pairs
        if line.startswith("url:"):
            config["url"] = line.split(":", 1)[1].strip()
        elif line.startswith("artist:"):
            config["artist"] = line.split(":", 1)[1].strip()
        elif line.startswith("album:"):
            config["album"] = line.split(":", 1)[1].strip()
        elif line.startswith("year:"):
            config["year"] = line.split(":", 1)[1].strip()
        else:
            # Try to parse as tracklist entry: "0:00 Track Title" or "1:23:45 Track Title"
            match = re.match(r'^(\d+:\d+(?::\d+)?)\s+(.+)$', line)
            if match:
                timestamp, title = match.groups()
                config["tracklist"].append((title.strip(), timestamp))
    
    # Validate required fields
    missing = []
    if not config["url"]:
        missing.append("url")
    if not config["artist"]:
        missing.append("artist")
    if not config["album"]:
        missing.append("album")
    if not config["tracklist"]:
        missing.append("tracklist")
    
    if missing:
        print(f"❌ Missing required fields in {filepath}: {', '.join(missing)}")
        sys.exit(1)
    
    return config


# =============================================================================
# Helper Functions
# =============================================================================

def timestamp_to_seconds(timestamp: str) -> float:
    """Convert MM:SS or HH:MM:SS timestamp to seconds."""
    parts = timestamp.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + int(seconds)
    elif len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
    else:
        raise ValueError(f"Invalid timestamp format: {timestamp}")


def get_audio_duration(filepath: Path) -> float:
    """Get the duration of an audio file in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(filepath),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def download_audio(url: str, output_path: Path) -> Path:
    """Download YouTube video as high-quality audio using yt-dlp."""
    print("\n📥 Downloading audio from YouTube...")
    print(f"   URL: {url}")
    
    output_template = str(output_path / "full_audio.%(ext)s")
    
    cmd = [
        "yt-dlp",
        "--remote-components", "ejs:github",
        "-x",
        "--audio-format", "mp3",
        "--audio-quality", "0",
        "-o", output_template,
    ]
    
    # Add cookies if available
    cookies_path = Path(COOKIES_FILE)
    if cookies_path.exists():
        cmd.extend(["--cookies", str(cookies_path)])
    
    cmd.append(url)
    subprocess.run(cmd, check=True)
    
    audio_file = output_path / "full_audio.mp3"
    if not audio_file.exists():
        raise FileNotFoundError(f"Downloaded audio not found at {audio_file}")
    
    print(f"   ✅ Downloaded: {audio_file}")
    return audio_file


def split_audio(
    input_file: Path,
    output_dir: Path,
    tracklist: list,
    total_duration: float,
) -> list[Path]:
    """Split audio file into individual tracks using ffmpeg."""
    print(f"\n✂️  Splitting audio into {len(tracklist)} tracks...")
    
    output_files = []
    
    for i, (title, start_time) in enumerate(tracklist, 1):
        track_num = f"{i:02d}"
        safe_title = title.replace("/", "-")
        output_file = output_dir / f"{track_num} - {safe_title}.mp3"
        
        start_seconds = timestamp_to_seconds(start_time)
        
        if i < len(tracklist):
            next_start = timestamp_to_seconds(tracklist[i][1])
            duration = next_start - start_seconds
        else:
            duration = total_duration - start_seconds
        
        print(f"   [{track_num}] {title} ({start_time}, {duration:.1f}s)")
        
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", str(input_file),
                "-ss", str(start_seconds),
                "-t", str(duration),
                "-acodec", "libmp3lame",
                "-ab", "320k",
                "-map_metadata", "-1",
                str(output_file),
            ],
            capture_output=True,
            check=True,
        )
        
        output_files.append(output_file)
    
    print(f"   ✅ Split into {len(output_files)} tracks")
    return output_files


def add_metadata(
    files: list[Path],
    tracklist: list,
    album_info: dict,
) -> None:
    """Add ID3 metadata to MP3 files using mutagen."""
    print("\n🏷️  Adding ID3 metadata...")
    
    for i, (filepath, (title, _)) in enumerate(zip(files, tracklist), 1):
        try:
            audio = ID3(filepath)
        except ID3NoHeaderError:
            audio = ID3()
        
        audio.add(TIT2(encoding=3, text=title))
        audio.add(TPE1(encoding=3, text=album_info["artist"]))
        audio.add(TALB(encoding=3, text=album_info["album"]))
        audio.add(TRCK(encoding=3, text=f"{i}/{len(tracklist)}"))
        if album_info.get("year"):
            audio.add(TDRC(encoding=3, text=album_info["year"]))
        
        audio.save(filepath)
        print(f"   [{i:02d}] {title}")
    
    print(f"   ✅ Metadata added to {len(files)} files")


def main():
    """Main entry point."""
    # Parse config
    config = parse_config(Path(CONFIG_FILE))
    
    album_info = {
        "artist": config["artist"],
        "album": config["album"],
        "year": config.get("year"),
    }
    tracklist = config["tracklist"]
    url = config["url"]
    
    print("=" * 60)
    print("🎵 YouTube Album Downloader & Splitter")
    print("=" * 60)
    print(f"\n   Album: {album_info['album']}")
    print(f"   Artist: {album_info['artist']}")
    if album_info.get("year"):
        print(f"   Year: {album_info['year']}")
    print(f"   Tracks: {len(tracklist)}")
    
    # Create output directory
    if album_info.get("year"):
        album_folder = f"{album_info['artist']} - {album_info['album']} ({album_info['year']})"
    else:
        album_folder = f"{album_info['artist']} - {album_info['album']}"
    output_dir = Path("output") / album_folder
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Download
        temp_dir = Path("output") / ".temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        audio_file = download_audio(url, temp_dir)
        
        # Get duration
        total_duration = get_audio_duration(audio_file)
        print(f"\n   Total duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")
        
        # Split
        track_files = split_audio(audio_file, output_dir, tracklist, total_duration)
        
        # Tag
        add_metadata(track_files, tracklist, album_info)
        
        # Cleanup
        print("\n🧹 Cleaning up temp files...")
        audio_file.unlink()
        temp_dir.rmdir()
        
        # Done
        print("\n" + "=" * 60)
        print("✅ COMPLETE!")
        print("=" * 60)
        print(f"\n   Output folder: {output_dir.absolute()}")
        print("\n   Files created:")
        for f in sorted(output_dir.iterdir()):
            print(f"     • {f.name}")
        print()
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error running command: {e}", file=sys.stderr)
        if e.stderr:
            print(f"   {e.stderr.decode()}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
