#!/usr/bin/env python
"""
Complete script to update product names, meta descriptions, and descriptions.
Optimized with batch processing to minimize API calls.
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

class CompleteProductGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = None
        self.setup_genai()
        self.call_count = 0
    
    def setup_genai(self):
        """Configure Google Generative AI."""
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def generate_batch_names(self, products_data):
        """Generate improved product names for multiple products."""
        
        product_list = "\n".join([
            f"{i+1}. {p['current_name']}"
            for i, p in enumerate(products_data)
        ])
        
        prompt = f"""Rewrite these product names to be SEO-friendly and user-friendly.

CURRENT NAMES:
{product_list}

For EACH name:
- Keep it under 100 characters
- Include brand and key specs
- Use natural language (avoid pipe characters |)
- Make it clear what the product is
- Include performance specs if available
- NO special characters or excessive punctuation
- Format: Brand Model - Key Specs (specs in parentheses)

Format EXACTLY as:
1. [new name]
2. [new name]
etc.

Start with "1." only."""

        try:
            response = self.model.generate_content(prompt)
            self.call_count += 1
            
            text = response.text.strip()
            names = []
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if line and line[0].isdigit() and '.' in line:
                    name = line.split('.', 1)[1].strip()
                    if len(name) > 150:
                        name = name[:147] + "..."
                    names.append(name)
            
            while len(names) < len(products_data):
                names.append(None)
            
            return names[:len(products_data)]
        
        except Exception as e:
            print(f"Error: {e}")
            return [None] * len(products_data)
    
    def generate_batch_descriptions(self, products_data):
        """Generate product descriptions for multiple products."""
        
        product_list = "\n".join([
            f"{i+1}. {p['name']} (Brand: {p['brand']}, Category: {p['category']})"
            for i, p in enumerate(products_data)
        ])
        
        prompt = f"""Generate unique, SEO-friendly product descriptions.

PRODUCTS:
{product_list}

For EACH description:
- Write 2-3 sentences (50-100 words)
- Focus on benefits and key features
- SEO-friendly but natural
- Unique - not generic
- Professional but conversational
- Include performance/value proposition
- NO markdown formatting

Format EXACTLY as:
1. [description]
2. [description]
etc.

Start with "1." only."""

        try:
            response = self.model.generate_content(prompt)
            self.call_count += 1
            
            text = response.text.strip()
            descriptions = []
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if line and line[0].isdigit() and '.' in line:
                    desc = line.split('.', 1)[1].strip()
                    descriptions.append(desc)
            
            while len(descriptions) < len(products_data):
                descriptions.append(None)
            
            return descriptions[:len(products_data)]
        
        except Exception as e:
            print(f"Error: {e}")
            return [None] * len(products_data)
    
    def generate_batch_metas(self, products_data):
        """Generate meta descriptions for multiple products."""
        
        product_list = "\n".join([
            f"{i+1}. {p['name']} - {p['brand']}"
            for i, p in enumerate(products_data)
        ])
        
        prompt = f"""Generate SEO meta descriptions (155 chars) for these products.

PRODUCTS:
{product_list}

For EACH:
- Write 150-160 characters
- Include product name and key benefit
- Make it compelling to click
- Include brand if possible
- NO markdown, NO special characters

Format EXACTLY as:
1. [meta description]
2. [meta description]
etc.

