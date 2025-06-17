#!/bin/bash

# Speech Processing Service Deployment Script
# Deploy to GPU server at 10.1.10.20

set -e

SERVER_IP="10.1.10.20"
APP_DIR="/opt/speech-processing"
SERVICE_NAME="speech-processing"

echo "=== Speech Processing Service Deployment ==="
echo "Target server: $SERVER_IP"
echo "Application directory: $APP_DIR"
echo ""

# Function to run commands on remote server
run_remote() {
    ssh root@$SERVER_IP "$1"
}

# Function to copy files to remote server
copy_to_remote() {
    rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' ./ root@$SERVER_IP:$APP_DIR/
}

echo "1. Copying application files to server..."
copy_to_remote

echo "2. Installing Python dependencies on server..."
run_remote "cd $APP_DIR && pip3 install flask flask-sqlalchemy psycopg2-binary gtts pyttsx3 moviepy opencv-python yt-dlp pypdf2 python-docx reportlab markdown trafilatura requests gunicorn email-validator werkzeug"

echo "3. Setting up environment file..."
run_remote "cat > $APP_DIR/.env << 'EOF'
DATABASE_URL=postgresql://speech_user:speech_password@localhost/speech_processing
SESSION_SECRET=$(openssl rand -hex 32)
FLASK_ENV=production
EOF"

echo "4. Setting up PostgreSQL database..."
run_remote "sudo -u postgres psql -c \"CREATE DATABASE IF NOT EXISTS speech_processing;\""
run_remote "sudo -u postgres psql -c \"CREATE USER IF NOT EXISTS speech_user WITH PASSWORD 'speech_password';\""
run_remote "sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE speech_processing TO speech_user;\""

echo "5. Creating systemd service..."
run_remote "cat > /etc/systemd/system/$SERVICE_NAME.service << 'EOF'
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

echo "6. Setting permissions..."
run_remote "chown -R www-data:www-data $APP_DIR"
run_remote "chmod +x $APP_DIR/main.py"

echo "7. Starting the service..."
run_remote "systemctl daemon-reload"
run_remote "systemctl enable $SERVICE_NAME"
run_remote "systemctl restart $SERVICE_NAME"

echo "8. Checking service status..."
run_remote "systemctl status $SERVICE_NAME --no-pager"

echo "9. Testing application health..."
sleep 5
if run_remote "curl -f http://localhost:5000/health"; then
    echo "✓ Application is running successfully!"
else
    echo "✗ Application health check failed"
    exit 1
fi

echo ""
echo "=== Deployment Complete ==="
echo "Application URL: https://speech.lcs.ai"
echo "Health check: https://speech.lcs.ai/health"
echo ""
echo "Next steps:"
echo "1. Update your HAProxy configuration to route speech.lcs.ai to $SERVER_IP:5000"
echo "2. Ensure faster-whisper service is running on $SERVER_IP"
echo "3. Verify SSL certificate covers speech.lcs.ai subdomain"
echo ""
echo "Monitor logs with: ssh root@$SERVER_IP journalctl -u $SERVICE_NAME -f"