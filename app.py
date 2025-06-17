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
from models import db, Transcription, ProcessingJob

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
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'mp4', 'mov'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf', 'docx', 'txt'}
ALL_ALLOWED_EXTENSIONS = ALLOWED_AUDIO_EXTENSIONS.union(ALLOWED_DOCUMENT_EXTENSIONS)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB limit

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
    # Get all processing jobs, ordered by most recent first
    jobs = ProcessingJob.query.order_by(ProcessingJob.created_at.desc()).all()
    
    # Convert to a list of dictionaries for the template
    history = [job.to_dict() for job in jobs]
    
    # Render the history template
    return render_template('history.html', history=history)

@app.route('/api/history', methods=['GET'])
def api_transcription_history():
    # Get all processing jobs, ordered by most recent first
    jobs = ProcessingJob.query.order_by(ProcessingJob.created_at.desc()).all()
    
    # Convert to a list of dictionaries for JSON
    history = [job.to_dict() for job in jobs]
    
    return jsonify({'jobs': history})

@app.route('/api/process', methods=['POST'])
def api_process():
    """Comprehensive processing endpoint for all input types"""
    try:
        # Determine input type and extract data
        if request.content_type and 'multipart/form-data' in request.content_type:
            # File upload
            input_type = request.form.get('input_type', 'audio-video')
            target_language = request.form.get('target_language', 'en')
            voice_id = request.form.get('voice_id', 'google_en')
            output_formats = request.form.get('output_formats', '["text"]')
            
            try:
                output_formats = eval(output_formats)  # Convert string to list
            except:
                output_formats = ['text']
            
            files = request.files.getlist('files')
            if not files or not files[0].filename:
                return jsonify({'error': 'No files provided'}), 400
            
            # Create processing job
            job = ProcessingJob(
                job_type='transcription' if input_type == 'audio-video' else 'document_processing',
                input_type='file',
                target_language=target_language,
                voice_id=voice_id,
                output_formats=output_formats,
                status='pending'
            )
            db.session.add(job)
            db.session.flush()  # Get the job ID
            
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
                
                # Extract YouTube processing options
                youtube_options = data.get('youtubeOptions', {})
                
                job = ProcessingJob(
                    job_type='transcription',
                    input_type='youtube',
                    source_url=source_url,
                    target_language=target_language,
                    voice_id=voice_id,
                    output_formats=output_formats,
                    job_metadata={'youtubeOptions': youtube_options},
                    status='pending'
                )
                
            elif input_type == 'text':
                input_text = data.get('input_text')
                if not input_text or not input_text.strip():
                    return jsonify({'error': 'No text provided'}), 400
                
                job = ProcessingJob(
                    job_type='tts',
                    input_type='text',
                    input_text=input_text,
                    target_language=target_language,
                    voice_id=voice_id,
                    output_formats=['mp3'],  # TTS always outputs audio
                    status='pending'
                )
                
            else:
                return jsonify({'error': 'Unsupported input type'}), 400
            
            db.session.add(job)
            db.session.commit()
            
            # Start background processing
            process_job_async(job.id)
            
            return jsonify({
                'success': True,
                'job_id': job.id,
                'message': 'Processing started'
            })
            
    except Exception as e:
        logger.error(f"Error in API process: {str(e)}")
        return jsonify({'error': f"Processing failed: {str(e)}"}), 500

@app.route('/api/job-status/<int:job_id>', methods=['GET'])
def api_job_status(job_id):
    """Get the status of a processing job"""
    try:
        job = ProcessingJob.query.get_or_404(job_id)
        
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
