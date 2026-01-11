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
3. Export YouTube cookies (see below)
4. Run: `uv run python download_album.py`

Output goes to `output/Artist - Album (Year)/`

## Exporting YouTube Cookies

YouTube requires authentication to download some videos. To export your cookies:

1. Install the [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) browser extension
2. Go to YouTube and make sure you're logged in
3. Click the extension icon and export cookies
4. Save the file as `cookies.txt` in this project folder
