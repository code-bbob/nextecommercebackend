# 👣 Step-by-Step Walkthrough

Follow these steps exactly to set up and run the SEO generator.

## STEP 1: Prepare Your Environment

Open your terminal in the backend directory:
```bash
cd /home/bibhab/digitech-ecommerce/backend
source ../env/bin/activate  # Activate virtualenv
```

**Expected output:** Your terminal should show `(env)` prefix

---

## STEP 2: Copy Configuration Template

```bash
cp .env.example .env
```

**What this does:** Creates a `.env` file for your API key

**Verification:**
```bash
ls -la .env
```

Should show `.env` file exists.

---

## STEP 3: Get Your Free API Key

1. Open browser: https://aistudio.google.com/apikey
2. Click "Create API Key"
3. Choose "Create API key in new Google Cloud project"
4. **Copy the key** (it will be something like `AIzaSy...`)

---

## STEP 4: Add API Key to .env

Edit the `.env` file:
```bash
nano .env
```

Replace this line:
```
GOOGLE_API_KEY=your-gemini-api-key-here
```

With your actual key:
```
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXX
```

Save and exit: `Ctrl+X`, then `Y`, then `Enter`

**Verification:**
```bash
cat .env | grep GOOGLE_API_KEY
```

Should show your key (not the placeholder).

---

## STEP 5: Install Dependency

```bash
pip install python-dotenv
```

**Expected output:** "Successfully installed python-dotenv..."

---

## STEP 6: Validate Setup

This script checks everything is working:
```bash
python validate_setup.py
```

**Expected output:**
```
🔍 SEO GENERATOR - SETUP VALIDATION

1️⃣  Checking .env file...
   ✅ .env file found

2️⃣  Checking GOOGLE_API_KEY...
   ✅ API key found: AIzaSy...

3️⃣  Checking Python packages...
   ✅ Django
   ✅ google-genai
   ✅ python-dotenv

4️⃣  Checking Django setup...
   ✅ Django configured

5️⃣  Checking database connection...
   ✅ Database connected (500 products found)

6️⃣  Checking Gemini API connection...
   ✅ Gemini API working (hello)

7️⃣  Checking main script...
   ✅ generate_seo_complete.py found

8️⃣  Checking sample product...
   ✅ Sample product: MSI Thin 15 B12VE...

✨ ALL CHECKS PASSED!
```

**If you see ❌ errors:** Check the error message and STEP 3-5 again.

---

## STEP 7: Preview (CRITICAL - DO THIS FIRST!)

```bash
python generate_seo_complete.py --dry-run
```

**What this does:**
- Shows you what WOULD be generated
- Generates one sample (name, description, meta)
- Does NOT change anything in database
- Takes 1-2 minutes

**Expected output:**
```
🚀 SEO PRODUCT OPTIMIZER
================================================================================

📊 STATISTICS:
   • Products to process: 500
   • Already processed: 0
   • Failed previously: 0
   • Batch size: 5

📞 API CALLS:
   • Expected total: 100 calls
   • Name generation: 20 calls
   • Description generation: 20 calls
   • Meta generation: 20 calls

🔍 DRY RUN MODE (preview only)

================================================================================
📦 SAMPLE PRODUCT: MSI Thin 15 B12VE i5 12450H | RTX 4050...

🔴 CURRENT NAME (XX chars):
   MSI Thin 15 B12VE i5 12450H | RTX 4050 6GB | 15.6" FHD...

🟢 NEW NAME (XX chars):
   MSI Thin 15 B12VE - Intel i5 12450H (RTX 4050, 15.6" FHD...)

🔴 CURRENT DESCRIPTION:
   [old description...]

🟢 NEW DESCRIPTION:
   [new AI-generated description...]

🔴 CURRENT META:
   [old meta...]

🟢 NEW META:
   [new AI-generated meta description...]

================================================================================
✨ Preview complete! Would update 500 products with 100 API calls
```

**Check the NEW output:**
- Does the new name look better?
- Is the description clear and helpful?
- Is the meta description good for Google?

If YES → Continue to STEP 8
If NO → Check the prompts in the script and adjust

---

## STEP 8: Run the Full Script

```bash
python generate_seo_complete.py
```

