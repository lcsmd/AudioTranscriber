# Speech Processing App - Ubuntu Server Deployment Guide

## Prerequisites
- Ubuntu server with faster-whisper and ollama installed
- sudo access on the server
- Your GitHub repository URL

## Quick Setup Commands

### 1. Clone and Setup Application
```bash
# Clone your repository
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME

# Run the automated setup script
sudo bash deployment/setup_ubuntu.sh
```

### 2. Manual Configuration Steps

#### Install System Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-dev python3-venv build-essential \
    libssl-dev libffi-dev python3-setuptools nginx postgresql postgresql-contrib \
    ffmpeg git supervisor
```

#### Setup Application
```bash
# Create application directory
sudo mkdir -p /var/www/speech-app
sudo chown $USER:www-data /var/www/speech-app
cd /var/www/speech-app

# Clone your repository (if not done already)
git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

#### Database Setup
```bash
# Create PostgreSQL database and user
sudo -u postgres createdb speechapp
sudo -u postgres createuser speechuser
sudo -u postgres psql -c "ALTER USER speechuser WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE speechapp TO speechuser;"
```

#### Environment Configuration
```bash
# Create environment file
cp deployment/.env.production /var/www/speech-app/.env

# Edit environment variables
nano /var/www/speech-app/.env
```

#### Configure Services
```bash
# Copy service files
sudo cp deployment/speech-app.service /etc/systemd/system/
sudo cp deployment/nginx.conf /etc/nginx/sites-available/speech-app
sudo ln -s /etc/nginx/sites-available/speech-app /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Set permissions
sudo chown -R www-data:www-data /var/www/speech-app

# Start services
sudo systemctl daemon-reload
sudo systemctl enable speech-app
sudo systemctl start speech-app
sudo systemctl restart nginx

# Enable firewall
sudo ufw allow 'Nginx Full'
sudo ufw allow ssh
sudo ufw enable
```

## Service Management

### Check Status
```bash
# Check application status
sudo systemctl status speech-app

# Check nginx status
sudo systemctl status nginx

# View application logs
sudo journalctl -u speech-app -f

# View nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Restart Services
```bash
# Restart application
sudo systemctl restart speech-app

# Restart nginx
sudo systemctl restart nginx

# Reload nginx (for config changes)
sudo systemctl reload nginx
```

## Update Application
```bash
cd /var/www/speech-app
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart speech-app
```

## Troubleshooting

### Common Issues
1. **Permission errors**: Make sure www-data owns the application directory
2. **Database connection**: Check PostgreSQL is running and credentials are correct
3. **Port conflicts**: Ensure port 5000 isn't used by other services
4. **Nginx errors**: Check nginx configuration syntax with `sudo nginx -t`

### Logs to Check
- Application logs: `sudo journalctl -u speech-app -f`
- Nginx error logs: `/var/log/nginx/error.log`
- PostgreSQL logs: `/var/log/postgresql/`

## Performance Tuning

### Gunicorn Workers
- Formula: (2 x CPU cores) + 1
- Check CPU cores: `nproc`
- Update in `/etc/systemd/system/speech-app.service`

### Nginx Optimization
- Increase client_max_body_size for large audio files
- Enable gzip compression
- Configure proper caching headers

## Security Considerations
- Change default database password
- Configure SSL certificate with Let's Encrypt
- Set up proper firewall rules
- Regular security updates

## Access Your Application
- Local: http://your_server_ip
- Domain: http://your_domain.com (after DNS configuration)