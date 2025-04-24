/**
 * JavaScript for handling audio file uploads and transcription
 */

document.addEventListener('DOMContentLoaded', function() {
    const dropArea = document.getElementById('upload-drop-area');
    const fileInput = document.getElementById('file-input');
    const form = document.getElementById('audio-upload-form');
    const progressBar = document.getElementById('upload-progress-bar');
    const statusElement = document.getElementById('upload-status');
    const transcriptionPlaceholder = document.getElementById('transcription-placeholder');
    const transcriptionContent = document.getElementById('transcription-content');
    const transcriptionFilename = document.getElementById('transcription-filename');
    const transcriptionText = document.getElementById('transcription-text');
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop area when file is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    // Remove highlight when file is dragged out or dropped
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    // Handle dropped files
    dropArea.addEventListener('drop', handleDrop, false);
    
    // Handle file input change
    fileInput.addEventListener('change', handleFileSelect, false);
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight() {
        dropArea.classList.add('dragover');
    }
    
    function unhighlight() {
        dropArea.classList.remove('dragover');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files.length > 0) {
            handleFiles(files);
        }
    }
    
    function handleFileSelect(e) {
        const files = e.target.files;
        
        if (files.length > 0) {
            handleFiles(files);
        }
    }
    
    function handleFiles(files) {
        const file = files[0]; // Only process the first file
        
        // Check if file is an audio file (MP3 or WAV)
        if (!file.type.match('audio/(mp3|wav|mpeg)')) {
            showAlert(
                '<i class="fas fa-exclamation-triangle"></i> Please select an MP3 or WAV audio file.',
                'warning',
                'upload-status'
            );
            return;
        }
        
        // Check file size (max 50MB)
        if (file.size > 50 * 1024 * 1024) {
            showAlert(
                '<i class="fas fa-exclamation-triangle"></i> File size exceeds the maximum limit of 50MB.',
                'warning',
                'upload-status'
            );
            return;
        }
        
        // Upload the file
        uploadFile(file);
    }
    
    function uploadFile(file) {
        // Reset UI
        updateProgress(0, 'upload-progress-bar');
        statusElement.classList.add('d-none');
        
        // Create a FormData object
        const formData = new FormData();
        formData.append('audio_file', file);
        
        // Create and send the XMLHttpRequest
        const xhr = new XMLHttpRequest();
        
        // Update progress bar
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                updateProgress(percentComplete, 'upload-progress-bar');
            }
        });
        
        // Handle response
        xhr.addEventListener('load', function() {
            updateProgress(100, 'upload-progress-bar');
            
            if (xhr.status === 200) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    
                    if (response.success) {
                        // Show success message
                        showAlert(
                            '<i class="fas fa-check-circle"></i> File transcribed successfully!',
                            'success',
                            'upload-status'
                        );
                        
                        // Display the transcription
                        displayTranscription(response.filename, response.transcription);
                    } else if (response.error) {
                        throw new Error(response.error);
                    }
                } catch (error) {
                    showAlert(
                        `<i class="fas fa-exclamation-circle"></i> ${error.message || 'An error occurred during transcription.'}`,
                        'danger',
                        'upload-status'
                    );
                }
            } else {
                try {
                    const response = JSON.parse(xhr.responseText);
                    showAlert(
                        `<i class="fas fa-exclamation-circle"></i> ${response.error || 'An error occurred during upload.'}`,
                        'danger',
                        'upload-status'
                    );
                } catch (error) {
                    showAlert(
                        `<i class="fas fa-exclamation-circle"></i> Server error: ${xhr.status}`,
                        'danger',
                        'upload-status'
                    );
                }
            }
            
            // Hide the progress bar after 2 seconds
            setTimeout(function() {
                updateProgress(0, 'upload-progress-bar');
            }, 2000);
        });
        
        // Handle network errors
        xhr.addEventListener('error', function() {
            updateProgress(0, 'upload-progress-bar');
            showAlert(
                '<i class="fas fa-exclamation-circle"></i> A network error occurred. Please try again.',
                'danger',
                'upload-status'
            );
        });
        
        // Handle timeout
        xhr.addEventListener('timeout', function() {
            updateProgress(0, 'upload-progress-bar');
            showAlert(
                '<i class="fas fa-clock"></i> The request timed out. Please try again.',
                'warning',
                'upload-status'
            );
        });
        
        // Set up and send the request
        xhr.open('POST', '/upload', true);
        xhr.timeout = 300000; // 5 minutes timeout for large files
        xhr.send(formData);
        
        // Show processing message
        showAlert(
            '<i class="fas fa-spinner fa-spin"></i> Uploading and processing your audio file. This may take a few minutes for large files...',
            'info',
            'upload-status'
        );
    }
    
    function displayTranscription(filename, transcription) {
        // Hide placeholder, show content
        transcriptionPlaceholder.classList.add('d-none');
        transcriptionContent.classList.remove('d-none');
        
        // Set filename
        transcriptionFilename.textContent = filename;
        
        // Set transcription text
        // Check the structure of the transcription response and extract the text
        if (typeof transcription === 'object') {
            // Whisper API typically returns an object with a 'text' field
            if (transcription.text) {
                transcriptionText.textContent = transcription.text;
            } else if (transcription.transcription) {
                transcriptionText.textContent = transcription.transcription;
            } else {
                // Try to format the entire response as readable text
                transcriptionText.textContent = JSON.stringify(transcription, null, 2);
            }
        } else if (typeof transcription === 'string') {
            transcriptionText.textContent = transcription;
        } else {
            transcriptionText.textContent = 'Transcription completed, but the format is unknown.';
        }
    }
});
