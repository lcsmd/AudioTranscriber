import os
import logging
import tempfile
import uuid
import time
from flask import Flask, render_template, request, jsonify, session, send_file
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from utils.audio_converter import convert_mp3_to_wav
from utils.whisper_client import send_to_whisper
from utils.youtube_processor import is_youtube_url, download_youtube_audio, get_youtube_info, get_youtube_transcript
from utils.document_processor import process_document, get_document_info
from utils.text_to_speech import convert_text_to_speech, get_available_voices
from utils.output_formatter import generate_output_file, get_supported_formats
from utils.llm_processor import process_text_with_llm, get_available_models
from utils.openqm_client import save_transcript_to_openqm, export_to_json_for_openqm
from models import db, Transcription, ProcessingJob

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https

# Enable template auto-reload and disable static file caching for development
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

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
    
    # Create database tables (retry on failure)
    try:
        with app.app_context():
            db.create_all()
            logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        logger.warning("Application will continue without database support")
else:
    logger.warning("DATABASE_URL environment variable is not set! Application will run without database support")

# Configure upload folder
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'mp4', 'mov'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'docx', 'txt'}
ALL_ALLOWED_EXTENSIONS = ALLOWED_AUDIO_EXTENSIONS.union(ALLOWED_DOCUMENT_EXTENSIONS)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB limit

# Configure transcriptions folder for file-based storage
TRANSCRIPTIONS_FOLDER = os.environ.get('TRANSCRIPTIONS_FOLDER', '/var/www/speech-app/transcriptions')
os.makedirs(TRANSCRIPTIONS_FOLDER, exist_ok=True)
logger.info(f"Transcriptions will be saved to: {TRANSCRIPTIONS_FOLDER}")

# Database availability flag
DB_AVAILABLE = False
if db_url:
    try:
        from sqlalchemy import text
        with app.app_context():
            db.session.execute(text('SELECT 1'))
            DB_AVAILABLE = True
            logger.info("✓ Database connection verified - DB_AVAILABLE = True")
    except Exception as e:
        logger.warning(f"✗ Database not available - DB_AVAILABLE = False: {str(e)}")
else:
    logger.warning("✗ No DATABASE_URL configured - DB_AVAILABLE = False")

def allowed_file(filename, file_type='all'):
    if not filename or '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    
    if file_type == 'audio':
        return extension in ALLOWED_AUDIO_EXTENSIONS
    elif file_type == 'document':
        return extension in ALLOWED_DOCUMENT_EXTENSIONS
    else:
        return extension in ALL_ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/suggested-prompts')
