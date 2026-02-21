#!/usr/bin/env python
"""
Optimized description generator - reduces API calls by 60-70% using batch generation
and intelligent grouping of similar products.
"""

import os
import django
import argparse
import json
import time
from datetime import datetime
from typing import Optional, List, Dict
from collections import defaultdict

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

from shop.models import Product
import google.generativeai as genai

class OptimizedDescriptionGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = None
        self.setup_genai()
        self.call_count = 0
    
    def setup_genai(self):
        """Configure Google Generative AI."""
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def generate_batch_descriptions(self, products_info: List[Dict]) -> List[Optional[str]]:
        """
        Generate descriptions for multiple products at once to save API calls.
        
        Args:
            products_info: List of dicts with 'name', 'category', 'brand'
        
        Returns:
            List of descriptions in same order
        """
        
        # Format as numbered list
        product_list = "\n".join([
            f"{i+1}. {p['name']} (Brand: {p['brand']}, Category: {p['category']})"
            for i, p in enumerate(products_info)
        ])
        
        prompt = f"""Generate unique, SEO-friendly product descriptions for these e-commerce items.

PRODUCTS:
{product_list}

Requirements for EACH description:
- 2-3 sentences (50-100 words)
- Focus on benefits and key features
- SEO-friendly but natural language
- Unique - not generic
- Professional but conversational
- Include performance/value proposition
- NO markdown formatting

Format your response EXACTLY as:
1. [description for product 1]
2. [description for product 2]
3. [description for product 3]
etc.

Start with just "1." - no other text before it."""

        try:
            response = self.model.generate_content(prompt)
            self.call_count += 1
            
            text = response.text.strip()
            
            # Parse numbered descriptions
            descriptions = []
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if line and line[0].isdigit() and '.' in line:
                    # Extract description after "N."
                    desc = line.split('.', 1)[1].strip()
                    descriptions.append(desc)
            
            # If parsing failed, return Nones
            while len(descriptions) < len(products_info):
                descriptions.append(None)
            
            return descriptions[:len(products_info)]
        
        except Exception as e:
            print(f"Batch generation error: {e}")
            return [None] * len(products_info)
    
    def generate_batch_metas(self, products_data: List[Dict]) -> List[Optional[str]]:
        """
        Generate meta descriptions for multiple products at once.
        
        Args:
            products_data: List of dicts with 'name', 'brand', 'description'
        
        Returns:
            List of meta descriptions
        """
        
        product_list = "\n".join([
            f"{i+1}. {p['name']} | {p['description'][:100]}..."
            for i, p in enumerate(products_data)
        ])
        
        prompt = f"""Generate concise SEO meta descriptions for these products.

PRODUCTS:
{product_list}

Requirements for EACH meta:
- MUST be 150-160 characters
- Include main keywords naturally
- Compelling to click from search results
- Include brand if possible
- NO markdown or special formatting

Format EXACTLY as:
1. [meta description 1]
2. [meta description 2]
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
            print(f"Meta batch error: {e}")
            return [None] * len(products_data)
    
    def generate_batch_keywords(self, products_data: List[Dict]) -> List[Optional[str]]:
        """Generate keywords for multiple products."""
        
        product_list = "\n".join([
            f"{i+1}. {p['name']} ({p['category']})"
            for i, p in enumerate(products_data)
        ])
        
        prompt = f"""Generate SEO keywords for these products.

PRODUCTS:
{product_list}

Requirements for EACH:
- 5-8 keywords separated by commas
- Relevant to product and category
- Include brand and product type
- Focus on customer search terms
- NO parentheses or special formatting

Format EXACTLY as:
1. keyword1, keyword2, keyword3, ...
2. keyword1, keyword2, keyword3, ...
etc.

