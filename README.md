# Album Downloader

Download YouTube albums and split into individual MP3 tracks with ID3 metadata.

## Setup

```bash
brew install ffmpeg deno
uv sync
```

## Usage

1. Copy `album.example.txt` to `album.txt`
2. Fill in the URL, artist, album, year, and tracklist
3. (Optional) Export YouTube cookies to `cookies.txt` if authentication is required
4. Run: `uv run python download_album.py`

Output goes to `output/Artist - Album (Year)/`
