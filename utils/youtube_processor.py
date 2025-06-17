import os
import tempfile
import logging
from yt_dlp import YoutubeDL
import re
from youtube_transcript_api._api import YouTubeTranscriptApi
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)

def is_youtube_url(url):
    """Check if the URL is a valid YouTube URL"""
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in youtube_patterns:
        if re.match(pattern, url.strip()):
            return True
    return False

def is_youtube_playlist(url):
    """Check if the URL is a YouTube playlist"""
    playlist_pattern = r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)'
    return bool(re.match(playlist_pattern, url.strip()))

def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url.strip())
        if match:
            return match.group(1)
    return None

def get_youtube_transcript(url, language_codes=['en', 'en-US', 'en-GB']):
    """
    Extract transcript from YouTube video
    
    Args:
        url (str): YouTube URL
        language_codes (list): Preferred language codes in order of preference
    
    Returns:
        dict: Transcript data with success status and content
    """
    try:
        video_id = extract_video_id(url)
        if not video_id:
            return {'success': False, 'error': 'Invalid YouTube URL'}
        
        logger.info(f"Extracting transcript for video ID: {video_id}")
        
        # Try to get transcript in preferred languages
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        transcript = None
        for lang_code in language_codes:
            try:
                transcript = transcript_list.find_transcript([lang_code])
                break
            except:
                continue
        
        # If no transcript in preferred languages, try auto-generated English
        if not transcript:
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
            except:
                pass
        
        # If still no transcript, try any available transcript
        if not transcript:
            try:
                available_transcripts = list(transcript_list)
                if available_transcripts:
                    transcript = available_transcripts[0]
            except:
                pass
        
        if not transcript:
            return {'success': False, 'error': 'No transcript available for this video'}
        
        # Fetch the transcript
        transcript_data = transcript.fetch()
        
        # Combine all text segments
        full_text = ' '.join([entry['text'] for entry in transcript_data])
        
        # Clean up the text
        full_text = full_text.replace('\n', ' ').strip()
        
        return {
            'success': True,
            'text': full_text,
            'language': transcript.language_code,
            'is_generated': transcript.is_generated,
            'video_id': video_id
        }
        
    except Exception as e:
        logger.error(f"Error extracting transcript: {str(e)}")
        return {'success': False, 'error': str(e)}

def download_youtube_audio(url, output_dir=None):
    """
    Download audio from YouTube video or playlist
    
    Args:
        url (str): YouTube URL
        output_dir (str): Directory to save the audio file(s)
    
    Returns:
        list: List of downloaded audio file paths
    """
    if output_dir is None:
        output_dir = tempfile.gettempdir()
    
    try:
        logger.info(f"Downloading audio from YouTube: {url}")
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'ffmpeg_location': '/nix/store/3zc5jbvqzrn8zmva4fx5p0nh4yy03wk4-ffmpeg-6.1.1-bin/bin/ffmpeg',
            'extractaudio': True,
            'audioformat': 'wav',
            'noplaylist': not is_youtube_playlist(url),
        }
        
        downloaded_files = []
        
        with YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info:  # Playlist
                for entry in info['entries']:
                    if entry:
                        video_url = entry['webpage_url']
                        try:
                            ydl.download([video_url])
                            # Construct expected filename
                            safe_title = re.sub(r'[^\w\-_\. ]', '_', entry['title'])
                            filename = os.path.join(output_dir, f"{safe_title}.wav")
                            if os.path.exists(filename):
                                downloaded_files.append(filename)
                        except Exception as e:
                            logger.error(f"Failed to download video {entry['title']}: {str(e)}")
            else:  # Single video
                ydl.download([url])
                # Construct expected filename
                safe_title = re.sub(r'[^\w\-_\. ]', '_', info['title'])
                filename = os.path.join(output_dir, f"{safe_title}.wav")
                if os.path.exists(filename):
                    downloaded_files.append(filename)
        
        logger.info(f"Successfully downloaded {len(downloaded_files)} audio files")
        return downloaded_files
        
    except Exception as e:
        logger.error(f"Error downloading YouTube audio: {str(e)}")
        raise Exception(f"Failed to download YouTube audio: {str(e)}")

def get_youtube_info(url):
    """
    Get information about YouTube video or playlist without downloading
    
    Args:
        url (str): YouTube URL
    
    Returns:
        dict: Video/playlist information
    """
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info:  # Playlist
                return {
                    'type': 'playlist',
                    'title': info.get('title', 'Unknown Playlist'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'video_count': len([e for e in info['entries'] if e]),
                    'description': info.get('description', ''),
                }
            else:  # Single video
                return {
                    'type': 'video',
                    'title': info.get('title', 'Unknown Video'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'description': info.get('description', ''),
                    'view_count': info.get('view_count', 0),
                }
                
    except Exception as e:
        logger.error(f"Error getting YouTube info: {str(e)}")
        raise Exception(f"Failed to get YouTube information: {str(e)}")