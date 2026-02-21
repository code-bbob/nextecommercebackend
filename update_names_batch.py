#!/usr/bin/env python
"""
Batch update product names only using Gemini API.
Optimized for free tier with 20 request limit.

With 373 products and 20 requests, batches of ~18-19 products per request.
"""

import os
import django
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

from shop.models import Product
import google.generativeai as genai
from dotenv import load_dotenv

# ============================================================================
# CONFIGURATION
# ============================================================================

ENV_PATH = Path(__file__).parent / '.env'
load_dotenv(ENV_PATH)

API_KEY = os.getenv('GOOGLE_API_KEY')
BATCH_SIZE = 20  # Products per API call (373 / 20 = 18.65, rounded to 20 = 19 requests total)
DELAY_BETWEEN_CALLS = 1.0  # Seconds between API calls
PROGRESS_FILE = 'name_update_progress.json'
LOG_FILE = 'name_update.log'

# ============================================================================
# LOGGING
# ============================================================================

def log_message(msg: str, level: str = "INFO"):
    """Log messages to both console and file."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] [{level}] {msg}"
    
    if level == "ERROR":
        print(f"❌ {msg}")
    elif level == "SUCCESS":
        print(f"✅ {msg}")
    elif level == "WARNING":
        print(f"⚠️ {msg}")
    else:
        print(f"ℹ️ {msg}")
    
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_entry + '\n')
    except:
        pass

# ============================================================================
# PROGRESS TRACKING
# ============================================================================

def load_progress() -> Dict:
    """Load progress from file to enable resuming."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        'processed': [],
        'failed': [],
        'total': 0,
        'started_at': None,
        'last_batch': 0
    }

def save_progress(progress: Dict):
    """Save progress to file."""
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f, indent=2)
    except Exception as e:
        log_message(f"Failed to save progress: {e}", "WARNING")

# ============================================================================
# NAME GENERATION
# ============================================================================

class NameGenerator:
    """Generates product names using Gemini AI."""
    
    def __init__(self, api_key: str):
        if not api_key:
            log_message("GOOGLE_API_KEY not found in .env file", "ERROR")
            raise SystemExit(1)
        
        self.api_key = api_key
        self.model = None
        self.call_count = 0
        self.setup_genai()
    
    def setup_genai(self):
        """Configure Google Generative AI."""
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(model_name='gemini-2.5-flash')
            log_message("Connected to Gemini API", "SUCCESS")
        except Exception as e:
            log_message(f"Failed to connect to Gemini API: {e}", "ERROR")
            raise SystemExit(1)
    
    def generate_batch_names(self, products_data: List[Dict]) -> List[Optional[str]]:
        """Generate product names for a batch of products."""
        
        product_list = "\n".join([
            f"{i+1}. {p['current_name']}"
            for i, p in enumerate(products_data)
        ])
        
        prompt = f"""Rewrite these product names for maximum SEO performance and user clarity.

CURRENT NAMES:
{product_list}

For EACH name, create a better version using this EXACT format:
[Brand] [Model] with [CPU/Processor] ([Specifications separated by commas])

Key requirements:
1. Start with brand and model name
2. Include "with" before the processor/CPU name
3. Put all specs inside parentheses, separated by commas
4. ONLY include specs that are clearly specified in the original name - do NOT include specs if they're not mentioned
5. Common specs to include (if present): Processor, GPU (if applicable), RAM, Storage, Display, Warranty, Battery, etc.
6. If a spec is missing or not mentioned, skip it completely
7. Example: "MSI Thin 15 B12VE with Intel i5 12450H Processor (RTX 4050 6GB, 8GB Ram, 512 GB SSD, 15.6" FHD 144Hz display, 2 Year warranty)"
8. Example for incomplete spec: "Dell XPS 13 with Intel i7 (16GB RAM, 512GB SSD)" - warranty and display not included if not specified

Output EXACTLY as:
1. [new name]
2. [new name]
3. [new name]
...etc

Start with "1." - nothing before it. Number each item sequentially."""

        try:
            response = self.model.generate_content(prompt)
            self.call_count += 1
            
            names = self._parse_batch_response(response.text, len(products_data))
            log_message(f"Generated {len([n for n in names if n])} names", "SUCCESS")
            return names
        
        except Exception as e:
            log_message(f"Name generation failed: {e}", "ERROR")
            return [None] * len(products_data)
    
    def _parse_batch_response(self, text: str, expected_count: int) -> List[Optional[str]]:
        """Parse numbered list response from API."""
        items = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for numbered items: "1. ", "2. ", etc.
            if line and len(line) > 2 and line[0].isdigit():
                # Find the period
                if '.' in line:
                    content = line.split('.', 1)[1].strip()
                    if content:
                        items.append(content)
        
        # Pad with None if not enough items parsed
        while len(items) < expected_count:
            items.append(None)
        
        return items[:expected_count]

