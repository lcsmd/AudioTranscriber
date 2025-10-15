# Final Deployment Guide - Speech Processing with QMClient

## Prerequisites

### 1. Install QMClient Python Library on Server

The `qmclient.py` file needs to be installed on your ubuai server. You can get it from:
- The SYSCOM file on your OpenQM server at 10.1.34.103
- Or use the qmclient.py from the OpenQM documentation you provided

**Installation Steps:**
```bash
# SSH to your ubuai server
ssh lawr@10.1.10.20

# Copy qmclient.py to your Python environment
# Option 1: If it's in OpenQM server, copy it
scp lawr@10.1.34.103:/path/to/qmclient.py /var/www/speech-app/

# Option 2: Or download from OpenQM resources
# Place it in /var/www/speech-app/ or system Python path

# Make sure it's accessible
export PYTHONPATH=/var/www/speech-app:$PYTHONPATH

# Or install it properly
sudo cp qmclient.py /usr/local/lib/python3.12/site-packages/
```

## Files to Deploy

Download these files from Replit and deploy to your server:

### 1. Core Application Files
```bash
cd ~/Downloads  # or wherever you saved the files

# Templates
scp index.html lawr@10.1.10.20:/var/www/speech-app/templates/index.html

# JavaScript
scp comprehensive-processor.js lawr@10.1.10.20:/var/www/speech-app/static/js/comprehensive-processor.js

# Main app
scp app.py lawr@10.1.10.20:/var/www/speech-app/app.py

# Prompts file
scp suggested_prompts.txt lawr@10.1.10.20:/var/www/speech-app/suggested_prompts.txt
```

### 2. Utility Modules (IMPORTANT - Updated!)
```bash
# LLM Processor
scp llm_processor.py lawr@10.1.10.20:/var/www/speech-app/utils/llm_processor.py

# OpenQM Client (UPDATED with QMClient API)
scp openqm_client.py lawr@10.1.10.20:/var/www/speech-app/utils/openqm_client.py
```

## OpenQM Configuration

The system is now configured to use:
- **Server**: 10.1.34.103
- **Port**: 4243 (QMClient default port)
- **Account**: LCS
- **Username**: lawr
- **Password**: apgar-66
- **File**: TRANSCRIPT

### Record Structure (Field Numbers)
1. TIMESTAMP - ISO format timestamp
2. ORIGINAL_TEXT - Full transcript
3. SOURCE_TYPE - audio/youtube/text/document
4. SOURCE_URL - URL if applicable
5. LANGUAGE - Language code
6. DURATION - Duration in seconds
7. FILE_NAME - Original filename
8. HAS_LLM_PROCESSING - 'Y' or 'N'
9. LLM_PROMPT - User's instruction to AI
10. LLM_RESPONSE - AI's response
11. LLM_MODEL - AI model used
12. PROCESSING_TYPE - Processing type

## Restart Service

After copying all files:
```bash
ssh lawr@10.1.10.20 "sudo systemctl restart speech-app"

# Check status
ssh lawr@10.1.10.20 "sudo systemctl status speech-app"

# Check logs if there are issues
ssh lawr@10.1.10.20 "sudo journalctl -xeu speech-app.service --no-pager | tail -50"
```

## Verify Deployment

1. Visit https://speech.lcs.ai
2. Hard refresh (Cmd+Shift+R or Ctrl+Shift+R)
3. Check "Enable AI Processing"
4. Verify suggested prompts dropdown loads
5. Test a transcription with OpenQM save enabled

## Troubleshooting

### If QMClient import fails:
```bash
# On server, test Python import
python3 -c "import qmclient; print('QMClient OK')"

# If fails, check PYTHONPATH
echo $PYTHONPATH

# Add to service file if needed
sudo nano /etc/systemd/system/speech-app.service
# Add: Environment="PYTHONPATH=/var/www/speech-app"
```

### If OpenQM connection fails:
- Verify OpenQM server is running on 10.1.34.103:4243
- Check firewall allows port 4243
- Verify credentials: lawr / apgar-66
- Confirm TRANSCRIPT file exists in LCS account
