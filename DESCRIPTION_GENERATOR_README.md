# Product Description Generator Scripts

Two Python scripts to automatically generate unique, SEO-friendly descriptions for your products using Google Gemini AI.

## Setup

### 1. Get Google API Key
- Go to https://aistudio.google.com/apikey
- Create a new API key (free tier available)
- Copy the key

### 2. Set Environment Variable
```bash
export GOOGLE_API_KEY='your-api-key-here'
```

Or permanently add to your `.bashrc` or `.bash_profile`:
```bash
echo "export GOOGLE_API_KEY='your-api-key-here'" >> ~/.bashrc
source ~/.bashrc
```

### 3. Activate Django Environment
```bash
cd /home/bibhab/digitech-ecommerce/backend
source ../env/bin/activate
```

---

## Script 1: Basic Script (`generate_descriptions.py`)

Simple, straightforward approach with progress saving.

### Features:
- ✅ Shows sample before processing
- ✅ Saves progress to JSON file (resume-friendly)
- ✅ Processes in batches
- ✅ Includes delay to avoid rate limiting
- ✅ Generates both description and meta description
- ✅ Tracks failed products

### Usage:
```bash
python generate_descriptions.py
```

### Output:
- Updates `description` and `meta_description` fields
- Creates `description_generation_progress.json` to track progress
- Shows real-time progress with ✅/❌ indicators

### Resume After Error:
Simply run the script again - it automatically continues from where it left off.

---

## Script 2: Advanced Script (`generate_descriptions_advanced.py`)

More flexible with command-line options.

### Features:
- ✅ Dry-run mode (preview without saving)
- ✅ Filter by category
- ✅ Process limited number of products
- ✅ Generate meta keywords too
- ✅ Skip first N products
- ✅ Configurable batch size

### Usage Examples:

**Dry run (preview only):**
```bash
python generate_descriptions_advanced.py --dry-run
```

**Process only laptops:**
```bash
python generate_descriptions_advanced.py --category laptop
```

**Process only first 50 products:**
```bash
python generate_descriptions_advanced.py --limit 50
```

**Process laptops with keywords:**
```bash
python generate_descriptions_advanced.py --category laptop --keywords
```

**Skip first 100, process next 50:**
```bash
python generate_descriptions_advanced.py --skip 100 --limit 50
```

**Dry run for laptops:**
```bash
python generate_descriptions_advanced.py --category laptop --dry-run
```

---

## How It Works

1. **Fetches products** from your database (filters by category/limits if specified)
2. **Generates description** using Gemini API - creates unique, SEO-friendly content
3. **Generates meta description** - 155 chars optimized for search engines
4. **(Optional) Generates keywords** - relevant search terms
5. **Updates database** with new content
6. **Tracks progress** - can resume if interrupted

---

## Output Quality

The AI generates:
- **Natural, conversational descriptions** (not generic templates)
- **SEO-optimized** but readable text
- **Unique per product** - even similar products get unique descriptions
- **Benefit-focused** - emphasizes value proposition
- **155-char meta** descriptions optimized for search engine display

---

## Pricing

Google's Gemini API offers:
- **Free tier**: 15 requests per minute
- **Pay-as-you-go**: Very cheap (~$0.075 per 1M input tokens)
- This script: ~500 laptops = ~$0.50-1.00 total cost

---

## Troubleshooting

### Error: "GOOGLE_API_KEY environment variable not set"
→ Run `export GOOGLE_API_KEY='your-key-here'` before running script

### Error: "Rate limit exceeded"
→ Increase `DELAY_BETWEEN_REQUESTS` in the script (currently 1 second)

### Script stops mid-way
→ Run again - it saves progress and continues automatically

### Meta description too long
→ Script automatically truncates to 160 chars with "..."

---

## Monitoring Progress

Check the progress file:
```bash
cat description_generation_progress.json
```

Output shows:
```json
{
  "processed": ["product-id-1", "product-id-2"],
  "failed": ["product-id-3"],
  "total": 500
}
```

---

## Next Steps After Running

1. **Verify quality** - Check a few updated products in Django admin
2. **Monitor SEO** - Track improvements in Google Search Console after a few weeks
3. **Adjust if needed** - If quality isn't perfect, we can tweak the prompts
4. **Expand to other categories** - Can run same script for other product types

---

## Questions?

The scripts are designed to be safe:
- ✅ Show sample before processing full batch
- ✅ Track progress and failures
- ✅ Can be run repeatedly (idempotent for already-processed items)
- ✅ Can test with `--dry-run` first
