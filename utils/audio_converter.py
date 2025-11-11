import subprocess
import logging
import os
import shutil

logger = logging.getLogger(__name__)

# Get the full path to ffmpeg - use environment variable or find it in the system
FFMPEG_PATH = shutil.which('ffmpeg') or os.environ.get('FFMPEG_PATH', 'ffmpeg')

def convert_mp3_to_wav(mp3_path, wav_path):
    """
    Convert an MP3 file to WAV format using ffmpeg
    
    Args:
        mp3_path (str): Path to the MP3 file
        wav_path (str): Path where the WAV file should be saved
    
    Returns:
        bool: True if conversion was successful, False otherwise
        
    Raises:
        Exception: If the conversion fails
    """
    if not os.path.exists(mp3_path):
        raise FileNotFoundError(f"MP3 file not found at {mp3_path}")
    
    try:
        logger.debug(f"Converting {mp3_path} to WAV format at {wav_path}")
        
        # Run ffmpeg command to convert MP3 to WAV
        # -y: Overwrite output file without asking
        # -i: Input file
        # -acodec pcm_s16le: Convert to 16-bit PCM WAV
        # -ar 16000: Set sample rate to 16kHz (common for speech recognition)
        result = subprocess.run(
            [FFMPEG_PATH, '-y', '-i', mp3_path, '-acodec', 'pcm_s16le', '-ar', '16000', wav_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        logger.debug("Conversion successful")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg conversion failed: {e.stderr.decode()}")
        raise Exception(f"Failed to convert MP3 to WAV: {e.stderr.decode()}")
    
    except Exception as e:
        logger.error(f"Error during conversion: {str(e)}")
        raise Exception(f"Error during conversion: {str(e)}")
