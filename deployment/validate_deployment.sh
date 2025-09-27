#!/bin/bash

# Deployment validation script
# Run this script to verify all deployment components are working correctly

APP_DIR="/var/www/speech-app"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Speech Processing App Deployment Validation${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to check status
check_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
        return 0
    else
        echo -e "${RED}✗ $2${NC}"
        return 1
    fi
}

check_warning() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠ $2${NC}"
        return 1
    fi
}

echo "1. Checking system dependencies..."

# Check Python
python3 --version > /dev/null 2>&1
check_status $? "Python 3 installed"

# Check pip
pip3 --version > /dev/null 2>&1
check_status $? "pip3 installed"

# Check PostgreSQL
systemctl is-active --quiet postgresql
check_status $? "PostgreSQL service running"

# Check Nginx
systemctl is-active --quiet nginx
check_status $? "Nginx service running"

echo ""
echo "2. Checking application files..."

# Check application directory
[ -d "$APP_DIR" ]
check_status $? "Application directory exists"

# Check virtual environment
[ -d "$APP_DIR/venv" ]
check_status $? "Python virtual environment exists"

# Check main application file
[ -f "$APP_DIR/main.py" ] || [ -f "$APP_DIR/app.py" ]
check_status $? "Main application file exists"

# Check environment file
[ -f "$APP_DIR/.env" ]
check_status $? "Environment configuration exists"

echo ""
echo "3. Checking Python dependencies..."

cd $APP_DIR
source venv/bin/activate

# Check Flask
python3 -c "import flask" 2>/dev/null
check_status $? "Flask installed"

# Check SQLAlchemy
python3 -c "import sqlalchemy" 2>/dev/null
check_status $? "SQLAlchemy installed"

# Check psycopg2
python3 -c "import psycopg2" 2>/dev/null
check_status $? "PostgreSQL adapter installed"

# Check faster-whisper
python3 -c "import faster_whisper" 2>/dev/null
check_warning $? "faster-whisper installed (warning if not available)"

# Check other key dependencies
python3 -c "import gunicorn" 2>/dev/null
check_status $? "Gunicorn installed"

echo ""
echo "4. Checking services..."

# Check application service
systemctl is-active --quiet speech-app
check_status $? "Speech app service running"

if systemctl is-active --quiet speech-app; then
    # Check if app is responding
    curl -s http://localhost:5000 > /dev/null 2>&1
    check_status $? "Application responding on port 5000"
else
    echo -e "${RED}✗ Cannot check application response (service not running)${NC}"
fi

echo ""
echo "5. Checking configuration files..."

# Check systemd service
[ -f "/etc/systemd/system/speech-app.service" ]
check_status $? "Systemd service file exists"

# Check nginx configuration
[ -f "/etc/nginx/sites-available/speech-app" ]
check_status $? "Nginx site configuration exists"

[ -L "/etc/nginx/sites-enabled/speech-app" ]
check_status $? "Nginx site enabled"

# Test nginx configuration
nginx -t > /dev/null 2>&1
check_status $? "Nginx configuration valid"

echo ""
echo "6. Checking database connectivity..."

# Test database connection
python3 -c "
import os
import sys
sys.path.append('$APP_DIR')
try:
    from app import db, app
    with app.app_context():
        db.engine.execute('SELECT 1')
    print('Database connection successful')
    exit(0)
except Exception as e:
    print(f'Database connection failed: {e}')
    exit(1)
" > /dev/null 2>&1
check_status $? "Database connection working"

echo ""
echo "7. Checking whisper functionality..."

# Test faster-whisper functionality
python3 -c "
try:
    from faster_whisper import WhisperModel
    model = WhisperModel('tiny', device='cpu', compute_type='int8')
    print('faster-whisper model loading successful')
    exit(0)
except Exception as e:
    print(f'faster-whisper test failed: {e}')
    exit(1)
" > /dev/null 2>&1
check_warning $? "faster-whisper model loading (may take time first run)"

# Check if custom script exists
[ -f "/mnt/bigdisk/projects/faster-whisper-gpu/smart_transcribe.py" ]
check_warning $? "Custom faster-whisper script available"

echo ""
echo "8. Checking file permissions..."

# Check application directory ownership
[ "$(stat -c '%U' $APP_DIR)" = "www-data" ] || [ "$(stat -c '%G' $APP_DIR)" = "www-data" ]
check_status $? "Application directory has correct ownership"

# Check uploads directory
[ -d "$APP_DIR/uploads" ]
if [ $? -eq 0 ]; then
    [ -w "$APP_DIR/uploads" ]
    check_status $? "Uploads directory is writable"
else
    echo -e "${YELLOW}⚠ Uploads directory does not exist${NC}"
fi

echo ""
echo "9. Checking logs..."

# Check if log directory exists
[ -d "/var/log/speech-app" ]
check_warning $? "Application log directory exists"

# Check if logs are being written
[ -f "/var/log/speech-app/error.log" ] || [ -f "/var/log/speech-app/access.log" ]
check_warning $? "Application logs exist"

echo ""
echo "10. Network connectivity test..."

# Test internal connectivity
curl -s http://127.0.0.1:5000 > /dev/null 2>&1
check_status $? "Internal HTTP connectivity (127.0.0.1:5000)"

# Test external connectivity via nginx
curl -s http://localhost > /dev/null 2>&1
check_status $? "External HTTP connectivity (port 80)"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Validation completed!${NC}"
echo -e "${GREEN}========================================${NC}"

echo ""
echo "Summary:"
echo "- Your speech processing app should be accessible at http://$(hostname -I | awk '{print $1}')"
echo "- Service logs: sudo journalctl -u speech-app -f"
echo "- Nginx logs: sudo tail -f /var/log/nginx/error.log"
echo "- Application logs: sudo tail -f /var/log/speech-app/error.log"

echo ""
echo "If you see any red ✗ marks above, check the deployment guide for troubleshooting steps."
echo "Yellow ⚠ marks indicate optional components that may need attention."