import subprocess
import logging
import os
import json
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Faster-whisper script configuration
WHISPER_SCRIPT_PATH = "/mnt/bigdisk/projects/faster-whisper-gpu/smart_transcribe.py"
WHISPER_SERVER = "10.1.10.20"

def send_to_whisper(audio_file_path, language='en'):
    """
    Send an audio file to the faster-whisper script for transcription
    
    Args:
        audio_file_path (str): Path to the audio file (WAV, MP3, etc.)
        language (str): Target language for transcription
    
    Returns:
        dict: The transcription result from the whisper script
        
    Raises:
        Exception: If the transcription request fails
    """
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found at {audio_file_path}")
    
    try:
        logger.info(f"Processing file {audio_file_path} with faster-whisper on GPU server")
        
        # Create a temporary directory for processing on the GPU server
        timestamp = int(time.time())
        remote_temp_dir = f"/tmp/speech_processing_{timestamp}"
        audio_filename = os.path.basename(audio_file_path)
        remote_audio_path = f"{remote_temp_dir}/{audio_filename}"
        
        # Copy file to GPU server
        logger.debug(f"Copying audio file to GPU server: {remote_audio_path}")
        subprocess.run([
            "ssh", f"root@{WHISPER_SERVER}",
            f"mkdir -p {remote_temp_dir}"
        ], check=True, capture_output=True)
        
        subprocess.run([
            "scp", audio_file_path, f"root@{WHISPER_SERVER}:{remote_audio_path}"
        ], check=True, capture_output=True)
        
        # Create a temporary script to process the audio file directly
        temp_script = f"""#!/bin/bash
cd /mnt/bigdisk/projects/faster-whisper-gpu
python3 -c "
import sys
sys.path.append('/mnt/bigdisk/projects/faster-whisper-gpu')
from faster_whisper import WhisperModel
import json

model = WhisperModel('medium', device='cuda', compute_type='float16')
segments, info = model.transcribe('{remote_audio_path}', task='transcribe', language='{language}' if '{language}' != 'auto' else None)

transcription_text = ''
segment_list = []
for segment in segments:
    transcription_text += segment.text + ' '
    segment_list.append({{
        'start': segment.start,
        'end': segment.end,
        'text': segment.text.strip()
    }})

result = {{
    'text': transcription_text.strip(),
    'language': info.language,
    'duration': info.duration,
    'language_probability': info.language_probability,
    'segments': segment_list
}}

print(json.dumps(result))
"
"""
        
        # Execute the transcription on GPU server
        logger.debug("Running transcription on GPU server")
        result = subprocess.run([
            "ssh", f"root@{WHISPER_SERVER}",
            temp_script
        ], capture_output=True, text=True, timeout=600)  # 10 minute timeout
        
        # Clean up temporary files
        subprocess.run([
            "ssh", f"root@{WHISPER_SERVER}",
            f"rm -rf {remote_temp_dir}"
        ], capture_output=True)
        
        if result.returncode == 0:
            try:
                # Parse the JSON output from the script
                transcription_result = json.loads(result.stdout.strip())
                logger.info(f"Transcription completed: {len(transcription_result.get('text', ''))} characters")
                return transcription_result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse transcription result: {e}")
                logger.error(f"Raw output: {result.stdout}")
                raise Exception(f"Invalid JSON response from whisper service: {e}")
        else:
            logger.error(f"Whisper script failed with return code {result.returncode}")
            logger.error(f"STDERR: {result.stderr}")
            raise Exception(f"Whisper transcription failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        logger.error("Whisper transcription timed out")
        raise Exception("Transcription timed out after 10 minutes")
    except Exception as e:
        logger.error(f"Error during whisper transcription: {str(e)}")
        raise Exception(f"Whisper transcription failed: {str(e)}")
