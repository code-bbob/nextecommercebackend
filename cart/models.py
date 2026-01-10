from django.db import models
from django.conf import settings
import uuid
from django.utils import timezone
class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending','Pending'),
        ('Dispatched','Dispatched'),
        ('Cancelled','Cancelled'),
        ('Cleared','Cleared'),

    ]
    id = models.UUIDField(primary_key=True,default=uuid.uuid4)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='orders', on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=10,choices=STATUS_CHOICES,default="Pending")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    carts = models.ManyToManyField('Cart', related_name='order', blank=True)

    def order_items_str(self):
        items_list= '\n'.join([str(order_item) for order_item in self.order_items.all()])
        return f"\n{items_list}"
    def __str__(self):
        user_info = self.user if self.user else "Guest"
        return f"{self.order_items_str()} by {user_info}"

class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, related_name='order_items', on_delete=models.CASCADE)
    product = models.ForeignKey('shop.Product', related_name='order_items', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)  # Default to 1, but can be adjusted
    price = models.PositiveIntegerField(default=0)  # Store price at time of order (auction vs full price)

    def __str__(self):
        return f"{self.quantity} x {self.product}"

    class Meta:
        # Allow same product multiple times if at different prices (auction scenario)
        # This lets auction price and full price items coexist in same order
        unique_together = ['order', 'product', 'price']

class Delivery(models.Model):
    order=models.OneToOneField(Order, related_name='delivery', on_delete=models.CASCADE)#yo rel name xai uta fields ma use hunxa serializers ko
    phone_number = models.CharField(max_length=10)
    first_name = models.CharField(max_length=100,null=True,blank=True)
    last_name = models.CharField(max_length=100,null=True,blank=True)
    email = models.EmailField(null=True,blank=True)
    shipping_address = models.CharField(max_length=100)
    tol = models.CharField(max_length=100,null=True,blank=True)
    municipality = models.CharField(max_length=100,null=True,blank=True)
    city = models.CharField(max_length=100,null=True,blank=True)
    payment_method = models.CharField(max_length=100,null=True,blank=True)
    shipping_method = models.CharField(max_length=100,null=True,blank=True)
    shipping_cost = models.FloatField(default=0)
    subtotal = models.FloatField(default=0,null=True,blank=True)
    discount = models.FloatField(default=0,null=True,blank=True)
    payment_amount = models.FloatField(default=0)
    payment_status = models.CharField(max_length=10,null=True,blank=True)
    coupon_code = models.CharField(max_length=100,null=True,blank=True)

    def __str__(self):
        user_info = self.order.user if self.order.user else "Guest"
        return f"Delivery for {user_info}"
    
class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='cart', on_delete=models.CASCADE)
    product = models.ForeignKey('shop.Product', related_name='cart', on_delete=models.CASCADE)
    color = models.ForeignKey('shop.Color', related_name='cart', on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)  # Default to 1, but can be adjusted
    price = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.quantity} x {self.product}"

    class Meta:
        unique_together = ['user', 'product']


class Coupon(models.Model):
    code = models.CharField(max_length=10)
    amount = models.FloatField(default=0,null=True,blank=True)
    percentage = models.IntegerField(default=0,null=True,blank=True)
    active = models.BooleanField(default=True)
    expiry_date = models.DateField(null=True,blank=True)
    usage_limit = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0)
    def __str__(self):
        return f"{self.code}"
    
    def is_valid(self):
        # Ensure the coupon is not expired
        if self.expiry_date < timezone.now().date():
            return False
        
        # Ensure the coupon hasn't been used up
        if self.used_count >= self.usage_limit:
            return False

        # If user-specific, ensure it belongs to the user
        # if self.user_specific and user:
        #     if not self.applies_to_user(user):
        #         return False
        
        return True

    def applies_to_user(self, user):
        # Logic to check if the coupon applies to a user (e.g., check user ID)
        return True  # You can customize this as needed

    def apply_coupon(self, user):
        if self.is_valid():
            self.used_count += 1
            self.save()
            return True
        return False


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, related_name='payment', on_delete=models.CASCADE, null=True, blank=True)
    delivery = models.OneToOneField(Delivery, related_name='payment', on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='payments', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Stripe information
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True, db_index=True)
    stripe_client_secret = models.CharField(max_length=255, blank=True)
    stripe_charge_id = models.CharField(max_length=255, blank=True, unique=True, null=True)
    
    # Payment details
    amount = models.IntegerField(help_text="Amount in cents")  # Store in cents for Stripe
    currency = models.CharField(max_length=3, default='usd')
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Customer information
    email = models.EmailField()
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['stripe_payment_intent_id']),
            models.Index(fields=['status']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.stripe_payment_intent_id} - {self.status}"
