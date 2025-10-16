#!/bin/bash

# Speech Processing Service Deployment Script
# GitHub → Production Server (ubuai)

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SERVER_USER="lawr"
SERVER_IP="10.1.10.20"
APP_DIR="/mnt/bigdisk/speech-app"
SERVICE_NAME="speech-app"

echo -e "${YELLOW}=== Speech App Deployment ===${NC}"
echo -e "Target: ${SERVER_USER}@${SERVER_IP}:${APP_DIR}\n"

# Step 1: Push to GitHub
echo -e "${YELLOW}Step 1: Pushing to GitHub...${NC}"
git add .
read -p "Enter commit message: " commit_msg
git commit -m "$commit_msg" || echo "No changes to commit"
git push origin main

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Pushed to GitHub${NC}\n"
else
    echo -e "${RED}✗ Failed to push to GitHub${NC}"
    exit 1
fi

# Step 2: Deploy to production
echo -e "${YELLOW}Step 2: Deploying to production...${NC}"

ssh ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
cd /mnt/bigdisk/speech-app
echo "Pulling latest changes from GitHub..."
git pull origin main
echo "Restarting speech-app service..."
sudo systemctl restart speech-app
echo "Checking service status..."
sudo systemctl status speech-app --no-pager | head -15
ENDSSH

if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ Deployment complete!${NC}"
    echo -e "${GREEN}✓ Live at: https://speech.lcs.ai${NC}"
else
    echo -e "\n${RED}✗ Deployment failed${NC}"
    exit 1
fi