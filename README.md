# YT-DLP Self-Hosted Video Downloader

A modern, self-hosted web application that wraps yt-dlp and ffmpeg to download and process videos from various internet sources. Features a clean, professional interface inspired by Final Cut Pro X.

## Features

### Core Functionality
- **Download Videos**: Download videos in MP4 format with best audio and video quality
- **Timestamp Cutting**: Cut precise snippets from videos using timestamps (supports half-second precision)
- **Smart Caching**: Downloaded videos are cached for 3 days to allow re-cutting without re-downloading
- **Multiple Timestamps**: Process multiple timestamp ranges in a single request
- **Background Processing**: Downloads process in the background with real-time progress tracking

### User Experience
- **Modern UI**: Clean, dark-themed interface inspired by Final Cut Pro X
- **Session-Based Authentication**: Sleek login/logout system integrated into the app design
- **Real-Time Progress**: Live progress bar with download percentage
- **Past Jobs History**: View and re-download from your last 3 days of completed jobs
- **Error Handling**: User-friendly error messages with helpful guidance
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Clickable Navigation**: Header links to home page from all screens

### Technical Features
- **Two-Level Caching**: 
  - Original video cache (3-day retention)
  - Cut video cache (reuses existing cuts)
- **Automatic Cleanup**: Old downloads and cache files automatically removed after 3 days
- **Thread-Safe**: Background processing with proper thread management
- **Half-Second Precision**: Support for timestamps like `00:01:30.5`

## Installation

### Prerequisites
- Python 3.7+
- ffmpeg (for video processing)
- yt-dlp (installed via pip)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/jacobrosenfeld/ytdlp-self-hosted.git
   cd ytdlp-self-hosted
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install ffmpeg**
   - **macOS**: `brew install ffmpeg`
   - **Ubuntu/Debian**: `sudo apt install ffmpeg`
   - **Amazon Linux 2**: `sudo yum install ffmpeg`
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your preferred settings
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   - Open your browser to http://localhost:5000

## Configuration

Create a `.env` file in the root directory with the following variables:

```env
# Company Branding
COMPANY_NAME=Your Company Name        # Full company name (shown in headers)
COMPANY_SHORT_NAME=YourCompany       # Short name (used in footer)

# Contact Information
SUPPORT_EMAIL=support@yourcompany.com
LOCATION=Teaneck, NJ

# Authentication (REQUIRED for security)
AUTH_USERNAME=admin                   # Username for login authentication
AUTH_PASSWORD=change_this_password    # Password for login authentication

# Security (optional)
SECRET_KEY=your-secret-key-here      # Flask secret key
```

## Authentication

This application includes **session-based authentication** for security. You **MUST** configure authentication before deploying to a server.

### Required Authentication Setup

1. **Set strong credentials** in your `.env` file:
   ```env
   AUTH_USERNAME=your_username
   AUTH_PASSWORD=your_strong_password
   ```

2. **Change the default password** - never use the example password in production

3. **Use HTTPS** in production to protect credentials in transit

### How Authentication Works

- All pages require authentication via login form
- Users see a sleek login page matching the app's FCP X theme
- Successful login creates a session that persists across requests
- Failed login shows error message on the login page
- Logout link available in top-right corner of all pages
- Sessions automatically expire when browser is closed

## Usage

### Basic Download

1. Navigate to the home page
2. Enter a video URL (supports YouTube, Vimeo, and many other platforms via yt-dlp)
3. Click "Download" to get the full video

### Download with Timestamps

1. Enter a video URL
2. Click "Add Timestamp" to add timestamp ranges
3. Enter timestamps in format: `HH:MM:SS` or `HH:MM:SS.S` (half-seconds supported)
   - Example: `00:01:00 - 00:02:00` (1 minute to 2 minutes)
   - Example: `00:00:30.5 - 00:01:15` (30.5 seconds to 1 minute 15 seconds)
4. Add multiple timestamp ranges if needed
5. Click "Download" to process

### Past Jobs

- Click "View Past Jobs" to see your download history
- Re-download files from the last 3 days without re-processing
- View details of each job including file sizes and timestamp ranges

## Project Structure

```
ytdlp-self-hosted/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment configuration template
├── .gitignore            # Git ignore rules
├── README.md             # This file
├── templates/            # HTML templates
│   ├── index.html        # Main download form
│   ├── progress.html     # Progress tracking page
│   ├── result.html       # Download results page
│   └── past_jobs.html    # Job history page
├── downloads/            # Processed downloads (auto-created)
├── cache/                # Video cache (auto-created)
└── jobs.json            # Job metadata (auto-created)
```

## Technical Details

### Caching System

The application implements a two-level caching system:

1. **Video Cache**: Original downloaded videos are stored in `cache/` for 3 days
2. **Cut Cache**: Processed video cuts are stored in `downloads/` and reused when possible

This prevents redundant downloads and processing when:
- Re-cutting the same video with different timestamps
- Processing the same timestamp range multiple times

### Job Persistence

Download jobs are tracked in `jobs.json` with the following information:
- Unique job ID
- Original video URL
- Video title
- Timestamp ranges (if any)
- File paths and sizes
- Creation timestamp

Jobs older than 3 days are automatically cleaned up.

## Security Considerations

⚠️ **Important Security Notes**:

- This application allows downloading arbitrary internet content to your server
- **Session-based authentication is included** - configure strong credentials before deployment
- Implement proper authentication/authorization in production environments
- Consider rate limiting to prevent abuse
- Run behind a reverse proxy (nginx, Apache) with SSL/TLS
- Restrict network access appropriately
- Monitor disk usage as video files can be large

### Production Deployment

For production use:

1. Use a production WSGI server (gunicorn, uWSGI)
2. Set up proper authentication
3. Configure firewall rules
4. Enable HTTPS
5. Set up monitoring and logging
6. Configure automatic backups if needed

## Troubleshooting

### Common Issues

**ffmpeg not found**
- Ensure ffmpeg is installed and in your system PATH
- Test with: `ffmpeg -version`

**Download fails**
- Check if the URL is supported by yt-dlp
- Verify internet connectivity
- Check server disk space

**Timestamps not working**
- Ensure format is correct: `HH:MM:SS` or `HH:MM:SS.S`
- Start time must be before end time
- Times must be within the video duration

**Cache files accumulating**
- The app automatically cleans up files older than 3 days
- Manual cleanup: Delete contents of `cache/` and `downloads/` directories

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project uses:
- **yt-dlp**: Public Domain / Unlicense
- **ffmpeg**: LGPL/GPL (depending on build)
- **Flask**: BSD License

Please ensure compliance with all third-party licenses.

## Acknowledgments

- Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- Video processing powered by [ffmpeg](https://ffmpeg.org/)
- Web framework: [Flask](https://flask.palletsprojects.com/)

## Support

For issues and questions:
- Open an issue on GitHub
- Contact: [support email from .env]

---

Made with ❤️ in Teaneck, NJ