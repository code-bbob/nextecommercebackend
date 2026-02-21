# Complete Setup Guide: Ollama + Product Description Updates

This guide walks you through setting up Ollama for local, free product description generation.

## ✅ Complete Flow

```
Names (Done) → Descriptions (Ollama) → Meta Descriptions (Ollama)
```

---

## 📋 Prerequisites

- Python 3.8+ (you already have this)
- ~10GB free disk space (for model download)
- ~4GB RAM (Ollama runs in background)
- Linux/Mac/Windows

---

## 🚀 Step-by-Step Setup

### Step 1: Install Ollama

**Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**macOS:**
```bash
# Download from https://ollama.ai and install
# Or use Homebrew:
brew install ollama
```

**Windows:**
```bash
# Download installer from https://ollama.ai/download/windows
# Run the installer
```

### Step 2: Download the Model

Open a terminal and run:

```bash
ollama pull mistral
```

This downloads Mistral 7B (~4GB). It's:
- ✅ Fast (generates descriptions in ~20-40 seconds each)
- ✅ Good quality (high accuracy)
- ✅ Lean (4GB vs 13GB+ for larger models)

**Alternative models** (if you want something different):
```bash
ollama pull llama2           # Slower but can be more creative
ollama pull neural-chat      # Optimized for chat
ollama pull orca-mini        # Very fast but lower quality
```

Monitor download:
```bash
# You'll see progress:
# pulling 4b5e8cde6ad8... 100%  [===========>] 1.3 GB / 3.2 GB
# ... wait for 100% completion
```

### Step 3: Start Ollama Server

Open a **new terminal** and run:

```bash
ollama serve
```

You should see:
```
2024/02/05 10:30:45 "GET / HTTP/1.1" 200 -
```

**Keep this terminal open!** The server must stay running.

### Step 4: Test Ollama Connection

Open another terminal and test:

```bash
curl http://localhost:11434/api/tags
```

You should see JSON with your downloaded model:
```json
{
  "models": [
    {
      "name": "mistral:latest",
      ...
    }
  ]
}
```

✅ If you see this, Ollama is running correctly!

### Step 5: Install Python Dependencies

```bash
cd /home/bibhab/digitech-ecommerce/backend
pip install requests  # For Ollama API calls
```

Check your Django environment is ready:
```bash
python manage.py shell
# Type: exit()
```

---

## 🎯 Running the Scripts

### Option A: Update Descriptions First

```bash
# Preview (shows sample with first product)
python update_descriptions_ollama.py --dry-run

# Run the actual update
python update_descriptions_ollama.py
```

**What happens:**
- Processes 393 products one-by-one
- Each takes ~20-40 seconds
- Total time: ~2-3 hours
- Saves progress after each product (resumable)

### Option B: Update Meta Descriptions

```bash
# Preview
python update_metas_ollama.py --dry-run

# Run the actual update
python update_metas_ollama.py
```

**What happens:**
- Processes 393 products one-by-one
- Each takes ~10-20 seconds (shorter output)
- Total time: ~1-2 hours
- Saves progress after each product (resumable)

---

## 📊 Recommended Order

1. **Names** ✅ (Already done - 19 requests with Gemini)
2. **Descriptions** (3+ hours with Ollama)
3. **Meta Descriptions** (2+ hours with Ollama)

---

## 💡 Advanced Options

### Process Only Specific Category

```bash
python update_descriptions_ollama.py --category laptop
python update_descriptions_ollama.py --category phone
```

### Process Limited Number

```bash
python update_descriptions_ollama.py --limit 50  # Only first 50
```

### Use Different Model

```bash
python update_descriptions_ollama.py --model llama2
```

### Resume After Interruption

If the script stops:

```bash
python update_descriptions_ollama.py
```

It automatically resumes from where it left off using `description_update_ollama_progress.json`

---

## 📝 Monitoring

### View Logs

```bash
tail -f description_update_ollama.log
tail -f meta_update_ollama.log
```

### Check Progress File

```bash
cat description_update_ollama_progress.json | jq
```

Shows:
- How many processed
- How many failed
- Last batch number
- When it started

---

## ⚠️ Troubleshooting

### "Cannot connect to Ollama at http://localhost:11434"

**Solution:** Make sure Ollama server is running
```bash
# Terminal 1:
ollama serve

# Terminal 2 (run your script):
python update_descriptions_ollama.py
```

### "Model 'mistral' not found"

**Solution:** Download it
```bash
ollama pull mistral
```

### Script is very slow (>1 minute per product)

**Possible causes:**
- Not enough RAM - Ollama may be swapping to disk
- CPU only mode - check if you have GPU support
- Model too large - try smaller model like `orca-mini`

### Ollama crashes or freezes

**Solutions:**
```bash
# Restart Ollama:
pkill ollama
ollama serve

# Or use smaller model:
ollama pull orca-mini
python update_descriptions_ollama.py --model orca-mini
```

---

## 🎯 Performance Tips

1. **Close unnecessary programs** - More RAM for Ollama
2. **Use Mistral model** - Best speed/quality balance
3. **Run on GPU if available** - Much faster (check Ollama docs)
4. **Process during off-hours** - Won't impact users

---

## ✅ Success Checklist

Before running:

- [ ] Ollama installed (`ollama --version`)
- [ ] Model downloaded (`ollama list` shows mistral)
- [ ] Ollama server running (`curl http://localhost:11434/api/tags` works)
- [ ] Django working (`python manage.py shell` works)
- [ ] requests installed (`pip list | grep requests`)
- [ ] Enough disk space (`df -h`)

---

## 🎓 What's Happening Behind the Scenes

1. Script fetches product from database
2. Creates a prompt with product name, brand, category
3. Sends to Ollama (runs locally on your machine)
4. Ollama uses Mistral model to generate description
5. Parses the response
6. Saves to database
7. Records progress in JSON file
8. Moves to next product

**Total flow:**
- Names: Gemini API (cloud) - 19 requests
- Descriptions: Ollama (local) - 393 products
- Meta: Ollama (local) - 393 products

---

## 🚀 Ready?

```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Test it works
curl http://localhost:11434/api/tags

# Terminal 3: Run the update
cd /home/bibhab/digitech-ecommerce/backend
python update_descriptions_ollama.py --dry-run
python update_descriptions_ollama.py
```

Let it run! Grab coffee ☕ - it'll take a few hours but it's 100% FREE and completely under your control.

---

## 📞 Need Help?

If something fails:
1. Check `description_update_ollama.log` for errors
2. Check `description_update_ollama_progress.json` to see progress
3. Just run the script again - it resumes automatically
4. Try with smaller batch or different model

Good luck! 🎉
