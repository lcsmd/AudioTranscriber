# Deploy to UBUAI Server

## Quick Deployment Guide for Your Ubuntu Server (ubuai)

Your server already has:
- ✅ Ollama installed
- ✅ faster-whisper installed in `/mnt/bigdisk/projects/faster-whisper-gpu/`

## Step 1: Connect to Your Server

```bash
ssh lawr@ubuai
# or if using IP:
ssh lawr@10.1.10.20
```

## Step 2: Clone Your Repository

```bash
# Navigate to your preferred location
cd /var/www

# Clone your repository
sudo git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git speech-app
sudo chown -R lawr:www-data speech-app
cd speech-app
```

## Step 3: Run the Automated Setup

```bash
# Make scripts executable
chmod +x deployment/*.sh

# Install system dependencies
sudo bash deployment/install_dependencies.sh

# Run main deployment
sudo bash deployment/setup_ubuntu.sh
```

The setup script will:
- Install all required system packages
- Create Python virtual environment
- Set up PostgreSQL database
- Configure Nginx reverse proxy
- Create systemd service
- Configure firewall

## Step 4: Optimize for Local Processing

Since faster-whisper and ollama are already on this server:

```bash
# Apply local optimizations
sudo bash deployment/update_for_local.sh
```

## Step 5: Verify Deployment

```bash
# Run validation
bash deployment/validate_deployment.sh
```

## Step 6: Access Your Application

Your speech processing app will be available at:
- **Local**: http://localhost
- **Network**: http://ubuai (if DNS configured)
- **IP**: http://10.1.10.20

## Configuration Notes

The deployment automatically configures:
- **Whisper Script**: `/mnt/bigdisk/projects/faster-whisper-gpu/smart_transcribe.py`
- **Server**: localhost (since it's on the same machine)
- **Database**: PostgreSQL on localhost
- **Web Server**: Nginx on port 80

## Service Management

```bash
# Check status
sudo systemctl status speech-app

# Restart service
sudo systemctl restart speech-app

# View logs
sudo journalctl -u speech-app -f

# Nginx logs
sudo tail -f /var/log/nginx/speech-app-error.log
```

## Troubleshooting

### If faster-whisper script not found
Edit `/var/www/speech-app/.env`:
```env
WHISPER_SCRIPT_PATH=/mnt/bigdisk/projects/faster-whisper-gpu/smart_transcribe.py
```

### If service won't start
```bash
sudo journalctl -u speech-app -n 50
```

### Database connection issues
```bash
sudo -u postgres psql
\l  # List databases
\du # List users
```

## Update Application

```bash
cd /var/www/speech-app
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart speech-app
```

## Important Paths on UBUAI

- Application: `/var/www/speech-app`
- Uploads: `/var/www/speech-app/uploads`
- Logs: `/var/log/speech-app/`
- faster-whisper: `/mnt/bigdisk/projects/faster-whisper-gpu/`
- Config: `/var/www/speech-app/.env`