import json
import os
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime

import yt_dlp
from dotenv import load_dotenv
from flask import Flask, request, render_template, send_file, flash, redirect, url_for
from flask_httpauth import HTTPBasicAuth

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')  # Change this in production

# Authentication setup
auth = HTTPBasicAuth()

# Get authentication credentials from environment
AUTH_USERNAME = os.getenv('AUTH_USERNAME', 'admin')
AUTH_PASSWORD = os.getenv('AUTH_PASSWORD', 'password')

@auth.verify_password
def verify_password(username, password):
    """Verify username and password for basic authentication."""
    if username == AUTH_USERNAME and password == AUTH_PASSWORD:
        return username
    return None

DOWNLOAD_DIR = 'downloads'
CACHE_DIR = 'cache'
JOBS_FILE = 'jobs.json'
for d in [DOWNLOAD_DIR, CACHE_DIR]:
    if not os.path.exists(d):
        os.makedirs(d)

# Global progress tracking
progress_data = {}

def load_jobs():
    """Load jobs from JSON file."""
    if os.path.exists(JOBS_FILE):
        try:
            with open(JOBS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_jobs(jobs):
    """Save jobs to JSON file."""
    with open(JOBS_FILE, 'w') as f:
        json.dump(jobs, f, indent=2, default=str)

def cleanup_old_jobs():
    """Remove jobs older than 3 days and their associated files."""
    jobs = load_jobs()
    current_time = time.time()
    max_age = 3 * 24 * 3600  # 3 days in seconds
    
    jobs_to_remove = []
    for job_id, job in jobs.items():
        # Check if job has created_timestamp (older jobs may not)
        if 'created_timestamp' in job and current_time - job['created_timestamp'] > max_age:
            jobs_to_remove.append(job_id)
            # Remove download directory
            download_path = os.path.join(DOWNLOAD_DIR, job_id)
            if os.path.exists(download_path):
                shutil.rmtree(download_path)
    
    for job_id in jobs_to_remove:
        del jobs[job_id]
    
    if jobs_to_remove:
        save_jobs(jobs)

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
        
        # Store job info for later use
        job_info = {'url': url, 'timestamps': timestamps}
        
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
            job_info['title'] = info.get('title', 'Video').replace('/', '_').replace('\\', '_')
            
            # Check if cached
            if os.path.exists(cache_path) and time.time() - os.path.getmtime(cache_path) < 3 * 24 * 3600:
                full_mp4 = cache_path
                progress_data[download_id] = 50  # Skip download step
            else:
                # Download to cache
                ydl.download([url])
                full_mp4 = cache_path
                progress_data[download_id] = 50
            
            # Store job info for result page with timestamp
            job_info['created_timestamp'] = time.time()
            job_info['created_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            jobs = load_jobs()
            jobs[download_id] = job_info
            save_jobs(jobs)
            
            title = job_info['title']
            current_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            
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
        error_message = str(e)
        progress_data[download_id] = {'status': 'error', 'message': error_message}
        print(f"Download error: {error_message}")

def start_download(url, timestamps):
    """Start a download and return the download_id."""
    download_id = str(uuid.uuid4())
    
    # Start background download
    thread = threading.Thread(target=download_video_async, args=(download_id, url, timestamps))
    thread.daemon = True
    thread.start()
    
    return download_id

def cleanup_cache():
    """Remove cache files older than 3 days."""
    now = time.time()
    max_age = 3 * 24 * 3600  # 3 days in seconds
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

@app.route('/progress/<download_id>')
@auth.login_required
def progress_page(download_id):
    return render_template('progress.html', download_id=download_id, **get_template_vars())

@app.route('/api/progress/<download_id>')
@auth.login_required
def get_progress_api(download_id):
    progress = progress_data.get(download_id, 0)
    
    # Check if it's an error dictionary
    if isinstance(progress, dict) and progress.get('status') == 'error':
        return {'progress': 0, 'status': 'error', 'message': progress.get('message', 'Unknown error occurred')}
    
    # Legacy error handling (for -1 value)
    if progress == -1:
        return {'progress': 0, 'status': 'error', 'message': 'Download failed'}
    elif progress >= 100:
        return {'progress': 100, 'status': 'complete'}
    else:
        return {'progress': progress, 'status': 'processing'}

@app.route('/past-jobs')
@auth.login_required
def past_jobs():
    cleanup_old_jobs()  # Clean expired jobs
    jobs = load_jobs()
    
    # Convert to list and sort by creation date (newest first)
    jobs_list = []
    for job_id, job in jobs.items():
        job['id'] = job_id
        jobs_list.append(job)
    
    jobs_list.sort(key=lambda x: x.get('created_timestamp', 0), reverse=True)
    
    return render_template('past_jobs.html', jobs=jobs_list, **get_template_vars())

@app.route('/redownload/<job_id>')
@auth.login_required
def redownload(job_id):
    jobs = load_jobs()
    if job_id not in jobs:
        flash('Job not found.')
        return redirect(url_for('past_jobs'))
    
    job = jobs[job_id]
    
    # Start a new download with the same parameters
    download_id = start_download(job['url'], job.get('timestamps', ''))
    
    # Redirect to progress page
    return redirect(url_for('progress_page', download_id=download_id))

@app.route('/result/<download_id>')
@auth.login_required
def result(download_id):
    output_dir = os.path.join(DOWNLOAD_DIR, download_id)
    if not os.path.exists(output_dir):
        flash('Download not found.')
        return redirect(url_for('index'))
    
    files = []
    total_size = 0
    for filename in os.listdir(output_dir):
        filepath = os.path.join(output_dir, filename)
        if os.path.isfile(filepath):
            file_size = os.path.getsize(filepath)
            files.append({
                'name': filename,
                'path': filepath,
                'size': file_size,
                'size_mb': round(file_size / (1024 * 1024), 2)
            })
            total_size += file_size
    
    if not files:
        flash('No files found for this download.')
        return redirect(url_for('index'))
    
    # Get job metadata
    jobs = load_jobs()
    job_info = jobs.get(download_id, {})
    
    # Save/update job metadata with file info (preserve existing data)
    if 'created_timestamp' not in job_info:
        job_info['created_timestamp'] = time.time()
    if 'created_date' not in job_info:
        job_info['created_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    job_info.update({
        'file_count': len(files),
        'total_size_mb': round(total_size / (1024 * 1024), 2),
    })
    jobs[download_id] = job_info
    save_jobs(jobs)
    
    return render_template('result.html', files=files, download_id=download_id, **get_template_vars())

def get_template_vars():
    return {
        'company_name': os.getenv('COMPANY_NAME', 'Your Company Name'),
        'company_short_name': os.getenv('COMPANY_SHORT_NAME', 'YourCompany'),
        'support_email': os.getenv('SUPPORT_EMAIL', 'support@yourcompany.com'),
        'location': os.getenv('LOCATION', 'Teaneck, NJ'),
        'current_year': datetime.now().year
    }

@app.route('/', methods=['GET', 'POST'])
@auth.login_required
def index():
    cleanup_cache()  # Clean old cache files on each request
    cleanup_old_jobs()  # Clean old jobs on each request
    
    if request.method == 'POST':
        url = request.form['url']
        timestamps = request.form.get('timestamps', '').strip()
        
        if not url:
            flash('Please provide a URL.')
            return redirect(url_for('index'))
        
        # Start download and get ID
        download_id = start_download(url, timestamps)
        
        # Redirect to progress page
        return redirect(url_for('progress_page', download_id=download_id))
    
    return render_template('index.html', **get_template_vars())

@app.route('/download/<download_id>/<filename>')
@auth.login_required
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
    # Duration calculation supporting HH:MM:SS.D format (with optional decimal seconds)
    def to_seconds(time_str):
        parts = time_str.split(':')
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), float(parts[2])
            return h*3600 + m*60 + s
        elif len(parts) == 2:
            m, s = int(parts[0]), float(parts[1])
            return m*60 + s
        else:
            return float(parts[0])
    
    start_sec = to_seconds(start)
    end_sec = to_seconds(end)
    return str(end_sec - start_sec)

if __name__ == '__main__':
    app.run(debug=True)