# YT-DLP Self-Hosted Video Downloader - Production Deployment Guide

## Overview
This guide covers deploying the YT-DLP video downloader to an Amazon Linux 2 server with Caddy as a reverse proxy.

## Prerequisites
- Amazon Linux 2 EC2 instance
- Caddy web server installed and running
- Domain name (optional but recommended)
- SSL certificate (Caddy will handle this automatically)

## 1. Server Preparation

### Update System Packages
```bash
sudo yum update -y
```

### Install Required Dependencies
```bash
# Install Python 3.9+ (Amazon Linux 2 comes with Python 3.7, but let's get a newer version)
sudo amazon-linux-extras install python3.9 -y

# Install ffmpeg (required for video processing)
sudo yum install -y ffmpeg ffmpeg-devel

# Install development tools
sudo yum groupinstall -y "Development Tools"

# Install pip
curl -O https://bootstrap.pypa.io/get-pip.py
python3.9 get-pip.py --user
export PATH="$HOME/.locapytl/bin:$PATH"
```

### Create Application User
```bash
sudo useradd -m -s /bin/bash ytdlp
sudo usermod -aG wheel ytdlp
```

## 2. Application Deployment

### Clone and Setup Application
```bash
# Switch to application user
sudo su - ytdlp

# Clone repository
git clone https://github.com/jacobrosenfeld/ytdlp-self-hosted.git
cd ytdlp-self-hosted

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn  # Production WSGI server
```

### Configure Environment Variables
```bash
# Create .env file
cat > .env << EOF
# Flask Configuration
SECRET_KEY=your-super-secure-random-secret-key-here
FLASK_ENV=production

# Authentication (CHANGE THESE!)
AUTH_USERNAME=your_admin_username
AUTH_PASSWORD=your_strong_password_here

# Application Settings
COMPANY_NAME=Your Company Name
LOCATION=Your Location
CURRENT_YEAR=2025

# Optional: Custom domain/port (if not using default)
# HOST=0.0.0.0
# PORT=8000
EOF

# Secure the .env file
chmod 600 .env
```

### Create Required Directories
```bash
mkdir -p downloads cache jobs
chmod 755 downloads cache jobs
```

### Test Application Locally
```bash
# Still as ytdlp user
source venv/bin/activate
python app.py
# Should start on http://127.0.0.1:5000
# Test login functionality, then Ctrl+C to stop
```

## 3. Production Server Setup

### Create Gunicorn Configuration
```bash
# Create gunicorn config file
cat > gunicorn.conf.py << EOF
# Gunicorn configuration for production
bind = "127.0.0.1:8000"
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 300
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
user = "ytdlp"
group = "ytdlp"
tmp_upload_dir = None
EOF
```

### Create Systemd Service
```bash
# Exit back to root user
exit

# Create systemd service file
sudo tee /etc/systemd/system/ytdlp.service > /dev/null << EOF
[Unit]
Description=YT-DLP Video Downloader
After=network.target

[Service]
User=ytdlp
Group=ytdlp
WorkingDirectory=/home/ytdlp/ytdlp-self-hosted
Environment="PATH=/home/ytdlp/ytdlp-self-hosted/venv/bin"
ExecStart=/home/ytdlp/ytdlp-self-hosted/venv/bin/gunicorn --config gunicorn.conf.py app:app
Restart=always
RestartSec=5

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectHome=yes
ReadWritePaths=/home/ytdlp/ytdlp-self-hosted

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable ytdlp
sudo systemctl start ytdlp

# Check status
sudo systemctl status ytdlp
```

## 4. Caddy Reverse Proxy Configuration

### Configure Caddy
```bash
# Edit Caddyfile (assuming Caddy is installed)
sudo vi /etc/caddy/Caddyfile

# Add this configuration (replace yourdomain.com with your actual domain)
yourdomain.com {
    # Enable automatic HTTPS
    tls your-email@example.com

    # Reverse proxy to Gunicorn
    reverse_proxy 127.0.0.1:8000

    # Security headers
    header {
        # Security headers
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"

        # Remove server header
        -Server
    }

    # Rate limiting (optional)
    rate_limit {
        zone static {
            key {remote_host}
            window 1m
            events 100
        }
    }

    # Logging
    log {
        output file /var/log/caddy/ytdlp.log {
            roll_size 10mb
            roll_keep 5
        }
        format json
    }
}
```

### Alternative: IP-based Access (if no domain)
```bash
# For IP-based access, add to Caddyfile:
your-server-ip {
    reverse_proxy 127.0.0.1:8000

    # Same security headers as above...
}
```

### Reload Caddy
```bash
sudo systemctl reload caddy
```

## 5. Security Hardening

### File Permissions
```bash
# As root user
sudo chown -R ytdlp:ytdlp /home/ytdlp/ytdlp-self-hosted
sudo chmod -R 755 /home/ytdlp/ytdlp-self-hosted
sudo chmod 600 /home/ytdlp/ytdlp-self-hosted/.env
```

