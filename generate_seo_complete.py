#!/usr/bin/env python
"""
Production-grade product SEO optimizer.
Updates product names, descriptions, and meta descriptions using Gemini AI.

Features:
- Loads API key from .env file (secure)
- Batch processing to minimize API calls (3x fewer calls)
- Progress tracking and resumable
- Comprehensive error handling
- Dry-run preview mode
- SEO-optimized content generation
- Rate limiting to respect API quotas
"""

import os
import django
import json
import time
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

from shop.models import Product
import google.generativeai as genai
from dotenv import load_dotenv

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load .env file
ENV_PATH = Path(__file__).parent / '.env'
load_dotenv(ENV_PATH)

API_KEY = os.getenv('GOOGLE_API_KEY')
BATCH_SIZE = 5  # Products per API call (optimal for cost/speed)
DELAY_BETWEEN_CALLS = 0.8  # Seconds between API calls (prevent rate limiting)
PROGRESS_FILE = 'seo_generation_progress.json'
LOG_FILE = 'seo_generation.log'

# ============================================================================
# LOGGING
# ============================================================================

def log_message(msg: str, level: str = "INFO"):
    """Log messages to both console and file."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"[{timestamp}] [{level}] {msg}"
    
    # Console
    if level == "ERROR":
        print(f"❌ {msg}")
    elif level == "SUCCESS":
        print(f"✅ {msg}")
    elif level == "WARNING":
        print(f"⚠️ {msg}")
    else:
        print(f"ℹ️ {msg}")
    
    # File
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
# SEO CONTENT GENERATION
# ============================================================================

class SEOContentGenerator:
    """Generates SEO-optimized product content using Gemini AI."""
    
    def __init__(self, api_key: str):
        if not api_key:
            log_message("GOOGLE_API_KEY not found in .env file", "ERROR")
            log_message("Create a .env file with: GOOGLE_API_KEY='your-key-here'", "ERROR")
            sys.exit(1)
        
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
            sys.exit(1)
    
    def generate_batch_names(self, products_data: List[Dict]) -> List[Optional[str]]:
        """
        Generate SEO-optimized product names for multiple products.
        
        SEO considerations:
        - Include brand and model
        - Include key specs (processor, RAM, storage)
        - Format: Brand Model (spec1, spec2, spec3)
        - Natural language (no special characters or pipes)
        """
        
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

Start with "1." - nothing before it."""

        try:
            response = self.model.generate_content(prompt)
            self.call_count += 1
            
            names = self._parse_batch_response(response.text, len(products_data))
            log_message(f"Generated {len([n for n in names if n])} names", "SUCCESS")
            return names
        
        except Exception as e:
            log_message(f"Name generation failed: {e}", "ERROR")
            return [None] * len(products_data)
    
    def generate_batch_descriptions(self, products_data: List[Dict]) -> List[Optional[str]]:
        """
        Generate SEO-optimized product descriptions.
        
        SEO considerations:
        - Include primary keyword (product name/type)
        - Natural keyword density
        - 80-120 words (optimal for SERP snippets)
        - Focus on benefits, not just specs
        - Include differentiators
        """
        
        product_list = "\n".join([
            f"{i+1}. {p['name']} | Brand: {p['brand']} | Type: {p['category']}"
            for i, p in enumerate(products_data)
        ])
        
        prompt = f"""Write compelling, SEO-optimized product descriptions.

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
8. NO markdown, NO special formatting

Example: "The [Product] is a powerful [category] designed for [use case]. With [key feature], it delivers [benefit]. Perfect for [target user]."

Output EXACTLY as:
1. [description 1]
2. [description 2]
3. [description 3]

Start with "1." - nothing before it."""

        try:
            response = self.model.generate_content(prompt)
            self.call_count += 1
            
            descriptions = self._parse_batch_response(response.text, len(products_data))
            log_message(f"Generated {len([d for d in descriptions if d])} descriptions", "SUCCESS")
            return descriptions
        
        except Exception as e:
            log_message(f"Description generation failed: {e}", "ERROR")
            return [None] * len(products_data)
    
    def generate_batch_metas(self, products_data: List[Dict]) -> List[Optional[str]]:
        """
        Generate SEO meta descriptions.
        
        SEO considerations:
        - Exactly 155-160 characters (Google SERP limit)
        - Include product name + brand + key benefit
        - Compelling call-to-action
        - No truncation of important info
        """
        
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
6. NO markdown, NO special characters
7. NO truncation - complete sentences
8. We are Digitech Enterprises, a trusted retailer.

