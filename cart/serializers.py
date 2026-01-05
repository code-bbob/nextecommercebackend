from rest_framework import serializers
from .models import Order, OrderItem, Delivery, Cart, Payment
from shop.models import Product
from shop.serializers import ProductSerializer

class OrderItemSerializer(serializers.ModelSerializer):
    # product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())  # Adjust queryset based on your Product model
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_id = serializers.CharField(source='product.product_id', read_only=True)
    class Meta:
        model = OrderItem
        fields = ['id', 'product_name','product_id', 'quantity']


class DeliverySerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = Delivery
        fields = '__all__'

class OrderSerializer(serializers.ModelSerializer):
    order_items = OrderItemSerializer(many=True, read_only=True)
    user_name = serializers.SerializerMethodField()
    delivery = DeliverySerializer(read_only=True)
    items = serializers.ListField(required=False, write_only=True)  # Accept direct items for guest checkout

    class Meta:
        model = Order
        fields = '__all__'#yo field ma xai uta ko related name use hunxa

    def create(self, validated_data):
        carts = validated_data.pop('carts', None)
        items = validated_data.pop('items', None)  # Items sent directly from frontend
        order = Order.objects.create(**validated_data)
        
        # Handle cart items (for logged-in users)
        if carts: 
            for cart in carts:
                product = cart.product
                quantity = cart.quantity
                cart.delete()
                OrderItem.objects.create(product=product, quantity=quantity, order=order)
        
        # Handle direct items (for guest users or when items are sent directly)
        elif items:
            for item in items:
                product_id = item.get('product_id')
                quantity = item.get('quantity', 1)
                try:
                    product = Product.objects.get(product_id=product_id)
                    OrderItem.objects.create(product=product, quantity=quantity, order=order)
                except Product.DoesNotExist:
                    continue  # Skip if product doesn't exist

        return order
    
    def get_user_name(self, obj):
        return obj.user.name if obj.user else "Guest"

class CartSerializer(serializers.ModelSerializer):
    product_id = serializers.CharField(source='product.product_id', read_only=True)
    image = serializers.SerializerMethodField()
    name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Cart
        fields = ['id','product_id', 'image', 'quantity','name','price','color']

    def get_image(self, obj):
        request = self.context.get('request')  # Get request from context
        first_image = obj.product.images.first()  # Get first product image
        
        if first_image and first_image.image:
            image_url = first_image.image.url
            
            # Ensure full URL is generated
            if request is not None:
                return request.build_absolute_uri(image_url)  # Generate absolute URL
        
        return None


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'stripe_payment_intent_id', 'stripe_client_secret', 'amount', 'currency', 'status', 'email', 'created_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreatePaymentIntentSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=100)  # Minimum 1 USD in cents
    email = serializers.EmailField()
    order_id = serializers.UUIDField(required=False, allow_null=True)
    delivery_id = serializers.UUIDField(required=False, allow_null=True)


class ConfirmPaymentSerializer(serializers.Serializer):
    payment_intent_id = serializers.CharField(max_length=255)
    payment_intent_client_secret = serializers.CharField(max_length=255)