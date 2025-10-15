import logging
import json
from datetime import datetime

# Import QMClient Python library
try:
    import qmclient as qm
    QMCLIENT_AVAILABLE = True
except ImportError:
    QMCLIENT_AVAILABLE = False
    print("Warning: qmclient module not found. OpenQM functionality will be limited.")

logger = logging.getLogger(__name__)

# OpenQM server configuration
OPENQM_SERVER = "10.1.34.103"
OPENQM_PORT = 4243  # Default QMClient port
OPENQM_ACCOUNT = "LCS"
OPENQM_USERNAME = "lawr"
OPENQM_PASSWORD = "apgar-66"
OPENQM_FILE = "TRANSCRIPT"

# QM field/value mark characters
FM = chr(254)  # Field Mark
VM = chr(253)  # Value Mark
SM = chr(252)  # Subvalue Mark

def save_transcript_to_openqm(transcript_data, summary_data=None):
    """
    Save transcript and optional summary to OpenQM database using QMClient
    
    Args:
        transcript_data (dict): Transcript data containing text, metadata, etc.
        summary_data (dict): Optional summary/LLM processed data
    
    Returns:
        dict: Result of save operation
    """
    if not QMCLIENT_AVAILABLE:
        return {
            'success': False,
            'error': 'QMClient library not available. Install qmclient.py to enable OpenQM integration.'
        }
    
    session = None
    fno = None
    
    try:
        # Generate unique record ID using timestamp
        record_id = f"TRANS_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        logger.info(f"Connecting to OpenQM server {OPENQM_SERVER}:{OPENQM_PORT}")
        
        # Connect to OpenQM server
        session = qm.Connect(OPENQM_SERVER, OPENQM_PORT, OPENQM_USERNAME, OPENQM_PASSWORD, OPENQM_ACCOUNT)
        
        if not session:
            return {
                'success': False,
                'error': f'Failed to connect to OpenQM at {OPENQM_SERVER}:{OPENQM_PORT}'
            }
        
        logger.info(f"Connected to OpenQM. Opening file {OPENQM_FILE}")
        
        # Open the TRANSCRIPT file
        fno = qm.Open(OPENQM_FILE)
        
        if fno < 0:
            qm.Disconnect()
            return {
                'success': False,
                'error': f'Failed to open file {OPENQM_FILE}. Error code: {qm.Status()}'
            }
        
        # Build record with field marks between fields
        fields = []
        fields.append(datetime.now().isoformat())  # Field 1: TIMESTAMP
        fields.append(transcript_data.get('text', ''))  # Field 2: ORIGINAL_TEXT
        fields.append(transcript_data.get('source_type', 'unknown'))  # Field 3: SOURCE_TYPE
        fields.append(transcript_data.get('source_url', ''))  # Field 4: SOURCE_URL
        fields.append(transcript_data.get('language', 'en'))  # Field 5: LANGUAGE
        fields.append(str(transcript_data.get('duration', 0)))  # Field 6: DURATION
        fields.append(transcript_data.get('file_name', ''))  # Field 7: FILE_NAME
        
        # Add LLM processing fields if available
        if summary_data:
            fields.append('Y')  # Field 8: HAS_LLM_PROCESSING
            fields.append(summary_data.get('prompt', ''))  # Field 9: LLM_PROMPT
            fields.append(summary_data.get('processed_text', ''))  # Field 10: LLM_RESPONSE
            fields.append(summary_data.get('model', ''))  # Field 11: LLM_MODEL
            fields.append(summary_data.get('processing_type', ''))  # Field 12: PROCESSING_TYPE
        else:
            fields.append('N')  # Field 8: HAS_LLM_PROCESSING
            fields.append('')  # Field 9: LLM_PROMPT
            fields.append('')  # Field 10: LLM_RESPONSE
            fields.append('')  # Field 11: LLM_MODEL
            fields.append('')  # Field 12: PROCESSING_TYPE
        
        # Join fields with field marks
        record_data = FM.join(fields)
        
        logger.info(f"Writing record {record_id} to OpenQM")
        
        # Write the record
        qm.Write(fno, record_id, record_data)
        
        # Check status
        status = qm.Status()
        if status == 0:  # SV_OK
            logger.info(f"Successfully saved record {record_id} to OpenQM")
            result = {
                'success': True,
                'record_id': record_id,
                'message': f'Record saved to OpenQM file {OPENQM_FILE}'
            }
        else:
            result = {
                'success': False,
                'error': f'Write failed with status code {status}'
            }
        
        # Close file and disconnect
        if fno is not None:
            qm.Close(fno)
        if session is not None:
            qm.Disconnect()
        
        return result
        
    except Exception as e:
        error_msg = f"Error saving to OpenQM: {str(e)}"
        logger.error(error_msg)
        
        # Clean up connection
        try:
            if fno is not None:
                qm.Close(fno)
            if session is not None:
                qm.Disconnect()
        except:
            pass
        
        return {'success': False, 'error': error_msg}


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
    Test connection to OpenQM server using QMClient
    
    Returns:
        dict: Connection status
    """
    if not QMCLIENT_AVAILABLE:
        return {
            'success': False,
            'error': 'QMClient library not available',
            'suggestion': 'Install qmclient.py to enable OpenQM integration'
        }
    
    try:
        # Try to connect using QMClient
        session = qm.Connect(OPENQM_SERVER, OPENQM_PORT, OPENQM_USERNAME, OPENQM_PASSWORD, OPENQM_ACCOUNT)
        
        if session:
            qm.Disconnect()
            return {
                'success': True,
                'message': f'Successfully connected to OpenQM at {OPENQM_SERVER}:{OPENQM_PORT}',
                'account': OPENQM_ACCOUNT,
                'method': 'QMClient'
            }
        else:
            return {
                'success': False,
                'error': f'Failed to connect to OpenQM at {OPENQM_SERVER}:{OPENQM_PORT}',
                'suggestion': 'Check server address, port, and credentials'
            }
    except Exception as e:
        return {
            'success': False,
            'error': f'Connection error: {str(e)}',
            'suggestion': 'Verify OpenQM server is running and accessible'
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
        'account': OPENQM_ACCOUNT,
        'username': OPENQM_USERNAME,
        'file': OPENQM_FILE,
        'qmclient_available': QMCLIENT_AVAILABLE
    }
