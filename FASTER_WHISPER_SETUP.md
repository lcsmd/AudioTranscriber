# Faster-Whisper GPU Setup Guide

## Current Setup
- Location: /mnt/bigdisk/projects/faster-whisper-gpu/ on 10.1.10.20
- Script: smart_transcribe.py (custom YouTube transcription tool)
- GPU server with CUDA support
- Integration with speech processing service via SSH

## Faster-Whisper Service Configuration

### 1. Check Current Setup
```bash
ssh root@10.1.10.20
cd ~/projects/faster-whisper-gpu/
ls -la
```

### 2. Standard Faster-Whisper Server Setup
If you need to set up the server component, here's the typical configuration:

```bash
# Install faster-whisper with GPU support
pip install faster-whisper[gpu]

# Create a simple HTTP server wrapper
cat > whisper_server.py << 'EOF'
#!/usr/bin/env python3
import os
import tempfile
import json
from flask import Flask, request, jsonify
from faster_whisper import WhisperModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize the model (adjust model size as needed)
# Available models: tiny, base, small, medium, large-v1, large-v2, large-v3
model = WhisperModel("large-v3", device="cuda", compute_type="float16")

@app.route('/v1/audio/transcriptions', methods=['POST'])
def transcribe():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        audio_file = request.files['file']
        if audio_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            audio_file.save(temp_file.name)
            
            logger.info(f"Processing audio file: {audio_file.filename}")
            
            # Transcribe with faster-whisper
            segments, info = model.transcribe(temp_file.name, beam_size=5)
            
            # Combine all segments into full transcription
            transcription_text = ""
            for segment in segments:
                transcription_text += segment.text + " "
            
            # Clean up temporary file
            os.unlink(temp_file.name)
            
            # Return in OpenAI-compatible format
            result = {
                "text": transcription_text.strip(),
                "language": info.language,
                "duration": info.duration,
                "language_probability": info.language_probability
            }
            
            logger.info(f"Transcription completed: {len(transcription_text)} characters")
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"Transcription error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'model': 'large-v3', 'device': 'cuda'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
EOF

chmod +x whisper_server.py
```

### 3. Create Systemd Service for Faster-Whisper
```bash
cat > /etc/systemd/system/faster-whisper.service << 'EOF'
[Unit]
Description=Faster Whisper GPU Service
After=network.target

[Service]
Type=exec
User=root
WorkingDirectory=/root/projects/faster-whisper-gpu
Environment=CUDA_VISIBLE_DEVICES=0
ExecStart=/usr/bin/python3 whisper_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
systemctl enable faster-whisper
systemctl start faster-whisper
systemctl status faster-whisper
```

### 4. Test Faster-Whisper Service
```bash
# Test with a sample audio file
curl -X POST http://10.1.10.20:8000/v1/audio/transcriptions \
  -F "file=@sample.wav"

# Health check
curl http://10.1.10.20:8000/health
```

## Alternative Configurations

### Option 1: Different Port
If faster-whisper runs on a different port, update the speech service:
```python
# In utils/whisper_client.py
WHISPER_SERVICE_URL = "http://10.1.10.20:PORT/v1/audio/transcriptions"
```

### Option 2: Direct Python Integration
If you prefer direct integration without HTTP server:
```python
# Alternative approach - direct faster-whisper integration
from faster_whisper import WhisperModel

def transcribe_local(audio_path):
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    segments, info = model.transcribe(audio_path, beam_size=5)
    return "".join(segment.text for segment in segments)
```

## GPU Performance Optimization

### Memory Management
```bash
# Monitor GPU memory usage
nvidia-smi -l 1

# Adjust model size based on GPU memory:
# - RTX 3090/4090: large-v3
# - RTX 3080: large-v2 or medium
# - RTX 3070: medium or small
```

### CUDA Configuration
```bash
# Ensure CUDA is properly configured
export CUDA_VISIBLE_DEVICES=0
export CUDNN_PATH=/usr/lib/x86_64-linux-gnu
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda/lib64
```

## Troubleshooting

### Common Issues
1. **CUDA not found**: Install CUDA toolkit and drivers
2. **Out of memory**: Use smaller model or adjust compute_type
3. **Slow transcription**: Check GPU utilization with nvidia-smi
4. **Connection refused**: Verify service is running on correct port

### Debug Commands
```bash
# Check if service is running
systemctl status faster-whisper

# View logs
journalctl -u faster-whisper -f

# Test GPU access
python3 -c "import torch; print(torch.cuda.is_available())"

# Check faster-whisper installation
python3 -c "from faster_whisper import WhisperModel; print('OK')"
```

## Integration with Speech Service

The speech processing service automatically connects to faster-whisper at:
- URL: http://10.1.10.20:8000/v1/audio/transcriptions
- Timeout: 300 seconds for large files
- Automatic file format conversion (MP3→WAV)
- Error handling and retry logic

Monitor the integration with:
```bash
# Speech service logs
journalctl -u speech-processing -f

# Faster-whisper logs
journalctl -u faster-whisper -f
```