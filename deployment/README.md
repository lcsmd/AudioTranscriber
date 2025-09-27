# Speech Processing App - Deployment Files

This directory contains all the necessary files for deploying the speech processing application to your Ubuntu server.

## Quick Start

1. **Clone your repository** to your Ubuntu server
2. **Run the setup script**:
   ```bash
   cd your-repo-directory
   sudo bash deployment/setup_ubuntu.sh
   ```

## What's Included

### Core Deployment Files
- `setup_ubuntu.sh` - Main automated deployment script
- `ubuntu_deployment_guide.md` - Detailed deployment instructions
- `install_dependencies.sh` - System dependency installation
- `update_for_local.sh` - Local server optimizations

### Configuration Files
- `nginx.conf` - Nginx reverse proxy configuration
- `speech-app.service` - Systemd service configuration
- `gunicorn.conf.py` - Gunicorn WSGI server configuration
- `.env.production` - Environment variables template

### Optimization Files
- `local_whisper_client.py` - Local-optimized whisper client
- `monitor_service.sh` - Service monitoring script

## Deployment Steps

### 1. Prepare Your Server
```bash
# Install dependencies first
sudo bash deployment/install_dependencies.sh
```

### 2. Run Main Setup
```bash
# Run the automated setup
sudo bash deployment/setup_ubuntu.sh
```

### 3. Optimize for Local Processing
```bash
# Apply local server optimizations
sudo bash deployment/update_for_local.sh
```

## Configuration

### Environment Variables
Copy and edit the environment file:
```bash
cp deployment/.env.production .env
nano .env
```

Key variables to configure:
- Database credentials
- Whisper server settings
- Upload directory paths
- Security keys

### Service Management
```bash
# Check service status
sudo systemctl status speech-app

# Restart service
sudo systemctl restart speech-app

# View logs
sudo journalctl -u speech-app -f
```

### Nginx Configuration
```bash
# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

## Troubleshooting

### Common Issues
1. **Service won't start**: Check logs with `sudo journalctl -u speech-app -f`
2. **Permission errors**: Ensure www-data owns application directory
3. **Database connection**: Verify PostgreSQL is running and credentials are correct
4. **Nginx errors**: Check configuration with `sudo nginx -t`

### Log Locations
- Application logs: `/var/log/speech-app/`
- Nginx logs: `/var/log/nginx/`
- System logs: `sudo journalctl -u speech-app`

### Performance Monitoring
```bash
# Run service monitor
./deployment/monitor_service.sh

# Check resource usage
htop
df -h
```

## Local Faster-Whisper Integration

The deployment is optimized for your local faster-whisper installation:

- **Primary**: Uses your GPU script at `/mnt/bigdisk/projects/faster-whisper-gpu/smart_transcribe.py`
- **Fallback**: Local faster-whisper library if script unavailable
- **Auto-detection**: Automatically detects best processing method

### Whisper Configuration
Edit the environment file to configure:
```env
WHISPER_SERVER=localhost
WHISPER_SCRIPT_PATH=/mnt/bigdisk/projects/faster-whisper-gpu/smart_transcribe.py
LOCAL_WHISPER_MODE=true
```

## Security Notes

- Change default database passwords
- Configure SSL with Let's Encrypt for production
- Set up proper firewall rules
- Regular security updates

## Updating the Application

```bash
cd /var/www/speech-app
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart speech-app
```

## Support

For issues:
1. Check the deployment guide
2. Review service logs
3. Verify all dependencies are installed
4. Ensure proper file permissions