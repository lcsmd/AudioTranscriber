// Application State
const appState = {
    currentStep: 1,
    inputType: null,
    inputData: null,
    processingMode: null, // 'transcription' or 'tts'
    currentJobId: null,
    currentTranscript: null,
    aiUsedInInitialProcess: false
};

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeInputSelection();
    initializeAccordions();
    initializeAIToggle();
    initializeProcessButton();
    initializePostAI();
    loadSuggestedPrompts();
});

// Step Management
function setStep(stepNumber) {
    appState.currentStep = stepNumber;
    
    // Update step indicator
    for (let i = 1; i <= 4; i++) {
        const step = document.getElementById(`step-${i}`);
        step.classList.remove('active', 'completed');
        
        if (i < stepNumber) {
            step.classList.add('completed');
        } else if (i === stepNumber) {
            step.classList.add('active');
        }
    }
    
    // Show/hide cards based on step
    // Keep input-selection-card visible in steps 1 and 2 (so URL/text inputs remain visible)
    document.getElementById('input-selection-card').classList.toggle('hidden', stepNumber > 2);
    document.getElementById('configuration-card').classList.toggle('hidden', stepNumber !== 2);
    document.getElementById('process-card').classList.toggle('hidden', stepNumber !== 3);
    document.getElementById('results-card').classList.toggle('hidden', stepNumber !== 4);
}

// Input Selection
function initializeInputSelection() {
    const inputCards = document.querySelectorAll('.input-type-card');
    const inputAreas = document.querySelectorAll('.input-area');
    
    inputCards.forEach(card => {
        card.addEventListener('click', function() {
            const type = this.dataset.type;
            
            // Update selection
            inputCards.forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');
            
            // Show appropriate input area
            inputAreas.forEach(area => area.classList.remove('active'));
            document.getElementById(`${type}-input-area`).classList.add('active');
            
            // Update app state
            appState.inputType = type;
            appState.processingMode = (type === 'text') ? 'tts' : 'transcription';
            
            // Load appropriate configuration
            loadConfiguration(type);
            
            // Progress to configuration step
            setTimeout(() => {
                setStep(2);
                document.getElementById('configuration-card').classList.remove('hidden');
                document.getElementById('configuration-card').scrollIntoView({ behavior: 'smooth' });
            }, 300);
        });
    });
    
    // File upload handling
    const fileDropZone = document.getElementById('file-drop-zone');
    const fileInput = document.getElementById('file-input');
    
    fileDropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop
    fileDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileDropZone.classList.add('drag-over');
    });
    
    fileDropZone.addEventListener('dragleave', () => {
        fileDropZone.classList.remove('drag-over');
    });
    
    fileDropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        fileDropZone.classList.remove('drag-over');
        fileInput.files = e.dataTransfer.files;
        handleFileSelect();
    });
    
    // Document upload
    const docDropZone = document.getElementById('document-drop-zone');
    const docInput = document.getElementById('document-input');
    
    docDropZone.addEventListener('click', () => docInput.click());
    docInput.addEventListener('change', handleDocumentSelect);
}

function handleFileSelect() {
    const files = document.getElementById('file-input').files;
    const fileList = document.getElementById('file-list');
    
    if (files.length > 0) {
        appState.inputData = files;
        fileList.innerHTML = `<div class="alert alert-info">
            <i class="fas fa-check-circle"></i> ${files.length} file(s) selected
        </div>`;
        setStep(2);
    }
}

function handleDocumentSelect() {
    const file = document.getElementById('document-input').files[0];
    const docInfo = document.getElementById('document-info');
    
    if (file) {
        appState.inputData = file;
        docInfo.innerHTML = `<div class="alert alert-info">
            <i class="fas fa-check-circle"></i> ${file.name}
        </div>`;
        setStep(2);
    }
}