**Expected output:**
```
🚀 SEO PRODUCT OPTIMIZER
================================================================================

📊 STATISTICS:
   • Products to process: 500
   • Already processed: 0
   • Failed previously: 0
   • Batch size: 5

📞 API CALLS:
   • Expected total: 100 calls
   • Cost estimate: <$0.02 or FREE (free tier, 15 calls/min)
   • Time estimate: 5-10 minutes

================================================================================
⚠️  ABOUT TO UPDATE 500 PRODUCTS
================================================================================

This will:
  • Update product names
  • Update product descriptions
  • Update meta descriptions
  • Use ~100 API calls
  • Make changes permanent in database

Are you sure? Type 'yes' to continue: 
```

**Type:** `yes` and press Enter

**Then you'll see:**
```
[Batch   1/20] Processing 5 products... ✅ 5 saved (5/500 total)
[Batch   2/20] Processing 5 products... ✅ 5 saved (10/500 total)
[Batch   3/20] Processing 5 products... ✅ 5 saved (15/500 total)
...
[Batch  20/20] Processing 5 products... ✅ 5 saved (500/500 total)

================================================================================
✨ COMPLETE!
================================================================================

📊 RESULTS:
   ✅ Successfully updated: 500 products
   ❌ Failed: 0 products
   📞 API calls used: 100
   ⏱️  Time taken: 456.3 seconds (7.6 minutes)
   💰 Estimated cost: <$0.02 or FREE
   ⏰ Completed: 2026-02-04 15:30:45

📝 Logs saved to: seo_generation.log
📊 Progress saved to: seo_generation_progress.json
```

---

## STEP 9: Monitor Progress (While Running)

In a separate terminal window:
```bash
tail -f seo_generation.log
```

This shows you real-time progress while the script runs.

---

## STEP 10: Verify Results

After script completes:

### Check logs
```bash
cat seo_generation.log | tail -20
```

### Check progress file
```bash
cat seo_generation_progress.json
```

### Check database
- Go to Django admin: http://localhost:8000/admin
- Check "Products" section
- Verify names changed
- Click on a product to verify description and meta

---

## STEP 11: Monitor SEO Impact (Next Steps)

After 1-2 weeks:
- Check Google Search Console
- Look for click-through rate improvement
- Monitor keyword rankings
- Check impressions vs clicks

---

## ⚠️ What If Something Goes Wrong?

### Script stops with error

```bash
# Just run it again - it resumes!
python generate_seo_complete.py
```

It saves progress to `seo_generation_progress.json` and picks up where it left off.

### API rate limit error

```bash
# Wait a few minutes (free tier = 15 calls/min)
# Then run again
python generate_seo_complete.py
```

### Poor quality output

```bash
# Run preview again
python generate_seo_complete.py --dry-run

# Check a few manually in Django admin
# If quality is bad, can manually edit or adjust prompts in script
```

### Key validation failed

```bash
# Verify key is in .env
cat .env | grep GOOGLE_API_KEY

# Make sure it's not the placeholder
# Get new key from: https://aistudio.google.com/apikey
```

---

## 🎯 Success Checklist

After STEP 10:

- [ ] `.env` file created
- [ ] API key added to `.env`
- [ ] `validate_setup.py` passed all checks
- [ ] Previewed with `--dry-run`
- [ ] Liked the sample output
- [ ] Ran `generate_seo_complete.py`
- [ ] No errors in logs
- [ ] All 500 products updated
- [ ] Verified in Django admin
- [ ] Names are better (60-100 chars)
- [ ] Descriptions are unique
- [ ] Meta descriptions look good

---

## 🎉 You're Done!

Congratulations! Your products are now SEO-optimized! 

### What changed:
✅ 500 product names improved
✅ 500 product descriptions generated
✅ 500 meta descriptions generated
✅ All unique and SEO-optimized
✅ Ready for Google to crawl

### Next steps:
1. Monitor Google Search Console
2. Track click-through rate improvement
3. Check keyword rankings in 2-4 weeks
4. Celebrate the SEO boost! 🚀

---

## 📞 Quick Reference

```bash
# Preview
python generate_seo_complete.py --dry-run

# Run full
python generate_seo_complete.py

# Resume after interrupt
python generate_seo_complete.py

# Just laptops
python generate_seo_complete.py --category laptop

# First 50 only
python generate_seo_complete.py --limit 50

# Check progress
tail -f seo_generation.log

# Check results
cat seo_generation_progress.json
```

Good luck! 🚀