def get_suggested_prompts():
    """Load suggested prompts from text file"""
    try:
        prompts = []
        prompts_file = 'suggested_prompts.txt'
        
        if os.path.exists(prompts_file):
            with open(prompts_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        prompts.append(line)
        
        # If no prompts file or empty, return default prompts
        if not prompts:
            prompts = [
                "Summarize this text in 3-5 key points",
                "Create a detailed summary with main themes and supporting details",
                "Provide a critical analysis highlighting strengths, weaknesses, and areas for improvement",
                "Expand on this content with additional context, examples, and detailed explanations",
                "Explain this in simple, easy-to-understand language suitable for a general audience"
            ]
        
        return jsonify({'prompts': prompts})
    
    except Exception as e:
        logger.error(f"Error loading suggested prompts: {str(e)}")
        return jsonify({'prompts': []})

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
        
        # Create a new transcription record (if database available)
        transcription = None
        transcription_id = None
        if DB_AVAILABLE:
            try:
                transcription = Transcription(
                    original_filename=original_filename,
                    file_type=file_extension,
                    file_size=0,  # Will update this after saving the file
                    status='processing'
                )
                db.session.add(transcription)
                db.session.commit()
                transcription_id = transcription.id
            except Exception as e:
                logger.warning(f"Could not save to database: {str(e)}")
        
        # Save the uploaded file temporarily
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        
        # Update file size
        file_size = os.path.getsize(filepath)
        if transcription:
            try:
                transcription.file_size = file_size
                db.session.commit()
            except Exception as e:
                logger.warning(f"Could not update database: {str(e)}")
        
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
                
            if transcription:
                try:
                    transcription.transcription_text = transcription_text
                    transcription.processing_time = processing_time
                    transcription.status = 'completed'
                    db.session.commit()
                except Exception as e:
                    logger.warning(f"Could not update database: {str(e)}")
            
            # Save transcription to file
            try:
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_filename = secure_filename(original_filename.rsplit('.', 1)[0])
                transcription_filename = f"{timestamp}_{safe_filename}.txt"
                transcription_path = os.path.join(TRANSCRIPTIONS_FOLDER, transcription_filename)
                
                with open(transcription_path, 'w', encoding='utf-8') as f:
                    f.write(f"Transcription of: {original_filename}\n")
                    f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Processing time: {processing_time}ms\n")
                    f.write(f"{'-' * 80}\n\n")
                    f.write(transcription_text)
                
                logger.info(f"Transcription saved to: {transcription_path}")
            except Exception as e:
                logger.warning(f"Could not save transcription to file: {str(e)}")
            
            # Clean up the audio file
            os.remove(filepath)
            
            return jsonify({
                'success': True, 
                'filename': original_filename,
                'transcription': transcription_result,
                'transcription_id': transcription_id
            })
            
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            
            # Update the transcription record to show the error
            if transcription:
                try:
                    transcription.status = 'failed'
                    transcription.error_message = str(e)
                    db.session.commit()
                except Exception as db_err:
                    logger.warning(f"Could not update database: {str(db_err)}")
            
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
    if not DB_AVAILABLE:
        return render_template('history.html', history=[], message="Database unavailable")
    
    try:
        # Get all processing jobs, ordered by most recent first
        jobs = ProcessingJob.query.order_by(ProcessingJob.created_at.desc()).all()
        
        # Convert to a list of dictionaries for the template
        history = [job.to_dict() for job in jobs]
        
        # Render the history template
        return render_template('history.html', history=history)
    except Exception as e:
        logger.error(f"Error fetching history: {str(e)}")
        return render_template('history.html', history=[], message="Error loading history")

@app.route('/api/history', methods=['GET'])
def api_transcription_history():
    if not DB_AVAILABLE:
        return jsonify({'jobs': [], 'message': 'Database unavailable'})
    
    try:
        # Get all processing jobs, ordered by most recent first
        jobs = ProcessingJob.query.order_by(ProcessingJob.created_at.desc()).all()
        
        # Convert to a list of dictionaries for JSON
        history = [job.to_dict() for job in jobs]
        
        return jsonify({'jobs': history})
    except Exception as e:
        logger.error(f"Error fetching history: {str(e)}")
        return jsonify({'jobs': [], 'error': str(e)}), 500

# Global dictionary to track processing progress
processing_progress = {}

def process_audio_files_directly(files):
    """Process audio files directly without database/job tracking"""
    from datetime import datetime
    import threading
    
    # Generate a unique job ID for tracking
    job_id = str(uuid.uuid4())
    processing_progress[job_id] = {
        'status': 'processing',
        'progress': 0,
        'message': 'Starting...',
        'result': None,
        'start_time': time.time(),
        'file_duration': None,
        'processed_duration': 0
    }
    
    logger.info(f"Processing {len(files)} audio files directly - Job ID: {job_id}")
    
    # Save files first (outside thread, while files are still open)
    saved_files = []
    for file in files:
        if not file.filename or not allowed_file(file.filename, 'audio'):
            continue
            
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        saved_files.append((filepath, original_filename, file_extension))
    
    # Start processing in background thread
    def process_async():
        all_transcriptions = []
        try:
            processing_progress[job_id]['progress'] = 10
            processing_progress[job_id]['message'] = 'Preparing files...'
    
            total_files = len(saved_files)
            current_file = 0
            
            for filepath, original_filename, file_extension in saved_files:
                current_file += 1
                
                processing_progress[job_id]['progress'] = 20 + (current_file - 1) * 60 // total_files
                processing_progress[job_id]['message'] = f'Processing file {current_file}/{total_files}: {original_filename}'
                
                try:
                    # Convert MP3 to WAV if needed
                    if file_extension == 'mp3':
                        wav_filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4()}.wav")
                        convert_mp3_to_wav(filepath, wav_filepath)
                        os.remove(filepath)
                        filepath = wav_filepath
                    
                    processing_progress[job_id]['message'] = f'Transcribing {current_file}/{total_files}: {original_filename}'
                    
                    # Get audio duration
                    try:
                        import subprocess
                        duration_result = subprocess.run(
                            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                             '-of', 'default=noprint_wrappers=1:nokey=1', filepath],
                            capture_output=True, text=True, timeout=10
                        )
                        if duration_result.returncode == 0:
                            duration_seconds = float(duration_result.stdout.strip())
                            processing_progress[job_id]['file_duration'] = duration_seconds
                            hours = int(duration_seconds // 3600)
                            minutes = int((duration_seconds % 3600) // 60)
                            seconds = int(duration_seconds % 60)
                            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"
                            logger.info(f"Audio duration: {duration_str}")
                    except Exception as e:
                        logger.warning(f"Could not get audio duration: {str(e)}")
                    
                    # Transcribe with progress callback
                    transcribe_start = time.time()
                    
                    def update_transcription_progress(processed_seconds, total_seconds):
                        processing_progress[job_id]['processed_duration'] = processed_seconds
                        if total_seconds > 0:
                            transcribe_progress = (processed_seconds / total_seconds) * 60
                            processing_progress[job_id]['progress'] = 20 + int(transcribe_progress)
                    
                    transcription_result = send_to_whisper(filepath, language='en', progress_callback=update_transcription_progress)
                    processing_time = int((time.time() - transcribe_start) * 1000)
                    
                    # Extract text
                    if isinstance(transcription_result, dict) and 'text' in transcription_result:
                        transcription_text = transcription_result['text']
                    else:
                        transcription_text = str(transcription_result)
                    
                    all_transcriptions.append(transcription_text)
                    
                    processing_progress[job_id]['message'] = f'Saving {current_file}/{total_files}: {original_filename}'
                    
                    # Save to file
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    safe_filename = secure_filename(original_filename.rsplit('.', 1)[0])
                    transcription_filename = f"{timestamp}_{safe_filename}.txt"
                    transcription_path = os.path.join(TRANSCRIPTIONS_FOLDER, transcription_filename)
                    
                    with open(transcription_path, 'w', encoding='utf-8') as f:
                        f.write(f"Transcription of: {original_filename}\n")
                        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"Processing time: {processing_time}ms\n")
                        f.write(f"{'-' * 80}\n\n")
                        f.write(transcription_text)
                    
                    logger.info(f"Audio transcription saved to: {transcription_path}")
                    
                    # Clean up
                    os.remove(filepath)
                    
                except Exception as e:
                    logger.error(f"Error processing {original_filename}: {str(e)}")
                    all_transcriptions.append(f"Error processing {original_filename}: {str(e)}")
                    if os.path.exists(filepath):
                        os.remove(filepath)
            
            result_text = '\n\n'.join(all_transcriptions) if all_transcriptions else "No transcriptions generated"
            
            # Mark as complete
            processing_progress[job_id]['status'] = 'completed'
            processing_progress[job_id]['progress'] = 100
            processing_progress[job_id]['message'] = 'Transcription completed!'
            processing_progress[job_id]['result'] = {'text': result_text}
            
        except Exception as e:
            logger.error(f"Error in async processing: {str(e)}")
            processing_progress[job_id]['status'] = 'failed'
            processing_progress[job_id]['message'] = f'Error: {str(e)}'
    
    # Start background thread
    thread = threading.Thread(target=process_async)
    thread.daemon = True
    thread.start()
    
    # Return job ID for polling
    return jsonify({
        'success': True,
        'job_id': job_id,
        'message': 'Processing started'
    })

def process_youtube_directly(source_url, data):
    """Process YouTube URL directly without database/job tracking"""
    from datetime import datetime
    
    logger.info(f"Processing YouTube URL directly: {source_url}")
    
    youtube_options = data.get('youtubeOptions', {})
    pull_transcript = youtube_options.get('pullTranscript', True)
    # Disable audio transcription due to YouTube 403 blocking
    transcribe_audio = False  # Force disabled - audio downloads are blocked by YouTube
    
    all_transcriptions = []
    transcript_sources = []
    
    # Try to pull existing transcript first if requested
    if pull_transcript:
        transcript_result = get_youtube_transcript(source_url)
        if transcript_result['success']:
            all_transcriptions.append(transcript_result['text'])
            transcript_sources.append(f"YouTube Transcript ({transcript_result['language']})")
            logger.info(f"Successfully extracted YouTube transcript")
        else:
            logger.info(f"No transcript available: {transcript_result['error']}")
            # Enable audio fallback if transcript not available
            logger.info("YouTube transcript not available - will download and transcribe audio")
            transcribe_audio = True
    
    # If no transcript, download low-res video and transcribe
    if not all_transcriptions and transcribe_audio:
        try:
            from utils.youtube_processor import download_youtube_video
            
            logger.info("Downloading YouTube video (low resolution) for transcription...")
            video_file = download_youtube_video(source_url, app.config['UPLOAD_FOLDER'])
            
            if video_file and os.path.exists(video_file):
                try:
                    logger.info(f"Transcribing downloaded YouTube video: {video_file}")
                    transcription_result = send_to_whisper(video_file)
                    
                    if isinstance(transcription_result, dict) and 'text' in transcription_result:
                        transcription_text = transcription_result['text']
                    else:
                        transcription_text = str(transcription_result)
                    
                    all_transcriptions.append(transcription_text)
                    transcript_sources.append("Video Transcription (Whisper)")
                    
                    # Clean up downloaded file
                    logger.info(f"Cleaning up downloaded video file: {video_file}")
                    if os.path.exists(video_file):
                        os.remove(video_file)
                        logger.info("Video file cleaned up successfully")
                        
                except Exception as e:
                    logger.error(f"Error transcribing YouTube video: {str(e)}")
                    if os.path.exists(video_file):
                        os.remove(video_file)
                    raise
        except Exception as e:
            logger.error(f"Error downloading/transcribing YouTube video: {str(e)}")
            if not all_transcriptions:
                raise Exception(f"Failed to get transcript: No YouTube transcript available and video download/transcription failed: {str(e)}")
    
    # Only raise error if we have no transcriptions at all
    if not all_transcriptions:
        raise Exception("No YouTube transcript available for this video and audio transcription was not enabled.")
    

    
    # Combine results
    if len(all_transcriptions) > 1:
        formatted_results = []
        for text, source in zip(all_transcriptions, transcript_sources):
            formatted_results.append(f"=== {source} ===\n{text}")
        result_text = '\n\n'.join(formatted_results)
    else:
        result_text = all_transcriptions[0] if all_transcriptions else "No transcript available"
    
    # Save to file
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Extract video ID for filename
        video_id = source_url.split('v=')[-1].split('&')[0] if 'v=' in source_url else 'youtube'
        transcription_filename = f"{timestamp}_youtube_{video_id}.txt"
        transcription_path = os.path.join(TRANSCRIPTIONS_FOLDER, transcription_filename)
        
        with open(transcription_path, 'w', encoding='utf-8') as f:
            f.write(f"YouTube Transcription\n")
            f.write(f"URL: {source_url}\n")
            f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'-' * 80}\n\n")
            f.write(result_text)
        
        logger.info(f"YouTube transcription saved to: {transcription_path}")
    except Exception as e:
        logger.warning(f"Could not save transcription to file: {str(e)}")
    
    return jsonify({
        'success': True,
        'transcription': {'text': result_text},
        'message': 'YouTube transcription completed'
    })