// Configuration Loading
function loadConfiguration(inputType) {
    const basicOptions = document.getElementById('basic-options');
    const outputAccordion = document.getElementById('output-accordion');
    
    if (inputType === 'text') {
        // TTS configuration
        basicOptions.innerHTML = `
            <div class="form-group">
                <label class="form-label">Language</label>
                <select id="tts-language" class="form-select">
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                    <option value="it">Italian</option>
                    <option value="pt">Portuguese</option>
                    <option value="ru">Russian</option>
                    <option value="ja">Japanese</option>
                    <option value="ko">Korean</option>
                    <option value="zh">Chinese</option>
                </select>
            </div>
            <div class="form-group">
                <label class="form-label">Voice</label>
                <select id="tts-voice" class="form-select">
                    <optgroup label="Google Cloud Voices">
                        <option value="google_en_us_female">US English (Female)</option>
                        <option value="google_en_us_male">US English (Male)</option>
                        <option value="google_en_uk_female">UK English (Female)</option>
                        <option value="google_en_uk_male">UK English (Male)</option>
                    </optgroup>
                </select>
            </div>
        `;
        outputAccordion.classList.add('hidden');
        document.getElementById('process-btn-text').textContent = 'Generate Speech';
    } else {
        // Transcription configuration
        basicOptions.innerHTML = `
            <div class="form-group">
                <label class="form-label">Output Language</label>
                <select id="output-language" class="form-select">
                    <option value="en">English</option>
                    <option value="es">Spanish</option>
                    <option value="fr">French</option>
                    <option value="de">German</option>
                    <option value="it">Italian</option>
                    <option value="pt">Portuguese</option>
                    <option value="ru">Russian</option>
                    <option value="ja">Japanese</option>
                    <option value="ko">Korean</option>
                    <option value="zh">Chinese</option>
                </select>
            </div>
        `;
        
        if (inputType === 'youtube') {
            basicOptions.innerHTML += `
                <div class="form-group">
                    <label class="form-label">YouTube Options</label>
                    <label style="display: flex; align-items: center; gap: 0.5rem;">
                        <input type="checkbox" id="pull-transcript" checked>
                        <span>Use existing transcript (if available)</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 0.5rem; margin-top: 0.5rem;">
                        <input type="checkbox" id="transcribe-audio">
                        <span>Transcribe from audio</span>
                    </label>
                </div>
            `;
        }
        
        outputAccordion.classList.remove('hidden');
        document.getElementById('process-btn-text').textContent = 'Start Transcription';
    }
    
    setStep(2);
}

// Accordion Functionality
function initializeAccordions() {
    const accordionHeaders = document.querySelectorAll('.accordion-header');
    
    accordionHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const item = this.parentElement;
            const wasExpanded = item.classList.contains('expanded');
            
            // Toggle expansion
            item.classList.toggle('expanded');
        });
    });
}

// AI Toggle
function initializeAIToggle() {
    const aiToggle = document.getElementById('enable-ai-processing');
    const aiSettings = document.getElementById('ai-settings');
    
    aiToggle.addEventListener('change', function() {
        if (this.checked) {
            aiSettings.classList.remove('hidden');
        } else {
            aiSettings.classList.add('hidden');
        }
    });
    
    // Suggested prompts
    const suggestedPrompts = document.getElementById('suggested-prompts');
    const aiPrompt = document.getElementById('ai-prompt');
    
    suggestedPrompts.addEventListener('change', function() {
        if (this.value) {
            aiPrompt.value = this.options[this.selectedIndex].text;
        }
    });
}

