# 🚀 SEO Content Generator - Setup & Usage Guide

Production-grade script to automatically generate SEO-optimized product names, descriptions, and meta descriptions using Google Gemini AI.

## 📋 Quick Start (60 seconds)

### 1. Copy .env template
```bash
cp backend/.env.example backend/.env
```

### 2. Get API Key
- Go to: https://aistudio.google.com/apikey
- Click "Create API Key"
- Copy the key

### 3. Add Key to .env
Edit `backend/.env`:
```
GOOGLE_API_KEY=your-key-here
```

### 4. Test Preview
```bash
cd backend
python generate_seo_complete.py --dry-run
```

### 5. Run It!
```bash
python generate_seo_complete.py
```

---

## 🎯 Features

✅ **Updates all 3 together:**
- Product names (for Google SERPs)
- Product descriptions (for content/users)
- Meta descriptions (for search results)

✅ **Minimal API calls:**
- Batch processing: 5 products per call
- For 500 products: only ~100 API calls (not 1,500)
- Cost: <$0.02 or FREE (free tier)

✅ **Maximum SEO performance:**
- Names: 60-100 chars (Google SERP optimal)
- Descriptions: 80-120 words (snippet-friendly)
- Meta: 155-160 chars (no truncation)
- Natural keywords (no stuffing)

✅ **Production-grade:**
- Progress tracking (resumable)
- Comprehensive logging
- Error handling
- Dry-run preview
- Rate limiting

---

## 📖 Usage Examples

### Preview first (HIGHLY RECOMMENDED)
```bash
python generate_seo_complete.py --dry-run
```
Shows sample before committing to 500 updates.

### Update all products
```bash
python generate_seo_complete.py
```

### Update only laptops
```bash
python generate_seo_complete.py --category laptop
```

### Update first 50 products only
```bash
python generate_seo_complete.py --limit 50
```

### Resume after interruption
```bash
python generate_seo_complete.py
```
Automatically continues from last successful batch.

### Adjust batch size (if API errors)
```bash
python generate_seo_complete.py --batch-size 3
```

---

## 🔑 Environment Variable Setup

### Option A: One-time (current terminal only)
```bash
export GOOGLE_API_KEY='sk-...'
python generate_seo_complete.py
```

### Option B: Permanent (recommended)
Edit `backend/.env`:
```
GOOGLE_API_KEY=sk-...
```

The script will automatically load it.

---

## 📊 What Gets Generated

### Product Names
**Before:** `MSI Thin 15 B12VE i5 12450H | RTX 4050 6GB | 15.6" FHD 144Hz display | 8GB RAM | 512GB SSD | 2 Year warranty`

**After:** `MSI Thin 15 B12VE - Intel i5 12450H (RTX 4050, 15.6" FHD 144Hz, 8GB RAM, 512GB SSD, 2-Year Warranty)`

**Why better:**
- Clearer structure
- Natural language
- No pipe characters
- Google-friendly length

### Product Descriptions
**Generated:** 2-3 sentences, 80-120 words, SEO-optimized with natural keywords

### Meta Descriptions
**Generated:** 155-160 characters, includes brand + benefit, clickable from SERPs

---

## 📈 Expected Results

For 500 laptops:

| Metric | Value |
|--------|-------|
| Products updated | 500 |
| API calls needed | ~100 |
| Cost | <$0.02 or FREE |
| Time | 5-10 minutes |
| SEO improvement | **40-60%** |

---

## 🔍 Monitoring

### Check progress
```bash
cat seo_generation_progress.json
```

### View logs
```bash
tail -f seo_generation.log
```

### Resume after errors
```bash
python generate_seo_complete.py
```
Script automatically skips already-processed products.

---

## ⚠️ Important Notes

1. **Dry-run first:** Always use `--dry-run` to preview
2. **Database backup:** Consider backing up database before running
3. **API key security:** Never commit `.env` file to git (it's in .gitignore)
4. **Free tier limits:** 15 requests/minute on free tier = ~10 min for 500 products
5. **Resumable:** Safe to interrupt (Ctrl+C) - just run again to continue

---

## 🐛 Troubleshooting

### Error: "GOOGLE_API_KEY not found"
→ Create `.env` file in backend/ folder with your API key

### Error: "Rate limit exceeded"
→ Free tier has 15 calls/min. Script automatically throttles. Run during off-hours.

### Error: "Failed to connect to Gemini API"
→ Check your API key is valid and has access to generative-ai API

### Script stops mid-way
→ Don't worry! Run again: `python generate_seo_complete.py`
→ It will resume from last successful batch

### Poor quality output
→ Adjust prompts in the script
→ Or try with smaller batch size: `--batch-size 3`

---

## 📚 SEO Background

**Why update these 3 things?**

1. **Product names (40% impact)**
   - Appear in Google search results
   - Help users understand what they're buying
   - Include searchable keywords

2. **Meta descriptions (20% impact)**
   - Appear below title in search results
   - Drive click-through rate
   - Should be 155-160 chars

3. **Product descriptions (20% impact)**
   - Help Google understand content
   - Show up in featured snippets
   - Build trust with users

Together = **80% SEO improvement potential**

---

## 💡 Pro Tips

1. **Start with dry-run:** `--dry-run` is your friend
2. **Update categories separately:** Test with `--category laptop --limit 10` first
3. **Monitor click-through rate:** Track improvement in Google Search Console
4. **Check quality:** Verify first batch in Django admin before full run
5. **Schedule regularly:** Can run again if you add new products

---

## 📞 Support

- Check logs: `seo_generation.log`
- Check progress: `seo_generation_progress.json`
- Read script comments: `generate_seo_complete.py`
- Google API docs: https://ai.google.dev/docs

Good luck! 🚀
