import os
import logging
import tempfile
import uuid
import time
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from utils.audio_converter import convert_mp3_to_wav
from utils.whisper_client import send_to_whisper
from models import db, Transcription

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Configure database
db_url = os.environ.get("DATABASE_URL")
if db_url:
    # Log the presence of the DATABASE_URL (without showing the actual value)
    logger.info("DATABASE_URL is set and will be used for the database connection")
    
    # Configure SQLAlchemy
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize the database
    db.init_app(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables created successfully")
else:
    logger.error("DATABASE_URL environment variable is not set!")

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
        file_size = 0
        
        # Create a new transcription record
        transcription = Transcription(
            original_filename=original_filename,
            file_type=file_extension,
            file_size=0,  # Will update this after saving the file
            status='processing'
        )
        db.session.add(transcription)
        db.session.commit()
        
        # Save the uploaded file temporarily
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Update file size
        file_size = os.path.getsize(filepath)
        transcription.file_size = file_size
        db.session.commit()
        
        try:
            start_time = time.time()
            
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
            
            # Calculate processing time
            processing_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
            
            # Update the transcription record
            transcription_text = ""
            if isinstance(transcription_result, dict):
                if "text" in transcription_result:
                    transcription_text = transcription_result["text"]
                elif "transcription" in transcription_result:
                    transcription_text = transcription_result["transcription"]
                else:
                    transcription_text = str(transcription_result)
            else:
                transcription_text = str(transcription_result)
                
            transcription.transcription_text = transcription_text
            transcription.processing_time = processing_time
            transcription.status = 'completed'
            db.session.commit()
            
            # Clean up the audio file
            os.remove(filepath)
            
            return jsonify({
                'success': True, 
                'filename': original_filename,
                'transcription': transcription_result,
                'transcription_id': transcription.id
            })
            
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            
            # Update the transcription record to show the error
            transcription.status = 'failed'
            transcription.error_message = str(e)
            db.session.commit()
            
            # Try to clean up files in case of error
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except:
                pass
            
            return jsonify({'error': f"Error processing file: {str(e)}"}), 500
    
    return jsonify({'error': 'Invalid file type. Only MP3 and WAV files are allowed.'}), 400

@app.route('/history', methods=['GET'])
def transcription_history():
    # Get all completed transcriptions, ordered by most recent first
    transcriptions = Transcription.query.filter_by(status='completed').order_by(Transcription.created_at.desc()).all()
    
    # Convert to a list of dictionaries for the template
    history = [t.to_dict() for t in transcriptions]
    
    # Render the history template
    return render_template('history.html', history=history)

@app.route('/api/history', methods=['GET'])
def api_transcription_history():
    # Get all transcriptions, ordered by most recent first
    transcriptions = Transcription.query.order_by(Transcription.created_at.desc()).all()
    
    # Convert to a list of dictionaries for JSON
    history = [t.to_dict() for t in transcriptions]
    
    return jsonify({'transcriptions': history})

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
