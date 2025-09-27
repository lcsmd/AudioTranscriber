#!/bin/bash

# Script to update the deployed application for local server environment
# Run this after the main deployment to optimize for local faster-whisper usage

APP_DIR="/var/www/speech-app"

echo "Updating application for local server deployment..."

# Backup original whisper client
if [ -f "$APP_DIR/utils/whisper_client.py" ] && [ ! -f "$APP_DIR/utils/whisper_client.py.backup" ]; then
    echo "Backing up original whisper client..."
    cp "$APP_DIR/utils/whisper_client.py" "$APP_DIR/utils/whisper_client.py.backup"
fi

# Update environment for local processing
echo "Updating environment configuration..."
cat >> $APP_DIR/.env << 'EOF'

# Local Server Optimizations
LOCAL_WHISPER_MODE=true
WHISPER_USE_LOCAL_FALLBACK=true
WHISPER_LOCAL_DEVICE=auto
WHISPER_LOCAL_MODEL=base

# Performance settings for local processing
GUNICORN_TIMEOUT=600
GUNICORN_WORKERS=3
EOF

# Update whisper client to prefer local processing
echo "Optimizing whisper client for local deployment..."
cat > "$APP_DIR/utils/whisper_config.py" << 'EOF'
# Local deployment configuration for whisper client
import os

# Deployment mode settings
LOCAL_DEPLOYMENT = True
PREFER_LOCAL_PROCESSING = True

# Local faster-whisper settings
LOCAL_SCRIPT_PATH = "/mnt/bigdisk/projects/faster-whisper-gpu/smart_transcribe.py"
LOCAL_MODEL_SIZE = "base"  # Can be: tiny, base, small, medium, large-v3
LOCAL_DEVICE = "auto"  # auto, cpu, cuda
LOCAL_COMPUTE_TYPE = "auto"  # auto, int8, float16, float32

# Timeout settings for longer audio files
TRANSCRIPTION_TIMEOUT = 600  # 10 minutes

# Fallback configuration
ENABLE_FALLBACK = True
SSH_TIMEOUT = 10  # Seconds to wait for SSH connection

def get_optimal_device():
    """Determine the best device for local processing"""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"

def get_optimal_compute_type(device):
    """Get optimal compute type based on device"""
    if device == "cuda":
        return "float16"
    else:
        return "int8"
EOF

# Create local service monitoring script
echo "Creating service monitoring script..."
cat > "$APP_DIR/deployment/monitor_service.sh" << 'EOF'
#!/bin/bash

# Service monitoring script for speech processing app

SERVICE_NAME="speech-app"
LOG_FILE="/var/log/speech-app/monitor.log"

# Create log directory if it doesn't exist
sudo mkdir -p /var/log/speech-app
sudo chown www-data:www-data /var/log/speech-app

echo "$(date): Starting service monitor" >> $LOG_FILE

# Check service status
check_service() {
    if systemctl is-active --quiet $SERVICE_NAME; then
        echo "$(date): Service $SERVICE_NAME is running" >> $LOG_FILE
        return 0
    else
        echo "$(date): Service $SERVICE_NAME is not running" >> $LOG_FILE
        return 1
    fi
}

# Check if faster-whisper is working
check_whisper() {
    python3 -c "
import sys
try:
    from faster_whisper import WhisperModel
    model = WhisperModel('tiny', device='cpu')
    print('faster-whisper is working')
    sys.exit(0)
except Exception as e:
    print(f'faster-whisper error: {e}')
    sys.exit(1)
" >> $LOG_FILE 2>&1
}

# Main monitoring loop
if check_service; then
    echo "$(date): Service is healthy" >> $LOG_FILE
    
    # Check whisper functionality
    if check_whisper; then
        echo "$(date): faster-whisper is functional" >> $LOG_FILE
    else
        echo "$(date): WARNING - faster-whisper may have issues" >> $LOG_FILE
    fi
else
    echo "$(date): ALERT - Service is down, attempting restart" >> $LOG_FILE
    sudo systemctl restart $SERVICE_NAME
    
    # Wait and check again
    sleep 10
    if check_service; then
        echo "$(date): Service restart successful" >> $LOG_FILE
    else
        echo "$(date): CRITICAL - Service restart failed" >> $LOG_FILE
    fi
fi
EOF

# Make scripts executable
chmod +x "$APP_DIR/deployment/monitor_service.sh"

# Update gunicorn configuration for local processing
echo "Updating gunicorn configuration..."
sudo tee /etc/systemd/system/speech-app.service > /dev/null << EOF
[Unit]
Description=Speech Processing Application (Local Deployment)
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 --timeout 600 --max-requests 500 --max-requests-jitter 50 --preload --access-logfile /var/log/speech-app/access.log --error-logfile /var/log/speech-app/error.log --log-level info main:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
Restart=on-failure
RestartSec=5
TimeoutStartSec=300
TimeoutStopSec=30

# Resource limits for audio processing
LimitNOFILE=8192
MemoryLimit=4G

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR/uploads /var/log/speech-app /tmp

[Install]
WantedBy=multi-user.target
EOF

# Create log rotation configuration
echo "Setting up log rotation..."
sudo tee /etc/logrotate.d/speech-app > /dev/null << 'EOF'
/var/log/speech-app/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
    postrotate
        systemctl reload speech-app || true
    endscript
}
EOF

# Reload systemd and restart service
echo "Reloading systemd configuration..."
sudo systemctl daemon-reload
sudo systemctl restart speech-app

echo "Local deployment optimization completed!"
echo "Service status:"
sudo systemctl status speech-app --no-pager -l