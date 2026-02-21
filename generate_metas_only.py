#!/usr/bin/env python
"""
Simple script to generate ONLY meta descriptions for products.
Minimal API calls - ~100 calls for 500 products with batch processing.
"""

import os
import django
import argparse
import time
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

from shop.models import Product
import google.generativeai as genai

class MetaDescriptionGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = None
        self.setup_genai()
        self.call_count = 0
    
    def setup_genai(self):
        """Configure Google Generative AI."""
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def generate_batch_metas(self, products_data):
        """
        Generate meta descriptions for multiple products at once.
        """
        
        product_list = "\n".join([
            f"{i+1}. {p['name']} - {p['brand']}"
            for i, p in enumerate(products_data)
        ])
        
        prompt = f"""Generate SEO meta descriptions for these products. These appear in Google search results.

PRODUCTS:
{product_list}

For EACH product:
- Write 150-160 characters exactly
- Include product name and key benefit
- Make it compelling to click
- Include brand if possible
- NO markdown, NO special characters

Format EXACTLY as:
1. [meta description]
2. [meta description]
etc.

Start with "1." only, nothing before it."""

        try:
            response = self.model.generate_content(prompt)
            self.call_count += 1
            
            text = response.text.strip()
            metas = []
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if line and line[0].isdigit() and '.' in line:
                    meta = line.split('.', 1)[1].strip()
                    # Enforce 160 char limit
                    if len(meta) > 160:
                        meta = meta[:157] + "..."
                    metas.append(meta)
            
            # Pad with None if parsing failed
            while len(metas) < len(products_data):
                metas.append(None)
            
            return metas[:len(products_data)]
        
        except Exception as e:
            print(f"Error: {e}")
            return [None] * len(products_data)

def main():
    parser = argparse.ArgumentParser(description='Generate meta descriptions only')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    parser.add_argument('--category', type=str, help='Filter by category')
    parser.add_argument('--limit', type=int, help='Max products to process')
    parser.add_argument('--batch-size', type=int, default=5, help='Products per API call')
    
    args = parser.parse_args()
    
    # Setup
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY not set!")
        print("Get one at: https://aistudio.google.com/apikey")
        exit(1)
    
    generator = MetaDescriptionGenerator(api_key)
    
    # Get products
    query = Product.objects.all()
    
    if args.category:
        query = query.filter(category__name__icontains=args.category)
    
    if args.limit:
        query = query[:args.limit]
    
    products = list(query)
    total = len(products)
    
    print(f"\n📊 Found {total} products")
    print(f"🔋 Batch size: {args.batch_size}")
    
    # Calculate API calls
    api_calls = (total + args.batch_size - 1) // args.batch_size
    print(f"📞 Expected API calls: {api_calls}")
    print(f"💰 Estimated cost: <$0.01 or FREE (free tier)\n")
    
    if total == 0:
        print("No products found!")
        return
    
    if args.dry_run:
        print("🔍 DRY RUN MODE\n")
        sample = products[0]
        print(f"Sample: {sample.name}")
        print(f"Current meta: {sample.meta_description}")
        print(f"Would generate: {api_calls} API calls")
        return
    
    # Show sample
    print("📋 Generating sample meta description...\n")
    sample = products[0]
    products_for_sample = [{
        'name': sample.name,
        'brand': sample.brand.name if sample.brand else 'Brand'
    }]
    
    sample_metas = generator.generate_batch_metas(products_for_sample)
    time.sleep(1)
    
    if sample_metas[0]:
        print(f"Product: {sample.name}")
        print(f"Current: {sample.meta_description}")
        print(f"New:     {sample_metas[0]}\n")
        
        confirm = input("Continue? (yes/no): ").strip().lower()
        if confirm != 'yes':
            print("Cancelled!")
            return
    
    print(f"\n🔄 Processing {total} products...\n")
    
    updated_count = 0
    failed_count = 0
    
    # Process in batches
    for batch_start in range(0, total, args.batch_size):
        batch_end = min(batch_start + args.batch_size, total)
        batch = products[batch_start:batch_end]
        batch_num = (batch_start // args.batch_size) + 1
        total_batches = (total + args.batch_size - 1) // args.batch_size
        
        print(f"[Batch {batch_num}/{total_batches}] ", end="", flush=True)
        
        try:
            # Prepare product info
            products_data = [
                {
                    'name': p.name,
                    'brand': p.brand.name if p.brand else 'Brand'
                }
                for p in batch
            ]
            
            # Generate metas
            metas = generator.generate_batch_metas(products_data)
            time.sleep(0.5)
            
            if all(m is None for m in metas):
                print(f"❌ Generation failed")
                failed_count += len(batch)
                continue
            
            # Update database
            for i, product in enumerate(batch):
                if metas[i]:
                    product.meta_description = metas[i]
                    product.save()
                    updated_count += 1
            
            print(f"✅ {len(batch)} products ({updated_count}/{total})")
        
        except Exception as e:
            print(f"❌ {str(e)[:40]}")
            failed_count += len(batch)
    
    print(f"\n{'='*60}")
    print(f"✨ Complete!")
    print(f"✅ Updated: {updated_count} products")
    print(f"❌ Failed: {failed_count} products")
    print(f"📞 API calls used: {generator.call_count}")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    main()
