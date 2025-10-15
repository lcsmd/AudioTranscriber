#!/bin/bash
# Deploy UI updates to production server

SERVER="lawr@10.1.10.20"
APP_DIR="/home/lawr/speech-app"

echo "Deploying UI updates to production server..."

# Copy updated files
scp templates/index.html $SERVER:$APP_DIR/templates/
scp static/js/comprehensive-processor.js $SERVER:$APP_DIR/static/js/
scp app.py $SERVER:$APP_DIR/
scp suggested_prompts.txt $SERVER:$APP_DIR/

# Restart the service
ssh $SERVER "sudo systemctl restart speech-app"

echo "Deployment complete! Check https://speech.lcs.ai"
