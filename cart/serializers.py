from rest_framework import serializers
from .models import Order, OrderItem, Delivery, Cart
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
    # delivery = DeliverySerializer(read_only=True)

    class Meta:
        model = Order
        fields = '__all__'#yo field ma xai uta ko related name use hunxa

    def create(self, validated_data):
        carts = validated_data.pop('carts', None)
        order = Order.objects.create(**validated_data)
        if carts: 
            for cart in carts:
                product = cart.product
                quantity = cart.quantity
                cart.delete()
                OrderItem.objects.create(product=product, quantity=quantity, order=order)

        return order
    
    def get_user_name(self, obj):
        return obj.user.name











class CartSerializer(serializers.ModelSerializer):
    product_id = serializers.CharField(source='product.product_id', read_only=True)
    image = serializers.SerializerMethodField()
    name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Cart
        fields = ['id','product_id', 'image', 'quantity','name','price']

    def get_image(self, obj):
        request = self.context.get('request')  # Get request from context
        first_image = obj.product.images.first()  # Get first product image
        
        if first_image and first_image.image:
            image_url = first_image.image.url
            
            # Ensure full URL is generated
            if request is not None:
                return request.build_absolute_uri(image_url)  # Generate absolute URL
        
        return None