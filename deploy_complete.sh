#!/bin/bash

# Complete Speech Processing Service Deployment Script
# Deploy to GPU server at 10.1.10.20 and configure HAProxy at 10.1.50.100

set -e

GPU_SERVER="10.1.10.20"
HAPROXY_SERVER="10.1.50.100"
APP_DIR="/opt/speech-processing"
SERVICE_NAME="speech-processing"

echo "=== Complete Speech Processing Service Deployment ==="
echo "GPU Server: $GPU_SERVER"
echo "HAProxy Server: $HAPROXY_SERVER"
echo "Application directory: $APP_DIR"
echo ""

# Function to run commands on GPU server
run_on_gpu() {
    ssh root@$GPU_SERVER "$1"
}

# Function to run commands on HAProxy server
run_on_haproxy() {
    ssh root@$HAPROXY_SERVER "$1"
}

# Function to copy files to GPU server
copy_to_gpu() {
    rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' ./ root@$GPU_SERVER:$APP_DIR/
}

echo "1. Copying application files to GPU server..."
copy_to_gpu

echo "2. Installing Python dependencies on GPU server..."
run_on_gpu "cd $APP_DIR && pip3 install flask flask-sqlalchemy psycopg2-binary gtts pyttsx3 moviepy opencv-python yt-dlp pypdf2 python-docx reportlab markdown trafilatura requests gunicorn email-validator werkzeug"

echo "2a. Setting up faster-whisper dependencies..."
run_on_gpu "cd /mnt/bigdisk/projects/faster-whisper-gpu && pip3 install faster-whisper yt-dlp"

echo "3. Setting up environment file on GPU server..."
run_on_gpu "cat > $APP_DIR/.env << 'EOF'
DATABASE_URL=postgresql://speech_user:speech_password@localhost/speech_processing
SESSION_SECRET=$(openssl rand -hex 32)
FLASK_ENV=production
EOF"

echo "4. Setting up PostgreSQL database on GPU server..."
run_on_gpu "sudo -u postgres psql -c \"SELECT 1 FROM pg_database WHERE datname = 'speech_processing';\" | grep -q 1 || sudo -u postgres createdb speech_processing"
run_on_gpu "sudo -u postgres psql -c \"SELECT 1 FROM pg_roles WHERE rolname = 'speech_user';\" | grep -q 1 || sudo -u postgres psql -c \"CREATE USER speech_user WITH PASSWORD 'speech_password';\""
run_on_gpu "sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE speech_processing TO speech_user;\""

echo "5. Creating systemd service on GPU server..."
run_on_gpu "cat > /etc/systemd/system/$SERVICE_NAME.service << 'EOF'
[Unit]
Description=Speech Processing Service
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment=PATH=/usr/local/bin:/usr/bin:/bin
EnvironmentFile=$APP_DIR/.env
ExecStart=/usr/local/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 300 --keep-alive 2 --max-requests 1000 --preload main:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF"

echo "6. Setting permissions on GPU server..."
run_on_gpu "chown -R www-data:www-data $APP_DIR"
run_on_gpu "chmod +x $APP_DIR/main.py"

echo "7. Starting speech processing service on GPU server..."
run_on_gpu "systemctl daemon-reload"
run_on_gpu "systemctl enable $SERVICE_NAME"
run_on_gpu "systemctl restart $SERVICE_NAME"

echo "8. Checking service status on GPU server..."
run_on_gpu "systemctl status $SERVICE_NAME --no-pager"

echo "8a. Testing faster-whisper script availability..."
if run_on_gpu "test -f /mnt/bigdisk/projects/faster-whisper-gpu/smart_transcribe.py"; then
    echo "✓ Faster-whisper script found at /mnt/bigdisk/projects/faster-whisper-gpu/smart_transcribe.py"
else
    echo "✗ Faster-whisper script not found"
fi

echo "9. Testing application health on GPU server..."
sleep 3
if run_on_gpu "curl -f http://localhost:5000/health"; then
    echo "✓ Application is running successfully on GPU server!"
else
    echo "✗ Application health check failed on GPU server"
    echo "Checking application logs:"
    run_on_gpu "journalctl -u $SERVICE_NAME --no-pager -n 20"
    exit 1
fi

echo "10. Backing up HAProxy configuration..."
run_on_haproxy "cp /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.backup.$(date +%Y%m%d_%H%M%S)"

echo "11. Updating HAProxy configuration..."
run_on_haproxy "cat > /tmp/speech_config.txt << 'EOF'
    acl is_speech hdr(host) -i speech.lcs.ai
EOF"

run_on_haproxy "cat > /tmp/speech_backend.txt << 'EOF'

backend speech_backend
    option http-server-close
    option forwardfor
    option httpchk GET /health
    http-request set-header X-Forwarded-Proto https
    timeout server 300000ms
    server speech $GPU_SERVER:5000 check inter 10s rise 2 fall 3
EOF"

# Add the ACL line after the existing ACLs
run_on_haproxy "sed -i '/acl is_ollama/a\    acl is_speech hdr(host) -i speech.lcs.ai' /etc/haproxy/haproxy.cfg"

# Add the use_backend line after the existing use_backend lines
run_on_haproxy "sed -i '/use_backend ollama_backend if is_ollama/a\    use_backend speech_backend if is_speech' /etc/haproxy/haproxy.cfg"

# Add the backend configuration at the end of the file
run_on_haproxy "cat /tmp/speech_backend.txt >> /etc/haproxy/haproxy.cfg"

echo "12. Validating HAProxy configuration..."
if run_on_haproxy "haproxy -c -f /etc/haproxy/haproxy.cfg"; then
    echo "✓ HAProxy configuration is valid"
else
    echo "✗ HAProxy configuration is invalid, restoring backup"
    run_on_haproxy "cp /etc/haproxy/haproxy.cfg.backup.* /etc/haproxy/haproxy.cfg"
    exit 1
fi

echo "13. Reloading HAProxy..."
run_on_haproxy "systemctl reload haproxy"

echo "14. Testing HAProxy routing..."
sleep 3
if run_on_haproxy "curl -f -H 'Host: speech.lcs.ai' http://localhost/health"; then
    echo "✓ HAProxy routing is working!"
else
    echo "⚠ HAProxy routing test failed, but service may still work via HTTPS"
fi

echo "15. Final connectivity test..."
echo "Testing external access to https://speech.lcs.ai/health"

echo ""
echo "=== Deployment Complete ==="
echo "Application URL: https://speech.lcs.ai"
echo "Health check: https://speech.lcs.ai/health"
echo "HAProxy Stats: http://$HAPROXY_SERVER:8404/stats (admin:apgar-66)"
echo ""
echo "Services:"
echo "- Speech Processing: $GPU_SERVER:5000"
echo "- faster-whisper: $GPU_SERVER (port 80)"
echo "- Ollama: $GPU_SERVER:11434"
echo ""
echo "Monitor logs:"
echo "- Application: ssh root@$GPU_SERVER journalctl -u $SERVICE_NAME -f"
echo "- HAProxy: ssh root@$HAPROXY_SERVER tail -f /var/log/haproxy.log"
echo ""
echo "Next steps:"
echo "1. Verify faster-whisper service is running on $GPU_SERVER"
echo "2. Test file upload and transcription functionality"
echo "3. Monitor GPU usage during processing"