@app.route('/api/process', methods=['POST'])
def api_process():
    """Comprehensive processing endpoint for all input types"""
    try:
        # Determine input type and extract data
        if request.content_type and 'multipart/form-data' in request.content_type:
            # File upload - always treat as audio-video for direct processing
            input_type = 'audio-video'  # Force audio processing to avoid DB
            target_language = request.form.get('target_language', 'en')
            voice_id = request.form.get('voice_id', 'google_en')
            output_formats = request.form.get('output_formats', '["text"]')
            
            try:
                import json
                output_formats = json.loads(output_formats)  # Safely convert string to list
                if not isinstance(output_formats, list):
                    output_formats = ['text']
            except:
                output_formats = ['text']
            
            files = request.files.getlist('files')
            if not files or not files[0].filename:
                return jsonify({'error': 'No files provided'}), 400
            
            # Extract LLM config from form data
            llm_config_str = request.form.get('llm_config', '{}')
            try:
                import json
                llm_config = json.loads(llm_config_str)
            except:
                llm_config = {}
            
            # Always process audio files directly without database
            # Database job tracking is not reliable when PostgreSQL is down
            if input_type == 'audio-video':
                logger.info("Processing audio files directly (no database required)")
                return process_audio_files_directly(files)
            
            # Create processing job (requires database)
            try:
                job = ProcessingJob(
                    job_type='transcription' if input_type == 'audio-video' else 'document_processing',
                    input_type='file',
                    target_language=target_language,
                    voice_id=voice_id,
                    output_formats=output_formats,
                    job_metadata={'llm': llm_config},
                    status='pending'
                )
                db.session.add(job)
                db.session.flush()  # Get the job ID
            except Exception as db_err:
                logger.error(f"Cannot create job - database unavailable: {str(db_err)}")
                return jsonify({'error': 'Database required for advanced processing is unavailable. Processing failed.'}), 503
            
            # Process files
            processed_files = []
            for file in files:
                if file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_extension = filename.rsplit('.', 1)[1].lower()
                    unique_filename = f"{uuid.uuid4()}.{file_extension}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    
                    job.original_filename = filename
                    job.file_type = file_extension
                    job.file_size = os.path.getsize(filepath)
                    
                    processed_files.append(filepath)
            
            db.session.commit()
            
            # Start background processing
            process_job_async(job.id, processed_files)
            
            return jsonify({
                'success': True,
                'job_id': job.id,
                'message': 'Processing started'
            })
            
        else:
            # JSON request (YouTube, text, etc.)
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            
            input_type = data.get('input_type')
            target_language = data.get('target_language', 'en')
            voice_id = data.get('voice_id', 'google_en')
            output_formats = data.get('output_formats', ['text'])
            
            if input_type == 'youtube':
                source_url = data.get('source_url')
                if not source_url or not is_youtube_url(source_url):
                    return jsonify({'error': 'Invalid YouTube URL'}), 400
                
                # Process YouTube with progress tracking (no database required)
                logger.info(f"Processing YouTube with progress tracking: {source_url}")
                
                job_id = str(uuid.uuid4())
                processing_progress[job_id] = {
                    'status': 'processing',
                    'progress': 0,
                    'message': 'Starting YouTube processing...',
                    'result': None,
                    'start_time': time.time()
                }
                
                def process_youtube_async():
                    try:
                        processing_progress[job_id]['progress'] = 10
                        processing_progress[job_id]['message'] = 'Checking for existing transcript...'
                        
                        transcript_result = get_youtube_transcript(source_url)
                        
                        if transcript_result['success']:
                            processing_progress[job_id]['progress'] = 100
                            processing_progress[job_id]['status'] = 'completed'
                            processing_progress[job_id]['result'] = {'text': transcript_result['text']}
                        else:
                            processing_progress[job_id]['progress'] = 30
                            processing_progress[job_id]['message'] = 'Downloading video...'
                            
                            from utils.youtube_processor import download_youtube_video
                            video_file = download_youtube_video(source_url, app.config['UPLOAD_FOLDER'])
                            
                            processing_progress[job_id]['progress'] = 50
                            processing_progress[job_id]['message'] = 'Transcribing...'
                            
                            result = send_to_whisper(video_file)
                            text = result['text'] if isinstance(result, dict) else str(result)
                            
                            processing_progress[job_id]['progress'] = 100
                            processing_progress[job_id]['status'] = 'completed'
                            processing_progress[job_id]['result'] = {'text': text}
                            
                            if os.path.exists(video_file):
                                os.remove(video_file)
                    except Exception as e:
                        logger.error(f"YouTube error: {str(e)}")
                        processing_progress[job_id]['status'] = 'failed'
                        processing_progress[job_id]['message'] = str(e)
                
                import threading
                threading.Thread(target=process_youtube_async, daemon=True).start()
                
                return jsonify({'success': True, 'job_id': job_id})
                
                # Extract YouTube processing options and LLM config
                youtube_options = data.get('youtubeOptions', {})
                llm_config = data.get('llm', {})
                
                try:
                    job = ProcessingJob(
                        job_type='transcription',
                        input_type='youtube',
                        source_url=source_url,
                        target_language=target_language,
                        voice_id=voice_id,
                        output_formats=output_formats,
                        job_metadata={'youtubeOptions': youtube_options, 'llm': llm_config},
                        status='pending'
                    )
                except Exception as db_err:
                    logger.error(f"Cannot create YouTube job - database unavailable: {str(db_err)}")
                    return jsonify({'error': 'Database required for job tracking is unavailable.'}), 503
                
            elif input_type == 'text':
                input_text = data.get('input_text')
                if not input_text or not input_text.strip():
                    return jsonify({'error': 'No text provided'}), 400
                
                try:
                    job = ProcessingJob(
                        job_type='tts',
                        input_type='text',
                        input_text=input_text,
                        target_language=target_language,
                        voice_id=voice_id,
                        output_formats=['mp3'],  # TTS always outputs audio
                        status='pending'
                    )
                except Exception as db_err:
                    logger.error(f"Cannot create TTS job - database unavailable: {str(db_err)}")
                    return jsonify({'error': 'Database required for TTS processing is unavailable.'}), 503
                
            else:
                return jsonify({'error': 'Unsupported input type'}), 400
            
            try:
                db.session.add(job)
                db.session.commit()
                
                # Start background processing
                process_job_async(job.id)
                
                return jsonify({
                    'success': True,
                    'job_id': job.id,
                    'message': 'Processing started'
                })
            except Exception as db_error:
                logger.error(f"Database error, cannot process with job tracking: {str(db_error)}")
                return jsonify({'error': 'Database unavailable. Please use file upload instead of advanced features.'}), 503
            
    except Exception as e:
        logger.error(f"Error in API process: {str(e)}")
        return jsonify({'error': f"Processing failed: {str(e)}"}), 500

