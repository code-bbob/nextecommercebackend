import os
import requests
import django
import time
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.utils.text import slugify

# 1. SETUP DJANGO ENVIRONMENT
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings') 
django.setup()

from shop.models import Product, Category, Brand, ProductImage, ProductAttribute

def parse_specs_table(html_content):
    """
    Parses the HTML table specifically from the 'specification' field.
    """
    specs = {}
    if not html_content:
        return specs
    
    soup = BeautifulSoup(html_content, 'html.parser')
    rows = soup.find_all('tr')
    
    for row in rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) >= 2:
            # Clean up the key and value (handling nested tags like <a> or <span>)
            key = cells[0].get_text(" ", strip=True).replace('\xa0', ' ')
            value = cells[1].get_text(" ", strip=True).replace('\xa0', ' ')
            
            if key and value:
                specs[key] = value
                
    return specs

def run_import():
    LIST_URL = "https://admin.itti.com.np/api/product-list?type=category&type_slug=laptops-by-brands&per_page=400"
    DETAIL_BASE_URL = "https://admin.itti.com.np/api/product-detail/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }

    print("--- Starting Import ---")
    list_response = requests.get(LIST_URL, headers=headers)
    if list_response.status_code != 200:
        return

    products_list = list_response.json().get('data', [])
    category_obj, _ = Category.objects.get_or_create(name="Laptops")

    for item in products_list:
        slug = item.get('slug')
        print(f"\nFetching: {slug}")
        
        try:
            detail_response = requests.get(f"{DETAIL_BASE_URL}{slug}", headers=headers, timeout=15)
            if detail_response.status_code != 200:
                continue
            
            # The JSON response per product
            response_json = detail_response.json()
            details = response_json.get('data', {})
        except Exception as e:
            print(f"Error: {e}")
            continue

        # Handle Brand
        brand_name = item['name'].split(' ')[0]
        brand_obj, _ = Brand.objects.get_or_create(name=brand_name)

        # Update Product
        price_data = item.get('price', {})
        product, created = Product.objects.update_or_create(
            name=item['name'],
            defaults={
                'seo_friendly_name': slug,
                'price': price_data.get('selling_price', 0),
                'old_price': price_data.get('mark_price', 0),
                'category': category_obj,
                'brand': brand_obj,
                'stock': price_data.get('stock', 10),
                'is_available': price_data.get('in_stock', True),
                'description': details.get('summary', '') or details.get('description', ''),
                'meta_description': details.get('meta_description', ''),
                'trending': details.get('is_new', False),
            }
        )

        # HANDLE ATTRIBUTES (FROM THE 'SPECIFICATION' FIELD)
        # Your API example shows a field called 'specification'
        html_spec = details.get('specification', '')
        parsed_specs = parse_specs_table(html_spec)
        
        if parsed_specs:
            # Refresh attributes
            ProductAttribute.objects.filter(product=product).delete()
            for attr_key, attr_val in parsed_specs.items():
                ProductAttribute.objects.create(
                    product=product,
                    attribute=attr_key,
                    value=attr_val
                )
            print(f"--- Filled {len(parsed_specs)} attributes.")
        else:
            print("--- No technical specifications found.")

        # Handle Images
        all_imgs = details.get('images', [])
        if not product.images.exists():
            for i, img_data in enumerate(all_imgs):
                img_url = img_data.get('image')
                if img_url:
                    try:
                        resp = requests.get(img_url, timeout=10)
                        if resp.status_code == 200:
                            p_img = ProductImage(product=product)
                            p_img.image.save(f"{slug}-{i}.webp", ContentFile(resp.content), save=True)
                    except:
                        pass

        time.sleep(0.5)

    print("\n✅ Process Finished!")

if __name__ == "__main__":
    run_import()