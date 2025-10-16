# Deployment Guide

## Quick Deploy (One Command)

For simple updates with a default commit message:
```bash
./quick-deploy.sh
```

Or with a custom commit message:
```bash
./quick-deploy.sh "Fixed YouTube URL input visibility"
```

This automatically:
1. Adds all changes
2. Commits with your message (or "Quick update")
3. Pushes to GitHub
4. SSHs to production server
5. Pulls latest changes
6. Restarts the service

---

## Interactive Deploy (Detailed)

For more control with interactive prompts:
```bash
./deploy.sh
```

This script:
1. Asks you for a commit message
2. Shows detailed progress at each step
3. Displays service status after deployment
4. Provides colored output for easier reading

---

## Manual Deployment

If you prefer manual control:

### Step 1: Push to GitHub
```bash
git add .
git commit -m "Your commit message"
git push origin main
```

### Step 2: Deploy to Production
```bash
ssh lawr@10.1.10.20
cd /mnt/bigdisk/speech-app
git pull origin main
sudo systemctl restart speech-app
sudo systemctl status speech-app
```

---

## Production Server Details
- **Server**: ubuai (10.1.10.20)
- **User**: lawr
- **App Directory**: /mnt/bigdisk/speech-app
- **Service**: speech-app
- **Live URL**: https://speech.lcs.ai

---

## Troubleshooting

Check service logs:
```bash
ssh lawr@10.1.10.20 'sudo journalctl -u speech-app -n 50 --no-pager'
```

Check service status:
```bash
ssh lawr@10.1.10.20 'sudo systemctl status speech-app'
```

Restart service manually:
```bash
ssh lawr@10.1.10.20 'sudo systemctl restart speech-app'
```
