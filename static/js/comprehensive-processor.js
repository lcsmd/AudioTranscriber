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
    
    // Initialize LLM options
    initializeLLMOptions();
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
    const youtubeTranscriptOptions = document.getElementById('youtube-transcript-options');
    
    if (inputType === 'text' || inputType === 'document') {
        // Show TTS options for text and document inputs
        ttsOptions.classList.remove('d-none');
        transcriptionOptions.classList.add('d-none');
        if (youtubeTranscriptOptions) {
            youtubeTranscriptOptions.classList.add('d-none');
        }
    } else {
        // Show transcription options for file, youtube inputs
        ttsOptions.classList.add('d-none');
        transcriptionOptions.classList.remove('d-none');
        
        // Show YouTube-specific options only for YouTube input
        if (youtubeTranscriptOptions) {
            if (inputType === 'youtube') {
                youtubeTranscriptOptions.classList.remove('d-none');
            } else {
                youtubeTranscriptOptions.classList.add('d-none');
            }
        }
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

function initializeLLMOptions() {
    // Handle LLM enable/disable
    const enableLLM = document.getElementById('enable-llm-processing');
    const llmSettings = document.getElementById('llm-settings');
    
    if (enableLLM) {
        enableLLM.addEventListener('change', function() {
            if (this.checked) {
                llmSettings.classList.remove('d-none');
            } else {
                llmSettings.classList.add('d-none');
            }
        });
    }
    
    // Handle custom prompt visibility
    const processingType = document.getElementById('llm-processing-type');
    const customPromptContainer = document.getElementById('custom-prompt-container');
    
    if (processingType) {
        processingType.addEventListener('change', function() {
            if (this.value === 'custom') {
                customPromptContainer.style.display = 'block';
            } else {
                customPromptContainer.style.display = 'none';
            }
        });
    }
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
    formData.append('llm_config', JSON.stringify(config.llm));
    
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
        voice_id: config.voice,
        youtubeOptions: config.youtubeOptions || {},
        llm: config.llm
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
        speakTextWithSelectedVoice(text, config);
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
        
        // Get LLM processing options
        const llmConfig = getLLMConfig();
        
        return {
            language: language,
            voice: voice,
            formats: createMp3 ? ['mp3'] : [],
            readAloud: readAloud,
            createMp3: createMp3,
            llm: llmConfig
        };
    } else {
        // Transcription configuration (audio/video/youtube input)
        const language = document.getElementById('output-language').value;
        const liveDisplay = document.getElementById('live-text-display').checked;
        
        const formatCheckboxes = document.querySelectorAll('input[type="checkbox"][id^="format-"]:checked');
        const formats = Array.from(formatCheckboxes).map(cb => cb.value);
        
        // YouTube-specific options
        const youtubeOptions = {};
        const youtubeTranscriptOptions = document.getElementById('youtube-transcript-options');
        if (youtubeTranscriptOptions && !youtubeTranscriptOptions.classList.contains('d-none')) {
            youtubeOptions.pullTranscript = document.getElementById('pull-transcript').checked;
            youtubeOptions.transcribeAudio = document.getElementById('transcribe-audio').checked;
        }
        
        // Get LLM processing options
        const llmConfig = getLLMConfig();
        
        return {
            language: language,
            voice: 'google_en', // Default voice for transcription
            formats: formats.length > 0 ? formats : ['text'],
            liveDisplay: liveDisplay,
            youtubeOptions: youtubeOptions,
            llm: llmConfig
        };
    }
}

