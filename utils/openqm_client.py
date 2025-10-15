import logging
import json
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

# OpenQM Save Service Configuration (running on mv1 Windows server)
OPENQM_SERVICE_URL = "http://10.1.34.103:5001"
OPENQM_ACCOUNT = "LCS"
OPENQM_FILE = "TRANSCRIPT"

def save_transcript_to_openqm(transcript_data, summary_data=None):
    """
    Save transcript and optional summary to OpenQM database via mv1 service
    
    Args:
        transcript_data (dict): Transcript data containing text, metadata, etc.
        summary_data (dict): Optional summary/LLM processed data
    
    Returns:
        dict: Result of save operation
    """
    try:
        # Build payload for OpenQM service on mv1
        payload = {
            'transcript_data': {
                'text': transcript_data.get('text', ''),
                'source_type': transcript_data.get('source_type', 'unknown'),
                'source_url': transcript_data.get('source_url', ''),
                'language': transcript_data.get('language', 'en'),
                'duration': transcript_data.get('duration', 0),
                'file_name': transcript_data.get('file_name', '')
            }
        }
        
        # Add LLM data if available
        if summary_data:
            payload['llm_data'] = {
                'prompt': summary_data.get('prompt', ''),
                'processed_text': summary_data.get('processed_text', ''),
                'model': summary_data.get('model', ''),
                'processing_type': summary_data.get('processing_type', '')
            }
        
        logger.info(f"Sending transcript to OpenQM service at {OPENQM_SERVICE_URL}")
        
        # Call the OpenQM save service on mv1
        response = requests.post(
            f"{OPENQM_SERVICE_URL}/save-transcript",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"OpenQM save successful: {result.get('record_id')}")
            return result
        else:
            error_msg = f"OpenQM service returned {response.status_code}: {response.text}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
            
    except requests.exceptions.ConnectionError:
        error_msg = f"Cannot connect to OpenQM service at {OPENQM_SERVICE_URL}. Is the service running on mv1?"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }
    except Exception as e:
        error_msg = f"Error calling OpenQM service: {str(e)}"
        logger.error(error_msg)
        return {
            'success': False,
            'error': error_msg
        }


def export_to_json_for_openqm(record_data, output_file=None):
    """
    Export record data to JSON file for manual import to OpenQM
    
    Args:
        record_data (dict): Record data
        output_file (str): Output file path (optional)
    
    Returns:
        str: JSON string or file path
    """
    try:
        json_data = json.dumps(record_data, indent=2)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(json_data)
            logger.info(f"Exported record to {output_file}")
            return output_file
        else:
            return json_data
            
    except Exception as e:
        logger.error(f"Error exporting to JSON: {str(e)}")
        return None

def test_openqm_connection():
    """
    Test connection to OpenQM save service on mv1
    
    Returns:
        dict: Connection status
    """
    try:
        # Try to connect to OpenQM service on mv1
        response = requests.get(
            f"{OPENQM_SERVICE_URL}/health",
            timeout=5
        )
        
        if response.status_code == 200:
            return {
                'success': True,
                'message': f'OpenQM service is running on mv1',
                'service_url': OPENQM_SERVICE_URL,
                'account': OPENQM_ACCOUNT,
                'file': OPENQM_FILE
            }
        else:
            return {
                'success': False,
                'error': f'OpenQM service returned status {response.status_code}',
                'suggestion': 'Check if the service is running on mv1'
            }
    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'error': f'Cannot connect to OpenQM service at {OPENQM_SERVICE_URL}',
            'suggestion': 'Start the openqm_service.py on mv1 Windows server'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Connection error: {str(e)}',
            'suggestion': 'Verify mv1 server is accessible and service is running'
        }

def get_openqm_config():
    """
    Get current OpenQM configuration
    
    Returns:
        dict: Configuration details
    """
    return {
        'service_url': OPENQM_SERVICE_URL,
        'account': OPENQM_ACCOUNT,
        'file': OPENQM_FILE,
        'method': 'REST API via mv1 Windows server'
    }
