import os
import logging
import tempfile
import uuid
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from utils.audio_converter import convert_mp3_to_wav
from utils.whisper_client import send_to_whisper

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure logging
logger = logging.getLogger(__name__)

# Configure upload folder
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'mp3', 'wav'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB limit

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['audio_file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        # Generate a unique filename
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        
        # Save the uploaded file temporarily
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        try:
            # If the file is mp3, convert it to wav
            if file_extension == 'mp3':
                logger.debug(f"Converting {filepath} from MP3 to WAV")
                wav_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4()}.wav")
                convert_mp3_to_wav(filepath, wav_filepath)
                
                # Remove the original mp3 file
                os.remove(filepath)
                filepath = wav_filepath
            
            # Send the file to the whisper service
            logger.debug(f"Sending {filepath} to Whisper service")
            transcription_result = send_to_whisper(filepath)
            
            # Clean up the audio file
            os.remove(filepath)
            
            return jsonify({
                'success': True, 
                'filename': original_filename,
                'transcription': transcription_result
            })
            
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            # Try to clean up files in case of error
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except:
                pass
            
            return jsonify({'error': f"Error processing file: {str(e)}"}), 500
    
    return jsonify({'error': 'Invalid file type. Only MP3 and WAV files are allowed.'}), 400

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