// Load Suggested Prompts
async function loadSuggestedPrompts() {
    try {
        const response = await fetch('/api/suggested-prompts');
        const data = await response.json();
        
        const select = document.getElementById('suggested-prompts');
        data.prompts.forEach(prompt => {
            const option = document.createElement('option');
            option.value = prompt;
            option.textContent = prompt;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load suggested prompts:', error);
    }
}

// Process Button
function initializeProcessButton() {
    // Continue to Process button (advances from config to process step)
    const continueBtn = document.getElementById('continue-to-process');
    
    continueBtn.addEventListener('click', function() {
        setStep(3);
        document.getElementById('process-card').classList.remove('hidden');
        document.getElementById('process-card').scrollIntoView({ behavior: 'smooth' });
    });
    
    // Actual process button
    const processBtn = document.getElementById('process-btn');
    
    processBtn.addEventListener('click', async function() {
        // Track if AI is being used
        appState.aiUsedInInitialProcess = document.getElementById('enable-ai-processing').checked;
        
        // Show progress
        showProgress();
        
        // Process based on input type
        if (appState.inputType === 'file') {
            await processFiles();
        } else if (appState.inputType === 'youtube') {
            await processYouTube();
        } else if (appState.inputType === 'text') {
            await processText();
        } else if (appState.inputType === 'document') {
            await processDocument();
        }
    });
    
    // Reset button
    document.getElementById('reset-btn').addEventListener('click', function() {
        location.reload();
    });
}

// Processing Functions
async function processFiles() {
    const formData = new FormData();
    const files = appState.inputData;
    
    Array.from(files).forEach(file => {
        formData.append('files', file);
    });
    
    const config = getConfiguration();
    formData.append('input_type', 'file');
    formData.append('target_language', config.language);
    formData.append('output_formats', JSON.stringify(config.formats));
    formData.append('llm_config', JSON.stringify(config.ai));
    
    try {
        updateProgress(30, 'Uploading files...');
        
        const response = await fetch('/api/process', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Check if result is immediate (no job_id) or requires polling
            if (result.job_id) {
                appState.currentJobId = result.job_id;
                pollJobStatus(result.job_id);
            } else if (result.transcription) {
                // Direct result - display immediately
                updateProgress(100, 'Processing completed!');
                showResults({ result_text: result.transcription.text, status: 'completed' });
            } else {
                throw new Error('Invalid response format');
            }
        } else {
            throw new Error(result.error || 'Processing failed');
        }
    } catch (error) {
        showError(error.message);
    }
}

async function processYouTube() {
    const url = document.getElementById('youtube-url').value.trim();
    
    if (!url) {
        showError('Please enter a YouTube URL');
        return;
    }
    
    const config = getConfiguration();
    
    const youtubeOptions = {
        pullTranscript: document.getElementById('pull-transcript')?.checked || false,
        transcribeAudio: document.getElementById('transcribe-audio')?.checked || false
    };
    
    try {
        updateProgress(30, 'Processing YouTube content...');
        
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                input_type: 'youtube',
                source_url: url,
                target_language: config.language,
                output_formats: config.formats,
                youtubeOptions: youtubeOptions,
                llm: config.ai
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Check if result is immediate (no job_id) or requires polling
            if (result.job_id) {
                appState.currentJobId = result.job_id;
                pollJobStatus(result.job_id);
            } else if (result.transcription) {
                // Direct result - display immediately
                updateProgress(100, 'Processing completed!');
                showResults({ result_text: result.transcription.text, status: 'completed' });
            } else {
                throw new Error('Invalid response format');
            }
        } else {
            throw new Error(result.error || 'Processing failed');
        }
    } catch (error) {
        showError(error.message);
    }
}

async function processText() {
    const text = document.getElementById('text-input').value.trim();
    
    if (!text) {
        showError('Please enter some text');
        return;
    }
    
    const config = getConfiguration();
    
    try {
        updateProgress(30, 'Generating speech...');
        
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                input_type: 'text',
                input_text: text,
                target_language: config.language,
                voice_id: config.voice,
                output_formats: ['mp3']
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Check if result is immediate (no job_id) or requires polling
            if (result.job_id) {
                appState.currentJobId = result.job_id;
                pollJobStatus(result.job_id);
            } else if (result.transcription) {
                // Direct result - display immediately
                updateProgress(100, 'Processing completed!');
                showResults({ result_text: result.transcription.text, status: 'completed' });
            } else {
                throw new Error('Invalid response format');
            }
        } else {
            throw new Error(result.error || 'Processing failed');
        }
    } catch (error) {
        showError(error.message);
    }
}

async function processDocument() {
    const formData = new FormData();
    formData.append('files', appState.inputData);
    
    const config = getConfiguration();
    formData.append('input_type', 'document');
    formData.append('target_language', config.language);
    formData.append('output_formats', JSON.stringify(config.formats));
    formData.append('llm_config', JSON.stringify(config.ai));
    
    try {
        updateProgress(30, 'Processing document...');
        
        const response = await fetch('/api/process', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Check if result is immediate (no job_id) or requires polling
            if (result.job_id) {
                appState.currentJobId = result.job_id;
                pollJobStatus(result.job_id);
            } else if (result.transcription) {
                // Direct result - display immediately
                updateProgress(100, 'Processing completed!');
                showResults({ result_text: result.transcription.text, status: 'completed' });
            } else {
                throw new Error('Invalid response format');
            }
        } else {
            throw new Error(result.error || 'Processing failed');
        }
    } catch (error) {
        showError(error.message);
    }
}

// Get Configuration
function getConfiguration() {
    const config = {
        language: null,
        voice: null,
        formats: [],
        ai: {
            enabled: false
        }
    };
    
    if (appState.processingMode === 'tts') {
        config.language = document.getElementById('tts-language')?.value || 'en';
        config.voice = document.getElementById('tts-voice')?.value || 'google_en_us_female';
    } else {
        config.language = document.getElementById('output-language')?.value || 'en';
        
        const formatChecks = document.querySelectorAll('input[id^="format-"]:checked');
        config.formats = Array.from(formatChecks).map(cb => cb.value);
        if (config.formats.length === 0) config.formats = ['text'];
    }
    
    // AI configuration
    const aiEnabled = document.getElementById('enable-ai-processing').checked;
    if (aiEnabled) {
        config.ai = {
            enabled: true,
            prompt: document.getElementById('ai-prompt').value.trim() || 'Summarize this text in 3-5 key points',
            model: document.getElementById('ai-model').value,
            saveToOpenQM: document.getElementById('save-to-openqm').checked,
            exportMarkdown: document.getElementById('export-markdown').checked
        };
    }
    
    return config;
}

// Progress Management
function showProgress() {
    document.getElementById('progress-card').classList.remove('hidden');
    document.getElementById('process-card').classList.add('hidden');
    setStep(3);
}

