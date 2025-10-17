from flask import Flask, request, render_template, send_file, flash, redirect, url_for
import yt_dlp
import os
import subprocess
import uuid
import datetime
from dotenv import load_dotenv
import time
import shutil

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')  # Change this in production

DOWNLOAD_DIR = 'downloads'
CACHE_DIR = 'cache'
for d in [DOWNLOAD_DIR, CACHE_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

def cleanup_cache():
    """Remove cache files older than 3 days."""
    now = time.time()
    max_age = 3 * 24 * 3600  # 3 days in seconds
    for filename in os.listdir(CACHE_DIR):
        filepath = os.path.join(CACHE_DIR, filename)
        if os.path.isfile(filepath):
            if now - os.path.getmtime(filepath) > max_age:
                os.remove(filepath)

def get_template_vars():
    return {
        'company_short_name': os.getenv('COMPANY_SHORT_NAME', 'YourCompany'),
        'support_email': os.getenv('SUPPORT_EMAIL', 'support@yourcompany.com'),
        'location': os.getenv('LOCATION', 'Teaneck, NJ'),
        'current_year': datetime.datetime.now().year
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    cleanup_cache()  # Clean old cache files on each request
    
    if request.method == 'POST':
        url = request.form['url']
        timestamps = request.form.get('timestamps', '').strip()
        
        if not url:
            flash('Please provide a URL.')
            return redirect(url_for('index'))
        
        # Generate unique ID for this download
        download_id = str(uuid.uuid4())
        output_dir = os.path.join(DOWNLOAD_DIR, download_id)
        os.makedirs(output_dir)
        
        # Download options
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(CACHE_DIR, '%(id)s.%(ext)s'),  # Use video ID for cache
            'merge_output_format': 'mp4',
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)  # First, get info without downloading
                video_id = info['id']
                cache_path = os.path.join(CACHE_DIR, f"{video_id}.mp4")
                
                # Check if cached
                if os.path.exists(cache_path) and time.time() - os.path.getmtime(cache_path) < 3 * 24 * 3600:
                    # Use cached file
                    full_mp4 = cache_path
                else:
                    # Download to cache
                    ydl.download([url])
                    full_mp4 = cache_path  # Assuming merge creates this
                
                title = info.get('title', 'video').replace('/', '_').replace('\\', '_')
                current_time = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                
                # For full download
                if not timestamps:
                    full_video_name = f"{title}_{current_time}.mp4"
                    full_video_path = os.path.join(output_dir, full_video_name)
                    shutil.copy2(full_mp4, full_video_path)
                    return render_template('result.html', files=[full_video_path], download_id=download_id, **get_template_vars())
                
                # For snippets
                timestamp_list = [t.strip() for t in timestamps.split(',') if t.strip()]
                snippets = []
                for ts in timestamp_list:
                    start, end = ts.split('-') if '-' in ts else (ts, None)
                    snippet_name = f"{title}_{current_time}_{start.replace(':', '')}-{'end' if end is None else end.replace(':', '')}.mp4"
                    snippet_path = os.path.join(output_dir, snippet_name)
                    cut_video(full_mp4, snippet_path, start.strip(), end.strip() if end else None)
                    snippets.append(snippet_path)
                
                return render_template('result.html', files=snippets, download_id=download_id, **get_template_vars())
        except Exception as e:
            flash(f'Error: {str(e)}')
            return redirect(url_for('index'))
    
    return render_template('index.html', **get_template_vars())

@app.route('/download/<download_id>/<filename>')
def download(download_id, filename):
    file_path = os.path.join(DOWNLOAD_DIR, download_id, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash('File not found.')
        return redirect(url_for('index'))

def cut_video(input_path, output_path, start, end=None):
    cmd = ['ffmpeg', '-i', input_path, '-ss', start]
    if end:
        duration = calculate_duration(start, end)
        cmd.extend(['-t', duration])
    cmd.extend(['-c', 'copy', output_path])
    subprocess.run(cmd, check=True)

def calculate_duration(start, end):
    # Simple duration calculation, assuming HH:MM:SS format
    def to_seconds(time_str):
        parts = time_str.split(':')
        if len(parts) == 3:
            h, m, s = map(int, parts)
            return h*3600 + m*60 + s
        elif len(parts) == 2:
            m, s = map(int, parts)
            return m*60 + s
        else:
            return int(parts[0])
    
    start_sec = to_seconds(start)
    end_sec = to_seconds(end)
    return str(end_sec - start_sec)

if __name__ == '__main__':
    app.run(debug=True)