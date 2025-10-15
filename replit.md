# Speech Processing Service

## Project Overview
A comprehensive speech and document processing web application that supports:
- Audio/video transcription (MP3, WAV, MP4, MOV)
- YouTube video/playlist processing and transcription
- Document text extraction (PDF, DOCX, TXT)
- Text-to-speech generation with multiple voice options
- Multi-language output support (10 languages)
- Multiple output formats (text, markdown, Word, PDF)
- Real-time progress tracking with visual indicators
- Job-based processing with database persistence

## Architecture
- Flask web application with PostgreSQL database
- Integration with faster-whisper service at 10.1.10.20 (GPU server)
- HAProxy SSL termination routing speech.lcs.ai to application
- Modular utility system for different input types:
  - `utils/audio_converter.py` - Audio format conversion
  - `utils/youtube_processor.py` - YouTube content downloading
  - `utils/document_processor.py` - Document text extraction
  - `utils/text_to_speech.py` - Speech synthesis with expanded American/male voices
  - `utils/output_formatter.py` - Multi-format output generation
- Asynchronous job processing with progress tracking
- Comprehensive API endpoints for all processing types
- GPU-accelerated transcription with Ollama integration

## User Preferences
- Target URL: https://speech.lcs.ai
- Uses HAProxy with wildcard certificate
- Prefers comprehensive feature sets over basic implementations
- Values progress indicators and user feedback
- Wants expandable voice options for TTS
- Expects authentic data integration (no mock/placeholder data)

## Recent Changes
- 2025-10-15: Implemented Ollama LLM integration for text processing (summarize, critique, expand, explain, custom)
- 2025-10-15: Added OpenQM database client for saving transcripts/summaries to Windows server (10.1.34.103)
- 2025-10-15: Created flexible prompt system with suggested prompts loaded from `suggested_prompts.txt`
- 2025-10-15: User can select suggested prompts or write custom instructions for AI processing
- 2025-10-15: Added Obsidian-compatible markdown export functionality
- 2025-10-15: Fixed critical security vulnerability (replaced eval() with json.loads())
- 2025-10-15: Integrated complete flow: transcription → LLM processing → database save/export
- 2025-06-17: Added PostgreSQL database with ProcessingJob model
- 2025-06-17: Implemented comprehensive multi-input interface
- 2025-06-17: Added YouTube video/playlist processing
- 2025-06-17: Integrated document processing (PDF, DOCX, TXT)
- 2025-06-17: Implemented text-to-speech with multiple voices
- 2025-06-17: Added multi-format output generation
- 2025-06-17: Created real-time progress tracking system
- 2025-06-17: Built asynchronous job processing framework
- 2025-06-17: Updated faster-whisper integration to use direct script at /mnt/bigdisk/projects/faster-whisper-gpu/smart_transcribe.py

## Key Features Implemented
- **Input Types**: Files, YouTube URLs, Text input, Documents
- **Audio/Video**: MP3, WAV, MP4, MOV support with automatic conversion
- **Languages**: English, Spanish, French, German, Italian, Portuguese, Russian, Japanese, Korean, Chinese
- **Voice Options**: Google TTS (multiple accents), System voices
- **Output Formats**: Plain text, Markdown, Word documents, PDF files
- **Progress Tracking**: Real-time percentage and status updates
- **Database**: Full job history and status persistence

## Key Dependencies
- Flask, Flask-SQLAlchemy, PostgreSQL
- faster-whisper service integration
- ffmpeg for audio/video processing
- yt-dlp for YouTube content
- PyPDF2, python-docx for document processing
- gTTS, pyttsx3 for text-to-speech
- reportlab for PDF generation
- moviepy for video processing