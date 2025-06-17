import os
import tempfile
import logging
from gtts import gTTS
import pyttsx3
import io

logger = logging.getLogger(__name__)

# Available voices configuration
AVAILABLE_VOICES = {
    # American English Voices
    'google_en_us_female': {
        'name': 'Google US English (Female)',
        'engine': 'gtts',
        'lang': 'en',
        'tld': 'com',
        'slow': False
    },
    'google_en_us_male': {
        'name': 'Google US English (Male)',
        'engine': 'gtts',
        'lang': 'en',
        'tld': 'com',
        'slow': True  # Slower speech for male-sounding effect
    },
    'google_en_us_wavenet_a': {
        'name': 'US WaveNet A (Female)',
        'engine': 'gtts',
        'lang': 'en',
        'tld': 'us',
        'slow': False
    },
    'google_en_us_wavenet_b': {
        'name': 'US WaveNet B (Male)',
        'engine': 'gtts',
        'lang': 'en',
        'tld': 'us',
        'slow': True
    },
    'google_en_us_wavenet_c': {
        'name': 'US WaveNet C (Female)',
        'engine': 'gtts',
        'lang': 'en',
        'tld': 'com',
        'slow': False
    },
    'google_en_us_wavenet_d': {
        'name': 'US WaveNet D (Male)',
        'engine': 'gtts',
        'lang': 'en',
        'tld': 'com',
        'slow': True
    },
    'google_en_us_neural2_a': {
        'name': 'US Neural2 A (Female)',
        'engine': 'gtts',
        'lang': 'en',
        'tld': 'us',
        'slow': False
    },
    'google_en_us_neural2_c': {
        'name': 'US Neural2 C (Male)',
        'engine': 'gtts',
        'lang': 'en',
        'tld': 'us',
        'slow': True
    },
    
    # Other English Variants
    'google_en_uk': {
        'name': 'Google English UK (Female)',
        'engine': 'gtts',
        'lang': 'en',
        'tld': 'co.uk',
        'slow': False
    },
    'google_en_au': {
        'name': 'Google English Australia (Female)',
        'engine': 'gtts',
        'lang': 'en',
        'tld': 'com.au',
        'slow': False
    },
    'google_en_ca': {
        'name': 'Google English Canada (Female)',
        'engine': 'gtts',
        'lang': 'en',
        'tld': 'ca',
        'slow': False
    },
    
    # Other Languages with Male/Female Options
    'google_es': {
        'name': 'Google Spanish (Female)',
        'engine': 'gtts',
        'lang': 'es',
        'tld': 'com',
        'slow': False
    },
    'google_es_male': {
        'name': 'Google Spanish (Male)',
        'engine': 'gtts',
        'lang': 'es',
        'tld': 'com.mx',
        'slow': True
    },
    'google_fr': {
        'name': 'Google French (Female)',
        'engine': 'gtts',
        'lang': 'fr',
        'tld': 'com',
        'slow': False
    },
    'google_fr_male': {
        'name': 'Google French (Male)',
        'engine': 'gtts',
        'lang': 'fr',
        'tld': 'ca',
        'slow': True
    },
    'google_de': {
        'name': 'Google German (Female)',
        'engine': 'gtts',
        'lang': 'de',
        'tld': 'com',
        'slow': False
    },
    'google_de_male': {
        'name': 'Google German (Male)',
        'engine': 'gtts',
        'lang': 'de',
        'tld': 'at',
        'slow': True
    },
    
    # System Voices
    'system_default': {
        'name': 'System Default Voice',
        'engine': 'pyttsx3',
        'voice_id': None
    },
    'system_male': {
        'name': 'System Male Voice',
        'engine': 'pyttsx3',
        'voice_type': 'male'
    },
    'system_female': {
        'name': 'System Female Voice',
        'engine': 'pyttsx3',
        'voice_type': 'female'
    }
}

def get_available_voices():
    """
    Get list of available TTS voices
    
    Returns:
        dict: Dictionary of available voices
    """
    return AVAILABLE_VOICES