### Firewall Configuration
```bash
# Allow SSH and HTTP/HTTPS
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload

# Check firewall status
sudo firewall-cmd --list-all
```

### SELinux (if enabled)
```bash
# Check SELinux status
sestatus

# If enforcing, you may need to adjust policies for the application
# This can be complex - consider disabling SELinux for simplicity on development servers
# sudo setenforce 0
# sudo sed -i 's/SELINUX=enforcing/SELINUX=disabled/g' /etc/selinux/config
```

## 6. Monitoring and Maintenance

### Log Monitoring
```bash
# View application logs
sudo journalctl -u ytdlp -f

# View Caddy logs
sudo tail -f /var/log/caddy/ytdlp.log
```

### Backup Strategy
```bash
# Create backup script
sudo tee /home/ytdlp/backup.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/ytdlp/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup application data
tar -czf $BACKUP_DIR/app_backup_$DATE.tar.gz \
    -C /home/ytdlp/ytdlp-self-hosted \
    downloads/ cache/ jobs/ jobs.json

# Keep only last 7 backups
cd $BACKUP_DIR
ls -t app_backup_*.tar.gz | tail -n +8 | xargs -r rm

echo "Backup completed: $BACKUP_DIR/app_backup_$DATE.tar.gz"
EOF

sudo chmod +x /home/ytdlp/backup.sh
sudo chown ytdlp:ytdlp /home/ytdlp/backup.sh

# Add to crontab for daily backups at 2 AM
sudo crontab -u ytdlp -l | { cat; echo "0 2 * * * /home/ytdlp/backup.sh"; } | sudo crontab -u ytdlp -
```

### Disk Space Monitoring
```bash
# Check disk usage
df -h

# Monitor application disk usage
sudo du -sh /home/ytdlp/ytdlp-self-hosted/downloads/
sudo du -sh /home/ytdlp/ytdlp-self-hosted/cache/
```

## 7. Troubleshooting

### Common Issues

**Application won't start:**
```bash
# Check systemd status
sudo systemctl status ytdlp

# Check logs
sudo journalctl -u ytdlp -n 50

# Test manually
sudo su - ytdlp
cd ytdlp-self-hosted
source venv/bin/activate
gunicorn --config gunicorn.conf.py app:app
```

**Caddy reverse proxy issues:**
```bash
# Check Caddy status
sudo systemctl status caddy

# Validate Caddyfile
sudo caddy validate

# Check Caddy logs
sudo journalctl -u caddy -n 50
```

**Permission issues:**
```bash
# Fix ownership
sudo chown -R ytdlp:ytdlp /home/ytdlp/ytdlp-self-hosted

# Check file permissions
ls -la /home/ytdlp/ytdlp-self-hosted/
```

### Performance Tuning

**Increase Gunicorn workers (for high traffic):**
```bash
# Edit gunicorn.conf.py
workers = 4  # Adjust based on CPU cores
```

**Memory management:**
```bash
# Monitor memory usage
ps aux --sort=-%mem | head -10

# If memory issues, reduce workers or add swap
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 8. Update Process

### Application Updates
```bash
# Stop service
sudo systemctl stop ytdlp

# Update code
sudo su - ytdlp
cd ytdlp-self-hosted
git pull origin main

# Update dependencies (if requirements.txt changed)
source venv/bin/activate
pip install -r requirements.txt

# Test application
python app.py  # Quick test

# Restart service
exit
sudo systemctl start ytdlp
```

## 9. Final Verification

### Test the deployment:
1. Visit your domain/IP in a web browser
2. Verify login page loads
3. Test login functionality
4. Try downloading a small video
5. Check that files are created in the downloads directory

### Health checks:
```bash
# Check all services are running
sudo systemctl status ytdlp caddy

# Test application health
curl -I https://yourdomain.com

# Check logs for errors
sudo journalctl -u ytdlp --since "1 hour ago" | grep -i error
```

## Security Checklist
- [ ] Changed default AUTH_USERNAME and AUTH_PASSWORD
- [ ] Set strong SECRET_KEY
- [ ] Configured HTTPS with Caddy
- [ ] Restricted file permissions
- [ ] Enabled firewall
- [ ] Set up log monitoring
- [ ] Configured backups
- [ ] Regular security updates: `sudo yum update -y`

## Support
If you encounter issues:
1. Check the logs: `sudo journalctl -u ytdlp -f`
2. Verify Caddy configuration: `sudo caddy validate`
3. Test locally: `sudo su - ytdlp && cd ytdlp-self-hosted && source venv/bin/activate && python app.py`
4. Check file permissions and ownership

This deployment provides a production-ready setup with automatic HTTPS, process management, and security hardening.</content>
<parameter name="filePath">/Users/jacobrosenfeld/Documents/GitHub/ytdlp-self-hosted/PRODUCTION_DEPLOYMENT.md