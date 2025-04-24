/**
 * Main JavaScript file for the Audio Transcription Service
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips if they exist
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // Copy to clipboard functionality
    const copyButton = document.getElementById('copy-transcription');
    if (copyButton) {
        copyButton.addEventListener('click', function() {
            const transcriptionText = document.getElementById('transcription-text');
            if (!transcriptionText) return;
            
            // Create a temporary textarea element to copy the text
            const textarea = document.createElement('textarea');
            textarea.value = transcriptionText.textContent;
            textarea.setAttribute('readonly', '');
            textarea.style.position = 'absolute';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            
            // Select and copy the text
            textarea.select();
            document.execCommand('copy');
            
            // Remove the temporary textarea
            document.body.removeChild(textarea);
            
            // Show success message
            const originalText = copyButton.innerHTML;
            copyButton.innerHTML = '<i class="fas fa-check"></i> Copied!';
            copyButton.classList.remove('btn-outline-primary');
            copyButton.classList.add('btn-success');
            
            // Restore original button after 2 seconds
            setTimeout(function() {
                copyButton.innerHTML = originalText;
                copyButton.classList.remove('btn-success');
                copyButton.classList.add('btn-outline-primary');
            }, 2000);
        });
    }
    
    // Download transcription functionality
    const downloadButton = document.getElementById('download-transcription');
    if (downloadButton) {
        downloadButton.addEventListener('click', function() {
            const transcriptionText = document.getElementById('transcription-text');
            const filenameElement = document.getElementById('transcription-filename');
            if (!transcriptionText || !filenameElement) return;
            
            // Create filename without the audio extension, but with .txt
            let filename = filenameElement.textContent.trim();
            filename = filename.replace(/\.(mp3|wav)$/i, '.txt');
            
            // Create and download the file
            const blob = new Blob([transcriptionText.textContent], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            
            // Clean up
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        });
    }
});

/**
 * Shows an alert message
 * @param {string} message - The message to display
 * @param {string} type - Alert type (success, danger, warning, info)
 * @param {string} elementId - ID of the element to show the alert in
 */
function showAlert(message, type, elementId) {
    const alertElement = document.getElementById(elementId);
    if (!alertElement) return;
    
    alertElement.className = `alert alert-${type} mt-3`;
    alertElement.innerHTML = message;
    alertElement.classList.remove('d-none');
    
    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
        setTimeout(function() {
            alertElement.classList.add('d-none');
        }, 5000);
    }
}

/**
 * Updates the progress bar
 * @param {number} percent - Progress percentage (0-100)
 * @param {string} elementId - ID of the progress bar element
 */
function updateProgress(percent, elementId) {
    const progressBar = document.getElementById(elementId);
    const progressContainer = document.getElementById(`${elementId}-container`);
    
    if (!progressBar || !progressContainer) return;
    
    if (percent === 0) {
        progressContainer.classList.add('d-none');
        return;
    }
    
    // Ensure percent is between 0 and 100
    percent = Math.min(Math.max(percent, 0), 100);
    
    // Update the progress bar
    progressContainer.classList.remove('d-none');
    progressBar.style.width = `${percent}%`;
    progressBar.setAttribute('aria-valuenow', percent);
    progressBar.textContent = `${Math.round(percent)}%`;
}
