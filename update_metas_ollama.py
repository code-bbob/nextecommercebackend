#!/usr/bin/env python
"""
Update product meta descriptions one-by-one using Ollama (local, free, no limits).

SEO meta descriptions: 155-160 characters for Google SERP.
"""

import os
import django
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

from shop.models import Product
import requests

# ============================================================================
# CONFIGURATION
# ============================================================================

OLLAMA_API_URL = "http://localhost:11434/api/generate"  # Default Ollama endpoint
MODEL = "mistral"  # Fast and good quality
PROGRESS_FILE = 'meta_update_ollama_progress.json'
LOG_FILE = 'meta_update_ollama.log'

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

def load_progress() -> dict:
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
        'started_at': None
    }

def save_progress(progress: dict):
    """Save progress to file."""
    try:
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f, indent=2)
    except Exception as e:
        log_message(f"Failed to save progress: {e}", "WARNING")

# ============================================================================
# OLLAMA INTEGRATION
# ============================================================================

class OllamaMetaGenerator:
    """Generates SEO meta descriptions using local Ollama model."""
    
    def __init__(self, api_url: str, model: str):
        self.api_url = api_url
        self.model = model
        self.call_count = 0
        self.check_ollama()
    
    def check_ollama(self):
        """Check if Ollama is running and model is available."""
        try:
            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=5
            )
            if response.status_code != 200:
                log_message("Ollama is not responding. Start it with: ollama serve", "ERROR")
                raise SystemExit(1)
            
            models = response.json().get('models', [])
            model_names = [m['name'].split(':')[0] for m in models]
            
            if self.model not in model_names:
                log_message(f"Model '{self.model}' not found in Ollama", "WARNING")
                log_message(f"Available models: {', '.join(model_names)}", "INFO")
                log_message(f"Download with: ollama pull {self.model}", "INFO")
                raise SystemExit(1)
            
            log_message(f"Connected to Ollama with model '{self.model}'", "SUCCESS")
        
        except requests.exceptions.ConnectionError:
            log_message("Cannot connect to Ollama at http://localhost:11434", "ERROR")
            log_message("Start Ollama with: ollama serve", "WARNING")
            raise SystemExit(1)
        except Exception as e:
            log_message(f"Error checking Ollama: {e}", "ERROR")
            raise SystemExit(1)
    
    def generate_meta(self, product_data: dict) -> Optional[str]:
        """Generate a single product meta description."""
        
        prompt = f"""Write a compelling SEO meta description for Google search results.

Product Name: {product_data['name']}
Brand: {product_data['brand']}

Requirements:
1. EXACTLY 155-160 characters (Google SERP limit)
2. Include product name and brand naturally
3. Highlight main benefit or key feature
4. Make it clickable from Google search results
5. Include relevant keywords naturally
6. NO markdown, NO special characters
7. Complete sentences, nothing truncated
8. We are Digitech Enterprises, a trusted retailer

Write ONLY the meta description, nothing else.
The description must be between 155-160 characters."""

        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                },
                timeout=120
            )
            
            if response.status_code != 200:
                log_message(f"API error: {response.status_code}", "ERROR")
                return None
            
            meta = response.json().get('response', '').strip()
            self.call_count += 1
            
            if meta:
                # Enforce character limit
                if len(meta) > 160:
                    meta = meta[:157] + "..."
                return meta
            return None
        
        except requests.exceptions.Timeout:
            log_message("Ollama request timed out - model may be slow", "ERROR")
            return None
        except Exception as e:
            log_message(f"Generation failed: {e}", "ERROR")
            return None

# ============================================================================
# MAIN SCRIPT
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Update meta descriptions using local Ollama (free, unlimited)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Setup required:
  1. Install Ollama: https://ollama.ai
  2. Download model: ollama pull mistral
  3. Start Ollama: ollama serve
  4. Run this script

