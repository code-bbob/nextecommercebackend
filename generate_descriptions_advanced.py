#!/usr/bin/env python
"""
Advanced script with more control options for generating product descriptions.
Supports dry-run mode, filtering, and batch operations.
"""

import os
import django
import argparse
import json
import time
from datetime import datetime
from typing import Optional

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

from shop.models import Product
import google.generativeai as genai

class DescriptionGenerator:
    def __init__(self, api_key: str, batch_size: int = 5):
        self.api_key = api_key
        self.batch_size = batch_size
        self.model = None
        self.setup_genai()
    
    def setup_genai(self):
        """Configure Google Generative AI."""
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def generate_description(self, product_name: str, category: str, brand: str, specs: Optional[str] = None) -> Optional[str]:
        """Generate a unique product description."""
        
        specs_context = f"Key specs: {specs}" if specs else ""
        
        prompt = f"""Generate a unique, compelling product description for an e-commerce website.

Product Name: {product_name}
Category: {category}
Brand: {brand}
{specs_context}

Requirements:
- Write 2-3 sentences (50-100 words)
- Focus on benefits and key features
- SEO-friendly but natural
- Unique - not generic or template-like
- Professional but conversational
- Include performance/value proposition
- NO markdown, plain text only

Output ONLY the description, nothing else."""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def generate_meta_description(self, product_name: str, description: str, brand: str) -> Optional[str]:
        """Generate SEO meta description (155 chars)."""
        
        prompt = f"""Generate a concise meta description for search engines.

Product: {product_name}
Brand: {brand}
Description: {description}

Requirements:
- MUST be 150-160 characters
- Include main keywords naturally
- Compelling to click from search results
- Include brand if possible
- NO markdown

Output ONLY the meta description, nothing else."""

        try:
            response = self.model.generate_content(prompt)
            result = response.text.strip()
            
            # Truncate if too long
            if len(result) > 160:
                result = result[:157] + "..."
            
            return result
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def generate_meta_keywords(self, product_name: str, category: str, brand: str) -> Optional[str]:
        """Generate SEO keywords."""
        
        prompt = f"""Generate SEO keywords for this product.

Product: {product_name}
Category: {category}
Brand: {brand}

Requirements:
- 5-8 relevant keywords
- Separated by commas
- Focus on what customers search for
- Include brand name
- Include category
- Include specific product type

Output ONLY the keywords, nothing else."""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(description='Generate SEO-friendly product descriptions')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without saving')
    parser.add_argument('--category', type=str, help='Filter by category (e.g., "laptop")')
    parser.add_argument('--limit', type=int, help='Process only N products')
    parser.add_argument('--skip', type=int, default=0, help='Skip first N products')
    parser.add_argument('--keywords', action='store_true', help='Also generate meta keywords')
    parser.add_argument('--batch-size', type=int, default=5, help='Batch size for progress saves')
    
    args = parser.parse_args()
    
    # Setup
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY not set!")
        exit(1)
    
    generator = DescriptionGenerator(api_key, batch_size=args.batch_size)
    
    # Get products
    query = Product.objects.all()
    
    if args.category:
        query = query.filter(category__name__icontains=args.category)
    
    query = query[args.skip:]
    
    if args.limit:
        query = query[:args.limit]
    
    products = list(query)
    total = len(products)
    
    print(f"\n📊 Found {total} products to process")
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be saved\n")
    
    if total == 0:
        print("No products found!")
        return
    
    # Show sample
    if products:
        print("\n📋 Generating sample...\n")
        sample = products[0]
        
        new_desc = generator.generate_description(
            sample.name,
            sample.category.name if sample.category else "Product",
            sample.brand.name if sample.brand else "Brand"
        )
        time.sleep(1)
        
        new_meta = generator.generate_meta_description(sample.name, new_desc, sample.brand.name if sample.brand else "Brand")
        time.sleep(1)
        
        if args.keywords:
            new_keywords = generator.generate_meta_keywords(
                sample.name,
                sample.category.name if sample.category else "Product",
                sample.brand.name if sample.brand else "Brand"
            )
            time.sleep(1)
        
        print(f"Product: {sample.name}\n")
        print(f"OLD Description:\n{sample.description[:150]}...\n")
        print(f"NEW Description:\n{new_desc}\n")
        print(f"OLD Meta:\n{sample.meta_description}\n")
        print(f"NEW Meta:\n{new_meta}\n")
        
        if args.keywords:
            print(f"NEW Keywords:\n{new_keywords}\n")
        
        if not args.dry_run:
            confirm = input("Continue? (yes/no): ").strip().lower()
            if confirm != 'yes':
                print("Cancelled!")
                return
    
    # Process all
    print(f"\n🔄 Processing {total} products...\n")
    
    for idx, product in enumerate(products, 1):
        try:
            print(f"[{idx}/{total}] {product.name[:50]:<50}", end=" ", flush=True)
            
            # Generate
            new_desc = generator.generate_description(
                product.name,
                product.category.name if product.category else "Product",
                product.brand.name if product.brand else "Brand"
            )
            time.sleep(0.5)
            
            if not new_desc:
                print("❌ Description failed")
                continue
            
            new_meta = generator.generate_meta_description(
                product.name,
                new_desc,
                product.brand.name if product.brand else "Brand"
            )
            time.sleep(0.5)
            
            if not new_meta:
                print("❌ Meta failed")
                continue
            
            updates = {
                'description': new_desc,
                'meta_description': new_meta,
            }
            
            if args.keywords:
                new_keywords = generator.generate_meta_keywords(
                    product.name,
                    product.category.name if product.category else "Product",
                    product.brand.name if product.brand else "Brand"
                )
                time.sleep(0.5)
                if new_keywords:
                    updates['meta_keywords'] = new_keywords
            
            if args.dry_run:
                print("✅ (DRY RUN)")
            else:
                for key, value in updates.items():
                    setattr(product, key, value)
                product.save()
                print("✅")
        
        except Exception as e:
            print(f"❌ {str(e)[:30]}")
    
    print(f"\n✨ Complete!")

if __name__ == '__main__':
    main()
