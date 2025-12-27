from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Order, OrderItem, Cart, Coupon, Delivery
from .serializers import OrderSerializer, OrderItemSerializer, DeliverySerializer, CartSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
import random
from rest_framework import generics
from .utils import Util
from shop.models import Product
import datetime
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from .tasks import send_order_email  # Import the Celery task


class OrderAPIView(APIView):
    permission_classes=[AllowAny]

    def get(self, request, *args, **kwargs):
        if request.user and request.user.is_superuser:
            print("Here")
            orders = Order.objects.all()
            print(orders)
        else:
            orders = []
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        data = request.data.copy()
        user = request.user if request.user and request.user.is_authenticated else None
        if user:
            data["user"] = user.pk
        
        # Check if items are provided directly (for guest checkout or alternative flow)
        items = data.get('items', [])
        carts = data.get('carts', [])
        
        if not items and not carts:
            return Response({'detail': 'Either items or carts must be provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = OrderSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CheckoutAPIView(APIView):
    """Handle checkout with delivery info and order creation in a single request"""
    permission_classes = [AllowAny]

    def post(self, request):
        """Create order and delivery info from checkout form"""
        data = request.data
        
        # Get cart items from request
        cart_items_data = data.get('items', [])
        print(data)
        
        if not cart_items_data:
            return Response({'detail': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user if authenticated
        user = request.user if request.user and request.user.is_authenticated else None
        
        try:
            # Create order
            order = Order.objects.create(user=user, status='Placed')
            
            # Create order items from cart items
            for item in cart_items_data:
                try:
                    product = Product.objects.get(product_id=item.get('product_id'))
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item.get('quantity', 1)
                    )
                except Product.DoesNotExist:
                    order.delete()
                    return Response({'detail': f'Product {item.get("product_id")} not found'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Create delivery info
            delivery_data = {
                'order': order.id,
                'phone_number': data.get('phone_number'),
                'first_name': data.get('first_name'),
                'last_name': data.get('last_name'),
                'email': data.get('email', ''),
                'shipping_address': data.get('shipping_address'),
                'city': data.get('city'),
                'municipality': data.get('municipality'),
                'payment_method': data.get('payment_method', 'COD'),
                'shipping_method': data.get('shipping_method'),
                'shipping_cost': data.get('shipping_cost', 0),
                'subtotal': data.get('subtotal', 0),
                'discount': data.get('discount', 0),
                'payment_amount': data.get('payment_amount', 0),
                'payment_status': 'Pending'
            }
            
            delivery_serializer = DeliverySerializer(data=delivery_data)
            if not delivery_serializer.is_valid():
                order.delete()
                return Response(delivery_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            delivery = delivery_serializer.save(order=order)
            
            # Clear user's cart if authenticated
            if user:
                Cart.objects.filter(user=user).delete()
            
            # Return order info with delivery
            order_serializer = OrderSerializer(order)
            return Response(order_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # Ensure order is deleted if something goes wrong
            if 'order' in locals():
                order.delete()
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class DeliveryView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = request.user if request.user and request.user.is_authenticated else None
        data = request.data
        order = Order.objects.filter(id=data["order"]).first()
        
        if not order:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = DeliverySerializer(data=data)
        
        if serializer.is_valid(raise_exception=True):
            delivery_instance = serializer.save(order=order)
            order.status = "Placed"
            order.save()

            order_item_data = OrderItemSerializer(order.order_items.all(), many=True).data

            # Build HTML rows for each item
            item_rows = ""
            for item in order_item_data:
                product_name = item.get("product_name", "N/A")
                product_id = item.get("product_id", "N/A")
                quantity = item.get("quantity", 0)
                item_rows += f"""
                <tr>
                    <td>{product_name}</td>
                    <td>{product_id}</td>
                    <td>{quantity}</td>
                </tr>
                """
            
            # Extract relevant fields from serializer.data
            first_name = serializer.data.get('first_name', 'N/A')
            last_name = serializer.data.get('last_name', 'N/A')
            phone_number = serializer.data.get('phone_number', 'N/A')
            shipping_address = serializer.data.get('shipping_address', 'N/A')
            city = serializer.data.get('city', 'N/A')
            payment_amount = serializer.data.get('payment_amount', 0)
            shipping_cost = serializer.data.get('shipping_cost', 0)
            subtotal = serializer.data.get('subtotal', 0)
            discount = serializer.data.get('discount', 0)
            
            # Build a more readable HTML output
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <title>New Order Notification</title>
              <style>
                body {{
                  font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                  background-color: #f7f7f7;
                  padding: 20px;
                  color: #333;
                }}
                .container {{
                  max-width: 600px;
                  margin: 0 auto;
                  background-color: #ffffff;
                  border-radius: 8px;
                  overflow: hidden;
                  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .header {{
                  background-color: #4CAF50;
                  color: #ffffff;
                  padding: 20px;
                  text-align: center;
                }}
                .content {{
                  padding: 20px;
                  line-height: 1.6;
                }}
                .footer {{
                  background-color: #f0f0f0;
                  color: #777;
                  text-align: center;
                  padding: 10px;
                  font-size: 12px;
                }}
                table {{
                  width: 100%;
                  border-collapse: collapse;
                  margin-top: 10px;
                }}
                table td {{
                  padding: 8px;
                  border: 1px solid #ddd;
                }}
                table th {{
                  background-color: #f9f9f9;
                  text-align: left;
                  padding: 8px;
                  border: 1px solid #ddd;
                }}
              </style>
            </head>
            <body>
              <div class="container">
                <div class="header">
                  <h1>New Order Placed</h1>
                </div>
                <div class="content">
                  <p>Hello,</p>
                  <p>A new order has been placed: <strong>{order}</strong>.</p>
                  <table>
                  {item_rows}
                  </table>
                  <p>Please deliver the order to the following address:</p>
                   <table>
                    <tr>
                      <th>Name</th>
                      <td>{first_name} {last_name}</td>
                    </tr>
                    <tr>
                      <th>Phone Number</th>
                      <td>{phone_number}</td>
                    </tr>
                    <tr>
                      <th>Address</th>
                      <td>{shipping_address},{city}</td>
                    </tr>
                    <tr>
                      <th>Subtotal</th>
                      <td>{subtotal}</td>
                    </tr>
                    <tr>
                      <th>Discount</th>
                      <td>{discount}</td>
                    </tr>
                    <tr>
                      <th>Shipping Cost</th>
                      <td>{shipping_cost}</td>
                    </tr>
                    <tr>
                      <th>Total Amount</th>
                      <td>{payment_amount}</td>
                    </tr>
                  </table>
                  <p>After delivery, please update the order status accordingly.</p>
                  <p>Thank you!</p>
                </div>
                <div class="footer">
                  &copy; {datetime.datetime.now().year} Your Company Name. All rights reserved.
                </div>
              </div>
            </body>
            </html>
            """

            # Generate a plain text version by stripping HTML tags
            text_content = strip_tags(html_content)
            
            subject = "New Order Placed"
            from_email = "your_email@example.com"
            to_email = "bbobbasnet@gmail.com"
            # Send the email asynchronously using Celery
            # send_order_email.delay(subject, text_content, html_content, from_email, [to_email])

            return Response('OKAY ',status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)


class CartView(APIView):
    """Manage the shopping cart"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve all cart items for the authenticated user"""
        cart_items = Cart.objects.filter(user=request.user)
        serializer = CartSerializer(cart_items, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        """Add a product to the cart"""
        data = request.data  # Extract request data
        product_id = data.get('product_id')  # Get product ID from request

        # Ensure product ID is provided
        if not product_id:
            return Response({"error": "Product ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Try to fetch the Product instance
        try:
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get quantity (default is 1)
        quantity = int(data.get('quantity', 1))
        price = int(data.get('price', 0))

        # Check if the product is already in the cart
        cart_item, created = Cart.objects.get_or_create(
            user=request.user, product=product,
            defaults={'quantity': quantity,'price':price}
        )

        # If item exists, update quantity
        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        return Response({
            "message": "Added to cart",
            "item": CartSerializer(cart_item).data
        }, status=status.HTTP_201_CREATED)

    def patch(self, request):
        """Update a cart item's quantity"""
        data = request.data
        product_id = data.get('product_id')
        if not product_id:
            return Response({"error": "Product ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the product instance
        try:
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get the corresponding cart item
        try:
            cart_item = Cart.objects.get(user=request.user, product=product)
        except Cart.DoesNotExist:
            return Response({"error": "Item not found in cart"}, status=status.HTTP_404_NOT_FOUND)

        # Get and validate the new quantity
        quantity = data.get('quantity')
        if quantity is None:
            return Response({"error": "Quantity is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
            if quantity < 1:
                return Response({"error": "Quantity must be at least 1"}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({"error": "Invalid quantity"}, status=status.HTTP_400_BAD_REQUEST)

        cart_item.quantity = quantity
        cart_item.save()

        return Response({
            "message": "Cart item updated",
            "item": CartSerializer(cart_item).data
        }, status=status.HTTP_200_OK)

    def delete(self, request):
        """Remove a product from the cart"""
        data = request.data  # Extract request data
        product_id = data.get('product_id')  # Use product_id consistently

        # Ensure product ID is provided
        if not product_id:
            return Response({"error": "Product ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the product instance
        try:
            product = Product.objects.get(product_id=product_id)
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            cart_item = Cart.objects.get(user=request.user, product=product)
            cart_item.delete()
            return Response({"message": "Item removed from cart"}, status=status.HTTP_200_OK)
        except Cart.DoesNotExist:
            return Response({"error": "Item not found in cart"}, status=status.HTTP_404_NOT_FOUND)

class MergeCartView(APIView):
    """
    Merge the unauthenticated cart (sent from the client) with the user's cart.
    Expected payload:
    {
      "items": [
        {"product_id": "550e8400-e29b-41d4-a716-446655440000", "quantity": 2},
        {"product_id": "660e8400-e29b-41d4-a716-446655440000", "quantity": 1},
        ...
      ]
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        items = request.data.get("items", [])
        if not items:
            return Response({"message": "No items provided for merging."},
                            status=status.HTTP_400_BAD_REQUEST)

        merged_cart_items = []

        for item_data in items:
            product_id = item_data.get("product_id")
            quantity = item_data.get("quantity", 1)
            price = item_data.get("price", 0)
            
            if not product_id:
                continue  # Skip items without a product_id

            try:
                # Assuming your Product model uses product_id as its UUID primary key
                product = Product.objects.get(product_id=product_id)
            except Product.DoesNotExist:
                continue  # Skip invalid products

            # Try to get an existing cart item for this product and user
            cart_item, created = Cart.objects.get_or_create(
                user=request.user,
                product=product,
                defaults={"quantity": quantity,"price":price}
            )
            if not created:
                # If the item exists, update its quantity by adding the new quantity
                cart_item.quantity += quantity
                cart_item.save()

            merged_cart_items.append(cart_item)

        # Serialize and return the merged cart items
        serializer = CartSerializer(merged_cart_items, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CouponView(APIView):
    permission_classes = [AllowAny]

    def get(self,request):
        code = request.GET.get('code')
        if code:
            coupon = Coupon.objects.filter(code=code).first()
            if coupon:
                if coupon.apply_coupon(request.user):
                  return Response({'status':'Success','amount':coupon.amount,'percentage':coupon.percentage})
                else:
                    return Response({'status':'Failed','message':'Coupon has already been used.'})
            else:
                return Response({'status':'Failed','message':'Coupon is not valid.'},status=status.HTTP_400_BAD_REQUEST)



class OrderDetailAPIView(APIView):
    """Get a specific order by ID"""
    permission_classes = [AllowAny]

    def get(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    
    def patch(self, request, order_id):
        """Update order status"""
        try:
            order = Order.objects.get(id=order_id)
            data = request.data
            
            # Update status if provided
            if 'status' in data:
                order.status = data['status']
            
            order.save()
            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Order.DoesNotExist:
            return Response({'detail': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