Examples:
  # Preview first
  python %(prog)s --dry-run
  
  # Update all products
  python %(prog)s
  
  # Resume after interruption
  python %(prog)s
  
  # Update specific category
  python %(prog)s --category laptop
        """
    )
    
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview with first product only')
    parser.add_argument('--category', type=str, 
                       help='Filter by category')
    parser.add_argument('--limit', type=int, 
                       help='Maximum products to process')
    parser.add_argument('--model', type=str, default='mistral',
                       help='Ollama model to use (default: mistral)')
    
    args = parser.parse_args()
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    print("\n" + "="*80)
    print("🚀 META DESCRIPTION UPDATER (OLLAMA - LOCAL, FREE)")
    print("="*80 + "\n")
    
    log_message("Checking Ollama connection...", "INFO")
    
    # ========================================================================
    # SETUP
    # ========================================================================
    
    generator = OllamaMetaGenerator(OLLAMA_API_URL, args.model)
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
    print(f"   • Total in database: {Product.objects.count()}")
    print(f"   • To process: {total}")
    print(f"   • Already processed: {len(processed_ids)}")
    print(f"   • Failed: {len(failed_ids)}")
    
    print(f"\n⚙️  SETTINGS:")
    print(f"   • Model: {args.model}")
    print(f"   • Endpoint: {OLLAMA_API_URL}")
    print(f"   • Processing: 1 product at a time (maximum accuracy)\n")
    
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
        print(f"📦 SAMPLE PRODUCT: {sample.name[:60]}")
        print(f"{'='*80}\n")
        
        log_message("Generating sample meta (this may take 10-20 seconds)...", "INFO")
        
        meta_data = {
            'name': sample.name,
            'brand': sample.brand.name if sample.brand else 'Brand'
        }
        new_meta = generator.generate_meta(meta_data)
        
        current_meta = sample.meta_description if sample.meta_description else "N/A"
        
        print(f"\n🔴 CURRENT ({len(sample.meta_description) if sample.meta_description else 0} chars):")
        print(f"   {current_meta}\n")
        print(f"🟢 NEW ({len(new_meta) if new_meta else 0} chars):")
        print(f"   {new_meta}\n")
        
        print(f"{'='*80}")
        print(f"✨ Preview complete! Would update {total} products")
        print(f"   Estimated time: {total * 0.5 / 60:.1f}-{total * 1 / 60:.1f} minutes")
        print(f"{'='*80}\n")
        return
    
    # ========================================================================
    # CONFIRMATION
    # ========================================================================
    
    print(f"{'='*80}")
    print(f"⚠️  ABOUT TO UPDATE {total} META DESCRIPTIONS")
    print(f"{'='*80}\n")
    print("This will:")
    print(f"  • Update meta descriptions ONE AT A TIME")
    print(f"  • Take approximately {total * 0.5 / 60:.0f}-{total * 1 / 60:.0f} minutes")
    print(f"  • Cost: FREE ✅ (local processing)\n")
    
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
    
    # Process each product
    for idx, product in enumerate(products, 1):
        print(f"[{idx:3d}/{total}] {product.name[:50]:<50}", end=" ", flush=True)
        
        try:
            meta_data = {
                'name': product.name,
                'brand': product.brand.name if product.brand else 'Brand'
            }
            
            new_meta = generator.generate_meta(meta_data)
            
            if new_meta:
                product.meta_description = new_meta
                product.save()
                processed_ids.add(product.product_id)
                updated_count += 1
                print("✅")
            else:
                failed_ids.add(product.product_id)
                failed_count += 1
                print("❌")
        
        except Exception as e:
            log_message(f"Error processing {product.name}: {e}", "ERROR")
            failed_ids.add(product.product_id)
            failed_count += 1
            print("❌")
        
        # Save progress every product
        progress['processed'] = list(processed_ids)
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
    print(f"   ✅ Updated: {updated_count} products")
    print(f"   ❌ Failed: {failed_count} products")
    print(f"   📞 Ollama calls: {generator.call_count}")
    print(f"   ⏱️  Time: {elapsed/60:.1f} minutes ({elapsed/3600:.1f} hours)")
    print(f"   💰 Cost: FREE ✅")
    print(f"   ⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if failed_count > 0:
        log_message(f"{failed_count} failed - run again to retry", "WARNING")
    
    print(f"📝 Logs: {LOG_FILE}")
    print(f"📊 Progress: {PROGRESS_FILE}\n")

if __name__ == '__main__':
    main()