Format EXACTLY as:
1. [meta description]
2. [meta description]
3. [meta description]

Character count must be 155-160 for each.
Start with "1." - nothing before it."""

        try:
            response = self.model.generate_content(prompt)
            self.call_count += 1
            
            metas = self._parse_batch_response(response.text, len(products_data))
            
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
        description='Production-grade SEO optimizer for e-commerce products',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes
  python %(prog)s --dry-run
  
  # Update all products
  python %(prog)s
  
  # Update only laptops
  python %(prog)s --category laptop
  
  # Resume after interruption
  python %(prog)s
  
  # Update specific number of products
  python %(prog)s --limit 50
        """
    )
    
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview changes without saving')
    parser.add_argument('--category', type=str, 
                       help='Filter by category (e.g., "laptop")')
    parser.add_argument('--limit', type=int, 
                       help='Maximum products to process')
    parser.add_argument('--batch-size', type=int, default=BATCH_SIZE,
                       help=f'Products per API call (default: {BATCH_SIZE})')
    parser.add_argument('--resume', action='store_true', 
                       help='Resume from last interrupted run')
    
    args = parser.parse_args()
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    print("\n" + "="*80)
    print("🚀 SEO PRODUCT OPTIMIZER")
    print("="*80 + "\n")
    
    if not API_KEY:
        log_message("GOOGLE_API_KEY not found!", "ERROR")
        log_message(f"Create a .env file at: {ENV_PATH}", "ERROR")
        log_message("Add: GOOGLE_API_KEY='your-api-key-here'", "ERROR")
        log_message("\nGet a free key at: https://aistudio.google.com/apikey", "WARNING")
        sys.exit(1)
    
    log_message("Configuration loaded", "SUCCESS")
    
    # ========================================================================
    # SETUP
    # ========================================================================
    
    generator = SEOContentGenerator(API_KEY)
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
    print(f"   • Products to process: {total}")
    print(f"   • Already processed: {len(processed_ids)}")
    print(f"   • Failed previously: {len(failed_ids)}")
    print(f"   • Batch size: {args.batch_size}")
    
    # Calculate API calls
    batches = (total + args.batch_size - 1) // args.batch_size
    api_calls = batches * 3  # names + descriptions + metas
    
    print(f"\n📞 API CALLS:")
    print(f"   • Expected total: {api_calls} calls")
    print(f"   • Name generation: {batches} calls")
    print(f"   • Description generation: {batches} calls")
    print(f"   • Meta generation: {batches} calls")
    print(f"   • Cost estimate: <$0.02 or FREE (free tier, 15 calls/min)")
    print(f"   • Time estimate: {max(api_calls // 15 + 1, 5)}-10 minutes\n")
    
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
        print(f"📦 SAMPLE PRODUCT: {sample.name[:60]}...")
        print(f"{'='*80}\n")
        
        # Generate samples
        log_message("Generating sample content...", "INFO")
        time.sleep(1)
        
        # Name
        names = generator.generate_batch_names([{'current_name': sample.name}])
        time.sleep(DELAY_BETWEEN_CALLS)
        
        print(f"🔴 CURRENT NAME ({len(sample.name)} chars):")
        print(f"   {sample.name}\n")
        print(f"🟢 NEW NAME ({len(names[0]) if names[0] else 0} chars):")
        print(f"   {names[0]}\n")
        
        # Description
        desc_data = [{
            'name': sample.name,
            'brand': sample.brand.name if sample.brand else 'Brand',
            'category': sample.category.name if sample.category else 'Category'
        }]
        descriptions = generator.generate_batch_descriptions(desc_data)
        time.sleep(DELAY_BETWEEN_CALLS)
        
        current_desc_preview = sample.description[:150] if sample.description else "N/A"
        if sample.description and len(sample.description) > 150:
            current_desc_preview += "..."
        
        print(f"🔴 CURRENT DESCRIPTION ({len(sample.description) if sample.description else 0} chars):")
        print(f"   {current_desc_preview}\n")
        print(f"🟢 NEW DESCRIPTION ({len(descriptions[0]) if descriptions[0] else 0} chars):")
        print(f"   {descriptions[0]}\n")
        
        # Meta
        meta_data = [{
            'name': names[0] if names[0] else sample.name,
            'brand': sample.brand.name if sample.brand else 'Brand'
        }]
        metas = generator.generate_batch_metas(meta_data)
        time.sleep(DELAY_BETWEEN_CALLS)
        
        print(f"🔴 CURRENT META ({len(sample.meta_description) if sample.meta_description else 0} chars):")
        print(f"   {sample.meta_description if sample.meta_description else 'N/A'}\n")
        print(f"🟢 NEW META ({len(metas[0]) if metas[0] else 0} chars):")
        print(f"   {metas[0]}\n")
        
        print(f"{'='*80}")
        print(f"✨ Preview complete! Would update {total} products with {api_calls} API calls")
        print(f"{'='*80}\n")
        return
    
    # ========================================================================
    # CONFIRMATION
    # ========================================================================
    
    print(f"{'='*80}")
    print(f"⚠️  ABOUT TO UPDATE {total} PRODUCTS")
    print(f"{'='*80}\n")
    print("This will:")
    print(f"  • Update product names")
    print(f"  • Update product descriptions")
    print(f"  • Update meta descriptions")
    print(f"  • Use ~{api_calls} API calls")
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
    for batch_start in range(0, total, args.batch_size):
        batch_end = min(batch_start + args.batch_size, total)
        batch = products[batch_start:batch_end]
        batch_num = (batch_start // args.batch_size) + 1
        total_batches = (total + args.batch_size - 1) // args.batch_size
        
        print(f"[Batch {batch_num:3d}/{total_batches}] Processing {len(batch)} products...", 
              end=" ", flush=True)
        
        try:
            # Generate names
            names_data = [{'current_name': p.name} for p in batch]
            new_names = generator.generate_batch_names(names_data)
            time.sleep(DELAY_BETWEEN_CALLS)
            
            # Generate descriptions
            desc_data = [
                {
                    'name': new_names[i] if new_names[i] else p.name,
                    'brand': p.brand.name if p.brand else 'Brand',
                    'category': p.category.name if p.category else 'Category'
                }
                for i, p in enumerate(batch)
            ]
            new_descriptions = generator.generate_batch_descriptions(desc_data)
            time.sleep(DELAY_BETWEEN_CALLS)
            
            # Generate metas
            meta_data = [
                {
                    'name': new_names[i] if new_names[i] else p.name,
                    'brand': p.brand.name if p.brand else 'Brand'
                }
                for i, p in enumerate(batch)
            ]
            new_metas = generator.generate_batch_metas(meta_data)
            time.sleep(DELAY_BETWEEN_CALLS)
            
            # Update database
            batch_success = 0
            for i, product in enumerate(batch):
                try:
                    if new_names[i]:
                        product.name = new_names[i]
                    if new_descriptions[i]:
                        product.description = new_descriptions[i]
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
            
            # Save progress
            progress['processed'] = list(processed_ids)
            progress['failed'] = list(failed_ids)
            progress['last_batch'] = batch_num
            save_progress(progress)
        
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
    print(f"   📞 API calls used: {generator.call_count}")
    print(f"   ⏱️  Time taken: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"   💰 Estimated cost: <$0.02 or FREE")
    print(f"   ⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if failed_count > 0:
        log_message(f"{failed_count} products failed - run again to retry", "WARNING")
    
    print(f"📝 Logs saved to: {LOG_FILE}")
    print(f"📊 Progress saved to: {PROGRESS_FILE}\n")

if __name__ == '__main__':
    main()
