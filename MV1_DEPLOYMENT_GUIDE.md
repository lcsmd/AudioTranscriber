# OpenQM Integration via mv1 Windows Server

## Architecture

Instead of installing qmclient on the Linux server, we run a simple Flask service on **mv1** (10.1.34.103) which already has OpenQM and qmclient configured. The speech app on ubuai calls this service via REST API.

```
Speech App (ubuai)  →  OpenQM Service (mv1)  →  OpenQM Database (mv1)
   10.1.10.20            10.1.34.103:5001         LCS/TRANSCRIPT
```

## Step 1: Setup OpenQM Service on mv1 (Windows Server)

### 1.1 Download Files to mv1
Download `openqm_service.py` from this Replit and save it to mv1, for example:
- `C:\openqm\openqm_service.py`

### 1.2 Install Flask on mv1 (if not already installed)
```cmd
pip install flask
```

### 1.3 Start the OpenQM Service
```cmd
cd C:\openqm
python openqm_service.py
```

You should see:
```
============================================================
OpenQM Save Service for mv1 (10.1.34.103)
============================================================
Account: LCS
File: TRANSCRIPT
Starting on http://0.0.0.0:5001
============================================================
```

### 1.4 Test the Service (Optional)
From another terminal on mv1:
```cmd
curl http://localhost:5001/health
```

Should return: `{"status":"ok","service":"openqm-save-service"}`

### 1.5 Keep the Service Running
For production, you may want to:
- Run as a Windows Service
- Use Task Scheduler to start on boot
- Or use a process manager like NSSM (Non-Sucking Service Manager)

## Step 2: Deploy Updated Files to ubuai (Speech App Server)

### 2.1 Download from Replit
Download these files:
1. `templates/index.html`
2. `static/js/comprehensive-processor.js`
3. `app.py`
4. `suggested_prompts.txt`
5. `utils/llm_processor.py`
6. `utils/openqm_client.py` **(UPDATED to call mv1 service)**

### 2.2 Upload to ubuai
```bash
cd ~/Downloads  # wherever you saved the files

scp index.html lawr@10.1.10.20:/var/www/speech-app/templates/
scp comprehensive-processor.js lawr@10.1.10.20:/var/www/speech-app/static/js/
scp app.py lawr@10.1.10.20:/var/www/speech-app/
scp suggested_prompts.txt lawr@10.1.10.20:/var/www/speech-app/
scp llm_processor.py lawr@10.1.10.20:/var/www/speech-app/utils/
scp openqm_client.py lawr@10.1.10.20:/var/www/speech-app/utils/
```

### 2.3 Restart Speech App
```bash
ssh lawr@10.1.10.20 "sudo systemctl restart speech-app"

# Check status
ssh lawr@10.1.10.20 "sudo systemctl status speech-app"
```

## Step 3: Test the Integration

1. Visit https://speech.lcs.ai
2. Upload an audio file or enter text
3. Check "Enable AI Processing"
4. Select a suggested prompt or write your own
5. Check "Save to OpenQM Database"
6. Submit

The transcript and AI analysis will be saved to the TRANSCRIPT file in the LCS account on mv1.

## Record Structure in OpenQM

The TRANSCRIPT file will contain records with these fields (separated by field marks):

1. TIMESTAMP
2. ORIGINAL_TEXT (full transcript)
3. SOURCE_TYPE
4. SOURCE_URL
5. LANGUAGE
6. DURATION
7. FILE_NAME
8. HAS_LLM_PROCESSING ('Y' or 'N')
9. LLM_PROMPT (user's instruction to AI)
10. LLM_RESPONSE (AI's response)
11. LLM_MODEL
12. PROCESSING_TYPE

## Troubleshooting

### Speech app can't connect to OpenQM service:
```bash
# On ubuai, test connection
curl http://10.1.34.103:5001/health
```

If it fails:
- Check if openqm_service.py is running on mv1
- Check Windows Firewall allows port 5001
- Verify network connectivity between servers

### OpenQM service errors:
- Check that qmclient is properly installed on mv1
- Verify TRANSCRIPT file exists in LCS account
- Check credentials (lawr/apgar-66)
- Review Windows Event Viewer or service logs

## Advantages of This Approach

✅ No need to install qmclient on Linux server  
✅ Uses existing mv1 OpenQM setup  
✅ Simple REST API communication  
✅ Easy to debug and maintain  
✅ Windows and Linux servers work together seamlessly
