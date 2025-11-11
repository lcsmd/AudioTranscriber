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
WHISPER_USERNAME = "lawr"
WHISPER_PASSWORD = "apgar-66"

def send_to_whisper(audio_file_path, language='en', progress_callback=None):
    """
    Send an audio file to the faster-whisper script for transcription
    
    Args:
        audio_file_path (str): Path to the audio file (WAV, MP3, etc.)
        language (str): Target language for transcription
        progress_callback: Optional callback function(processed_seconds, total_seconds) for progress updates
    
    Returns:
        dict: The transcription result from the whisper script
        
    Raises:
        Exception: If the transcription request fails
    """
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found at {audio_file_path}")
    
    # Check if we're running on the GPU server (local script available)
    if os.path.exists(WHISPER_SCRIPT_PATH):
        logger.info("Running on GPU server, using local faster-whisper script")
        try:
            return _process_with_local_script(audio_file_path, language)
        except Exception as e:
            logger.warning(f"Local script processing failed: {str(e)}, falling back to faster-whisper library")
            return _process_locally(audio_file_path, language, progress_callback)
    
    # Check if SSH is available for remote GPU server connection
    ssh_available = False
    try:
        subprocess.run(["which", "ssh"], check=True, capture_output=True)
        subprocess.run(["which", "sshpass"], check=True, capture_output=True)
        ssh_available = True
        logger.info("SSH tools available, attempting remote GPU server connection")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.info("SSH tools not available, using local processing")
    
    if ssh_available:
        try:
            return _process_with_gpu_server(audio_file_path, language)
        except Exception as e:
            logger.warning(f"GPU server processing failed: {str(e)}, falling back to local processing")
            return _process_locally(audio_file_path, language, progress_callback)
    else:
        return _process_locally(audio_file_path, language, progress_callback)

def _process_with_local_script(audio_file_path, language='en'):
    """Process audio file using local faster-whisper script"""
    logger.info(f"Processing file {audio_file_path} with local faster-whisper script")
    
    # Get the directory of the script and the venv python
    script_dir = os.path.dirname(WHISPER_SCRIPT_PATH)
    venv_python = os.path.join(script_dir, 'venv', 'bin', 'python3')
    
    # Try to use venv python if available, otherwise use system python3
    python_cmd = venv_python if os.path.exists(venv_python) else 'python3'
    
    start_time = time.time()
    
    try:
        # Run the script directly
        result = subprocess.run([
            python_cmd,
            WHISPER_SCRIPT_PATH,
            audio_file_path,
            '--language', language
        ], check=True, capture_output=True, text=True, timeout=600)
        
        # Parse the result
        transcription_data = json.loads(result.stdout)
        processing_time = time.time() - start_time
        
        logger.info(f"Local script transcription completed in {processing_time:.2f} seconds")
        return transcription_data
        
    except subprocess.TimeoutExpired:
        logger.error("Transcription timed out after 10 minutes")
        raise Exception("Transcription timed out")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse script output: {result.stdout}")
        raise Exception(f"Invalid response from transcription script: {str(e)}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Script execution failed: {e.stderr}")
        raise Exception(f"Transcription script failed: {e.stderr}")

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
        "sshpass", "-p", WHISPER_PASSWORD,
        "ssh", "-o", "StrictHostKeyChecking=no",
        f"{WHISPER_USERNAME}@{WHISPER_SERVER}",
        f"mkdir -p {remote_temp_dir}"
    ], check=True, capture_output=True)
    
    subprocess.run([
        "sshpass", "-p", WHISPER_PASSWORD,
        "scp", "-o", "StrictHostKeyChecking=no",
        audio_file_path, f"{WHISPER_USERNAME}@{WHISPER_SERVER}:{remote_audio_path}"
    ], check=True, capture_output=True)
    
    # Run transcription on GPU server
    logger.debug("Running transcription on GPU server")
    result = subprocess.run([
        "sshpass", "-p", WHISPER_PASSWORD,
        "ssh", "-o", "StrictHostKeyChecking=no",
        f"{WHISPER_USERNAME}@{WHISPER_SERVER}",
        f"cd {WHISPER_SCRIPT_PATH.rsplit('/', 1)[0]} && python3 {WHISPER_SCRIPT_PATH.rsplit('/', 1)[1]} '{remote_audio_path}' --language {language}"
    ], check=True, capture_output=True, text=True)
    
    # Parse the result
    try:
        transcription_data = json.loads(result.stdout)
        logger.info("Successfully received transcription from GPU server")
        
        # Clean up remote files
        subprocess.run([
            "sshpass", "-p", WHISPER_PASSWORD,
            "ssh", "-o", "StrictHostKeyChecking=no",
            f"{WHISPER_USERNAME}@{WHISPER_SERVER}",
            f"rm -rf {remote_temp_dir}"
        ], capture_output=True)
        
        return transcription_data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse GPU server response: {result.stdout}")
        raise Exception(f"Invalid response from GPU server: {str(e)}")

