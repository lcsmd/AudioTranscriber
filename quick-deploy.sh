#!/bin/bash
# Quick deployment: Add all, commit with message, push to GitHub, and deploy to production

MESSAGE="${1:-Quick update}"
git add . && git commit -m "$MESSAGE" && git push origin main && ssh lawr@10.1.10.20 'cd /mnt/bigdisk/speech-app && git pull origin main && sudo systemctl restart speech-app && echo "✓ Deployed to https://speech.lcs.ai"'
