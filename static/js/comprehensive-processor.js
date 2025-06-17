/**
 * Comprehensive Speech Processing JavaScript
 * Handles multiple input types, progress tracking, and various output formats
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tab switching
    initializeTabs();
    
    // Initialize drag and drop for file inputs
    initializeFileDropZones();
    
    // Initialize processing buttons
    initializeProcessingButtons();
    
    // Initialize progress tracking
    initializeProgressTracking();
    
    // Initialize result handling
    initializeResultHandling();
});

function initializeTabs() {
    const tabs = document.querySelectorAll('.input-tab');
    const contents = document.querySelectorAll('.input-content');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // Remove active class from all tabs and contents
            tabs.forEach(t => t.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked tab and corresponding content
            this.classList.add('active');
            document.getElementById(targetTab + '-content').classList.add('active');
            
            // Update configuration options based on selected tab
            updateConfigurationOptions(targetTab);
        });
    });
    
    // Initialize with file tab active
    updateConfigurationOptions('file');
}

function updateConfigurationOptions(inputType) {
    const ttsOptions = document.getElementById('tts-options');
    const transcriptionOptions = document.getElementById('transcription-options');
    
    if (inputType === 'text' || inputType === 'document') {
        // Show TTS options for text and document inputs
        ttsOptions.classList.remove('d-none');
        transcriptionOptions.classList.add('d-none');
    } else {
        // Show transcription options for file, youtube inputs
        ttsOptions.classList.add('d-none');
        transcriptionOptions.classList.remove('d-none');
    }
}

function initializeFileDropZones() {
    // File upload drop zone
    const fileDropArea = document.getElementById('file-drop-area');
    const fileInput = document.getElementById('file-input');
    
    // Document upload drop zone
    const documentDropArea = document.getElementById('document-drop-area');
    const documentInput = document.getElementById('document-input');
    
    setupDropZone(fileDropArea, fileInput);
    setupDropZone(documentDropArea, documentInput);
}

function setupDropZone(dropArea, fileInput) {
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });
    
    // Handle dropped files
    dropArea.addEventListener('drop', handleDrop, false);
    
    // Handle file input change
    fileInput.addEventListener('change', handleFileSelect, false);
    
    // Handle click to open file dialog
    dropArea.addEventListener('click', () => fileInput.click());
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight(e) {
        dropArea.classList.add('dragover');
    }
    
    function unhighlight(e) {
        dropArea.classList.remove('dragover');
    }
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }
    
    function handleFileSelect(e) {
        const files = e.target.files;
        handleFiles(files);
    }
    
    function handleFiles(files) {
        const inputType = fileInput.id === 'file-input' ? 'audio-video' : 'document';
        processFiles(Array.from(files), inputType);
    }
}

function initializeProcessingButtons() {
    // YouTube processing
    document.getElementById('youtube-process').addEventListener('click', function() {
        const url = document.getElementById('youtube-url').value.trim();
        if (!url) {
            showMessage('Please enter a YouTube URL', 'warning');
            return;
        }
        processYouTubeURL(url);
    });
    
    // Text to speech processing
    document.getElementById('text-process').addEventListener('click', function() {
        const text = document.getElementById('text-input').value.trim();
        if (!text) {
            showMessage('Please enter text for speech synthesis', 'warning');
            return;
        }
        processTextToSpeech(text);
    });
}

function initializeProgressTracking() {
    // Progress tracking will be handled during processing
}

function initializeResultHandling() {
    // Result handling will be setup during processing completion
}

async function processFiles(files, inputType) {
    if (files.length === 0) return;
    
    showProgress();
    updateProgress(10, 'Preparing files...');
    
    const formData = new FormData();
    const config = getProcessingConfig();
    
    // Add files to form data
    files.forEach((file, index) => {
        formData.append(`files`, file);
    });
    
    // Add configuration
    formData.append('input_type', inputType);
    formData.append('target_language', config.language);
    formData.append('output_formats', JSON.stringify(config.formats));
    formData.append('voice_id', config.voice);
    
    try {
        updateProgress(30, 'Uploading files...');
        
        const response = await fetch('/api/process', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            updateProgress(50, 'Processing started...');
            const config = getProcessingConfig();
            pollJobStatus(result.job_id, config.liveDisplay);
        } else {
            throw new Error(result.error || 'Processing failed');
        }
        
    } catch (error) {
        hideProgress();
        showMessage(`Error: ${error.message}`, 'danger');
    }
}

async function processYouTubeURL(url) {
    showProgress();
    updateProgress(10, 'Validating YouTube URL...');
    
    const config = getProcessingConfig();
    
    const requestData = {
        input_type: 'youtube',
        source_url: url,
        target_language: config.language,
        output_formats: config.formats,
        voice_id: config.voice
    };
    
    try {
        updateProgress(20, 'Starting YouTube processing...');
        
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            updateProgress(30, 'Processing started...');
            const config = getProcessingConfig();
            pollJobStatus(result.job_id, config.liveDisplay);
        } else {
            throw new Error(result.error || 'Processing failed');
        }
        
    } catch (error) {
        hideProgress();
        showMessage(`Error: ${error.message}`, 'danger');
    }
}

async function processTextToSpeech(text) {
    showProgress();
    updateProgress(10, 'Preparing text for speech synthesis...');
    
    const config = getProcessingConfig();
    
    // Handle read-aloud functionality
    if (config.readAloud) {
        try {
            // Use browser's built-in speech synthesis for immediate playback
            if ('speechSynthesis' in window) {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = config.language;
                speechSynthesis.speak(utterance);
                showMessage('Reading text aloud...', 'info');
            } else {
                showMessage('Read-aloud not supported in this browser', 'warning');
            }
        } catch (error) {
            showMessage('Read-aloud failed: ' + error.message, 'warning');
        }
    }
    
    // Only process MP3 creation if requested
    if (!config.createMp3) {
        hideProgress();
        showMessage('Text read aloud successfully', 'success');
        return;
    }
    
    const requestData = {
        input_type: 'text',
        input_text: text,
        target_language: config.language,
        output_formats: ['mp3'],
        voice_id: config.voice
    };
    
    try {
        updateProgress(30, 'Generating MP3 file...');
        
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            updateProgress(50, 'Processing speech...');
            pollJobStatus(result.job_id, config.liveDisplay);
        } else {
            throw new Error(result.error || 'Processing failed');
        }
        
    } catch (error) {
        hideProgress();
        showMessage(`Error: ${error.message}`, 'danger');
    }
}

async function pollJobStatus(jobId, liveDisplay = false) {
    const pollInterval = 2000; // 2 seconds
    const maxAttempts = 300; // 10 minutes max
    let attempts = 0;
    let lastTextLength = 0;
    
    const poll = async () => {
        attempts++;
        
        try {
            const response = await fetch(`/api/job-status/${jobId}`);
            if (!response.ok) {
                throw new Error('Failed to get job status');
            }
            
            const status = await response.json();
            
            updateProgress(status.progress_percentage, status.status_message || 'Processing...');
            
            // Handle live text display for transcription
            if (liveDisplay && status.result_text && status.result_text.length > lastTextLength) {
                updateLiveTextDisplay(status.result_text);
                lastTextLength = status.result_text.length;
            }
            
            if (status.status === 'completed') {
                updateProgress(100, 'Processing complete!');
                setTimeout(() => {
                    hideProgress();
                    showResults(status);
                }, 1000);
                return;
            } else if (status.status === 'failed') {
                hideProgress();
                showMessage(`Processing failed: ${status.error_message}`, 'danger');
                return;
            } else if (attempts >= maxAttempts) {
                hideProgress();
                showMessage('Processing timeout. Please try again.', 'warning');
                return;
            }
            
            // Continue polling
            setTimeout(poll, pollInterval);
            
        } catch (error) {
            hideProgress();
            showMessage(`Error checking status: ${error.message}`, 'danger');
        }
    };
    
    poll();
}

function updateLiveTextDisplay(text) {
    const resultsSection = document.getElementById('results-section');
    const resultContent = document.getElementById('result-content');
    
    // Show results section if not already visible
    if (resultsSection.classList.contains('d-none')) {
        resultsSection.classList.remove('d-none');
        resultContent.innerHTML = `
            <div class="live-text-display">
                <h6><i class="fas fa-eye"></i> Live Transcription:</h6>
                <div id="live-text-content" class="text-content" style="background: #f8f9fa; padding: 15px; border-radius: 5px; max-height: 300px; overflow-y: auto;">
                    ${text.replace(/\n/g, '<br>')}
                </div>
            </div>
        `;
    } else {
        // Update existing live text content
        const liveTextContent = document.getElementById('live-text-content');
        if (liveTextContent) {
            liveTextContent.innerHTML = text.replace(/\n/g, '<br>');
            // Auto-scroll to bottom
            liveTextContent.scrollTop = liveTextContent.scrollHeight;
        }
    }
}

function getProcessingConfig() {
    // Determine which configuration section is active
    const ttsOptions = document.getElementById('tts-options');
    const transcriptionOptions = document.getElementById('transcription-options');
    
    if (!ttsOptions.classList.contains('d-none')) {
        // TTS configuration (text/document input)
        const language = document.getElementById('tts-language').value;
        const voice = document.getElementById('tts-voice').value;
        const readAloud = document.getElementById('read-aloud-now').checked;
        const createMp3 = document.getElementById('auto-create-mp3').checked;
        
        return {
            language: language,
            voice: voice,
            formats: createMp3 ? ['mp3'] : [],
            readAloud: readAloud,
            createMp3: createMp3
        };
    } else {
        // Transcription configuration (audio/video/youtube input)
        const language = document.getElementById('output-language').value;
        const liveDisplay = document.getElementById('live-text-display').checked;
        
        const formatCheckboxes = document.querySelectorAll('input[type="checkbox"][id^="format-"]:checked');
        const formats = Array.from(formatCheckboxes).map(cb => cb.value);
        
        return {
            language: language,
            voice: 'google_en', // Default voice for transcription
            formats: formats.length > 0 ? formats : ['text'],
            liveDisplay: liveDisplay
        };
    }
}

function showProgress() {
    document.getElementById('progress-section').classList.remove('d-none');
    document.getElementById('results-section').classList.add('d-none');
}

function hideProgress() {
    document.getElementById('progress-section').classList.add('d-none');
}

function updateProgress(percentage, message) {
    const progressBar = document.getElementById('main-progress-bar');
    const statusElement = document.getElementById('progress-status');
    
    progressBar.style.width = `${percentage}%`;
    progressBar.textContent = `${Math.round(percentage)}%`;
    statusElement.textContent = message;
}

function showResults(jobData) {
    const resultsSection = document.getElementById('results-section');
    const resultContent = document.getElementById('result-content');
    const resultDownloads = document.getElementById('result-downloads');
    
    // Show results section
    resultsSection.classList.remove('d-none');
    
    // Display result text if available
    if (jobData.result_text) {
        resultContent.innerHTML = `
            <div class="result-text">
                <h6>Result:</h6>
                <div class="text-content" style="background: #f8f9fa; padding: 15px; border-radius: 5px; max-height: 300px; overflow-y: auto;">
                    ${jobData.result_text.replace(/\n/g, '<br>')}
                </div>
            </div>
        `;
    }
    
    // Display download links for generated files
    if (jobData.result_files && jobData.result_files.length > 0) {
        const downloadLinks = jobData.result_files.map(file => {
            const fileType = file.split('.').pop().toUpperCase();
            return `<a href="/download/${file}" class="result-file" target="_blank">
                <i class="fas fa-download"></i> Download ${fileType}
            </a>`;
        }).join('');
        
        resultDownloads.innerHTML = `
            <h6>Download Files:</h6>
            ${downloadLinks}
        `;
    }
    
    showMessage('Processing completed successfully!', 'success');
}

function showMessage(message, type) {
    const messagesContainer = document.getElementById('status-messages');
    
    const messageElement = document.createElement('div');
    messageElement.className = `alert alert-${type} alert-dismissible fade show`;
    messageElement.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    messagesContainer.appendChild(messageElement);
    
    // Auto-remove success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            if (messageElement.parentNode) {
                messageElement.remove();
            }
        }, 5000);
    }
}

// Utility function to format file sizes
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}