def _process_locally(audio_file_path, language='en', progress_callback=None):
    """Process audio file using local faster-whisper"""
    logger.info(f"Processing file {audio_file_path} with local faster-whisper")
    
    # Try using GPU-enabled Python environment first
    gpu_python = "/mnt/bigdisk/smart_transcribe_webapp/app/venv/bin/python3"
    if os.path.exists(gpu_python):
        logger.info(f"Using GPU-enabled Python at {gpu_python}")
        return _process_with_gpu_python(audio_file_path, language, progress_callback, gpu_python)
    
    try:
        from faster_whisper import WhisperModel
        
        # Detect CUDA availability and use GPU if available
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"
        except ImportError:
            # torch not available, use CPU for safety
            device = "cpu"
            compute_type = "int8"
            logger.info("torch module not found, using CPU")
        
        logger.info(f"Using device: {device} with compute_type: {compute_type}")
        
        # Initialize the model (using 'base' for better performance/accuracy balance)
        try:
            model = WhisperModel("base", device=device, compute_type=compute_type)
        except Exception as e:
            # If GPU initialization fails, fall back to CPU
            if device == "cuda":
                logger.warning(f"GPU initialization failed: {str(e)}, falling back to CPU")
                device = "cpu"
                compute_type = "int8"
                model = WhisperModel("base", device=device, compute_type=compute_type)
            else:
                raise
        
        # Convert language code if needed
        whisper_language = language if language != 'auto' else None
        
        start_time = time.time()
        segments, info = model.transcribe(
            audio_file_path, 
            language=whisper_language,
            task="transcribe"
        )
        
        # Extract text and segments, updating progress as we go
        transcription_text = ""
        segment_list = []
        total_duration = info.duration if hasattr(info, 'duration') else None
        
        for segment in segments:
            transcription_text += segment.text + " "
            segment_list.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            })
            
            # Report progress if callback provided
            if progress_callback and total_duration:
                progress_callback(segment.end, total_duration)
        
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

def _process_with_gpu_python(audio_file_path, language='en', progress_callback=None, python_path="/mnt/bigdisk/smart_transcribe_webapp/app/venv/bin/python3"):
    """Process audio file using GPU-enabled Python environment"""
    import subprocess
    import json
    
    logger.info(f"Processing with GPU Python: {python_path}")
    
    # Create a temporary Python script to run transcription
    script = f'''
import sys
import json
from faster_whisper import WhisperModel

audio_file = sys.argv[1]
language = sys.argv[2]

# Load model with GPU
model = WhisperModel("base", device="cuda", compute_type="float16")

# Transcribe
segments, info = model.transcribe(audio_file, language=language if language != "auto" else None)

# Collect results
transcription_text = ""
segment_list = []
for segment in segments:
    transcription_text += segment.text + " "
    segment_list.append({{
        "start": segment.start,
        "end": segment.end,
        "text": segment.text
    }})

result = {{
    "text": transcription_text.strip(),
    "segments": segment_list,
    "language": info.language,
    "duration": info.duration
}}

print(json.dumps(result))
'''
    
    # Write script to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script)
        script_path = f.name
    
    try:
        # Run with GPU Python
        result = subprocess.run(
            [python_path, script_path, audio_file_path, language],
            capture_output=True,
            text=True,
            timeout=3600
        )
        
        if result.returncode != 0:
            raise Exception(f"GPU transcription failed: {result.stderr}")
        
        # Parse result
        result_data = json.loads(result.stdout.strip())
        
        # Call progress callback with final duration if provided
        if progress_callback and result_data.get('duration'):
            progress_callback(result_data['duration'], result_data['duration'])
        
        logger.info(f"GPU transcription completed successfully")
        return result_data
        
    finally:
        # Clean up temp script
        os.unlink(script_path)