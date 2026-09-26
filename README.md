Youtube Video Downloader
=======================

A simple command-line tool to download YouTube videos with optional subtitles.

Installation
------------

1. Install Python 3.8 or higher
2. Install required libraries:
   pip install yt-dlp pandas requests
3. Install FFmpeg (required for audio conversion):
   - Ubuntu/Debian: sudo apt install ffmpeg
   - macOS: brew install ffmpeg
   - Windows: Download from https://ffmpeg.org/download.html

Usage
-----

Run the script:
  python "Youtube Video Downloader.py"

The program will:
1. Ask for a YouTube video URL
2. Show available formats
3. Let you choose audio or video download
4. Download the selected format with subtitles (if available)

Notes
-----
- Videos are saved to your Downloads folder
- Subtitles are downloaded when available
- Audio-only downloads are converted to MP3
- The script handles duplicate filenames automatically