@app.route('/api/job-status/<job_id>', methods=['GET'])
def api_job_status(job_id):
    """Get the status of a processing job"""
    # Check in-memory progress first (for direct processing)
    if job_id in processing_progress:
        progress = processing_progress[job_id]
        
        # Calculate time information
        elapsed_time = time.time() - progress['start_time']
        
        # Build status message with time info
        status_message = progress['message']
        if progress.get('file_duration'):
            duration = progress['file_duration']
            processed = progress.get('processed_duration', 0)
            
            # Format durations
            def format_time(seconds):
                h = int(seconds // 3600)
                m = int((seconds % 3600) // 60)
                s = int(seconds % 60)
                if h > 0:
                    return f"{h}h {m}m {s}s"
                elif m > 0:
                    return f"{m}m {s}s"
                else:
                    return f"{s}s"
            
            # Estimate remaining time based on processing speed
            if processed > 0 and elapsed_time > 0:
                processing_speed = processed / elapsed_time  # seconds of audio per second of processing
                remaining_audio = duration - processed
                estimated_remaining = remaining_audio / processing_speed if processing_speed > 0 else 0
                
                status_message += f"\n📊 Duration: {format_time(duration)} | Processed: {format_time(processed)} | Remaining: ~{format_time(estimated_remaining)}"
            else:
                status_message += f"\n📊 Total duration: {format_time(duration)} | Analyzing..."
        
        return jsonify({
            'job_id': job_id,
            'status': progress['status'],
            'progress_percentage': progress['progress'],
            'status_message': status_message,
            'result_text': progress['result']['text'] if progress.get('result') else None,
            'result_files': [],
            'error_message': None,
            'processing_time': int(elapsed_time * 1000)
        })
    
    # Fallback to database job (if available)
    if not DB_AVAILABLE:
        return jsonify({'error': 'Job not found'}), 404
    
    try:
        # Try to convert to int for database lookup
        try:
            job_id_int = int(job_id)
        except ValueError:
            return jsonify({'error': 'Job not found'}), 404
        
        job = ProcessingJob.query.get_or_404(job_id_int)
        
        status_message = {
            'pending': 'Waiting to start...',
            'processing': 'Processing in progress...',
            'completed': 'Processing completed!',
            'failed': 'Processing failed'
        }.get(job.status, 'Unknown status')
        
        return jsonify({
            'job_id': job.id,
            'status': job.status,
            'progress_percentage': job.progress_percentage,
            'status_message': status_message,
            'result_text': job.result_text,
            'result_files': job.result_files,
            'error_message': job.error_message,
            'processing_time': job.processing_time
        })
        
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        return jsonify({'error': 'Failed to get job status'}), 500

@app.route('/api/process-text-with-ai', methods=['POST'])
def api_process_text_with_ai():
    """Process already-transcribed text with AI"""
    try:
        data = request.get_json()
        
        text = data.get('text', '').strip()
        prompt = data.get('prompt', '').strip()
        model = data.get('model', 'llama2')
        save_to_openqm = data.get('save_to_openqm', False)
        export_markdown = data.get('export_markdown', False)
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        if not prompt:
            prompt = 'Summarize this text in 3-5 key points'
        
        logger.info(f"Processing text with AI - Model: {model}, Prompt: {prompt[:50]}...")
        
        # Process with LLM
        from utils.llm_processor import process_text_with_llm
        processed_text = process_text_with_llm(text, prompt, model)
        
        if not processed_text:
            return jsonify({'error': 'AI processing failed to generate output'}), 500
        
        result_files = []
        
        # Save to OpenQM if requested
        if save_to_openqm:
            try:
                from utils.openqm_client import save_to_openqm
                record_id = save_to_openqm(
                    original_text=text,
                    llm_prompt=prompt,
                    llm_response=processed_text,
                    model_used=model
                )
                logger.info(f"Saved to OpenQM with record ID: {record_id}")
            except Exception as e:
                logger.error(f"Failed to save to OpenQM: {str(e)}")
        
        # Export as markdown if requested
        if export_markdown:
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                markdown_filename = f'ai_processed_{timestamp}.md'
                markdown_path = os.path.join(app.config['UPLOAD_FOLDER'], markdown_filename)
                
                with open(markdown_path, 'w', encoding='utf-8') as f:
                    f.write(f"# AI Processed Text\n\n")
                    f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(f"**Model:** {model}\n\n")
                    f.write(f"**Prompt:** {prompt}\n\n")
                    f.write(f"---\n\n")
                    f.write(f"## Original Text\n\n{text}\n\n")
                    f.write(f"---\n\n")
                    f.write(f"## AI Response\n\n{processed_text}\n")
                
                result_files.append(markdown_filename)
                logger.info(f"Exported markdown: {markdown_filename}")
            except Exception as e:
                logger.error(f"Failed to export markdown: {str(e)}")
        
        return jsonify({
            'success': True,
            'processed_text': processed_text,
            'files': result_files
        })
        
    except Exception as e:
        logger.error(f"Error in AI text processing: {str(e)}")
        return jsonify({'error': f"AI processing failed: {str(e)}"}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    """Download generated files"""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500

def process_job_async(job_id, file_paths=None):
    """Process a job asynchronously (simplified version)"""
    import threading
    thread = threading.Thread(target=process_job_worker, args=(job_id, file_paths))
    thread.daemon = True
    thread.start()

def process_job_worker(job_id, file_paths=None):
    """Background worker to process jobs"""
    try:
        with app.app_context():
            job = ProcessingJob.query.get(job_id)
            if not job:
                return
            
            job.status = 'processing'
            job.progress_percentage = 10
            db.session.commit()
            
            start_time = time.time()
            result_files = []
            
            if job.job_type == 'transcription':
                if job.input_type == 'file' and file_paths:
                    # Process uploaded files
                    all_transcriptions = []
                    
                    for i, filepath in enumerate(file_paths):
                        job.progress_percentage = 20 + (i * 40 // len(file_paths))
                        db.session.commit()
                        
                        try:
                            # Convert to appropriate format if needed
                            if job.file_type in ['mp3', 'mp4', 'mov']:
                                wav_path = filepath.replace(f'.{job.file_type}', '.wav')
                                if job.file_type == 'mp3':
                                    convert_mp3_to_wav(filepath, wav_path)
                                else:
                                    # Use moviepy for video files
                                    from moviepy.editor import VideoFileClip
                                    video = VideoFileClip(filepath)
                                    video.audio.write_audiofile(wav_path)
                                    video.close()
                                os.remove(filepath)
                                filepath = wav_path
                            
                            # Transcribe
                            transcription_result = send_to_whisper(filepath)
                            
                            if isinstance(transcription_result, dict) and 'text' in transcription_result:
                                all_transcriptions.append(transcription_result['text'])
                            else:
                                all_transcriptions.append(str(transcription_result))
                            
                            os.remove(filepath)
                            
                        except Exception as e:
                            logger.error(f"Error processing file {filepath}: {str(e)}")
                            all_transcriptions.append(f"Error processing file: {str(e)}")
                    
                    job.result_text = '\n\n'.join(all_transcriptions)
                    
                elif job.input_type == 'youtube':
                    # Process YouTube content with transcript options
                    job.progress_percentage = 30
                    db.session.commit()
                    
                    # Get YouTube options from job metadata
                    youtube_options = job.job_metadata.get('youtubeOptions', {}) if job.job_metadata else {}
                    pull_transcript = youtube_options.get('pullTranscript', True)
                    transcribe_audio = youtube_options.get('transcribeAudio', False)
                    
                    all_transcriptions = []
                    transcript_sources = []
                    
                    # Try to pull existing transcript first if requested
                    if pull_transcript:
                        job.progress_percentage = 35
                        db.session.commit()
                        
                        transcript_result = get_youtube_transcript(job.source_url)
                        if transcript_result['success']:
                            all_transcriptions.append(transcript_result['text'])
                            transcript_sources.append(f"YouTube Transcript ({transcript_result['language']})")
                            logger.info(f"Successfully extracted YouTube transcript")
                        else:
                            logger.info(f"No transcript available: {transcript_result['error']}")
                            # If transcript not available and user didn't want audio transcription, enable it
                            if not transcribe_audio:
                                transcribe_audio = True
                                logger.info("Automatically enabling audio transcription as fallback")
                    
                    # Transcribe from audio if requested or as fallback
                    if transcribe_audio or not all_transcriptions:
                        job.progress_percentage = 50
                        db.session.commit()
                        
                        audio_files = download_youtube_audio(job.source_url)
                        
                        for i, audio_file in enumerate(audio_files):
                            job.progress_percentage = 55 + (i * 25 // len(audio_files))
                            db.session.commit()
                            
                            try:
                                transcription_result = send_to_whisper(audio_file)
                                if isinstance(transcription_result, dict) and 'text' in transcription_result:
                                    all_transcriptions.append(transcription_result['text'])
                                    transcript_sources.append("Audio Transcription")
                                else:
                                    all_transcriptions.append(str(transcription_result))
                                    transcript_sources.append("Audio Transcription (Error)")
                                os.remove(audio_file)
                            except Exception as e:
                                logger.error(f"Error transcribing {audio_file}: {str(e)}")
                                all_transcriptions.append(f"Error transcribing: {str(e)}")
                                transcript_sources.append("Audio Transcription (Error)")
                    
                    # Combine results with source information
                    if len(all_transcriptions) > 1:
                        formatted_results = []
                        for i, (text, source) in enumerate(zip(all_transcriptions, transcript_sources)):
                            formatted_results.append(f"=== {source} ===\n{text}")
                        job.result_text = '\n\n'.join(formatted_results)
                    else:
                        job.result_text = all_transcriptions[0] if all_transcriptions else "No transcript available"
            
            elif job.job_type == 'tts':
                # Text to speech
                job.progress_percentage = 40
                db.session.commit()
                
                audio_file = convert_text_to_speech(job.input_text, job.voice_id)
                result_files.append(os.path.basename(audio_file))
                job.result_text = f"Speech generated from {len(job.input_text)} characters of text"
            
            elif job.job_type == 'document_processing':
                # Document processing
                if file_paths:
                    all_text = []
                    for filepath in file_paths:
                        try:
                            text = process_document(filepath, job.file_type)
                            all_text.append(text)
                            os.remove(filepath)
                        except Exception as e:
                            logger.error(f"Error processing document {filepath}: {str(e)}")
                            all_text.append(f"Error processing document: {str(e)}")
                    
                    job.result_text = '\n\n'.join(all_text)
            
            # LLM Processing (if enabled)
            llm_config = job.job_metadata.get('llm', {}) if job.job_metadata else {}
            llm_result_text = None
            
            if llm_config.get('enabled') and job.result_text:
                job.progress_percentage = 75
                db.session.commit()
                
                try:
                    user_prompt = llm_config.get('prompt', 'Summarize this text in 3-5 key points')
                    logger.info(f"Starting LLM processing with prompt: {user_prompt[:100]}...")
                    
                    llm_result = process_text_with_llm(
                        text=job.result_text,
                        processing_type='custom',
                        custom_prompt=user_prompt,
                        model=llm_config.get('model')
                    )
                    
                    if llm_result.get('success'):
                        llm_result_text = llm_result.get('processed_text')
                        logger.info("LLM processing completed successfully")
                        
                        # Save to OpenQM if requested
                        if llm_config.get('saveToOpenQM'):
                            transcript_data = {
                                'text': job.result_text,
                                'source_type': job.input_type,
                                'source_url': job.source_url,
                                'language': job.target_language,
                                'file_name': job.original_filename
                            }
                            # Add the user's prompt to the LLM result data
                            llm_result_with_prompt = llm_result.copy()
                            llm_result_with_prompt['prompt'] = user_prompt
                            
                            save_result = save_transcript_to_openqm(transcript_data, llm_result_with_prompt)
                            logger.info(f"OpenQM save result: {save_result.get('message', save_result.get('error'))}")
                        
                        # Export to Markdown if requested
                        if llm_config.get('exportMarkdown'):
                            markdown_content = f"# {job.original_filename or 'Transcript'}\n\n"
                            markdown_content += f"**AI Task:** {user_prompt}\n\n"
                            markdown_content += f"## Original Transcript\n\n{job.result_text}\n\n"
                            markdown_content += f"## AI Analysis\n\n{llm_result_text}\n"
                            
                            markdown_filename = f"transcript_{uuid.uuid4().hex[:8]}.md"
                            markdown_path = os.path.join(app.config['UPLOAD_FOLDER'], markdown_filename)
                            
                            with open(markdown_path, 'w') as f:
                                f.write(markdown_content)
                            
                            result_files.append(markdown_filename)
                            logger.info(f"Markdown exported to {markdown_filename}")
                        
                        # Append LLM result to job result text for display
                        job.result_text = f"{job.result_text}\n\n--- AI Analysis ---\n\n{llm_result_text}"
                    else:
                        logger.error(f"LLM processing failed: {llm_result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"Error in LLM processing: {str(e)}")
            
            # Generate output files in requested formats
            job.progress_percentage = 80
            db.session.commit()
            
            if job.result_text and job.output_formats:
                metadata = {
                    'filename': job.original_filename,
                    'processing_time': int((time.time() - start_time) * 1000),
                    'language': job.target_language,
                    'created_at': job.created_at
                }
                
                for format_type in job.output_formats:
                    try:
                        if format_type != 'mp3':  # Skip for TTS jobs
                            output_file = generate_output_file(
                                job.result_text, 
                                format_type, 
                                metadata,
                                app.config['UPLOAD_FOLDER']
                            )
                            result_files.append(os.path.basename(output_file))
                    except Exception as e:
                        logger.error(f"Error generating {format_type} output: {str(e)}")
            
            # Update job completion
            job.status = 'completed'
            job.progress_percentage = 100
            job.processing_time = int((time.time() - start_time) * 1000)
            job.result_files = result_files
            db.session.commit()
            
    except Exception as e:
        logger.error(f"Error in job worker: {str(e)}")
        with app.app_context():
            job = ProcessingJob.query.get(job_id)
            if job:
                job.status = 'failed'
                job.error_message = str(e)
                db.session.commit()

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'}), 200

@app.route('/api/recent-transcriptions', methods=['GET'])
def recent_transcriptions():
    """List recent transcription files"""
    try:
        import glob
        from datetime import datetime
        
        files = glob.glob(os.path.join(TRANSCRIPTIONS_FOLDER, '*.txt'))
        files.sort(key=os.path.getmtime, reverse=True)
        
        results = []
        for filepath in files[:10]:  # Last 10 files
            filename = os.path.basename(filepath)
            mtime = os.path.getmtime(filepath)
            size = os.path.getsize(filepath)
            
            results.append({
                'filename': filename,
                'modified': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'size': size,
                'url': f'/api/download-transcription/{filename}'
            })
        
        return jsonify({'transcriptions': results})
    except Exception as e:
        logger.error(f"Error listing transcriptions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-transcription/<filename>', methods=['GET'])
def download_transcription(filename):
    """Download a transcription file"""
    try:
        filepath = os.path.join(TRANSCRIPTIONS_FOLDER, secure_filename(filename))
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=filename)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Error downloading transcription: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