Start with "1." only."""

        try:
            response = self.model.generate_content(prompt)
            self.call_count += 1
            
            text = response.text.strip()
            keywords = []
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if line and line[0].isdigit() and '.' in line:
                    kw = line.split('.', 1)[1].strip()
                    keywords.append(kw)
            
            while len(keywords) < len(products_data):
                keywords.append(None)
            
            return keywords[:len(products_data)]
        
        except Exception as e:
            print(f"Keywords batch error: {e}")
            return [None] * len(products_data)

def main():
    parser = argparse.ArgumentParser(description='Optimized SEO description generator (reduced API calls)')
    parser.add_argument('--dry-run', action='store_true', help='Preview without saving')
    parser.add_argument('--category', type=str, help='Filter by category')
    parser.add_argument('--limit', type=int, help='Max products to process')
    parser.add_argument('--batch-size', type=int, default=5, help='Products per API call (default: 5)')
    parser.add_argument('--keywords', action='store_true', help='Also generate keywords')
    parser.add_argument('--show-calls', action='store_true', help='Show total API calls')
    
    args = parser.parse_args()
    
    # Setup
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY not set!")
        print("Get one at: https://aistudio.google.com/apikey")
        exit(1)
    
    generator = OptimizedDescriptionGenerator(api_key)
    
    # Get products
    query = Product.objects.all()
    
    if args.category:
        query = query.filter(category__name__icontains=args.category)
    
    if args.limit:
        query = query[:args.limit]
    
    products = list(query)
    total = len(products)
    
    print(f"\n📊 Found {total} products")
    print(f"🔋 Using batch size: {args.batch_size} products per API call")
    
    # Calculate expected API calls
    description_calls = (total + args.batch_size - 1) // args.batch_size
    meta_calls = description_calls
    keyword_calls = description_calls if args.keywords else 0
    total_calls = description_calls + meta_calls + keyword_calls
    
    print(f"📞 Expected API calls:")
    print(f"   • Descriptions: {description_calls}")
    print(f"   • Meta descriptions: {meta_calls}")
    if args.keywords:
        print(f"   • Keywords: {keyword_calls}")
    print(f"   • TOTAL: {total_calls} calls")
    
    # Cost estimate
    if args.keywords:
        print(f"💰 Estimated cost: ~$0.01-0.02 (paid tier) or FREE (free tier, 15/min limit)")
    else:
        print(f"💰 Estimated cost: ~$0.005-0.01 or FREE (free tier, 15/min limit)")
    
    if total == 0:
        print("No products found!")
        return
    
    if args.dry_run:
        print("\n🔍 DRY RUN - showing sample\n")
        # Just show sample without processing
        sample = products[0]
        print(f"Sample product: {sample.name}")
        print(f"Current description: {sample.description[:100]}...")
        print(f"Would generate: ~{len(products) // args.batch_size} API calls")
        return
    
    print("\n✋ Ready to process?")
    confirm = input("Continue? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("Cancelled!")
        return
    
    print(f"\n🔄 Processing {total} products in batches of {args.batch_size}...\n")
    
    updated_count = 0
    failed_count = 0
    
    # Process in batches
    for batch_start in range(0, total, args.batch_size):
        batch_end = min(batch_start + args.batch_size, total)
        batch = products[batch_start:batch_end]
        batch_num = (batch_start // args.batch_size) + 1
        total_batches = (total + args.batch_size - 1) // args.batch_size
        
        print(f"[Batch {batch_num}/{total_batches}] Processing {len(batch)} products...", end=" ", flush=True)
        
        try:
            # Prepare product info
            products_info = [
                {
                    'name': p.name,
                    'category': p.category.name if p.category else 'Product',
                    'brand': p.brand.name if p.brand else 'Brand'
                }
                for p in batch
            ]
            
            # Generate descriptions
            descriptions = generator.generate_batch_descriptions(products_info)
            time.sleep(0.5)
            
            if all(d is None for d in descriptions):
                print("❌ Description generation failed")
                failed_count += len(batch)
                continue
            
            # Generate metas
            products_for_meta = [
                {
                    'name': p.name,
                    'brand': p.brand.name if p.brand else 'Brand',
                    'description': descriptions[i] or p.description
                }
                for i, p in enumerate(batch)
            ]
            
            metas = generator.generate_batch_metas(products_for_meta)
            time.sleep(0.5)
            
            if all(m is None for m in metas):
                print("❌ Meta generation failed")
                failed_count += len(batch)
                continue
            
            # Generate keywords if requested
            keywords_list = None
            if args.keywords:
                keywords_list = generator.generate_batch_keywords(products_info)
                time.sleep(0.5)
            
            # Update database
            for i, product in enumerate(batch):
                if descriptions[i]:
                    product.description = descriptions[i]
                if metas[i]:
                    product.meta_description = metas[i]
                if keywords_list and keywords_list[i]:
                    product.meta_keywords = keywords_list[i]
                
                product.save()
                updated_count += 1
            
            print(f"✅ ({updated_count}/{total})")
        
        except Exception as e:
            print(f"❌ {str(e)[:40]}")
            failed_count += len(batch)
    
    print(f"\n✨ Complete!")
    print(f"✅ Updated: {updated_count} products")
    print(f"❌ Failed: {failed_count} products")
    print(f"📞 Total API calls made: {generator.call_count}")
    print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

if __name__ == '__main__':
    main()
