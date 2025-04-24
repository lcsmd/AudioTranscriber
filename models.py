import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean

db = SQLAlchemy()

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