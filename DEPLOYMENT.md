# Speech Processing Service - GPU Server Deployment Guide

## Overview
Deploy the comprehensive speech processing service to a GPU server at 10.1.10.20 with faster-whisper and Ollama, accessible via HAProxy at speech.lcs.ai.

## Server Requirements
- GPU server at 10.1.10.20
- faster-whisper installed and running
- Ollama installed
- Python 3.11+ with pip
- PostgreSQL database
- HAProxy for SSL termination and routing

## Deployment Steps

### 1. Server Setup on 10.1.10.20

```bash
# Clone the repository
git clone <your-repo-url> /opt/speech-processing
cd /opt/speech-processing

# Install Python dependencies
pip install -r requirements.txt

# Or install individual packages
pip install flask flask-sqlalchemy psycopg2-binary gtts pyttsx3 moviepy opencv-python yt-dlp pypdf2 python-docx reportlab markdown trafilatura requests gunicorn
```

### 2. Database Configuration

```bash
# Install PostgreSQL if not already installed
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE speech_processing;
CREATE USER speech_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE speech_processing TO speech_user;
\q
```

### 3. Environment Variables

Create `/opt/speech-processing/.env`:
```bash
DATABASE_URL=postgresql://speech_user:your_secure_password@localhost/speech_processing
SESSION_SECRET=your_secure_session_key_here
FLASK_ENV=production
```

### 4. Faster-Whisper Service Setup

Ensure faster-whisper is running on the GPU server at port 80:
```bash
# Example faster-whisper service (adjust based on your setup)
# The service should be accessible at http://10.1.10.20/v1/audio/transcriptions
```

### 5. Systemd Service Configuration

Create `/etc/systemd/system/speech-processing.service`:
```ini
[Unit]
Description=Speech Processing Service
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/opt/speech-processing
Environment=PATH=/usr/local/bin:/usr/bin:/bin
EnvironmentFile=/opt/speech-processing/.env
ExecStart=/usr/local/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 300 --keep-alive 2 --max-requests 1000 --preload main:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### 6. Start the Service

```bash
# Set permissions
sudo chown -R www-data:www-data /opt/speech-processing
sudo chmod +x /opt/speech-processing/main.py

# Enable and start service
sudo systemctl enable speech-processing
sudo systemctl start speech-processing
sudo systemctl status speech-processing
```

### 7. HAProxy Configuration

Add to your HAProxy configuration (typically `/etc/haproxy/haproxy.cfg`):

```haproxy
frontend speech_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/lcs.ai.pem
    redirect scheme https if !{ ssl_fc }
    
    # Route speech.lcs.ai to the speech processing service
    acl is_speech_subdomain hdr(host) -i speech.lcs.ai
    use_backend speech_backend if is_speech_subdomain

backend speech_backend
    balance roundrobin
    option httpchk GET /health
    server speech1 10.1.10.20:5000 check inter 5s rise 2 fall 3
    
    # Set proper headers for the application
    http-request set-header X-Forwarded-Proto https if { ssl_fc }
    http-request set-header X-Forwarded-Proto http if !{ ssl_fc }
```

### 8. SSL Certificate Setup

Ensure your wildcard certificate for *.lcs.ai is properly configured:
```bash
# Verify certificate includes speech.lcs.ai
openssl x509 -in /etc/ssl/certs/lcs.ai.pem -text -noout | grep -A1 "Subject Alternative Name"
```

### 9. Firewall Configuration

```bash
# Allow necessary ports
sudo ufw allow 5000/tcp  # Application port
sudo ufw allow 80/tcp    # Faster-whisper service
sudo ufw allow 443/tcp   # If running HTTPS directly
```

### 10. Health Check and Testing

```bash
# Test application locally
curl http://10.1.10.20:5000/health

# Test through HAProxy
curl https://speech.lcs.ai/health

# Test faster-whisper connection
curl http://10.1.10.20/v1/audio/transcriptions
```

## Monitoring and Logs

```bash
# Application logs
sudo journalctl -u speech-processing -f

# HAProxy logs
sudo tail -f /var/log/haproxy.log

# Check service status
sudo systemctl status speech-processing
```

## Backup Configuration

### Database Backup
```bash
# Create backup script /opt/speech-processing/backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump speech_processing > /opt/backups/speech_processing_$DATE.sql
find /opt/backups -name "speech_processing_*.sql" -mtime +7 -delete
```

### File Uploads Cleanup
```bash
# Clean temporary files older than 1 day
find /tmp -name "*.mp3" -mtime +1 -delete
find /tmp -name "*.wav" -mtime +1 -delete
find /tmp -name "tts_*" -mtime +1 -delete
```

## Performance Optimization

### Gunicorn Configuration
- Workers: 4 (adjust based on CPU cores)
- Timeout: 300 seconds (for large file processing)
- Max requests: 1000 (restart workers after 1000 requests)

### GPU Utilization
- Ensure faster-whisper uses GPU acceleration
- Monitor GPU memory usage during processing
- Consider batch processing for multiple files

## Troubleshooting

### Common Issues
1. **Connection to faster-whisper fails**: Check if service is running on port 80
2. **Database connection errors**: Verify DATABASE_URL and PostgreSQL service
3. **SSL certificate issues**: Ensure wildcard cert covers speech.lcs.ai
4. **File processing timeouts**: Increase gunicorn timeout for large files

### Debug Commands
```bash
# Check faster-whisper service
curl -X POST http://10.1.10.20/v1/audio/transcriptions -F "file=@test.wav"

# Test database connection
python -c "import psycopg2; conn=psycopg2.connect('postgresql://speech_user:password@localhost/speech_processing'); print('DB OK')"

# Check disk space for uploads
df -h /tmp
```

## Security Considerations

1. **Database security**: Use strong passwords and limit network access
2. **File uploads**: Implement size limits and virus scanning
3. **SSL/TLS**: Ensure proper certificate configuration
4. **Access control**: Consider implementing authentication for sensitive operations
5. **Input validation**: Validate all user inputs and file types

## Maintenance

### Regular Tasks
- Monitor disk usage in /tmp directory
- Check application logs for errors
- Update dependencies monthly
- Backup database weekly
- Monitor GPU usage and performance

### Updates
```bash
# Update application
cd /opt/speech-processing
git pull
sudo systemctl restart speech-processing
```