"""
OpenQM Save Service for Windows Server (mv1)
Run this on mv1 (10.1.34.103) where qmclient is already installed

Usage:
  python openqm_service.py

This creates a REST API endpoint that receives transcript data and saves it to OpenQM
"""

from flask import Flask, request, jsonify
import qmclient as qm
from datetime import datetime
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenQM Configuration
OPENQM_ACCOUNT = "LCS"
OPENQM_USERNAME = "lawr"
OPENQM_PASSWORD = "apgar-66"
OPENQM_FILE = "TRANSCRIPT"

# QM field/value mark characters
FM = chr(254)  # Field Mark
VM = chr(253)  # Value Mark

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'service': 'openqm-save-service'})

@app.route('/save-transcript', methods=['POST'])
def save_transcript():
    """
    Save transcript to OpenQM
    
    Expected JSON payload:
    {
        "transcript_data": {
            "text": "transcript text",
            "source_type": "audio|youtube|text|document",
            "source_url": "url if applicable",
            "language": "en",
            "duration": 0,
            "file_name": "filename"
        },
        "llm_data": {  # optional
            "prompt": "user's instruction",
            "processed_text": "AI response",
            "model": "llama3",
            "processing_type": "custom"
        }
    }
    """
    try:
        data = request.json
        transcript_data = data.get('transcript_data', {})
        llm_data = data.get('llm_data')
        
        # Generate unique record ID
        record_id = f"TRANS_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        logger.info(f"Connecting to OpenQM locally...")
        
        # Connect to local OpenQM server
        session = qm.Connect("localhost", 4243, OPENQM_USERNAME, OPENQM_PASSWORD, OPENQM_ACCOUNT)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Failed to connect to OpenQM'
            }), 500
        
        logger.info(f"Opening file {OPENQM_FILE}")
        
        # Open the TRANSCRIPT file
        fno = qm.Open(OPENQM_FILE)
        
        if fno < 0:
            qm.Disconnect()
            return jsonify({
                'success': False,
                'error': f'Failed to open file {OPENQM_FILE}'
            }), 500
        
        # Build record with field marks
        fields = []
        fields.append(datetime.now().isoformat())  # Field 1: TIMESTAMP
        fields.append(transcript_data.get('text', ''))  # Field 2: ORIGINAL_TEXT
        fields.append(transcript_data.get('source_type', 'unknown'))  # Field 3: SOURCE_TYPE
        fields.append(transcript_data.get('source_url', ''))  # Field 4: SOURCE_URL
        fields.append(transcript_data.get('language', 'en'))  # Field 5: LANGUAGE
        fields.append(str(transcript_data.get('duration', 0)))  # Field 6: DURATION
        fields.append(transcript_data.get('file_name', ''))  # Field 7: FILE_NAME
        
        # Add LLM processing fields if available
        if llm_data:
            fields.append('Y')  # Field 8: HAS_LLM_PROCESSING
            fields.append(llm_data.get('prompt', ''))  # Field 9: LLM_PROMPT
            fields.append(llm_data.get('processed_text', ''))  # Field 10: LLM_RESPONSE
            fields.append(llm_data.get('model', ''))  # Field 11: LLM_MODEL
            fields.append(llm_data.get('processing_type', ''))  # Field 12: PROCESSING_TYPE
        else:
            fields.append('N')  # Field 8: HAS_LLM_PROCESSING
            fields.append('')  # Field 9-12: Empty
            fields.append('')
            fields.append('')
            fields.append('')
        
        # Join fields with field marks
        record_data = FM.join(fields)
        
        logger.info(f"Writing record {record_id} to OpenQM")
        
        # Write the record
        qm.Write(fno, record_id, record_data)
        
        # Check status
        status = qm.Status()
        
        # Close file and disconnect
        qm.Close(fno)
        qm.Disconnect()
        
        if status == 0:  # SV_OK
            logger.info(f"Successfully saved record {record_id}")
            return jsonify({
                'success': True,
                'record_id': record_id,
                'message': f'Record saved to OpenQM file {OPENQM_FILE}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Write failed with status code {status}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("="*60)
    print("OpenQM Save Service for mv1 (10.1.34.103)")
    print("="*60)
    print(f"Account: {OPENQM_ACCOUNT}")
    print(f"File: {OPENQM_FILE}")
    print(f"Starting on http://0.0.0.0:5001")
    print("="*60)
    
    # Run on port 5001 to avoid conflict with other services
    app.run(host='0.0.0.0', port=5001, debug=False)
