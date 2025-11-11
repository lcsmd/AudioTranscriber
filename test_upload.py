#!/usr/bin/env python3
"""
Test script to upload an audio file to the speech processing service
"""
import requests
import sys
import os

def test_upload(file_path, url='https://speech.lcs.ai'):
    """Test uploading an audio file to the API"""
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False
    
    print(f"Testing upload to {url}/api/process")
    print(f"File: {file_path}")
    print(f"File size: {os.path.getsize(file_path) / 1024 / 1024:.2f} MB")
    print("-" * 60)
    
    # Prepare the multipart form data
    files = {
        'files': (os.path.basename(file_path), open(file_path, 'rb'), 'audio/mpeg')
    }
    
    data = {
        'input_type': 'audio-video',
        'target_language': 'en',
        'output_formats': '["text"]'
    }
    
    try:
        print("Uploading file...")
        response = requests.post(
            f"{url}/api/process",
            files=files,
            data=data,
            timeout=300  # 5 minute timeout
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print("\n✅ SUCCESS!")
                if 'transcription' in result:
                    text = result['transcription'].get('text', '')
                    print(f"\nTranscription (first 200 chars):")
                    print(text[:200] + "..." if len(text) > 200 else text)
                return True
            else:
                print("\n❌ FAILED - success=False in response")
                return False
        else:
            print(f"\n❌ FAILED - HTTP {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n❌ FAILED - Request timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"\n❌ FAILED - {str(e)}")
        return False
    finally:
        files['files'][1].close()

if __name__ == '__main__':
    file_path = '/Users/lawr/Desktop/2020-03-13T215338 copy.mp3'
    test_upload(file_path)
