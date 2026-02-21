#!/usr/bin/env python
"""
Update product descriptions one-by-one using Ollama (local, free, no limits).

Perfect for accuracy and control. One description per API call.
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
PROGRESS_FILE = 'description_update_ollama_progress.json'
LOG_FILE = 'description_update_ollama.log'

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

class OllamaDescriptionGenerator:
    """Generates product descriptions using local Ollama model."""
    
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
    
    def generate_description(self, product_data: dict) -> Optional[str]:
        """Generate a single product description."""
        
        prompt = f"""Write a compelling, SEO-optimized product description for this product.

Product Name: {product_data['name']}
Brand: {product_data['brand']}
Category: {product_data['category']}

Requirements:
1. Write 2-3 sentences (80-120 words)
2. Start with product name/type (include primary keyword)
3. Focus on BENEFITS and key differentiators, not just specs
4. Use natural language with related keywords
5. Include performance/value proposition
6. Make it unique - not generic
7. Professional but conversational tone
8. NO markdown, NO special formatting

Write ONLY the description, nothing else."""

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
            
            description = response.json().get('response', '').strip()
            self.call_count += 1
            
            if description:
                return description
            return None
        
        except requests.exceptions.Timeout:
            log_message("Ollama request timed out - model may be slow or overloaded", "ERROR")
            return None
        except Exception as e:
            log_message(f"Generation failed: {e}", "ERROR")
            return None

# ============================================================================
# MAIN SCRIPT
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Update product descriptions using local Ollama (free, unlimited)',
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
    print("🚀 PRODUCT DESCRIPTION UPDATER (OLLAMA - LOCAL, FREE)")
    print("="*80 + "\n")
    
    log_message("Checking Ollama connection...", "INFO")
    
    # ========================================================================
    # SETUP
    # ========================================================================
    
    generator = OllamaDescriptionGenerator(OLLAMA_API_URL, args.model)
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
        
        log_message("Generating sample description (this may take 30-60 seconds)...", "INFO")
        
        desc_data = {
            'name': sample.name,
            'brand': sample.brand.name if sample.brand else 'Brand',
            'category': sample.category.name if sample.category else 'Category'
        }
        new_desc = generator.generate_description(desc_data)
        
        current_desc_preview = sample.description[:150] if sample.description else "N/A"
        if sample.description and len(sample.description) > 150:
            current_desc_preview += "..."
        
        print(f"\n🔴 CURRENT ({len(sample.description) if sample.description else 0} chars):")
        print(f"   {current_desc_preview}\n")
        print(f"🟢 NEW ({len(new_desc) if new_desc else 0} chars):")
        print(f"   {new_desc}\n")
        
        print(f"{'='*80}")
        print(f"✨ Preview complete! Would update {total} products")
        print(f"   Estimated time: {total * 0.75 / 60:.1f}-{total * 1.5 / 60:.1f} minutes")
        print(f"{'='*80}\n")
        return
    
    # ========================================================================
    # CONFIRMATION
    # ========================================================================
    
    print(f"{'='*80}")
    print(f"⚠️  ABOUT TO UPDATE {total} PRODUCT DESCRIPTIONS")
    print(f"{'='*80}\n")
    print("This will:")
    print(f"  • Update descriptions ONE AT A TIME")
    print(f"  • Take approximately {total * 0.75 / 60:.0f}-{total * 1.5 / 60:.0f} minutes")
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
            desc_data = {
                'name': product.name,
                'brand': product.brand.name if product.brand else 'Brand',
                'category': product.category.name if product.category else 'Category'
            }
            
            new_description = generator.generate_description(desc_data)
            
            if new_description:
                product.description = new_description
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
