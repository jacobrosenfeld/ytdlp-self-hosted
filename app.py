from flask import Flask, request, render_template, send_file, flash, redirect, url_for
import yt_dlp
import os
import subprocess
import uuid
import datetime
from dotenv import load_dotenv
import time
import shutil
import threading

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')  # Change this in production

DOWNLOAD_DIR = 'downloads'
CACHE_DIR = 'cache'
for d in [DOWNLOAD_DIR, CACHE_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

# Global progress tracking
progress_data = {}

def cleanup_cache():
    """Remove cache files older than 3 days."""
    now = time.time()
    max_age = 3 * 24 * 3600  # 3 days in seconds
    
    # Clean main cache files
    for filename in os.listdir(CACHE_DIR):
        filepath = os.path.join(CACHE_DIR, filename)
        if os.path.isfile(filepath):
            if now - os.path.getmtime(filepath) > max_age:
                os.remove(filepath)
        elif os.path.isdir(filepath) and filename == 'cuts':
            # Clean cuts cache directories
            cuts_dir = filepath
            for cut_dir in os.listdir(cuts_dir):
                cut_path = os.path.join(cuts_dir, cut_dir)
                if os.path.isdir(cut_path) and now - os.path.getmtime(cut_path) > max_age:
                    shutil.rmtree(cut_path)

def download_video_async(download_id, url, timestamps):
    """Background function to download and process video."""
    try:
        progress_data[download_id] = 0
        
        output_dir = os.path.join(DOWNLOAD_DIR, download_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Download options with progress hook
        def progress_hook(d):
            if d['status'] == 'downloading':
                if 'total_bytes' in d and d['total_bytes'] > 0:
                    progress = int((d['downloaded_bytes'] / d['total_bytes']) * 100)
                    progress_data[download_id] = progress
            elif d['status'] == 'finished':
                progress_data[download_id] = 100
        
        ydl_opts = {
            'format': 'bestvideo+bestaudio/best',
            'outtmpl': os.path.join(CACHE_DIR, '%(id)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'progress_hooks': [progress_hook],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_id = info['id']
            cache_path = os.path.join(CACHE_DIR, f"{video_id}.mp4")
            
            # Check if cached
            if os.path.exists(cache_path) and time.time() - os.path.getmtime(cache_path) < 3 * 24 * 3600:
                full_mp4 = cache_path
                progress_data[download_id] = 50  # Skip download step
            else:
                # Download to cache
                ydl.download([url])
                full_mp4 = cache_path
                progress_data[download_id] = 50
            
            title = info.get('title', 'video').replace('/', '_').replace('\\', '_')
            current_time = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # For full download
            if not timestamps:
                full_video_name = f"{title}_{current_time}.mp4"
                full_video_path = os.path.join(output_dir, full_video_name)
                shutil.copy2(full_mp4, full_video_path)
                progress_data[download_id] = 100
                return
            
            # For snippets - check if already cached
            timestamp_list = [t.strip() for t in timestamps.split(',') if t.strip()]
            cache_key = f"{video_id}_{'_'.join(timestamp_list)}"
            cache_dir = os.path.join(CACHE_DIR, 'cuts', cache_key)
            
            # Check if cuts are already cached
            if os.path.exists(cache_dir) and time.time() - os.path.getmtime(cache_dir) < 3 * 24 * 3600:
                # Copy cached cuts to output directory
                for filename in os.listdir(cache_dir):
                    if filename.endswith('.mp4'):
                        src_path = os.path.join(cache_dir, filename)
                        dst_path = os.path.join(output_dir, filename)
                        shutil.copy2(src_path, dst_path)
                progress_data[download_id] = 100
                return
            
            # Create cache directory for cuts
            os.makedirs(cache_dir, exist_ok=True)
            
            # Process snippets
            snippets = []
            total_snippets = len(timestamp_list)
            
            for i, ts in enumerate(timestamp_list):
                start, end = ts.split('-') if '-' in ts else (ts, None)
                snippet_name = f"{title}_{current_time}_{start.replace(':', '')}-{'end' if end is None else end.replace(':', '')}.mp4"
                snippet_path = os.path.join(output_dir, snippet_name)
                cache_snippet_path = os.path.join(cache_dir, snippet_name)
                
                # Cut video and save to both output and cache
                cut_video(full_mp4, snippet_path, start.strip(), end.strip() if end else None)
                shutil.copy2(snippet_path, cache_snippet_path)
                snippets.append(snippet_path)
                
                # Update progress for cutting
                progress = 50 + int(((i + 1) / total_snippets) * 50)
                progress_data[download_id] = progress
            
            progress_data[download_id] = 100
            
    except Exception as e:
        progress_data[download_id] = -1  # Error state
        print(f"Download error: {e}")
    """Remove cache files older than 3 days."""
    now = time.time()
    max_age = 3 * 24 * 3600  # 3 days in seconds
    for filename in os.listdir(CACHE_DIR):
        filepath = os.path.join(CACHE_DIR, filename)
        if os.path.isfile(filepath):
            if now - os.path.getmtime(filepath) > max_age:
                os.remove(filepath)

@app.route('/progress/<download_id>')
def progress_page(download_id):
    return render_template('progress.html', download_id=download_id, **get_template_vars())

@app.route('/api/progress/<download_id>')
def get_progress_api(download_id):
    progress = progress_data.get(download_id, 0)
    if progress == -1:
        return {'progress': 0, 'status': 'error', 'message': 'Download failed'}
    elif progress >= 100:
        return {'progress': 100, 'status': 'complete'}
    else:
        return {'progress': progress, 'status': 'processing'}

@app.route('/result/<download_id>')
def result(download_id):
    output_dir = os.path.join(DOWNLOAD_DIR, download_id)
    if not os.path.exists(output_dir):
        flash('Download not found.')
        return redirect(url_for('index'))
    
    files = []
    for filename in os.listdir(output_dir):
        filepath = os.path.join(output_dir, filename)
        if os.path.isfile(filepath):
            files.append(filepath)
    
    if not files:
        flash('No files found for this download.')
        return redirect(url_for('index'))
    
    return render_template('result.html', files=files, download_id=download_id, **get_template_vars())

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
        
        # Start background download
        thread = threading.Thread(target=download_video_async, args=(download_id, url, timestamps))
        thread.daemon = True
        thread.start()
        
        # Redirect to progress page
        return redirect(url_for('progress_page', download_id=download_id))
    
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