# M3U to Local Downloader

A Python script to search and download VOD content from M3U playlist files.

## Description

This application parses an M3U file (`chans.m3u`), searches for specific content based on `tvg-id` or `tvg-name`, and downloads the matched video files locally. It is designed to specifically target static video files (like `.mp4`, `.mkv`, etc.) while ignoring live TV streams.

## Key Features

- **M3U Parsing**: Specifically looks for `tvg-id`, `tvg-name`, and stream URLs in `#EXTINF` tags.
- **Smart Search**: Performs a case-insensitive search across both `tvg-id` and `tvg-name` fields.
- **Live Stream Filtering**: Automatically skips entries that don't end with common video file extensions, preventing accidental downloads of infinite live streams.
- **Safe Downloads**: 
    - Uses temporary filenames during the download process to prevent corrupted files from incomplete downloads.
    - Checks if a file already exists before downloading to avoid duplicates.
    - Sanitizes filenames to ensure compatibility with different operating systems.
- **Conflict Resolution**: Appends a numeric suffix to filenames if multiple matches for the same title are found.
- **User Confirmation**: Displays matched items and asks for confirmation before starting downloads.
- **Automation Friendly**: Includes a `-y` flag to bypass confirmation prompts.
- **Custom M3U Path**: Specify an alternative M3U file using the `-m` or `--m3u` argument.

## Installation

### Using Makefile (Recommended)
You can install the script as a system-wide command `m3utolocal`:
```bash
make install
```
This will install the script to `/usr/local/bin` and install dependencies.

### Manual Installation
1. Ensure you have Python 3 installed.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Place your `chans.m3u` file in the same directory where you run the command.

## Usage

### System-wide Command
After installation, you can use `m3utolocal` from anywhere:
```bash
m3utolocal "Movie Title"
```

### Local Execution
You can also run it locally using `make`:
```bash
make run ARGS="Movie Title"
```
Or directly with Python:
```bash
python3 main.py "Movie Title"
```
The script will list all matches found and ask: `Do you want to download these files? (y/N):`.

### Bypass Confirmation
Use the `-y` or `--yes` flag to start downloads immediately:
```bash
python main.py -y "Movie Title"
```

### Help
To see all available options:
```bash
python main.py -h
```

### Specifying an M3U file
To use a different M3U file:
```bash
m3utolocal -m /path/to/your/playlist.m3u "Movie Title"
```

## Directory Structure
- `main.py`: The main script.
- `Makefile`: Build and installation script.
- `requirements.txt`: Python dependencies.
- `ports/`: FreeBSD ports entry.
- `chans.m3u`: Your input M3U playlist (expected in the root).
- `downloads/`: All downloaded files are placed here.
