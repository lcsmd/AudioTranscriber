#!/bin/bash

# One-command deployment script for UBUAI server
# This script deploys the speech processing app on your Ubuntu server with faster-whisper and ollama

set -e

echo "================================================"
echo "Deploying Speech Processing App to UBUAI Server"
echo "================================================"
echo ""

# Configuration
APP_DIR="/var/www/speech-app"
REPO_URL="$1"
CURRENT_USER=$(whoami)

# Check if repository URL provided
if [ -z "$REPO_URL" ]; then
    echo "Usage: $0 <github-repository-url>"
    echo "Example: $0 https://github.com/username/repo-name.git"
    exit 1
fi

echo "Step 1: Creating application directory..."
sudo mkdir -p /var/www
sudo mkdir -p $APP_DIR
sudo chown $CURRENT_USER:www-data $APP_DIR

echo "Step 2: Cloning repository..."
if [ -d "$APP_DIR/.git" ]; then
    echo "Repository already exists, pulling latest changes..."
    cd $APP_DIR
    git pull
else
    git clone $REPO_URL $APP_DIR
fi

cd $APP_DIR

echo "Step 3: Making scripts executable..."
chmod +x deployment/*.sh

echo "Step 4: Installing system dependencies..."
sudo bash deployment/install_dependencies.sh

echo "Step 5: Running main deployment..."
sudo bash deployment/setup_ubuntu.sh

echo "Step 6: Applying local server optimizations..."
sudo bash deployment/update_for_local.sh

echo "Step 7: Validating deployment..."
bash deployment/validate_deployment.sh

echo ""
echo "================================================"
echo "Deployment Complete!"
echo "================================================"
echo ""
echo "Your speech processing app is now running on UBUAI!"
echo ""
echo "Access your application at:"
echo "  - http://localhost"
echo "  - http://ubuai (if DNS configured)"
echo "  - http://10.1.10.20"
echo ""
echo "Service management:"
echo "  Status:  sudo systemctl status speech-app"
echo "  Restart: sudo systemctl restart speech-app"
echo "  Logs:    sudo journalctl -u speech-app -f"
echo ""
echo "Application directory: $APP_DIR"