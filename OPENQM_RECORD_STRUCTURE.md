# OpenQM Record Structure

## Configuration
- **Server**: 10.1.34.103:8181
- **Account**: LCS
- **Username**: lawr
- **Password**: apgar-66
- **File**: TRANSCRIPT

## Record Fields

Each transcript saved to OpenQM will contain:

### Basic Fields
- `ID` - Unique record identifier (TRANS_YYYYMMDD_HHMMSS_microseconds)
- `TIMESTAMP` - ISO format timestamp of when record was created
- `ORIGINAL_TEXT` - The full transcript text
- `SOURCE_TYPE` - Type of source (audio, youtube, text, document)
- `SOURCE_URL` - URL if from YouTube or web source
- `LANGUAGE` - Language code (en, es, fr, etc.)
- `DURATION` - Duration in seconds (for audio/video)
- `FILE_NAME` - Original filename

### LLM Processing Fields (when AI processing is enabled)
- `HAS_LLM_PROCESSING` - 'Y' or 'N'
- `LLM_PROMPT` - **The user's instruction to the AI** (e.g., "Summarize this text in 3-5 key points")
- `LLM_RESPONSE` - **The AI's response/output**
- `LLM_MODEL` - AI model used (llama2, llama3, mistral, etc.)
- `PROCESSING_TYPE` - Type of processing (custom, summarize, etc.)

### Additional Fields
- `METADATA` - JSON string of any additional metadata

## Example Record

```json
{
  "ID": "TRANS_20251015_143052_123456",
  "TIMESTAMP": "2025-10-15T14:30:52.123456",
  "ORIGINAL_TEXT": "This is the transcribed text...",
  "SOURCE_TYPE": "youtube",
  "SOURCE_URL": "https://youtube.com/watch?v=abc123",
  "LANGUAGE": "en",
  "FILE_NAME": "video_transcript.mp4",
  "HAS_LLM_PROCESSING": "Y",
  "LLM_PROMPT": "Summarize this text in 3-5 key points",
  "LLM_RESPONSE": "1. Main point one...\n2. Main point two...",
  "LLM_MODEL": "llama3",
  "PROCESSING_TYPE": "custom"
}
```

## Authentication
The system now includes credentials in the REST API calls:
- Username and password in payload
- HTTP Basic Auth header
- Both methods ensure proper authentication with OpenQM server
