<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## YT-DLP Self-Hosted Video Downloader - Development Guide

### Project Overview
Python Flask web application that wraps yt-dlp and ffmpeg for video downloading and processing. Features a modern, professional UI inspired by Final Cut Pro X.

### Completed Features
- [x] Core video download functionality with yt-dlp
- [x] Timestamp-based video cutting with ffmpeg (supports half-second precision)
- [x] Two-level caching system (video cache + cut cache)
- [x] Background processing with threading
- [x] Real-time progress tracking with progress bar
- [x] Past jobs history (3-day retention)
- [x] Error handling with user-friendly messages
- [x] Final Cut Pro X inspired dark theme (#1a1a1a background, #0a84ff accents)
- [x] Dynamic timestamp input fields
- [x] Clickable headers for navigation
- [x] Responsive design
- [x] Comprehensive documentation

### Design System
**Colors:**
- Background: `#1a1a1a`
- Containers: `#252525`
- Hero/Footer: `#0a0a0a`
- Borders: `#2a2a2a`, `#3a3a3a`, `#333`
- Accent: `#0a84ff`
- Text: `#ffffff`, `#e5e5e5`, `#8a8a8a`, `#666`

**Typography:**
- Font: `-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Helvetica Neue', sans-serif`
- Base size: `0.875rem`
- Border radius: `6px` (small), `8px` (containers)

**Transitions:**
- Standard: `0.2s ease`

### Development Guidelines
- Follow Flask best practices
- Use environment variables for configuration
- Maintain consistent styling across all pages
- Keep code modular and well-documented
- Test timestamp parsing for edge cases
- Ensure proper error handling and user feedback
- Follow conventional commit messages (feat:, fix:, style:, docs:, etc.)

### File Structure
- `app.py`: Main Flask application with all routes and business logic
- `templates/`: Jinja2 templates (index, progress, result, past_jobs)
- `downloads/`: Processed video files (auto-created)
- `cache/`: Original video cache (auto-created)
- `jobs.json`: Job metadata persistence
- `.env`: Environment configuration (not in git)

### Key Technical Details
- Background downloads use threading
- Progress updates via polling API endpoint
- Automatic cleanup of files older than 3 days
- Job tracking with UUID identifiers
- Half-second timestamp precision using float parsing
- Error messages stored as dict with status and message

### Future Considerations
- Authentication/authorization for production
- Rate limiting
- Production WSGI server (gunicorn)
- HTTPS/SSL configuration
- Monitoring and logging
- Disk space management

### Development Commands
```bash
# Run development server
python app.py

# Install dependencies
pip install -r requirements.txt

# Git workflow
git add .
git commit -m "type: description"
git push
```

### Important Notes
- Always test timestamp formats including half-seconds
- Verify clickable headers work on all pages
- Maintain consistent styling with FCP X theme
- Update documentation when adding features
- Work through checklist items systematically
- Keep communication concise and focused
- Follow development best practices