# Deploy UI Updates to Production Server

## Quick Deployment Steps

### Step 1: Download files from Replit
Download these 4 files from your Replit to your local computer:
- `templates/index.html`
- `static/js/comprehensive-processor.js`
- `app.py`
- `suggested_prompts.txt`

### Step 2: Upload to your server

**Using SCP (from your local computer terminal):**

```bash
# Navigate to where you downloaded the files
cd ~/Downloads  # or wherever you saved them

# Copy files to server
scp index.html lawr@10.1.10.20:/home/lawr/speech-app/templates/
scp comprehensive-processor.js lawr@10.1.10.20:/home/lawr/speech-app/static/js/
scp app.py lawr@10.1.10.20:/home/lawr/speech-app/
scp suggested_prompts.txt lawr@10.1.10.20:/home/lawr/speech-app/
```

**Or using SFTP client** (like FileZilla, Cyberduck):
1. Connect to: `lawr@10.1.10.20`
2. Navigate to `/home/lawr/speech-app/`
3. Upload:
   - `index.html` → `templates/` folder
   - `comprehensive-processor.js` → `static/js/` folder
   - `app.py` → root folder
   - `suggested_prompts.txt` → root folder

### Step 3: Restart the service

SSH into your server and restart:

```bash
ssh lawr@10.1.10.20
sudo systemctl restart speech-app
```

### Step 4: Test

Visit https://speech.lcs.ai and hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

---

## Alternative: Direct from Replit (if you have SSH keys set up)

If your Replit can SSH to your server:

```bash
scp templates/index.html lawr@10.1.10.20:/home/lawr/speech-app/templates/
scp static/js/comprehensive-processor.js lawr@10.1.10.20:/home/lawr/speech-app/static/js/
scp app.py lawr@10.1.10.20:/home/lawr/speech-app/
scp suggested_prompts.txt lawr@10.1.10.20:/home/lawr/speech-app/
ssh lawr@10.1.10.20 "sudo systemctl restart speech-app"
```
