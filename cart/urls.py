from django.urls import path
from .views import OrderAPIView, CheckoutAPIView
from .stripe_views import (
    CreatePaymentIntentView,
    ConfirmPaymentView,
    PaymentStatusView,
    stripe_webhook,
)
from . import views

urlpatterns = [ 
    # URL for listing and creating orders (GET and POST)
    path('api/', OrderAPIView.as_view(), name='order-list'),
    path('api/checkout/', CheckoutAPIView.as_view(), name='checkout'),
    path('api/delivery/', views.DeliveryView.as_view(), name="delivery"),
    path('api/cart/', views.CartView.as_view(), name="cart"),
    path('api/cart/update/', views.CartView.as_view(), name="cart-update"),
    path('api/cart/merge/', views.MergeCartView.as_view(), name="cart-merge"),
    path('api/order/', views.OrderAPIView.as_view(), name="order"),
    path('api/coupon/', views.CouponView.as_view(), name="coupon"),
    path('api/<str:order_id>/', views.OrderDetailAPIView.as_view(), name='order-detail'),

    # Stripe Payment endpoints
    path('api/payment/create-intent/', CreatePaymentIntentView.as_view(), name='create-payment-intent'),
    path('api/payment/confirm/', ConfirmPaymentView.as_view(), name='confirm-payment'),
    path('api/payment/<str:payment_intent_id>/status/', PaymentStatusView.as_view(), name='payment-status'),
    path('api/payment/webhook/', stripe_webhook, name='stripe-webhook'),
]
