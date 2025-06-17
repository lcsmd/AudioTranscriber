import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON

db = SQLAlchemy()

class ProcessingJob(db.Model):
    __tablename__ = 'processing_jobs'

    id = Column(Integer, primary_key=True)
    job_type = Column(String(50), nullable=False)  # transcription, tts, document_processing
    input_type = Column(String(50), nullable=False)  # file, youtube, text, url
    original_filename = Column(String(255), nullable=True)
    source_url = Column(Text, nullable=True)  # For YouTube URLs
    input_text = Column(Text, nullable=True)  # For text-to-speech
    file_type = Column(String(10), nullable=True)  # mp3, wav, mp4, pdf, etc.
    file_size = Column(Integer, nullable=True)  # Size in bytes
    
    # Processing configuration
    target_language = Column(String(10), nullable=True, default='en')  # Output language
    voice_id = Column(String(50), nullable=True)  # For TTS
    output_formats = Column(JSON, nullable=True)  # List of requested formats
    
    # Results
    result_text = Column(Text, nullable=True)
    result_files = Column(JSON, nullable=True)  # List of generated file paths
    processing_time = Column(Integer, nullable=True)  # Processing time in milliseconds
    progress_percentage = Column(Integer, nullable=False, default=0)
    
    # Status tracking
    status = Column(String(20), nullable=False, default='pending')  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    job_metadata = Column(JSON, nullable=True)  # Additional metadata
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<ProcessingJob {self.id}: {self.job_type} - {self.status}>'
    
    def to_dict(self):
        """Convert the model instance to a dictionary"""
        return {
            'id': self.id,
            'job_type': self.job_type,
            'input_type': self.input_type,
            'original_filename': self.original_filename,
            'source_url': self.source_url,
            'input_text': self.input_text[:100] + '...' if self.input_text and len(self.input_text) > 100 else self.input_text,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'target_language': self.target_language,
            'voice_id': self.voice_id,
            'output_formats': self.output_formats,
            'result_text': self.result_text[:200] + '...' if self.result_text and len(self.result_text) > 200 else self.result_text,
            'result_files': self.result_files,
            'processing_time': self.processing_time,
            'progress_percentage': self.progress_percentage,
            'status': self.status,
            'error_message': self.error_message,
            'metadata': self.job_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# Keep the old Transcription model for backward compatibility
class Transcription(db.Model):
    __tablename__ = 'transcriptions'

    id = Column(Integer, primary_key=True)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)  # mp3, wav, etc.
    file_size = Column(Integer, nullable=False)  # Size in bytes
    transcription_text = Column(Text, nullable=True)
    processing_time = Column(Integer, nullable=True)  # Processing time in milliseconds
    status = Column(String(20), nullable=False, default='processing')  # processing, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<Transcription {self.id}: {self.original_filename}>'
    
    def to_dict(self):
        """Convert the model instance to a dictionary"""
        return {
            'id': self.id,
            'original_filename': self.original_filename,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'transcription_text': self.transcription_text,
            'processing_time': self.processing_time,
            'status': self.status,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }