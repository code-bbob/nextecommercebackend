#!/usr/bin/env python
"""
Script to generate unique, SEO-friendly product descriptions using Google Gemini AI.
Useful for bulk updating products with duplicated descriptions.
"""

import os
import django
import time
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

from shop.models import Product
import google.generativeai as genai

# ========================
# CONFIGURATION
# ========================
BATCH_SIZE = 5  # Process this many products before saving progress
DELAY_BETWEEN_REQUESTS = 1  # Seconds to wait between API calls (to avoid rate limiting)
PROGRESS_FILE = 'description_generation_progress.json'

# Get API key from environment
API_KEY = os.getenv('GOOGLE_API_KEY')
if not API_KEY:
    print("❌ ERROR: GOOGLE_API_KEY environment variable not set!")
    print("Set it with: export GOOGLE_API_KEY='your-key-here'")
    exit(1)

genai.configure(api_key=API_KEY)

# ========================
# HELPER FUNCTIONS
# ========================

def load_progress():
    """Load progress from file to resume from where we left off."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'processed': [], 'total': 0, 'failed': []}

def save_progress(progress):
    """Save progress to file."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def generate_description(product_name, category, brand):
    """Generate a unique, SEO-friendly description using Gemini AI."""
    
    prompt = f"""Generate a unique, compelling product description for an e-commerce website.

Product Name: {product_name}
Category: {category}
Brand: {brand}

Requirements:
- Write 2-3 sentences (50-100 words)
- Focus on benefits and key features that customers care about
- Make it SEO-friendly but natural (avoid keyword stuffing)
- Unique - not generic
- Professional but conversational tone
- Include performance/value proposition
- NO markdown formatting, plain text only

Format your response as: DESCRIPTION: [your description here]"""

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt, safety_settings=[
            {
                "category": "HARM_CATEGORY_UNSPECIFIED",
                "threshold": "BLOCK_NONE",
            },
        ])
        
        result = response.text.strip()
        
        # Extract description if it has the prefix
        if result.startswith("DESCRIPTION:"):
            result = result.replace("DESCRIPTION:", "").strip()
        
        return result
    except Exception as e:
        print(f"❌ Error generating description: {e}")
        return None

def generate_meta_description(product_name, description, brand):
    """Generate a concise meta description (155 characters) for SEO."""
    
    prompt = f"""Generate a concise meta description for search engines.

Product Name: {product_name}
Brand: {brand}
Description: {description}

Requirements:
- MUST be 150-160 characters (including spaces)
- Include main keywords naturally
- Make it compelling to click from search results
- Include brand name if possible
- NO markdown or special formatting

Format: META: [your meta description here]"""

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        result = response.text.strip()
        if result.startswith("META:"):
            result = result.replace("META:", "").strip()
        
        # Ensure it's not too long
        if len(result) > 160:
            result = result[:157] + "..."
        
        return result
    except Exception as e:
        print(f"❌ Error generating meta description: {e}")
        return None

def display_sample(product_name, old_desc, new_desc, old_meta, new_meta):
    """Display a sample of the changes."""
    print("\n" + "="*80)
    print(f"📦 Product: {product_name}")
    print("="*80)
    
    print("\n🔴 OLD Description:")
    print(f"   {old_desc[:150]}..." if len(old_desc) > 150 else f"   {old_desc}")
    
    print("\n🟢 NEW Description:")
    print(f"   {new_desc}")
    
    print("\n🔴 OLD Meta:")
    print(f"   {old_meta[:100]}..." if len(old_meta) > 100 else f"   {old_meta}")
    
    print("\n🟢 NEW Meta:")
    print(f"   {new_meta}")
    print("="*80)

# ========================
# MAIN SCRIPT
# ========================

def main():
    print("\n🚀 Starting Product Description Generator...")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load progress
    progress = load_progress()
    processed_ids = set(progress['processed'])
    failed_ids = set(progress['failed'])
    
    # Get all laptop products (assuming there's a Laptop subcategory or we filter by category)
    # Adjust the filter based on how your data is organized
    products = Product.objects.filter(category__name__icontains='laptop').exclude(
        product_id__in=processed_ids
    ).exclude(
        product_id__in=failed_ids
    )
    
    total_products = products.count()
    print(f"📊 Total products to process: {total_products}")
    print(f"✅ Already processed: {len(processed_ids)}")
    print(f"❌ Failed previously: {len(failed_ids)}")
    print(f"⏳ Remaining: {total_products}\n")
    
    if total_products == 0:
        print("✨ No products to process!")
        return
    
    # Ask for confirmation with sample
    print("Generating sample descriptions...\n")
    sample_product = products.first()
    if sample_product:
        sample_desc = generate_description(
            sample_product.name,
            sample_product.category.name if sample_product.category else "Laptop",
            sample_product.brand.name if sample_product.brand else "Brand"
        )
        time.sleep(DELAY_BETWEEN_REQUESTS)
        
        sample_meta = generate_meta_description(
            sample_product.name,
            sample_desc,
            sample_product.brand.name if sample_product.brand else "Brand"
        )
        
        if sample_desc and sample_meta:
            display_sample(
                sample_product.name,
                sample_product.description[:200] if sample_product.description else "No description",
                sample_desc,
                sample_product.meta_description[:100] if sample_product.meta_description else "No meta",
                sample_meta
            )
        
        response = input("\n✋ Does this look good? Continue? (yes/no): ").strip().lower()
        if response != 'yes':
            print("❌ Cancelled!")
            return
    
    print("\n" + "="*80)
    print("🔄 Starting batch processing...")
    print("="*80 + "\n")
    
    batch_count = 0
    for idx, product in enumerate(products, 1):
        try:
            print(f"[{idx}/{total_products}] Processing: {product.name[:50]}...", end=" ")
            
            # Generate new description
            new_description = generate_description(
                product.name,
                product.category.name if product.category else "Laptop",
                product.brand.name if product.brand else "Brand"
            )
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
            if not new_description:
                print("⚠️ Failed to generate description")
                failed_ids.add(product.product_id)
                continue
            
            # Generate meta description
            new_meta = generate_meta_description(
                product.name,
                new_description,
                product.brand.name if product.brand else "Brand"
            )
            
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
            if not new_meta:
                print("⚠️ Failed to generate meta")
                failed_ids.add(product.product_id)
                continue
            
            # Update product
            product.description = new_description
            product.meta_description = new_meta
            product.save()
            
            processed_ids.add(product.product_id)
            batch_count += 1
            
            print("✅ Done")
            
            # Save progress every batch
            if batch_count >= BATCH_SIZE:
                progress['processed'] = list(processed_ids)
                progress['failed'] = list(failed_ids)
                progress['total'] = total_products
                save_progress(progress)
                batch_count = 0
                print(f"\n💾 Progress saved! ({len(processed_ids)}/{total_products})\n")
        
        except Exception as e:
            print(f"❌ Error: {e}")
            failed_ids.add(product.product_id)
    
    # Final save
    progress['processed'] = list(processed_ids)
    progress['failed'] = list(failed_ids)
    progress['total'] = total_products
    save_progress(progress)
    
    print("\n" + "="*80)
    print("✨ Script Complete!")
    print(f"✅ Successfully updated: {len(processed_ids)} products")
    print(f"❌ Failed: {len(failed_ids)} products")
    print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")

if __name__ == '__main__':
    main()
