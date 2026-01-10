import sys
from django.db import models
from userauth.models import User
import uuid
from django.conf import settings
from django.utils import timezone
from django.db.models import Avg
from django.utils.text import slugify
from ckeditor.fields import RichTextField

# Create your models here.



class Product(models.Model):
    # product_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_id = models.SlugField(primary_key=True, unique=True,blank=True,editable=False)
    name = models.CharField(max_length=300)
    seo_friendly_name = models.CharField(max_length=200, blank=True, null=True)
    emi = models.BooleanField(default=False)
    category = models.ForeignKey('Category', on_delete=models.CASCADE,null=True, related_name='products')
    sub_category = models.ForeignKey('SubCategory', on_delete=models.CASCADE,null=True,blank=True, related_name='products')
    brand = models.ForeignKey('Brand', on_delete=models.CASCADE,null=True, related_name='products')
    series = models.ForeignKey('Series', on_delete=models.CASCADE,null=True,blank=True, related_name='products')   
    deal = models.BooleanField(default=False)
    old_price = models.FloatField(null=True,blank=True)
    before_deal_price = models.FloatField(null=True,blank=True)
    price = models.IntegerField(default=0)
    description= RichTextField()
    meta_description = models.TextField(blank=True)
    meta_keywords = models.TextField(blank=True)
    published_date = models.DateField(default=timezone.now)
    is_available = models.BooleanField(default=True)
    stock = models.IntegerField(default=10)
    trending = models.BooleanField(default=False)
    best_seller = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    auction = models.BooleanField(default=False)
    auction_start_time = models.DateTimeField(null=True, blank=True)
    base_price = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name
    def save(self, *args, **kwargs):
        if not self.product_id:
            # Use seo_friendly_name if it exists, otherwise use name
            slug_source = self.seo_friendly_name if self.seo_friendly_name else self.name
            self.product_id = slugify(slug_source)
            original_id = self.product_id
            num = 1
            while Product.objects.filter(product_id=self.product_id).exists():
                self.product_id = f"{original_id}-{num}"
                num += 1
        super().save(*args, **kwargs)

class Color(models.Model):
    name = models.CharField(max_length=50)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='colors')
    hex = models.CharField(max_length=7, blank=True, null=True)  # e.g., #FFFFFF

    def __str__(self):
        return f"{self.product.name} - {self.name}"

class Variant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)
    additional_price = models.FloatField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.name}"    

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to='shop/images', default='')
    color = models.ForeignKey(Color, on_delete=models.CASCADE, related_name='images', null=True, blank=True)
    
    def __str__(self):
        return f"Image for {self.product.name} and color {self.color.name if self.color else 'N/A'}"
    
class ProductAttribute(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='attributes')
    attribute = models.CharField(max_length=50, blank=True, null=True)
    value = models.TextField(max_length=200,blank=True, null=True)


class Rating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(default=0, choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to='shop/images', blank=True, null=True)

    class Meta:
        unique_together = ('product', 'user')  # Ensure each user can only rate a product once

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='comments', on_delete=models.CASCADE)
    text = models.CharField(max_length=100)
    published_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.text


class Repliess(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, related_name='replies', on_delete=models.CASCADE)#very important is related name
    text = models.CharField(max_length=100)
    published_date = models.DateField(auto_now_add=True)

class Brand(models.Model):
    name = models.CharField(max_length=50)
    category = models.ManyToManyField('Category', related_name='brands', null=True, blank=True)
    def __str__(self):
        return self.name
    
class Series(models.Model):
    name = models.CharField(max_length=50)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='series')
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='series')
    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=50)
    def __str__(self):
        return self.name
    
class SubCategory(models.Model):
    name = models.CharField(max_length=50)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    def __str__(self):
        return self.name
    

class Emi(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='emis')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='emis')
    applicant_firstName = models.CharField(max_length=100)
    applicant_middleName = models.CharField(max_length=100,blank=True,null=True)
    applicant_lastName = models.CharField(max_length=100)
    applicant_grandfathersName = models.CharField(max_length=100,blank=True,null=True)
    applicant_occupation = models.CharField(max_length=100)
    applicant_contactNumber = models.CharField(max_length=10)
    applicant_vdc = models.CharField(max_length=100)
    applicant_ward = models.CharField(max_length=10)
    applicant_city = models.CharField(max_length=100)
    applicant_citizenshipFront = models.FileField(upload_to='shop/emi',blank=True,null=True)
    applicant_citizenshipBack = models.FileField(upload_to='shop/emi',blank=True,null=True)
    applicant_passportPhoto = models.FileField(upload_to='shop/emi',blank=True,null=True)
    applicant_nid = models.FileField(upload_to='shop/emi',blank=True,null=True)
    guarantor_firstName = models.CharField(max_length=100)
    guarantor_middleName = models.CharField(max_length=100,blank=True,null=True)
    guarantor_lastName = models.CharField(max_length=100)
    guarantor_grandfathersName = models.CharField(max_length=100,blank=True,null=True)
    guarantor_occupation = models.CharField(max_length=100)
    guarantor_contactNumber = models.CharField(max_length=10)
    guarantor_vdc = models.CharField(max_length=100)
    guarantor_ward = models.CharField(max_length=10)
    guarantor_city = models.CharField(max_length=100)
    guarantor_citizenshipFront = models.FileField(upload_to='shop/emi',blank=True,null=True)
    guarantor_citizenshipBack = models.FileField(upload_to='shop/emi',blank=True,null=True)
    guarantor_passportPhoto = models.FileField(upload_to='shop/emi',blank=True,null=True)
    guarantor_nid = models.FileField(upload_to='shop/emi',blank=True,null=True)
    applicant_salaryCertificate = models.FileField(upload_to='shop/emi',blank=True,null=True)
    applicant_salaryCreditBankStatement = models.FileField(upload_to='shop/emi',blank=True,null=True)
    emiDuration = models.PositiveIntegerField()
    # interest_rate = models.FloatField()
    downpaymentAmount = models.FloatField()
    monthlyInstallment = models.FloatField()

    def __str__(self):
        return f"{self.product} - {self.duration} months"
    

# models.py
class PredefinedAttribute(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='predefined_attributes')
    key = models.CharField(max_length=50)
    default_value = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.category.name} - {self.key}"

# models.py
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Product)
def create_default_attributes(sender, instance, created, **kwargs):
    if 'loaddata' in sys.argv or 'migrate' in sys.argv:
        return
    if created:
        # Get predefined attributes for the product's category
        predefined_attrs = instance.category.predefined_attributes.all() if instance.category else []
        for predef in predefined_attrs:
            # Create a ProductAttribute with default value (if any)
            ProductAttribute.objects.create(
                product=instance,
                attribute=predef.key,
                value=predef.default_value or ''
            )

class PageStats(models.Model):
    visits = models.BigIntegerField(default=0)
    last_reset = models.DateField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.pk and PageStats.objects.exists():
        # if you'll not check for self.pk 
        # then error will also raised in update of exists model
            raise Exception('There is can be only one PageStats instance')
        return super(PageStats, self).save(*args, **kwargs)

    def __str__(self):
        return f"Visits: {self.visits}"
