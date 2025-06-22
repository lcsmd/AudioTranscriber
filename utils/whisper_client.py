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
    
    # Check if SSH is available for GPU server connection
    ssh_available = False
    try:
        subprocess.run(["which", "ssh"], check=True, capture_output=True)
        ssh_available = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.info("SSH not available, using local processing")
    
    if ssh_available:
        try:
            return _process_with_gpu_server(audio_file_path, language)
        except Exception as e:
            logger.warning(f"GPU server processing failed: {str(e)}, falling back to local processing")
            return _process_locally(audio_file_path, language)
    else:
        return _process_locally(audio_file_path, language)

def _process_with_gpu_server(audio_file_path, language='en'):
    """Process audio file using remote GPU server"""
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
    
    # Run transcription on GPU server
    logger.debug("Running transcription on GPU server")
    result = subprocess.run([
        "ssh", f"root@{WHISPER_SERVER}",
        f"cd /mnt/bigdisk/projects/faster-whisper-gpu && python3 smart_transcribe.py '{remote_audio_path}' --language {language}"
    ], check=True, capture_output=True, text=True)
    
    # Parse the result
    try:
        transcription_data = json.loads(result.stdout)
        logger.info("Successfully received transcription from GPU server")
        
        # Clean up remote files
        subprocess.run([
            "ssh", f"root@{WHISPER_SERVER}",
            f"rm -rf {remote_temp_dir}"
        ], capture_output=True)
        
        return transcription_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse GPU server response: {result.stdout}")
        raise Exception(f"Invalid response from GPU server: {str(e)}")

def _process_locally(audio_file_path, language='en'):
    """Process audio file using local faster-whisper"""
    logger.info(f"Processing file {audio_file_path} with local faster-whisper")
    
    try:
        from faster_whisper import WhisperModel
        
        # Initialize the model (using 'base' for better performance/accuracy balance)
        model = WhisperModel("base", device="cpu", compute_type="int8")
        
        # Convert language code if needed
        whisper_language = language if language != 'auto' else None
        
        start_time = time.time()
        segments, info = model.transcribe(
            audio_file_path, 
            language=whisper_language,
            task="transcribe"
        )
        
        # Extract text and segments
        transcription_text = ""
        segment_list = []
        
        for segment in segments:
            transcription_text += segment.text + " "
            segment_list.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            })
        
        processing_time = time.time() - start_time
        
        result = {
            "text": transcription_text.strip(),
            "segments": segment_list,
            "language": info.language,
            "duration": info.duration,
            "processing_time": processing_time
        }
        
        logger.info(f"Local transcription completed in {processing_time:.2f} seconds")
        return result
        
    except ImportError as e:
        logger.error(f"faster-whisper not available: {str(e)}")
        return {
            "text": "Local transcription requires faster-whisper installation. Please install faster-whisper or configure GPU server access.",
            "segments": [],
            "language": language,
            "duration": 0,
            "processing_time": 0.0
        }
    except Exception as e:
        logger.error(f"Error in local transcription: {str(e)}")
        raise Exception(f"Local transcription failed: {str(e)}")