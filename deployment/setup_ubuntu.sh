#!/bin/bash

# Speech Processing App - Ubuntu Server Setup Script
# This script automates the deployment of the speech processing application

set -e  # Exit on any error

echo "=========================================="
echo "Speech Processing App Ubuntu Deployment"
echo "=========================================="

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "This script should not be run as root. Please run as a regular user with sudo access."
   exit 1
fi

# Variables
APP_DIR="/var/www/speech-app"
APP_USER="www-data"
DB_NAME="speechapp"
DB_USER="speechuser"
DB_PASSWORD=$(openssl rand -base64 32)

echo "Step 1: Updating system packages..."
sudo apt update && sudo apt upgrade -y

echo "Step 2: Installing system dependencies..."
sudo apt install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-setuptools \
    nginx \
    postgresql \
    postgresql-contrib \
    ffmpeg \
    git \
    supervisor \
    openssl

echo "Step 3: Creating application directory..."
sudo mkdir -p $APP_DIR
sudo chown $USER:$APP_USER $APP_DIR

echo "Step 4: Setting up Python virtual environment..."
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate

echo "Step 5: Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "requirements.txt not found. Installing basic dependencies..."
    pip install flask gunicorn flask-sqlalchemy psycopg2-binary python-dotenv
fi

echo "Step 6: Setting up PostgreSQL database..."
sudo -u postgres createdb $DB_NAME 2>/dev/null || echo "Database already exists"
sudo -u postgres createuser $DB_USER 2>/dev/null || echo "User already exists"
sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

echo "Step 7: Creating environment configuration..."
cat > $APP_DIR/.env << EOF
# Production Environment Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=$(openssl rand -hex 32)
SESSION_SECRET=$(openssl rand -hex 32)

# Database Configuration
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME
PGDATABASE=$DB_NAME
PGUSER=$DB_USER
PGPASSWORD=$DB_PASSWORD
PGHOST=localhost
PGPORT=5432

# Whisper Configuration (Local Server)
WHISPER_SERVER=localhost
WHISPER_SCRIPT_PATH=/mnt/bigdisk/projects/faster-whisper-gpu/smart_transcribe.py
WHISPER_USERNAME=lawr
WHISPER_PASSWORD=apgar-66

# Application Configuration
UPLOAD_FOLDER=$APP_DIR/uploads
MAX_CONTENT_LENGTH=100000000
EOF

echo "Step 8: Creating uploads directory..."
mkdir -p $APP_DIR/uploads
sudo chown -R $APP_USER:$APP_USER $APP_DIR

echo "Step 9: Creating systemd service..."
sudo tee /etc/systemd/system/speech-app.service > /dev/null << EOF
[Unit]
Description=Speech Processing Application
After=network.target postgresql.service

[Service]
Type=notify
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 --timeout 300 --preload main:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "Step 10: Configuring Nginx..."
sudo tee /etc/nginx/sites-available/speech-app > /dev/null << EOF
server {
    listen 80;
    server_name _;

    client_max_body_size 100M;
    client_body_timeout 300s;
    proxy_read_timeout 300s;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
    }

    location /static {
        alias $APP_DIR/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/speech-app /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

echo "Step 11: Testing Nginx configuration..."
sudo nginx -t

echo "Step 12: Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable speech-app
sudo systemctl start speech-app
sudo systemctl restart nginx

echo "Step 13: Configuring firewall..."
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
echo "y" | sudo ufw enable 2>/dev/null || true

echo "Step 14: Initializing database..."
cd $APP_DIR
source venv/bin/activate
python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created successfully')
"

echo "=========================================="
echo "Deployment completed successfully!"
echo "=========================================="
echo
echo "Database credentials:"
echo "  Database: $DB_NAME"
echo "  Username: $DB_USER"
echo "  Password: $DB_PASSWORD"
echo
echo "Your application should be accessible at:"
echo "  http://$(hostname -I | awk '{print $1}')"
echo "  http://localhost (if accessing from the server)"
echo
echo "Service management commands:"
echo "  Check status: sudo systemctl status speech-app"
echo "  View logs:    sudo journalctl -u speech-app -f"
echo "  Restart app:  sudo systemctl restart speech-app"
echo "  Restart nginx: sudo systemctl restart nginx"
echo
echo "Important: Save the database password shown above!"