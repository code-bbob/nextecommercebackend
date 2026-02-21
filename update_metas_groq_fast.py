#!/usr/bin/env python
"""
Fast batch update product meta descriptions using Groq API.
Batch 5 products per request - FREE, unlimited, fast.

Continues from Ollama progress file (product 149).
"""

import os
import django
import json
import time
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

from shop.models import Product
from groq import Groq
from dotenv import load_dotenv

# ============================================================================
# CONFIGURATION
# ============================================================================

ENV_PATH = Path(__file__).parent / '.env'
load_dotenv(ENV_PATH)

API_KEY = os.getenv('GROQ_API_KEY')
BATCH_SIZE = 5  # Products per API call
DELAY_BETWEEN_CALLS = 0.2  # Groq is fast
PROGRESS_FILE = 'meta_groq_progress.json'  # Separate progress file
LOG_FILE = 'meta_groq.log'

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
# GROQ META GENERATION
# ============================================================================

class GroqMetaGenerator:
    """Generates meta descriptions using Groq API (batch mode)."""
    
    def __init__(self, api_key: str):
        if not api_key:
            log_message("GROQ_API_KEY not found in .env file", "ERROR")
            log_message("Create a .env file with: GROQ_API_KEY='your-key-here'", "ERROR")
            log_message("Get free key at: https://console.groq.com", "WARNING")
            sys.exit(1)
        
        self.api_key = api_key
        self.client = None
        self.call_count = 0
        self.setup_groq()
    
    def setup_groq(self):
        """Configure Groq client."""
        try:
            self.client = Groq(api_key=self.api_key)
            # Test connection
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": "Hi"}],
                max_tokens=10,
            )
            log_message("Connected to Groq API", "SUCCESS")
        except Exception as e:
            log_message(f"Failed to connect to Groq API: {e}", "ERROR")
            sys.exit(1)
    
    def generate_batch_metas(self, products_data: List[Dict]) -> List[Optional[str]]:
        """Generate meta descriptions for multiple products in one request."""
        
        product_list = "\n".join([
            f"{i+1}. {p['name']} | {p['brand']}"
            for i, p in enumerate(products_data)
        ])
        
        prompt = f"""Write compelling SEO meta descriptions (155-160 chars each).

PRODUCTS:
{product_list}

For EACH meta description:
1. Must be EXACTLY 155-160 characters
2. Include product name and brand naturally
3. Highlight main benefit or key feature
4. Make it clickable from Google search results
5. Include relevant keywords naturally
6. Naturally mention "Nepal" or "Digitech" if it fits naturally
7. NO markdown, NO special characters
8. NO truncation - complete sentences

Format EXACTLY as:
1. [meta description]
2. [meta description]
3. [meta description]
...etc

Character count must be 155-160 for each.
Start with "1." - nothing before it. Number each item sequentially."""

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            self.call_count += 1
            
            metas = self._parse_batch_response(response.choices[0].message.content, len(products_data))
            
            # Enforce character limit
            for i, meta in enumerate(metas):
                if meta and len(meta) > 160:
                    metas[i] = meta[:157] + "..."
            
            log_message(f"Generated {len([m for m in metas if m])} meta descriptions", "SUCCESS")
            return metas
        
        except Exception as e:
            log_message(f"Meta generation failed: {e}", "ERROR")
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
        description='Fast batch update meta descriptions using Groq (FREE)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes
  python %(prog)s --dry-run
  
  # Update all remaining products
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
    print("🚀 META DESCRIPTION BATCH UPDATER (GROQ - FREE, FAST)")
    print("="*80 + "\n")
    
    if not API_KEY:
        log_message("GROQ_API_KEY not found!", "ERROR")
        log_message(f"Create a .env file at: {ENV_PATH}", "ERROR")
        log_message("Add: GROQ_API_KEY='your-api-key-here'", "ERROR")
        log_message("\nGet a free key at: https://console.groq.com", "WARNING")
        sys.exit(1)
    
    log_message("Configuration loaded", "SUCCESS")
    
    # ========================================================================
    # SETUP
    # ========================================================================
    
    generator = GroqMetaGenerator(API_KEY)
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
    print(f"   • Groq free tier: UNLIMITED ✅")
    print(f"   • Time estimate: {batches // 2}-{batches} minutes\n")
    
    if total == 0:
        log_message("No products to process!", "WARNING")
        return
    
    # ========================================================================
    # DRY RUN MODE
    # ========================================================================
    
    if args.dry_run:
        log_message("Running in DRY-RUN mode (preview only)", "INFO")
        
        # Take first 3 products for preview
        sample_batch = products[:min(3, len(products))]
        print(f"\n{'='*80}")
        print(f"📦 SAMPLE BATCH ({len(sample_batch)} products)")
        print(f"{'='*80}\n")
        
        log_message("Generating sample metas...", "INFO")
        
        meta_data = [
            {
                'name': p.name,
                'brand': p.brand.name if p.brand else 'Brand'
            }
            for p in sample_batch
        ]
        metas = generator.generate_batch_metas(meta_data)
        
        for i, product in enumerate(sample_batch):
            print(f"\n--- Product {i+1} ---")
            print(f"🔴 CURRENT ({len(product.meta_description) if product.meta_description else 0} chars):")
            current_meta = product.meta_description if product.meta_description else "N/A"
            print(f"   {current_meta}\n")
            
            print(f"🟢 NEW ({len(metas[i]) if metas[i] else 0} chars):")
            print(f"   {metas[i]}\n")
        
        print(f"{'='*80}")
        print(f"✨ Preview complete! Would update {total} products with {batches} API requests")
        print(f"{'='*80}\n")
        return
    
    # ========================================================================
    # CONFIRMATION
    # ========================================================================
    
    print(f"{'='*80}")
    print(f"⚠️  ABOUT TO UPDATE {total} META DESCRIPTIONS")
    print(f"{'='*80}\n")
    print("This will:")
    print(f"  • Update meta descriptions ONLY")
    print(f"  • Use {batches} API requests (completely FREE)")
    print(f"  • Batch size: {BATCH_SIZE} products per request")
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
        
        print(f"[Batch {batch_num:2d}/{total_batches}] Processing {len(batch):2d} products...", 
              end=" ", flush=True)
        
        try:
            # Generate metas
            meta_data = [
                {
                    'name': p.name,
                    'brand': p.brand.name if p.brand else 'Brand'
                }
                for p in batch
            ]
            new_metas = generator.generate_batch_metas(meta_data)
            time.sleep(DELAY_BETWEEN_CALLS)
            
            # Update database
            batch_success = 0
            for i, product in enumerate(batch):
                try:
                    if new_metas[i]:
                        product.meta_description = new_metas[i]
                        product.save()
                        processed_ids.add(product.product_id)
                        batch_success += 1
                        updated_count += 1
                except Exception as e:
                    log_message(f"Failed to save {product.name}: {e}", "ERROR")
                    failed_ids.add(product.product_id)
                    failed_count += 1
            
            print(f"✅ {batch_success}/{len(batch)} saved ({updated_count}/{total} total)")
            
            # Save progress IMMEDIATELY after each batch
            progress['processed'] = list(processed_ids)
            progress['failed'] = list(failed_ids)
            progress['last_batch'] = batch_num
            save_progress(progress)
        
        except Exception as e:
            print(f"❌ Batch error: {str(e)[:50]}")
            failed_count += len(batch)
            for p in batch:
                failed_ids.add(p.product_id)
            
            # Save progress even on error
            progress['failed'] = list(failed_ids)
            progress['processed'] = list(processed_ids)
            progress['last_batch'] = batch_num
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
    print(f"   💰 Cost: FREE ✅")
    print(f"   ⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if failed_count > 0:
        log_message(f"{failed_count} products failed - run again to retry", "WARNING")
    
    print(f"📝 Logs saved to: {LOG_FILE}")
    print(f"📊 Progress saved to: {PROGRESS_FILE}\n")

if __name__ == '__main__':
    main()