Start with "1." only."""

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
                    if len(meta) > 160:
                        meta = meta[:157] + "..."
                    metas.append(meta)
            
            while len(metas) < len(products_data):
                metas.append(None)
            
            return metas[:len(products_data)]
        
        except Exception as e:
            print(f"Error: {e}")
            return [None] * len(products_data)

def main():
    parser = argparse.ArgumentParser(description='Update product names, descriptions, and meta descriptions')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    parser.add_argument('--category', type=str, help='Filter by category')
    parser.add_argument('--limit', type=int, help='Max products to process')
    parser.add_argument('--batch-size', type=int, default=5, help='Products per API call')
    parser.add_argument('--names-only', action='store_true', help='Only update names')
    parser.add_argument('--metas-only', action='store_true', help='Only update meta descriptions')
    parser.add_argument('--descriptions-only', action='store_true', help='Only update descriptions')
    
    args = parser.parse_args()
    
    # Setup
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY not set!")
        print("\nSet it with:")
        print('  export GOOGLE_API_KEY="your-key-here"')
        print("\nOr permanently add to ~/.bashrc:")
        print('  echo \'export GOOGLE_API_KEY="your-key-here"\' >> ~/.bashrc')
        print('  source ~/.bashrc')
        print("\nGet a free key at: https://aistudio.google.com/apikey")
        exit(1)
    
    generator = CompleteProductGenerator(api_key)
    
    # Get products
    query = Product.objects.all()
    
    if args.category:
        query = query.filter(category__name__icontains=args.category)
    
    if args.limit:
        query = query[:args.limit]
    
    products = list(query)
    total = len(products)
    
    # Determine what we're updating
    update_names = not args.metas_only and not args.descriptions_only
    update_descriptions = not args.names_only and not args.metas_only
    update_metas = not args.names_only and not args.descriptions_only
    
    if args.names_only:
        update_descriptions = False
        update_metas = False
    if args.metas_only:
        update_names = False
        update_descriptions = False
    if args.descriptions_only:
        update_names = False
        update_metas = False
    
    print(f"\n📊 Found {total} products")
    print(f"🔋 Batch size: {args.batch_size}")
    
    # Calculate API calls
    api_calls_per_product = sum([update_names, update_descriptions, update_metas])
    api_calls = ((total + args.batch_size - 1) // args.batch_size) * api_calls_per_product
    
    print(f"\n🔄 Will update:")
    if update_names:
        print(f"   ✅ Product names")
    if update_descriptions:
        print(f"   ✅ Product descriptions")
    if update_metas:
        print(f"   ✅ Meta descriptions")
    
    print(f"\n📞 Expected API calls: {api_calls}")
    if api_calls_per_product == 3:
        print(f"💰 Cost: ~$0.01-0.02 or FREE (free tier, 15/min)")
    elif api_calls_per_product == 2:
        print(f"💰 Cost: ~$0.01 or FREE (free tier, 15/min)")
    else:
        print(f"💰 Cost: <$0.01 or FREE (free tier, 15/min)")
    
    if total == 0:
        print("\n❌ No products found!")
        return
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - Showing sample\n")
        sample = products[0]
        print(f"{'='*70}")
        print(f"Product: {sample.name}")
        print(f"{'='*70}")
        
        # Generate samples
        products_data = [{
            'current_name': sample.name,
            'name': sample.name,
            'brand': sample.brand.name if sample.brand else 'Brand',
            'category': sample.category.name if sample.category else 'Category'
        }]
        
        if update_names:
            sample_names = generator.generate_batch_names([{'current_name': sample.name}])
            time.sleep(0.5)
            print(f"\n🔴 Current Name:\n{sample.name}")
            print(f"\n🟢 New Name:\n{sample_names[0]}")
        
        if update_descriptions:
            sample_descs = generator.generate_batch_descriptions(products_data)
            time.sleep(0.5)
            print(f"\n🔴 Current Description:\n{sample.description[:150]}...")
            print(f"\n🟢 New Description:\n{sample_descs[0]}")
        
        if update_metas:
            sample_metas = generator.generate_batch_metas(products_data)
            time.sleep(0.5)
            print(f"\n🔴 Current Meta:\n{sample.meta_description}")
            print(f"\n🟢 New Meta:\n{sample_metas[0]}")
        
        print(f"\n{'='*70}")
        print(f"Would generate: {api_calls} API calls")
        return
    
    # Show sample and confirm
    print("\n📋 Generating sample...\n")
    sample = products[0]
    print(f"Product: {sample.name[:60]}...")
    
    products_data = [{
        'current_name': sample.name,
        'name': sample.name,
        'brand': sample.brand.name if sample.brand else 'Brand',
        'category': sample.category.name if sample.category else 'Category'
    }]
    
    sample_updates = {}
    
    if update_names:
        sample_names = generator.generate_batch_names([{'current_name': sample.name}])
        time.sleep(0.5)
        sample_updates['name'] = sample_names[0]
        print(f"New name: {sample_names[0]}\n")
    
    if update_descriptions:
        sample_descs = generator.generate_batch_descriptions(products_data)
        time.sleep(0.5)
        sample_updates['description'] = sample_descs[0]
        print(f"New description: {sample_descs[0]}\n")
    
    if update_metas:
        sample_metas = generator.generate_batch_metas(products_data)
        time.sleep(0.5)
        sample_updates['meta'] = sample_metas[0]
        print(f"New meta: {sample_metas[0]}\n")
    
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
            batch_updates = {}
            
            if update_names:
                names_data = [{'current_name': p.name} for p in batch]
                batch_updates['names'] = generator.generate_batch_names(names_data)
                time.sleep(0.5)
            
            if update_descriptions:
                desc_data = [
                    {
                        'name': p.name,
                        'brand': p.brand.name if p.brand else 'Brand',
                        'category': p.category.name if p.category else 'Category'
                    }
                    for p in batch
                ]
                batch_updates['descriptions'] = generator.generate_batch_descriptions(desc_data)
                time.sleep(0.5)
            
            if update_metas:
                meta_data = [
                    {
                        'name': p.name,
                        'brand': p.brand.name if p.brand else 'Brand'
                    }
                    for p in batch
                ]
                batch_updates['metas'] = generator.generate_batch_metas(meta_data)
                time.sleep(0.5)
            
            # Update database
            for i, product in enumerate(batch):
                if update_names and batch_updates['names'][i]:
                    product.name = batch_updates['names'][i]
                if update_descriptions and batch_updates['descriptions'][i]:
                    product.description = batch_updates['descriptions'][i]
                if update_metas and batch_updates['metas'][i]:
                    product.meta_description = batch_updates['metas'][i]
                
                product.save()
                updated_count += 1
            
            print(f"✅ {len(batch)} products ({updated_count}/{total})")
        
        except Exception as e:
            print(f"❌ {str(e)[:40]}")
            failed_count += len(batch)
    
    print(f"\n{'='*70}")
    print(f"✨ Complete!")
    print(f"✅ Updated: {updated_count} products")
    print(f"❌ Failed: {failed_count} products")
    print(f"📞 API calls used: {generator.call_count}")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    main()
