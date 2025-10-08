# Speech Processing Service

A comprehensive web application for audio transcription, text-to-speech conversion, and document processing with GPU-accelerated performance.

## Features

- 🎙️ **Audio/Video Transcription** - Support for MP3, WAV, MP4, MOV files
- 📺 **YouTube Processing** - Extract transcripts from videos and playlists
- 📄 **Document Processing** - Extract text from PDF, DOCX, and TXT files
- 🔊 **Text-to-Speech** - Generate audio with multiple voice options
- 🌍 **Multi-Language Support** - 10 languages including English, Spanish, French, German, and more
- 📊 **Multiple Output Formats** - Text, Markdown, Word documents, and PDF
- ⚡ **GPU Acceleration** - Powered by faster-whisper for efficient transcription
- 📈 **Real-time Progress** - Track processing status with visual indicators
- 💾 **Job History** - All processing jobs saved to database

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database
- FFmpeg
- faster-whisper (for transcription)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
   cd YOUR_REPO
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the application**
   ```bash
   gunicorn --bind 0.0.0.0:5000 main:app
   ```

5. **Access the app**
   Open http://localhost:5000 in your browser

## Deployment

### Deploy to Ubuntu Server

For detailed deployment instructions, see [deployment/DEPLOY_TO_UBUAI.md](deployment/DEPLOY_TO_UBUAI.md)

**Quick deployment on Ubuntu:**

```bash
# On your Ubuntu server
sudo mkdir -p /var/www
sudo git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git /var/www/speech-app
cd /var/www/speech-app
sudo bash deployment/setup_ubuntu.sh
```

### Deployment Features

- ✅ Nginx reverse proxy
- ✅ Gunicorn WSGI server
- ✅ Systemd service management
- ✅ PostgreSQL database
- ✅ Automatic service restart
- ✅ Log rotation
- ✅ Security hardening

## Usage

### Audio Transcription

1. Select the **Files** tab
2. Upload your audio/video file (MP3, WAV, MP4, MOV)
3. Choose the language
4. Select output format
5. Click "Process"

### YouTube Transcription

1. Select the **YouTube** tab
2. Paste a YouTube video or playlist URL
3. Choose whether to use existing transcript or transcribe audio
4. Select language and output format
5. Click "Process"

### Document Processing

1. Select the **Documents** tab
2. Upload a PDF, DOCX, or TXT file
3. Select output format
4. Click "Process"

### Text-to-Speech

1. Select the **Text** tab
2. Enter or paste your text
3. Choose a voice and language
4. Click "Generate Speech"

## Architecture

- **Backend**: Flask + SQLAlchemy
- **Database**: PostgreSQL
- **Transcription**: faster-whisper (GPU-accelerated)
- **Web Server**: Gunicorn + Nginx
- **TTS**: gTTS + pyttsx3
- **Video Processing**: yt-dlp + moviepy

## Configuration

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost/dbname

# Whisper Configuration
WHISPER_SERVER=localhost
WHISPER_SCRIPT_PATH=/path/to/faster-whisper/script

# Application
FLASK_ENV=production
SECRET_KEY=your-secret-key
```

### Supported Languages

- English (en)
- Spanish (es)
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Russian (ru)
- Japanese (ja)
- Korean (ko)
- Chinese (zh)

### Output Formats

- Plain Text (.txt)
- Markdown (.md)
- Word Document (.docx)
- PDF (.pdf)

## API Integration

### faster-whisper GPU Server

The application integrates with a GPU-accelerated faster-whisper instance:

- Primary: Remote GPU server via SSH
- Fallback: Local faster-whisper installation
- Auto-detection of best processing method

## Troubleshooting

### Common Issues

**Service won't start:**
```bash
sudo journalctl -u speech-app -f
```

**Database connection errors:**
```bash
sudo systemctl status postgresql
```

**Transcription fails:**
- Check faster-whisper installation
- Verify GPU server connectivity
- Review application logs

### Logs

- Application: `/var/log/speech-app/`
- Nginx: `/var/log/nginx/`
- System: `sudo journalctl -u speech-app`

## Development

### Project Structure

```
.
├── app.py                 # Flask application setup
├── main.py               # Application entry point
├── models.py             # Database models
├── utils/
│   ├── audio_converter.py
│   ├── youtube_processor.py
│   ├── document_processor.py
│   ├── text_to_speech.py
│   ├── output_formatter.py
│   └── whisper_client.py
├── templates/            # HTML templates
├── static/              # CSS, JS, assets
└── deployment/          # Deployment scripts

```

### Adding Features

1. Create utility modules in `utils/`
2. Add routes in `app.py`
3. Update models in `models.py`
4. Add templates in `templates/`

## Service Management

### Commands

```bash
# Check status
sudo systemctl status speech-app

# Restart service
sudo systemctl restart speech-app

# View logs
sudo journalctl -u speech-app -f

# Update application
cd /var/www/speech-app
git pull
sudo systemctl restart speech-app
```

## Performance

- GPU-accelerated transcription with faster-whisper
- Asynchronous job processing
- Efficient file handling for large uploads
- Database query optimization
- Nginx caching for static assets

## Security

- Environment-based secret management
- SQL injection protection via SQLAlchemy
- XSS protection headers
- CSRF protection
- File upload validation
- Secure password handling

## License

This project is for internal use.

## Support

For deployment assistance, see:
- [Ubuntu Deployment Guide](deployment/ubuntu_deployment_guide.md)
- [UBUAI Server Guide](deployment/DEPLOY_TO_UBUAI.md)
- [Deployment README](deployment/README.md)

## Credits

Built with:
- Flask
- faster-whisper
- PostgreSQL
- Nginx
- Gunicorn