# ============================================================================
# MAIN SCRIPT
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Batch update product names using Gemini API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes
  python %(prog)s --dry-run
  
  # Update all products
  python %(prog)s
  
  # Update specific category
  python %(prog)s --category laptop
  
  # Resume after interruption
  python %(prog)s
        """
    )
    
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview changes without saving')
    parser.add_argument('--category', type=str, 
                       help='Filter by category (e.g., "laptop")')
    parser.add_argument('--limit', type=int, 
                       help='Maximum products to process')
    
    args = parser.parse_args()
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    print("\n" + "="*80)
    print("🚀 PRODUCT NAME BATCH UPDATER")
    print("="*80 + "\n")
    
    if not API_KEY:
        log_message("GOOGLE_API_KEY not found!", "ERROR")
        log_message(f"Create a .env file at: {ENV_PATH}", "ERROR")
        log_message("Add: GOOGLE_API_KEY='your-api-key-here'", "ERROR")
        log_message("\nGet a free key at: https://aistudio.google.com/apikey", "WARNING")
        return
    
    log_message("Configuration loaded", "SUCCESS")
    
    # ========================================================================
    # SETUP
    # ========================================================================
    
    generator = NameGenerator(API_KEY)
    progress = load_progress()
    processed_ids = set(progress['processed'])
    failed_ids = set(progress['failed'])
    
    # Get products
    query = Product.objects.all()
    
    if args.category:
        query = query.filter(category__name__icontains=args.category)
        log_message(f"Filtering by category: {args.category}", "INFO")
    
    # Exclude already processed
    query = query.exclude(product_id__in=processed_ids)
    query = query.exclude(product_id__in=failed_ids)
    
    if args.limit:
        query = query[:args.limit]
    
    products = list(query)
    total = len(products)
    
    # ========================================================================
    # DISPLAY STATS
    # ========================================================================
    
    print(f"📊 STATISTICS:")
    print(f"   • Total products in database: {Product.objects.count()}")
    print(f"   • Products to process: {total}")
    print(f"   • Already processed: {len(processed_ids)}")
    print(f"   • Failed previously: {len(failed_ids)}")
    print(f"   • Batch size: {BATCH_SIZE} products per request")
    
    # Calculate API calls needed
    batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"\n📞 API CALLS:")
    print(f"   • Expected total: {batches} requests")
    print(f"   • Free tier limit: 20 requests")
    
    if batches > 20:
        print(f"   ⚠️  WARNING: This will require {batches} requests, exceeding free tier limit of 20")
        print(f"   • Consider using --limit or --category to reduce scope")
    else:
        print(f"   ✅ Will fit within free tier limit!")
    
    print(f"   • Time estimate: {batches * 2}-{batches * 5} minutes (with delays)\n")
    
    if total == 0:
        log_message("No products to process!", "WARNING")
        return
    
    # ========================================================================
    # DRY RUN MODE
    # ========================================================================
    
    if args.dry_run:
        log_message("Running in DRY-RUN mode (preview only)", "INFO")
        
        sample = products[0]
        print(f"\n{'='*80}")
        print(f"📦 SAMPLE PRODUCT")
        print(f"{'='*80}\n")
        
        # Generate sample
        log_message("Generating sample name...", "INFO")
        
        names = generator.generate_batch_names([{'current_name': sample.name}])
        
        print(f"🔴 CURRENT NAME ({len(sample.name)} chars):")
        print(f"   {sample.name}\n")
        print(f"🟢 NEW NAME ({len(names[0]) if names[0] else 0} chars):")
        print(f"   {names[0]}\n")
        
        print(f"{'='*80}")
        print(f"✨ Preview complete! Would update {total} products with {batches} API requests")
        print(f"{'='*80}\n")
        return
    
    # ========================================================================
    # CONFIRMATION
    # ========================================================================
    
    print(f"{'='*80}")
    print(f"⚠️  ABOUT TO UPDATE {total} PRODUCT NAMES")
    print(f"{'='*80}\n")
    print("This will:")
    print(f"  • Update product names ONLY")
    print(f"  • Use {batches} API requests")
    print(f"  • Make changes permanent in database\n")
    
    confirm = input("Are you sure? Type 'yes' to continue: ").strip().lower()
    if confirm != 'yes':
        log_message("Cancelled by user", "WARNING")
        return
    
    # ========================================================================
    # PROCESSING
    # ========================================================================
    
    print(f"\n{'='*80}")
    print("🔄 PROCESSING STARTED")
    print(f"{'='*80}\n")
    
    progress['started_at'] = datetime.now().isoformat()
    progress['total'] = total
    save_progress(progress)
    
    updated_count = 0
    failed_count = 0
    start_time = time.time()
    
    # Process in batches
    for batch_start in range(0, total, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total)
        batch = products[batch_start:batch_end]
        batch_num = (batch_start // BATCH_SIZE) + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"[Request {batch_num:2d}/{total_batches}] Processing {len(batch):2d} products...", 
              end=" ", flush=True)
        
        try:
            # Generate names
            names_data = [{'current_name': p.name} for p in batch]
            new_names = generator.generate_batch_names(names_data)
            
            # Update database
            batch_success = 0
            for i, product in enumerate(batch):
                try:
                    if new_names[i]:
                        old_name = product.name
                        product.name = new_names[i]
                        product.save()
                        processed_ids.add(product.product_id)
                        batch_success += 1
                        updated_count += 1
                        log_message(f"Updated: {old_name[:40]}... → {new_names[i][:40]}...", "INFO")
                except Exception as e:
                    log_message(f"Failed to save {product.name}: {e}", "ERROR")
                    failed_ids.add(product.product_id)
                    failed_count += 1
            
            print(f"✅ {batch_success}/{len(batch)} saved")
            
            # Save progress
            progress['processed'] = list(processed_ids)
            progress['failed'] = list(failed_ids)
            progress['last_batch'] = batch_num
            save_progress(progress)
            
            # Delay before next request
            if batch_num < total_batches:
                time.sleep(DELAY_BETWEEN_CALLS)
        
        except Exception as e:
            print(f"❌ Batch error: {str(e)[:50]}")
            failed_count += len(batch)
            for p in batch:
                failed_ids.add(p.product_id)
            
            progress['failed'] = list(failed_ids)
            save_progress(progress)
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    
    elapsed = time.time() - start_time
    
    print(f"\n{'='*80}")
    print("✨ COMPLETE!")
    print(f"{'='*80}\n")
    print(f"📊 RESULTS:")
    print(f"   ✅ Successfully updated: {updated_count} products")
    print(f"   ❌ Failed: {failed_count} products")
    print(f"   📞 API requests used: {generator.call_count}/{batches}")
    print(f"   ⏱️  Time taken: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"   ⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if failed_count > 0:
        log_message(f"{failed_count} products failed - run again to retry", "WARNING")
    
    print(f"📝 Logs saved to: {LOG_FILE}")
    print(f"📊 Progress saved to: {PROGRESS_FILE}\n")

if __name__ == '__main__':
    main()