function updateProgress(percentage, message) {
    document.getElementById('progress-fill').style.width = `${percentage}%`;
    document.getElementById('progress-status').textContent = message;
}

// Job Status Polling
async function pollJobStatus(jobId) {
    const interval = setInterval(async () => {
        try {
            const response = await fetch(`/api/job-status/${jobId}`);
            const status = await response.json();
            
            updateProgress(status.progress_percentage, status.status_message);
            
            if (status.status === 'completed') {
                clearInterval(interval);
                showResults(status);
            } else if (status.status === 'failed') {
                clearInterval(interval);
                showError(status.error_message || 'Processing failed');
            }
        } catch (error) {
            clearInterval(interval);
            showError('Failed to get job status');
        }
    }, 500);
}

// Results Display
function showResults(jobData) {
    document.getElementById('progress-card').classList.add('hidden');
    document.getElementById('results-card').classList.remove('hidden');
    setStep(4);
    
    const resultContent = document.getElementById('result-content');
    const resultDownloads = document.getElementById('result-downloads');
    const aiEnhancement = document.getElementById('ai-enhancement-section');
    
    // Display transcript/result
    if (jobData.result_text) {
        appState.currentTranscript = jobData.result_text;
        
        resultContent.innerHTML = `
            <div class="result-preview">${jobData.result_text.replace(/\n/g, '<br>')}</div>
        `;
        
        // Show AI enhancement if not already used
        const isTTSJob = jobData.result_files?.some(f => f.endsWith('.mp3') || f.endsWith('.wav'));
        if (!isTTSJob && !appState.aiUsedInInitialProcess) {
            aiEnhancement.classList.remove('hidden');
        }
    }
    
    // Display download links
    if (jobData.result_files && jobData.result_files.length > 0) {
        resultDownloads.innerHTML = jobData.result_files.map(file => {
            const ext = file.split('.').pop().toUpperCase();
            return `<a href="/download/${file}" class="chip" target="_blank">
                <i class="fas fa-download"></i> ${ext}
            </a>`;
        }).join('');
    }
    
    showMessage('Processing completed successfully!', 'success');
}

// Post-AI Processing
function initializePostAI() {
    const quickActionBtns = document.querySelectorAll('.quick-action-btn[data-prompt]');
    const customAIBtn = document.getElementById('custom-ai-btn');
    const customPanel = document.getElementById('custom-ai-panel');
    const executeBtn = document.getElementById('execute-post-ai');
    
    quickActionBtns.forEach(btn => {
        btn.addEventListener('click', async function() {
            const prompt = this.dataset.prompt;
            await processWithAI(prompt);
        });
    });
    
    customAIBtn.addEventListener('click', function() {
        customPanel.classList.toggle('hidden');
    });
    
    executeBtn.addEventListener('click', async function() {
        const prompt = document.getElementById('post-ai-prompt').value.trim();
        if (prompt) {
            await processWithAI(prompt);
        } else {
            showError('Please enter instructions for the AI');
        }
    });
}

async function processWithAI(prompt) {
    if (!appState.currentTranscript) {
        showError('No transcript available');
        return;
    }
    
    try {
        showMessage('Processing with AI...', 'info');
        
        const response = await fetch('/api/process-text-with-ai', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: appState.currentTranscript,
                prompt: prompt,
                model: 'llama2',
                save_to_openqm: false,
                export_markdown: false
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayAIResult(result.processed_text, result.files);
            showMessage('AI processing complete!', 'success');
        } else {
            throw new Error(result.error || 'AI processing failed');
        }
    } catch (error) {
        showError(error.message);
    }
}

function displayAIResult(text, files) {
    const resultContent = document.getElementById('result-content');
    
    resultContent.innerHTML += `
        <hr style="margin: 2rem 0;">
        <h4><i class="fas fa-brain" style="color: var(--primary-color);"></i> AI Enhanced Result</h4>
        <div class="result-preview" style="background: #eff6ff;">${text.replace(/\n/g, '<br>')}</div>
    `;
    
    if (files && files.length > 0) {
        const downloads = document.getElementById('result-downloads');
        files.forEach(file => {
            const ext = file.split('.').pop().toUpperCase();
            downloads.innerHTML += `<a href="/download/${file}" class="chip" target="_blank">
                <i class="fas fa-download"></i> AI ${ext}
            </a>`;
        });
    }
    
    // Hide AI enhancement section after use
    document.getElementById('ai-enhancement-section').classList.add('hidden');
}

// Utility Functions
function showMessage(message, type) {
    const container = document.getElementById('status-messages');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-circle' : 'info-circle'}"></i> ${message}`;
    container.appendChild(alert);
    
    setTimeout(() => alert.remove(), 5000);
}

function showError(message) {
    document.getElementById('progress-card').classList.add('hidden');
    showMessage(message, 'danger');
}