function getLLMConfig() {
    const enableLLM = document.getElementById('enable-llm-processing');
    
    if (!enableLLM || !enableLLM.checked) {
        return {
            enabled: false
        };
    }
    
    return {
        enabled: true,
        processingType: document.getElementById('llm-processing-type').value,
        model: document.getElementById('llm-model').value,
        customPrompt: document.getElementById('custom-llm-prompt').value,
        saveToOpenQM: document.getElementById('save-to-openqm').checked,
        exportMarkdown: document.getElementById('export-markdown').checked
    };
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

function mapVoiceSelection(selectedVoice, availableVoices, language) {
    /**
     * Maps the UI voice selection to browser speech synthesis voices
     * @param {string} selectedVoice - Voice ID from the UI dropdown
     * @param {Array} availableVoices - Available browser voices
     * @param {string} language - Selected language
     * @returns {SpeechSynthesisVoice|null} - Matched voice or null
     */
    
    if (!availableVoices || availableVoices.length === 0) {
        return null;
    }
    
    // Log all available voices for debugging
    console.log('All available voices:');
    availableVoices.forEach((voice, index) => {
        console.log(`${index}: ${voice.name} (${voice.lang}) - ${voice.localService ? 'Local' : 'Remote'}`);
    });
    
    // Define comprehensive voice mapping with multiple fallback strategies
    const voiceMapping = {
        'google_en_us_female': {
            primary: ['Google US English', 'Samantha', 'Victoria', 'Allison'],
            lang: 'en-US',
            gender: 'female'
        },
        'google_en_us_male': {
            primary: ['Google US English', 'Alex', 'Fred', 'Daniel'],
            lang: 'en-US', 
            gender: 'male'
        },
        'google_en_us_wavenet_a': {
            primary: ['Samantha', 'Victoria', 'Allison', 'Ava'],
            lang: 'en-US',
            gender: 'female'
        },
        'google_en_us_wavenet_b': {
            primary: ['Alex', 'Fred', 'Daniel', 'Nathan'],
            lang: 'en-US',
            gender: 'male'
        },
        'google_en_us_wavenet_c': {
            primary: ['Karen', 'Susan', 'Victoria'],
            lang: 'en-US',
            gender: 'female'
        },
        'google_en_us_wavenet_d': {
            primary: ['Tom', 'Aaron', 'Alex'],
            lang: 'en-US',
            gender: 'male'
        },
        'google_en_us_neural2_a': {
            primary: ['Ava', 'Samantha', 'Victoria'],
            lang: 'en-US',
            gender: 'female'
        },
        'google_en_us_neural2_c': {
            primary: ['Alex', 'Daniel', 'Fred'],
            lang: 'en-US',
            gender: 'male'
        },
        'google_en_uk': {
            primary: ['Daniel', 'Kate', 'Oliver'],
            lang: 'en-GB',
            gender: 'female'
        },
        'google_en_au': {
            primary: ['Karen', 'Catherine'],
            lang: 'en-AU',
            gender: 'female'
        },
        'google_en_ca': {
            primary: ['Alex', 'Samantha'],
            lang: 'en-CA',
            gender: 'female'
        },
        'google_en_uk_female': {
            primary: ['Google UK English Female', 'Kate', 'Stephanie'],
            lang: 'en-GB',
            gender: 'female'
        },
        'google_en_uk_male': {
            primary: ['Google UK English Male', 'Daniel', 'Oliver'],
            lang: 'en-GB',
            gender: 'male'
        },
        'system_alex': {
            primary: ['Alex'],
            lang: 'en-US',
            gender: 'male'
        },
        'system_samantha': {
            primary: ['Samantha'],
            lang: 'en-US',
            gender: 'female'
        },
        'system_victoria': {
            primary: ['Victoria'],
            lang: 'en-US',
            gender: 'female'
        },
        'system_daniel': {
            primary: ['Daniel'],
            lang: 'en-GB',
            gender: 'male'
        },
        'system_kate': {
            primary: ['Kate'],
            lang: 'en-GB',
            gender: 'female'
        },
        'system_karen': {
            primary: ['Karen'],
            lang: 'en-AU',
            gender: 'female'
        },
        'system_stephanie': {
            primary: ['Stephanie'],
            lang: 'en-GB',
            gender: 'female'
        },
        'system_tessa': {
            primary: ['Tessa'],
            lang: 'en-ZA',
            gender: 'female'
        },
        'system_allison': {
            primary: ['Allison'],
            lang: 'en-US',
            gender: 'female'
        },
        'system_ava': {
            primary: ['Ava'],
            lang: 'en-US',
            gender: 'female'
        },
        'system_fred': {
            primary: ['Fred'],
            lang: 'en-US',
            gender: 'male'
        },
        'system_oliver': {
            primary: ['Oliver'],
            lang: 'en-GB',
            gender: 'male'
        },
        'system_susan': {
            primary: ['Susan'],
            lang: 'en-US',
            gender: 'female'
        },
        'system_tom': {
            primary: ['Tom'],
            lang: 'en-US',
            gender: 'male'
        },
        'system_zoe': {
            primary: ['Zoe'],
            lang: 'en-US',
            gender: 'female'
        },
        'system_aaron': {
            primary: ['Aaron'],
            lang: 'en-US',
            gender: 'male'
        },
        'system_catherine': {
            primary: ['Catherine'],
            lang: 'en-AU',
            gender: 'female'
        },
        'system_moira': {
            primary: ['Moira'],
            lang: 'en-IE',
            gender: 'female'
        },
        'system_whisper': {
            primary: ['Whisper'],
            lang: 'en-US',
            gender: 'neutral'
        },
        'system_superstar': {
            primary: ['Superstar'],
            lang: 'en-US',
            gender: 'neutral'
        },
        'system_trinoids': {
            primary: ['Trinoids'],
            lang: 'en-US',
            gender: 'neutral'
        },
        'system_zarvox': {
            primary: ['Zarvox'],
            lang: 'en-US',
            gender: 'neutral'
        },
        'system_wobble': {
            primary: ['Wobble'],
            lang: 'en-US',
            gender: 'neutral'
        },
        'system_thomas': {
            primary: ['Thomas'],
            lang: 'fr-FR',
            gender: 'male'
        },
        'system_marie': {
            primary: ['Marie'],
            lang: 'fr-FR',
            gender: 'female'
        },
        'system_anna': {
            primary: ['Anna'],
            lang: 'de-DE',
            gender: 'female'
        },
        'system_jorge': {
            primary: ['Jorge'],
            lang: 'es-ES',
            gender: 'male'
        }
    };
    
    const mapping = voiceMapping[selectedVoice];
    if (!mapping) {
        console.log('No mapping found for:', selectedVoice);
        return availableVoices.find(voice => voice.lang.startsWith(language.substring(0, 2))) || availableVoices[0];
    }
    
    console.log('Voice mapping for', selectedVoice, ':', mapping);
    
    let matchedVoice = null;
    
    // Strategy 1: Try exact name matches
    for (const voiceName of mapping.primary) {
        matchedVoice = availableVoices.find(voice => 
            voice.name.toLowerCase() === voiceName.toLowerCase() && 
            voice.lang === mapping.lang
        );
        if (matchedVoice) {
            console.log('Exact match found:', matchedVoice.name);
            break;
        }
    }
    
    // Strategy 2: Try partial name matches with language
    if (!matchedVoice) {
        for (const voiceName of mapping.primary) {
            matchedVoice = availableVoices.find(voice => 
                voice.name.toLowerCase().includes(voiceName.toLowerCase()) && 
                voice.lang === mapping.lang
            );
            if (matchedVoice) {
                console.log('Partial match found:', matchedVoice.name);
                break;
            }
        }
    }
    
    // Strategy 3: Gender-based matching with language
    if (!matchedVoice) {
        const genderKeywords = mapping.gender === 'male' ? 
            ['male', 'man', 'alex', 'daniel', 'fred', 'tom', 'aaron', 'nathan'] : 
            ['female', 'woman', 'samantha', 'karen', 'victoria', 'allison', 'ava', 'susan'];
        
        matchedVoice = availableVoices.find(voice => 
            voice.lang === mapping.lang &&
            genderKeywords.some(keyword => voice.name.toLowerCase().includes(keyword))
        );
        if (matchedVoice) {
            console.log('Gender match found:', matchedVoice.name);
        }
    }
    
    // Strategy 4: Any voice with matching language
    if (!matchedVoice) {
        matchedVoice = availableVoices.find(voice => voice.lang === mapping.lang);
        if (matchedVoice) {
            console.log('Language match found:', matchedVoice.name);
        }
    }
    
    // Strategy 5: Any English voice if target was English
    if (!matchedVoice && mapping.lang.startsWith('en')) {
        matchedVoice = availableVoices.find(voice => voice.lang.startsWith('en'));
        if (matchedVoice) {
            console.log('English fallback found:', matchedVoice.name);
        }
    }
    
    return matchedVoice || availableVoices[0];
}

function speakTextWithSelectedVoice(text, config) {
    /**
     * Speaks text using browser speech synthesis with the selected voice
     * @param {string} text - Text to speak
     * @param {Object} config - Configuration object with voice and language settings
     */
    try {
        if (!('speechSynthesis' in window)) {
            showMessage('Read-aloud not supported in this browser', 'warning');
            return;
        }

        // Function to actually speak the text
        const speakText = () => {
            // Cancel any existing speech
            speechSynthesis.cancel();
            
            // Wait a bit for cancellation to complete
            setTimeout(() => {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.lang = config.language;
                
                // Get fresh voices list every time
                const voices = speechSynthesis.getVoices();
                console.log('Available voices for selection:', voices.length);
                console.log('Selected voice ID:', config.voice);
                
                const selectedVoice = mapVoiceSelection(config.voice, voices, config.language);
                
                if (selectedVoice) {
                    utterance.voice = selectedVoice;
                    console.log('Using voice:', selectedVoice.name, selectedVoice.lang);
                } else {
                    console.log('No voice mapped, using default. Voice ID was:', config.voice);
                }
                
                // Set speech properties based on voice selection
                if (config.voice && config.voice.includes('male')) {
                    utterance.pitch = 0.8; // Lower pitch for male voices
                } else {
                    utterance.pitch = 1.0; // Default pitch for female voices
                }
                
                utterance.rate = 0.9; // Slightly slower for better clarity
                utterance.volume = 1.0; // Full volume
                
                // Add event listeners for feedback
                utterance.onstart = () => {
                    console.log('Speech started');
                    showMessage('Reading text aloud with selected voice...', 'info');
                };
                
                utterance.onend = () => {
                    console.log('Speech ended');
                    showMessage('Finished reading text aloud', 'success');
                };
                
                utterance.onerror = (event) => {
                    console.error('Speech error:', event.error);
                    showMessage(`Read-aloud error: ${event.error}`, 'warning');
                };
                
                console.log('Starting speech synthesis...');
                speechSynthesis.speak(utterance);
                
                // Chrome workaround
                setTimeout(() => {
                    if (speechSynthesis.paused) {
                        speechSynthesis.resume();
                    }
                }, 100);
            }, 50); // Small delay to ensure cancellation completes
        };

        // Check if voices are already loaded
        const voices = speechSynthesis.getVoices();
        if (voices.length > 0) {
            speakText();
        } else {
            // Wait for voices to be loaded
            speechSynthesis.onvoiceschanged = () => {
                speakText();
                speechSynthesis.onvoiceschanged = null; // Remove listener
            };
        }
        
    } catch (error) {
        console.error('Read-aloud error:', error);
        showMessage('Read-aloud failed: ' + error.message, 'warning');
    }
}

function testSpeechSynthesis() {
    /**
     * Comprehensive speech synthesis diagnostics
     */
    console.log('=== Speech Synthesis Diagnostics ===');
    
    // Check basic support
    if (!('speechSynthesis' in window)) {
        console.error('Speech synthesis not supported');
        showMessage('Speech synthesis not supported in this browser', 'danger');
        return;
    }
    
    // Browser info
    console.log('User Agent:', navigator.userAgent);
    console.log('Platform:', navigator.platform);
    
    // Audio context check (for general audio support)
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        console.log('Audio Context State:', audioContext.state);
        if (audioContext.state === 'suspended') {
            audioContext.resume().then(() => {
                console.log('Audio context resumed');
            });
        }
    } catch (e) {
        console.log('Audio Context Error:', e.message);
    }
    
    // Cancel any existing speech
    speechSynthesis.cancel();
    
    // Voice availability
    const voices = speechSynthesis.getVoices();
    console.log('Available voices:', voices.length);
    if (voices.length > 0) {
        console.log('First voice:', voices[0].name, voices[0].lang);
    } else {
        console.log('No voices available, waiting for voices...');
        speechSynthesis.onvoiceschanged = () => {
            const newVoices = speechSynthesis.getVoices();
            console.log('Voices loaded:', newVoices.length);
            if (newVoices.length > 0) {
                console.log('First voice:', newVoices[0].name, newVoices[0].lang);
            }
        };
    }
    
    // Create test utterance
    const testText = "Audio test. Can you hear this message?";
    const utterance = new SpeechSynthesisUtterance(testText);
    
    // Basic settings
    utterance.volume = 1.0;
    utterance.rate = 0.8;
    utterance.pitch = 1.0;
    utterance.lang = 'en-US';
    
    // Set a specific voice if available
    if (voices.length > 0) {
        utterance.voice = voices[0];
        console.log('Using voice:', voices[0].name);
    }
    
    // Event handlers with detailed logging
    utterance.onstart = () => {
        console.log('✓ Speech STARTED');
        showMessage('Audio test started - listen for speech...', 'info');
    };
    
    utterance.onend = () => {
        console.log('✓ Speech ENDED normally');
        showMessage('Audio test completed successfully', 'success');
    };
    
    utterance.onerror = (event) => {
        console.error('✗ Speech ERROR:', event.error);
        showMessage(`Audio test failed: ${event.error}`, 'danger');
    };
    
    utterance.onpause = () => {
        console.log('⏸ Speech PAUSED');
    };
    
    utterance.onresume = () => {
        console.log('▶ Speech RESUMED');
    };
    
    utterance.onboundary = (event) => {
        console.log('📍 Speech boundary:', event.name, event.charIndex);
    };
    
    // Current state before speaking
    console.log('Before speaking:');
    console.log('- Speaking:', speechSynthesis.speaking);
    console.log('- Pending:', speechSynthesis.pending);
    console.log('- Paused:', speechSynthesis.paused);
    
    // Speak the utterance
    console.log('🎤 Starting speech synthesis...');
    speechSynthesis.speak(utterance);
    
    // Monitor progress
    let checkCount = 0;
    const checkInterval = setInterval(() => {
        checkCount++;
        console.log(`Check ${checkCount}:`, {
            speaking: speechSynthesis.speaking,
            pending: speechSynthesis.pending,
            paused: speechSynthesis.paused
        });
        
        if (!speechSynthesis.speaking && !speechSynthesis.pending) {
            clearInterval(checkInterval);
            if (checkCount === 1) {
                console.log('⚠ Speech never started');
                showMessage('Audio test failed to start. Check browser permissions and volume.', 'warning');
            }
        }
        
        if (checkCount > 20) { // Stop after 10 seconds
            clearInterval(checkInterval);
        }
    }, 500);
}