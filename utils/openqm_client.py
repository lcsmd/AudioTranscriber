import requests
import logging
import json
import socket
from datetime import datetime

logger = logging.getLogger(__name__)

# OpenQM server configuration
OPENQM_SERVER = "10.1.34.103"
OPENQM_PORT = 8181  # Default REST API port, adjust if needed
OPENQM_REST_URL = f"http://{OPENQM_SERVER}:{OPENQM_PORT}"

# Database configuration
OPENQM_ACCOUNT = "LCS"  # Account/database name
OPENQM_USERNAME = "lawr"
OPENQM_PASSWORD = "apgar-66"
OPENQM_FILE = "TRANSCRIPT"  # File/table name

def save_transcript_to_openqm(transcript_data, summary_data=None):
    """
    Save transcript and optional summary to OpenQM database
    
    Args:
        transcript_data (dict): Transcript data containing text, metadata, etc.
        summary_data (dict): Optional summary/LLM processed data
    
    Returns:
        dict: Result of save operation
    """
    try:
        # Generate unique record ID using timestamp
        record_id = f"TRANS_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Build record data structure
        record = {
            'ID': record_id,
            'TIMESTAMP': datetime.now().isoformat(),
            'ORIGINAL_TEXT': transcript_data.get('text', ''),
            'SOURCE_TYPE': transcript_data.get('source_type', 'unknown'),
            'SOURCE_URL': transcript_data.get('source_url', ''),
            'LANGUAGE': transcript_data.get('language', 'en'),
            'DURATION': transcript_data.get('duration', 0),
            'FILE_NAME': transcript_data.get('file_name', ''),
        }
        
        # Add LLM processing data if available
        if summary_data:
            record['HAS_LLM_PROCESSING'] = 'Y'
            record['LLM_PROMPT'] = summary_data.get('prompt', '')  # User's instruction to LLM
            record['LLM_RESPONSE'] = summary_data.get('processed_text', '')  # LLM's response
            record['LLM_MODEL'] = summary_data.get('model', '')
            record['PROCESSING_TYPE'] = summary_data.get('processing_type', '')
        else:
            record['HAS_LLM_PROCESSING'] = 'N'
        
        # Add any additional metadata
        if 'metadata' in transcript_data:
            record['METADATA'] = json.dumps(transcript_data['metadata'])
        
        logger.info(f"Attempting to save record {record_id} to OpenQM")
        
        # Try REST API method first
        result = _save_via_rest_api(record)
        
        if result['success']:
            return result
        
        # If REST fails, try alternative methods
        logger.warning(f"REST API save failed: {result.get('error')}")
        
        # Return the record data for manual saving or alternative method
        return {
            'success': False,
            'error': 'OpenQM REST API not available. Record data prepared but not saved.',
            'record_id': record_id,
            'record_data': record,
            'alternative_methods': [
                'Use OpenQM UniObjects for direct connection',
                'Use ODBC connection',
                'Manually import JSON record',
                'Use OpenQM telnet/socket interface'
            ]
        }
        
    except Exception as e:
        error_msg = f"Error saving to OpenQM: {str(e)}"
        logger.error(error_msg)
        return {'success': False, 'error': error_msg}

def _save_via_rest_api(record):
    """
    Save record using OpenQM REST API
    
    Args:
        record (dict): Record data to save
    
    Returns:
        dict: Result of save operation
    """
    try:
        # Construct REST API endpoint
        # Adjust based on your OpenQM REST API configuration
        endpoint = f"{OPENQM_REST_URL}/api/write"
        
        payload = {
            'account': OPENQM_ACCOUNT,
            'username': OPENQM_USERNAME,
            'password': OPENQM_PASSWORD,
            'file': OPENQM_FILE,
            'record_id': record['ID'],
            'data': record
        }
        
        response = requests.post(
            endpoint,
            json=payload,
            auth=(OPENQM_USERNAME, OPENQM_PASSWORD) if OPENQM_USERNAME else None,
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully saved record {record['ID']} to OpenQM")
            return {
                'success': True,
                'record_id': record['ID'],
                'message': 'Record saved to OpenQM'
            }
        else:
            return {
                'success': False,
                'error': f'OpenQM API returned status {response.status_code}: {response.text}'
            }
            
    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'error': f'Cannot connect to OpenQM REST API at {OPENQM_REST_URL}'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'REST API error: {str(e)}'
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
    Test connection to OpenQM server
    
    Returns:
        dict: Connection status
    """
    try:
        # Try REST API
        response = requests.get(f"{OPENQM_REST_URL}/api/ping", timeout=5)
        if response.status_code == 200:
            return {
                'success': True,
                'message': 'Successfully connected to OpenQM REST API',
                'url': OPENQM_REST_URL,
                'method': 'REST API'
            }
    except:
        pass
    
    # Try socket connection
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((OPENQM_SERVER, OPENQM_PORT))
        sock.close()
        
        if result == 0:
            return {
                'success': True,
                'message': f'OpenQM server is reachable at {OPENQM_SERVER}:{OPENQM_PORT}',
                'method': 'Socket',
                'note': 'Configure REST API or UniObjects for data operations'
            }
    except:
        pass
    
    return {
        'success': False,
        'error': f'Cannot connect to OpenQM at {OPENQM_SERVER}:{OPENQM_PORT}',
        'suggestion': 'Verify OpenQM server is running and port/IP are correct'
    }

def get_openqm_config():
    """
    Get current OpenQM configuration
    
    Returns:
        dict: Configuration details
    """
    return {
        'server': OPENQM_SERVER,
        'port': OPENQM_PORT,
        'rest_url': OPENQM_REST_URL,
        'account': OPENQM_ACCOUNT,
        'file': OPENQM_FILE
    }
