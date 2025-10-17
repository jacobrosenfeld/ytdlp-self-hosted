# YT-DLP Self-Hosted Downloader

A simple web wrapper for yt-dlp with ffmpeg to download videos from internet sources.

## Features

- Download videos in MP4 format with best audio and video quality.
- Cut snippets from videos using timestamps.
- Caches downloaded videos for 3 days to allow re-cutting without re-downloading.
- Simple web interface.

## Installation

1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Install ffmpeg on your system (required for video processing).
   - On Amazon Linux 2: `sudo yum install ffmpeg`
4. Copy `.env.example` to `.env` and customize the variables.
5. Run the app: `python app.py`
6. Access at http://localhost:5000

## Configuration

Edit the `.env` file to customize branding:

- `COMPANY_SHORT_NAME`: Your company name
- `SUPPORT_EMAIL`: Support email address
- `LOCATION`: Location for the footer
- `SECRET_KEY`: Flask secret key (optional, defaults to a placeholder)

## Usage

- Enter the video URL.
- Optionally, enter timestamps in the format start-end (e.g., 00:00:10-00:01:00) separated by commas for multiple snippets.
- Click Download.
- Download the resulting MP4 file(s).

## Security Note

This app allows downloading files to the server. Ensure proper access controls in production.