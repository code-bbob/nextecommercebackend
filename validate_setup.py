#!/usr/bin/env python
"""
Validation script to verify everything is set up correctly before running the main SEO generator.
Run this to diagnose issues before running the full script.
"""

import os
import sys
from pathlib import Path

print("\n" + "="*80)
print("🔍 SEO GENERATOR - SETUP VALIDATION")
print("="*80 + "\n")

# Check 1: .env file exists
print("1️⃣  Checking .env file...")
env_path = Path('.env')
if env_path.exists():
    print("   ✅ .env file found")
else:
    print("   ❌ .env file NOT found")
    print("   📝 Create it: cp .env.example .env")
    sys.exit(1)

# Check 2: GOOGLE_API_KEY is set
print("\n2️⃣  Checking GOOGLE_API_KEY...")
from dotenv import load_dotenv
load_dotenv('.env')
api_key = os.getenv('GOOGLE_API_KEY')

if not api_key:
    print("   ❌ GOOGLE_API_KEY not found in .env")
    sys.exit(1)
elif api_key == 'your-gemini-api-key-here':
    print("   ❌ GOOGLE_API_KEY is still the placeholder")
    print("   📝 Get a key at: https://aistudio.google.com/apikey")
    print("   ✏️  Edit .env and replace with your actual key")
    sys.exit(1)
else:
    print(f"   ✅ API key found: {api_key[:20]}...")

# Check 3: Required packages
print("\n3️⃣  Checking Python packages...")
packages = {
    'django': 'Django',
    'google.generativeai': 'google-generativeai',
    'dotenv': 'python-dotenv'
}

missing = []
for package, name in packages.items():
    try:
        __import__(package)
        print(f"   ✅ {name}")
    except ImportError:
        print(f"   ❌ {name} not found")
        missing.append(name)

if missing:
    print(f"\n   📦 Install missing packages:")
    print(f"      pip install {' '.join(missing)}")
    sys.exit(1)

# Check 4: Django setup
print("\n4️⃣  Checking Django setup...")
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
    import django
    django.setup()
    print("   ✅ Django configured")
except Exception as e:
    print(f"   ❌ Django setup failed: {e}")
    sys.exit(1)

# Check 5: Database connection
print("\n5️⃣  Checking database connection...")
try:
    from shop.models import Product
    count = Product.objects.count()
    print(f"   ✅ Database connected ({count} products found)")
except Exception as e:
    print(f"   ❌ Database connection failed: {e}")
    sys.exit(1)

# Check 6: Gemini API connection
print("\n6️⃣  Checking Gemini API connection...")
try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    # Try with gemini-2.5-flash which is available
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # Test with a simple request
    response = model.generate_content("Say 'hello' in one word.")
    if response.text:
        print(f"   ✅ Gemini API working ({response.text.strip()})")
    else:
        print(f"   ⚠️  Gemini API responded but no text")
except Exception as e:
    error_msg = str(e)
    print(f"   ❌ Gemini API failed: {error_msg[:100]}...")
    print("   💡 Possible causes:")
    if "quota" in error_msg.lower():
        print("      • Free tier quota exceeded (enable billing: https://console.cloud.google.com/billing)")
    if "429" in error_msg:
        print("      • Rate limit exceeded - try again later")
    else:
        print("      • Invalid API key")
        print("      • Network connectivity issue")
    sys.exit(1)

# Check 7: Main script exists
print("\n7️⃣  Checking main script...")
if Path('generate_seo_complete.py').exists():
    print("   ✅ generate_seo_complete.py found")
else:
    print("   ❌ generate_seo_complete.py not found")
    sys.exit(1)

# Check 8: Sample product
print("\n8️⃣  Checking sample product...")
try:
    from shop.models import Product
    sample = Product.objects.first()
    if sample:
        print(f"   ✅ Sample product: {sample.name[:50]}...")
    else:
        print("   ⚠️  No products in database")
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

# All checks passed
print("\n" + "="*80)
print("✨ ALL CHECKS PASSED!")
print("="*80)
print("\nYou're ready to run the SEO generator:")
print("  python generate_seo_complete.py --dry-run")
print("\nThen:")
print("  python generate_seo_complete.py")
print()
