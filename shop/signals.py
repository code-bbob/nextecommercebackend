from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Product
import requests
from django.http import JsonResponse
from django.conf import settings

@receiver(post_save, sender=Product)
def post_to_fb(sender, instance, created, **kwargs):
    if created:
        print("HERE")
        message = f"The wait is now over for {instance.name}. The product is now available on our website. Click below to check it out now!"
        page_access_token = settings.FACEBOOK_PAGE_ACCESS_TOKEN
        print(page_access_token)
        page_id = settings.FACEBOOK_PAGE_ID
        print(page_id)

        url = f"https://graph.facebook.com/{page_id}/feed"
        payload = {
            'message': message,
            'link': f'https://www.dgtech.com.np/product/{instance.product_id}/',
            'access_token': page_access_token
        }

        res = requests.post(url, data=payload)
        print(res.json())