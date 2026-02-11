#!/usr/bin/env python
"""
Interactive script to update laptop prices.
Loops through each laptop product and prompts for new price.
Press Enter to skip and keep current price.
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

from shop.models import Product, Category


def update_laptop_prices():
    """
    Interactive function to update laptop prices.
    Goes through each laptop one by one.
    """
    try:
        # Get the laptop category
        laptop_category = Category.objects.filter(name__iexact='laptop').first()
        
        if not laptop_category:
            print("Error: Laptop category not found in database.")
            print("Available categories:")
            for cat in Category.objects.all():
                print(f"  - {cat.name}")
            return
        
        # Get all laptop products
        laptops = Product.objects.filter(category=laptop_category).order_by('name')
        
        if not laptops.exists():
            print(f"No laptops found in category '{laptop_category.name}'")
            return
        
        print(f"\n{'='*60}")
        print(f"Found {laptops.count()} laptops to update")
        print(f"{'='*60}\n")
        
        updated_count = 0
        skipped_count = 0
        
        for index, laptop in enumerate(laptops, 1):
            print(f"{index}. {laptop.name} (Current price: Rs. {laptop.price})")
            
            # Get user input
            new_price_input = input("Enter the new price (or press Enter to skip): ").strip()
            
            # If user pressed Enter, skip this product
            if not new_price_input:
                print(f"   → Skipped. Keeping price at Rs. {laptop.price}\n")
                skipped_count += 1
                continue
            
            # Validate input
            try:
                new_price = int(new_price_input)
                
                if new_price < 0:
                    print("   ✗ Error: Price cannot be negative. Skipping...\n")
                    skipped_count += 1
                    continue
                
                # Update the price
                old_price = laptop.price
                laptop.price = new_price
                laptop.save()
                
                print(f"   ✓ Updated: Rs. {old_price} → Rs. {new_price}\n")
                updated_count += 1
                
            except ValueError:
                print(f"   ✗ Error: '{new_price_input}' is not a valid number. Skipping...\n")
                skipped_count += 1
                continue
        
        # Summary
        print(f"\n{'='*60}")
        print(f"Update Summary:")
        print(f"  • Total laptops: {laptops.count()}")
        print(f"  • Updated: {updated_count}")
        print(f"  • Skipped: {skipped_count}")
        print(f"{'='*60}\n")
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("           Laptop Price Update Tool")
    print("="*60)
    print("\nThis script will go through each laptop product.")
    print("Enter a new price or press Enter to keep the current price.\n")
    
    update_laptop_prices()
    
    print("Done! All laptops have been processed.\n")
