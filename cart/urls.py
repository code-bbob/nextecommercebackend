from django.urls import path
from .views import OrderAPIView
from . import views

urlpatterns = [ 
    # URL for listing and creating orders (GET and POST)
    path('api/', OrderAPIView.as_view(), name='order-list'),
    path('api/delivery/', views.DeliveryView.as_view(), name="delivery"),
    path('api/cart/', views.CartView.as_view(), name="cart"),
    path('api/cart/update/', views.CartView.as_view(), name="cart-update"),
    path('api/cart/merge/', views.MergeCartView.as_view(), name="cart-merge"),
    path('api/order/', views.OrderAPIView.as_view(), name="order"),
    path('api/coupon/', views.CouponView.as_view(), name="coupon"),

    # # URL for retrieving, updating, and deleting a specific order (GET, PUT, PATCH, DELETE)
    # path('api/<str:pk>/', OrderAPIView.as_view(), name='order-detail'),
]
