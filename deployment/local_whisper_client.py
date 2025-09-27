# Local deployment version of whisper_client.py
# This version is optimized for local Ubuntu server deployment where faster-whisper is installed locally

import os
import subprocess
import tempfile
import uuid
import logging
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Local faster-whisper configuration
LOCAL_WHISPER_SCRIPT = "/mnt/bigdisk/projects/faster-whisper-gpu/smart_transcribe.py"
LOCAL_WHISPER_FALLBACK = True  # Use local faster-whisper if script not available

class LocalWhisperClient:
    """Whisper client optimized for local Ubuntu server deployment"""
    
    def __init__(self):
        self.script_path = LOCAL_WHISPER_SCRIPT
        self.use_local_fallback = LOCAL_WHISPER_FALLBACK
        
    def transcribe_audio(self, audio_file_path: str, language: str = 'en') -> Dict[str, Any]:
        """
        Transcribe audio using local faster-whisper installation
        
        Args:
            audio_file_path: Path to the audio file
            language: Language code for transcription
            
        Returns:
            Dictionary containing transcription results
        """
        try:
            # Try using the custom script first
            if os.path.exists(self.script_path):
                return self._process_with_script(audio_file_path, language)
            elif self.use_local_fallback:
                return self._process_with_local_whisper(audio_file_path, language)
            else:
                raise Exception("No faster-whisper processing method available")
                
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            return {
                'status': 'error',
                'message': f'Transcription failed: {str(e)}',
                'text': '',
                'segments': []
            }
    
    def _process_with_script(self, audio_file_path: str, language: str) -> Dict[str, Any]:
        """Process audio using the custom faster-whisper script"""
        try:
            logger.info(f"Processing audio with custom script: {self.script_path}")
            
            # Create temporary output file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                output_file = temp_file.name
            
            # Run the faster-whisper script
            cmd = [
                "python3", self.script_path,
                "--input", audio_file_path,
                "--output", output_file,
                "--language", language,
                "--model", "base"  # Can be configured
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"Script failed: {result.stderr}")
            
            # Read the output
            with open(output_file, 'r', encoding='utf-8') as f:
                transcription_text = f.read().strip()
            
            # Clean up
            os.unlink(output_file)
            
            logger.info("Transcription completed successfully with custom script")
            return {
                'status': 'success',
                'text': transcription_text,
                'segments': self._parse_segments(transcription_text),
                'language': language
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Transcription timed out")
            return {
                'status': 'error',
                'message': 'Transcription timed out',
                'text': '',
                'segments': []
            }
        except Exception as e:
            logger.error(f"Custom script processing failed: {str(e)}")
            # Fall back to local whisper if available
            if self.use_local_fallback:
                return self._process_with_local_whisper(audio_file_path, language)
            raise
    
    def _process_with_local_whisper(self, audio_file_path: str, language: str) -> Dict[str, Any]:
        """Process audio using local faster-whisper installation"""
        try:
            logger.info("Processing audio with local faster-whisper")
            
            from faster_whisper import WhisperModel
            
            # Initialize model (use CPU for compatibility, GPU if available)
            try:
                # Try GPU first
                model = WhisperModel("base", device="cuda", compute_type="float16")
                logger.info("Using GPU for transcription")
            except:
                # Fall back to CPU
                model = WhisperModel("base", device="cpu", compute_type="int8")
                logger.info("Using CPU for transcription")
            
            # Convert language code for whisper
            whisper_language = self._convert_language_code(language)
            
            # Transcribe
            segments, info = model.transcribe(
                audio_file_path, 
                language=whisper_language, 
                task="transcribe"
            )
            
            # Collect results
            transcription_text = ""
            segment_list = []
            
            for segment in segments:
                transcription_text += segment.text + " "
                segment_list.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text.strip()
                })
            
            logger.info("Local transcription completed successfully")
            return {
                'status': 'success',
                'text': transcription_text.strip(),
                'segments': segment_list,
                'language': info.language,
                'confidence': info.language_probability
            }
            
        except ImportError:
            logger.error("faster-whisper not installed locally")
            return {
                'status': 'error',
                'message': 'faster-whisper not installed. Please install with: pip install faster-whisper',
                'text': '',
                'segments': []
            }
        except Exception as e:
            logger.error(f"Local processing failed: {str(e)}")
            return {
                'status': 'error',
                'message': f'Local transcription failed: {str(e)}',
                'text': '',
                'segments': []
            }
    
    def _convert_language_code(self, language: str) -> str:
        """Convert language code to whisper format"""
        language_map = {
            'en': 'en',
            'es': 'es', 
            'fr': 'fr',
            'de': 'de',
            'it': 'it',
            'pt': 'pt',
            'ru': 'ru',
            'ja': 'ja',
            'ko': 'ko',
            'zh': 'zh'
        }
        return language_map.get(language, 'en')
    
    def _parse_segments(self, text: str) -> list:
        """Parse text into segments (basic implementation)"""
        # Simple sentence-based segmentation
        sentences = text.split('. ')
        segments = []
        
        for i, sentence in enumerate(sentences):
            if sentence.strip():
                segments.append({
                    'start': i * 3.0,  # Approximate timing
                    'end': (i + 1) * 3.0,
                    'text': sentence.strip()
                })
        
        return segments

# Initialize the client
whisper_client = LocalWhisperClient()

# Main transcription function to maintain compatibility
def transcribe_audio(audio_file_path: str, language: str = 'en') -> Dict[str, Any]:
    """Main transcription function for compatibility with existing code"""
    return whisper_client.transcribe_audio(audio_file_path, language)