def text_to_speech_gtts(text, voice_config, output_path):
    """
    Convert text to speech using Google TTS
    
    Args:
        text (str): Text to convert
        voice_config (dict): Voice configuration
        output_path (str): Path to save the audio file
    
    Returns:
        str: Path to the generated audio file
    """
    try:
        logger.debug(f"Converting text to speech using gTTS: {voice_config['name']}")
        
        tts = gTTS(
            text=text,
            lang=voice_config['lang'],
            tld=voice_config.get('tld', 'com'),
            slow=voice_config.get('slow', False)
        )
        
        # Save to a temporary WAV-like file first
        temp_path = output_path.replace('.mp3', '_temp.mp3')
        tts.save(temp_path)
        
        # Move to final destination
        os.rename(temp_path, output_path)
        
        logger.debug(f"Successfully generated audio file: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating speech with gTTS: {str(e)}")
        raise Exception(f"Failed to generate speech: {str(e)}")

def text_to_speech_pyttsx3(text, voice_config, output_path):
    """
    Convert text to speech using pyttsx3 (system TTS)
    
    Args:
        text (str): Text to convert
        voice_config (dict): Voice configuration
        output_path (str): Path to save the audio file
    
    Returns:
        str: Path to the generated audio file
    """
    try:
        logger.debug(f"Converting text to speech using pyttsx3: {voice_config['name']}")
        
        engine = pyttsx3.init()
        
        # Configure voice based on type or ID
        voices = engine.getProperty('voices')
        
        if voice_config.get('voice_type'):
            # Select voice by gender preference
            selected_voice = None
            for voice in voices:
                voice_name = voice.name.lower()
                if voice_config['voice_type'] == 'male' and any(keyword in voice_name for keyword in ['male', 'david', 'mark', 'alex']):
                    selected_voice = voice.id
                    break
                elif voice_config['voice_type'] == 'female' and any(keyword in voice_name for keyword in ['female', 'zira', 'hazel', 'samantha']):
                    selected_voice = voice.id
                    break
            
            if selected_voice:
                engine.setProperty('voice', selected_voice)
        elif voice_config.get('voice_id'):
            # Configure voice by specific ID
            for voice in voices:
                if voice_config['voice_id'] in voice.id:
                    engine.setProperty('voice', voice.id)
                    break
        
        # Set speech rate and volume
        engine.setProperty('rate', 150)  # Speed of speech
        engine.setProperty('volume', 0.9)  # Volume level (0.0 to 1.0)
        
        # Save to file
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        
        logger.debug(f"Successfully generated audio file: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating speech with pyttsx3: {str(e)}")
        raise Exception(f"Failed to generate speech: {str(e)}")

def convert_text_to_speech(text, voice_id='google_en', output_dir=None):
    """
    Convert text to speech using the specified voice
    
    Args:
        text (str): Text to convert to speech
        voice_id (str): ID of the voice to use
        output_dir (str): Directory to save the audio file
    
    Returns:
        str: Path to the generated audio file
    """
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    
    # Get voice configuration
    if voice_id not in AVAILABLE_VOICES:
        logger.warning(f"Voice {voice_id} not found, using default")
        voice_id = 'google_en'
    
    voice_config = AVAILABLE_VOICES[voice_id]
    
    # Generate output filename
    import uuid
    filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
    output_path = os.path.join(output_dir, filename)
    
    try:
        # Choose the appropriate TTS engine
        if voice_config['engine'] == 'gtts':
            return text_to_speech_gtts(text, voice_config, output_path)
        elif voice_config['engine'] == 'pyttsx3':
            return text_to_speech_pyttsx3(text, voice_config, output_path)
        else:
            raise ValueError(f"Unknown TTS engine: {voice_config['engine']}")
            
    except Exception as e:
        logger.error(f"Error in text-to-speech conversion: {str(e)}")
        raise Exception(f"Text-to-speech conversion failed: {str(e)}")

def get_system_voices():
    """
    Get available system voices (for pyttsx3)
    
    Returns:
        list: List of available system voices
    """
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        
        system_voices = []
        for voice in voices:
            system_voices.append({
                'id': voice.id,
                'name': voice.name,
                'languages': getattr(voice, 'languages', []),
                'gender': getattr(voice, 'gender', 'unknown'),
                'age': getattr(voice, 'age', 'unknown')
            })
        
        engine.stop()
        return system_voices
        
    except Exception as e:
        logger.error(f"Error getting system voices: {str(e)}")
        return []

def validate_text_length(text, max_chars=5000):
    """
    Validate text length for TTS conversion
    
    Args:
        text (str): Text to validate
        max_chars (int): Maximum allowed characters
    
    Returns:
        bool: True if valid, raises exception if too long
    """
    if len(text) > max_chars:
        raise ValueError(f"Text too long ({len(text)} characters). Maximum allowed: {max_chars}")
    
    if not text.strip():
        raise ValueError("Text cannot be empty")
    
    return True