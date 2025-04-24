import requests
import logging
import os
import json

logger = logging.getLogger(__name__)

# Whisper service configuration
WHISPER_SERVICE_URL = "http://10.0.10.1/v1/audio/transcriptions"  # Adjust the endpoint as needed

def send_to_whisper(audio_file_path):
    """
    Send an audio file to the faster-whisper service for transcription
    
    Args:
        audio_file_path (str): Path to the audio file (WAV format)
    
    Returns:
        dict: The transcription result from the whisper service
        
    Raises:
        Exception: If the transcription request fails
    """
    if not os.path.exists(audio_file_path):
        raise FileNotFoundError(f"Audio file not found at {audio_file_path}")
    
    try:
        logger.debug(f"Sending file {audio_file_path} to Whisper service at {WHISPER_SERVICE_URL}")
        
        with open(audio_file_path, 'rb') as audio_file:
            files = {
                'file': (os.path.basename(audio_file_path), audio_file, 'audio/wav')
            }
            
            # You can add additional parameters as needed by the service
            data = {
                'model': 'whisper-1',  # Assuming this is the model name
                'language': 'en'       # English language, change as needed
            }
            
            response = requests.post(
                WHISPER_SERVICE_URL,
                files=files,
                data=data,
                timeout=300  # 5 minute timeout for large files
            )
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            logger.debug(f"Transcription successful: {result}")
            return result
        else:
            logger.error(f"Transcription failed with status code {response.status_code}: {response.text}")
            raise Exception(f"Transcription service returned error: {response.status_code} {response.text}")
            
    except requests.RequestException as e:
        logger.error(f"Network error when connecting to Whisper service: {str(e)}")
        raise Exception(f"Network error when connecting to Whisper service: {str(e)}")
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse response from Whisper service: {str(e)}")
        raise Exception(f"Failed to parse response from Whisper service: {str(e)}")
        
    except Exception as e:
        logger.error(f"Unexpected error during transcription: {str(e)}")
        raise Exception(f"Unexpected error during transcription: {str(e)}")
