import requests
import logging
import json

logger = logging.getLogger(__name__)

# Ollama server configuration
OLLAMA_SERVER = "10.1.10.20"
OLLAMA_PORT = 11434
OLLAMA_URL = f"http://{OLLAMA_SERVER}:{OLLAMA_PORT}"

# Default model to use
DEFAULT_MODEL = "llama2"

def get_available_models():
    """
    Get list of available models from Ollama
    
    Returns:
        list: List of available model names
    """
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            logger.info(f"Available Ollama models: {models}")
            return models
        else:
            logger.error(f"Failed to get models: {response.status_code}")
            return [DEFAULT_MODEL]
    except Exception as e:
        logger.error(f"Error getting Ollama models: {str(e)}")
        return [DEFAULT_MODEL]

def process_text_with_llm(text, processing_type='summarize', custom_prompt=None, model=None):
    """
    Process text using Ollama LLM
    
    Args:
        text (str): The text to process
        processing_type (str): Type of processing - 'summarize', 'critique', 'expand', 'explain', 'custom'
        custom_prompt (str): Custom prompt for 'custom' processing type
        model (str): Ollama model to use (defaults to DEFAULT_MODEL)
    
    Returns:
        dict: Result containing processed text and metadata
    """
    if not text or not text.strip():
        return {'success': False, 'error': 'No text provided'}
    
    # Use default model if none specified
    if not model:
        model = DEFAULT_MODEL
    
    # Build the system prompt based on processing type
    prompts = {
        'summarize': {
            'system': 'You are a helpful assistant that creates clear, concise summaries.',
            'user': f'Please provide a comprehensive summary of the following text:\n\n{text}'
        },
        'critique': {
            'system': 'You are a thoughtful critic who provides constructive analysis and feedback.',
            'user': f'Please provide a detailed critique of the following text, including strengths, weaknesses, and suggestions for improvement:\n\n{text}'
        },
        'expand': {
            'system': 'You are a creative writer who expands ideas with depth and detail.',
            'user': f'Please expand on the following text with additional details, examples, and context:\n\n{text}'
        },
        'explain': {
            'system': 'You are a clear educator who explains complex topics in simple terms.',
            'user': f'Please explain the following text in clear, easy-to-understand language:\n\n{text}'
        },
        'custom': {
            'system': 'You are a helpful AI assistant.',
            'user': f'{custom_prompt}\n\n{text}' if custom_prompt else text
        }
    }
    
    if processing_type not in prompts:
        processing_type = 'summarize'
    
    prompt_config = prompts[processing_type]
    
    try:
        logger.info(f"Processing text with Ollama ({model}) - type: {processing_type}")
        
        # Call Ollama API
        payload = {
            'model': model,
            'prompt': f"{prompt_config['system']}\n\n{prompt_config['user']}",
            'stream': False
        }
        
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=300  # 5 minutes timeout for large texts
        )
        
        if response.status_code == 200:
            result = response.json()
            processed_text = result.get('response', '')
            
            logger.info(f"Successfully processed text with Ollama")
            
            return {
                'success': True,
                'original_text': text,
                'processed_text': processed_text,
                'processing_type': processing_type,
                'model': model,
                'metadata': {
                    'model': result.get('model'),
                    'created_at': result.get('created_at'),
                    'total_duration': result.get('total_duration'),
                    'load_duration': result.get('load_duration'),
                    'prompt_eval_count': result.get('prompt_eval_count'),
                    'eval_count': result.get('eval_count')
                }
            }
        else:
            error_msg = f"Ollama API error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
            
    except requests.exceptions.Timeout:
        error_msg = "Ollama request timed out after 5 minutes"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}
    except Exception as e:
        error_msg = f"Error processing text with Ollama: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

def test_ollama_connection():
    """
    Test connection to Ollama server
    
    Returns:
        dict: Connection status and available models
    """
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = get_available_models()
            return {
                'success': True,
                'message': 'Successfully connected to Ollama',
                'url': OLLAMA_URL,
                'models': models
            }
        else:
            return {
                'success': False,
                'error': f'Ollama server returned status {response.status_code}',
                'url': OLLAMA_URL
            }
    except Exception as e:
        return {
            'success': False,
            'error': f'Cannot connect to Ollama: {str(e)}',
            'url': OLLAMA_URL
        }
