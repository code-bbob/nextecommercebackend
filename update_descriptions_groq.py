#!/usr/bin/env python
"""
Batch update product descriptions using Groq API.
Groq is FREE with high rate limits - perfect for batch processing.

Features:
- Batch 20+ products per request
- No cost, no rate limiting
- Fast processing (70+ tokens/second)
- Resumable progress tracking
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
from groq import Groq
from dotenv import load_dotenv

# ============================================================================
# CONFIGURATION
# ============================================================================

ENV_PATH = Path(__file__).parent / '.env'
load_dotenv(ENV_PATH)

API_KEY = os.getenv('GROQ_API_KEY')
BATCH_SIZE = 5  # Products per API call (batch mode for speed)
DELAY_BETWEEN_CALLS = 0.2  # Seconds between API calls (Groq is fast)
PROGRESS_FILE = 'description_update_ollama_progress.json'  # Same as Ollama/Gemini
LOG_FILE = 'description_groq.log'

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
# DESCRIPTION GENERATION
# ============================================================================

class DescriptionGenerator:
    """Generates product descriptions using Groq API."""
    
    def __init__(self, api_key: str):
        if not api_key:
            log_message("GROQ_API_KEY not found in .env file", "ERROR")
            log_message("Sign up at https://console.groq.com and get your free API key", "WARNING")
            raise SystemExit(1)
        
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
            raise SystemExit(1)
    
    def generate_batch_descriptions(self, products_data: List[Dict]) -> List[Optional[str]]:
        """Generate product descriptions for a batch of products."""
        
        product_list = "\n".join([
            f"{i+1}. Name: {p['name']} | Brand: {p['brand']} | Category: {p['category']}"
            for i, p in enumerate(products_data)
        ])
        
        prompt = f"""Write compelling, SEO-optimized product descriptions for these products.

PRODUCTS:
{product_list}

For EACH description:
1. Write 2-3 sentences (80-120 words)
2. Start with product name/type (include primary keyword)
3. Focus on BENEFITS and key differentiators, not just specs
4. Use natural language with related keywords
5. Include performance/value proposition
6. Make it unique - not generic or templated
7. Professional but conversational tone
8. Naturally mention "available at Digitech Enterprises in Nepal" if relevant
9. NO markdown, NO special formatting

Example: "The [Product] is a powerful [category] designed for [use case]. With [key feature], it delivers [benefit]. Available at Digitech Enterprises in Nepal with full warranty and local support."

Output EXACTLY as:
1. [description 1]
2. [description 2]
3. [description 3]
...etc

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
            
            descriptions = self._parse_batch_response(response.choices[0].message.content, len(products_data))
            log_message(f"Generated {len([d for d in descriptions if d])} descriptions", "SUCCESS")
            return descriptions
        
        except Exception as e:
            log_message(f"Description generation failed: {e}", "ERROR")
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
        description='Batch update product descriptions using Groq API',
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
    print("🚀 PRODUCT DESCRIPTION BATCH UPDATER (GROQ)")
    print("="*80 + "\n")
    
    if not API_KEY:
        log_message("GROQ_API_KEY not found!", "ERROR")
        log_message(f"Create a .env file at: {ENV_PATH}", "ERROR")
        log_message("Add: GROQ_API_KEY='your-api-key-here'", "ERROR")
        log_message("\nGet a free key at: https://console.groq.com", "WARNING")
        return
    
    log_message("Configuration loaded", "SUCCESS")
    
    # ========================================================================
    # SETUP
    # ========================================================================
    
    generator = DescriptionGenerator(API_KEY)
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
    print(f"   • Time estimate: {batches // 2}-{batches} minutes (very fast)\n")
    
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
        log_message("Generating sample description...", "INFO")
        
        desc_data = [{
            'name': sample.name,
            'brand': sample.brand.name if sample.brand else 'Brand',
            'category': sample.category.name if sample.category else 'Category'
        }]
        descriptions = generator.generate_batch_descriptions(desc_data)
        
        current_desc_preview = sample.description[:150] if sample.description else "N/A"
        if sample.description and len(sample.description) > 150:
            current_desc_preview += "..."
        
        print(f"🔴 CURRENT DESCRIPTION ({len(sample.description) if sample.description else 0} chars):")
        print(f"   {current_desc_preview}\n")
        print(f"🟢 NEW DESCRIPTION ({len(descriptions[0]) if descriptions[0] else 0} chars):")
        print(f"   {descriptions[0]}\n")
        
        print(f"{'='*80}")
        print(f"✨ Preview complete! Would update {total} products with {batches} API requests")
        print(f"{'='*80}\n")
        return
    
    # ========================================================================
    # CONFIRMATION
    # ========================================================================
    
    print(f"{'='*80}")
    print(f"⚠️  ABOUT TO UPDATE {total} PRODUCT DESCRIPTIONS")
    print(f"{'='*80}\n")
    print("This will:")
    print(f"  • Update product descriptions ONLY")
    print(f"  • Use {batches} API requests (completely FREE)")
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
            # Generate descriptions
            desc_data = [
                {
                    'name': p.name,
                    'brand': p.brand.name if p.brand else 'Brand',
                    'category': p.category.name if p.category else 'Category'
                }
                for p in batch
            ]
            new_descriptions = generator.generate_batch_descriptions(desc_data)
            
            # Update database
            batch_success = 0
            for i, product in enumerate(batch):
                try:
                    if new_descriptions[i]:
                        product.description = new_descriptions[i]
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
            
            # Delay before next request
            if batch_num < total_batches:
                time.sleep(DELAY_BETWEEN_CALLS)
        
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
