import stripe
import json
import logging
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .models import Payment, Order, Delivery
from .serializers import (
    PaymentSerializer,
    CreatePaymentIntentSerializer,
    ConfirmPaymentSerializer,
)

stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)


class CreatePaymentIntentView(APIView):
    """Initiate a payment"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CreatePaymentIntentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = serializer.validated_data['amount']
            email = serializer.validated_data['email']
            order_id = serializer.validated_data.get('order_id')
            delivery_id = serializer.validated_data.get('delivery_id')

            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency='usd',
                metadata={
                    'order_id': str(order_id) if order_id else None,
                    'delivery_id': str(delivery_id) if delivery_id else None,
                    'email': email,
                },
                receipt_email=email,
            )

            # Create payment record
            payment = Payment.objects.create(
                stripe_payment_intent_id=intent.id,
                stripe_client_secret=intent.client_secret,
                amount=amount,
                currency='usd',
                email=email,
                status='pending',
                user=request.user if request.user.is_authenticated else None,
            )

            # Link to order/delivery if provided
            if order_id:
                try:
                    payment.order = Order.objects.get(id=order_id)
                except Order.DoesNotExist:
                    pass

            if delivery_id:
                try:
                    payment.delivery = Delivery.objects.get(id=delivery_id)
                except Delivery.DoesNotExist:
                    pass

            payment.save()

            return Response(
                {
                    'clientSecret': intent.client_secret,
                    'paymentIntentId': intent.id,
                    'amount': amount,
                    'currency': 'usd',
                },
                status=status.HTTP_201_CREATED,
            )

        except stripe.error.CardError as e:
            logger.error(f"Card error: {e.user_message}")
            return Response(
                {'error': e.user_message},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except stripe.error.RateLimitError:
            logger.error("Rate limit exceeded")
            return Response(
                {'error': 'Too many requests. Please try again later.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except stripe.error.InvalidRequestError as e:
            logger.error(f"Invalid request: {e.user_message}")
            return Response(
                {'error': e.user_message},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except stripe.error.AuthenticationError:
            logger.error("Payment processor authentication failed")
            return Response(
                {'error': 'Payment processor authentication failed.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except stripe.error.APIConnectionError:
            logger.error("Network error")
            return Response(
                {'error': 'Network error. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ConfirmPaymentView(APIView):
    """Confirm payment and update order status"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ConfirmPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Validation error: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment_intent_id = serializer.validated_data['payment_intent_id']
            
            # Retrieve payment intent
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            # Get payment record
            try:
                payment = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
            except Payment.DoesNotExist:
                return Response(
                    {'error': 'Payment not found.'},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Update payment status based on intent status
            if intent.status == 'succeeded':
                payment.status = 'succeeded'
                # Get charge ID if available
                if hasattr(intent, 'charges') and intent.charges.data:
                    payment.stripe_charge_id = intent.charges.data[0].id
                elif hasattr(intent, 'charge') and intent.charge:
                    payment.stripe_charge_id = intent.charge
                
                # Update linked order status
                if payment.order:
                    payment.order.status = 'Cleared'
                    payment.order.save()
                
                # Update delivery payment status
                if payment.delivery:
                    payment.delivery.payment_status = 'Completed'
                    payment.delivery.save()

            elif intent.status == 'processing':
                payment.status = 'pending'
            elif intent.status == 'requires_payment_method':
                payment.status = 'failed'
            elif intent.status == 'canceled':
                payment.status = 'cancelled'

            payment.save()

            payment_serializer = PaymentSerializer(payment)
            return Response(payment_serializer.data, status=status.HTTP_200_OK)

        except stripe.error.InvalidRequestError as e:
            logger.error(f"Invalid request: {e.user_message}")
            return Response(
                {'error': e.user_message},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Payment confirmation error: {str(e)}")
            return Response(
                {'error': f'Failed to confirm payment: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PaymentStatusView(APIView):
    """Get payment status"""
    permission_classes = [AllowAny]

    def get(self, request, payment_intent_id):
        try:
            payment = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
            serializer = PaymentSerializer(payment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Payment.DoesNotExist:
            return Response(
                {'error': 'Payment not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )


@csrf_exempt
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if not webhook_secret:
        logger.warning("STRIPE_WEBHOOK_SECRET not configured")
        return JsonResponse({'warning': 'Webhook secret not configured'}, status=200)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    # Handle specific events
    try:
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            _handle_payment_succeeded(payment_intent)

        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            _handle_payment_failed(payment_intent)

        elif event['type'] == 'charge.dispute.created':
            charge = event['data']['object']
            _handle_charge_dispute(charge)

        return JsonResponse({'status': 'success'}, status=200)

    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def _handle_payment_succeeded(payment_intent):
    """Handle successful payment"""
    payment_intent_id = payment_intent['id']
    
    try:
        payment = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
        payment.status = 'succeeded'
        payment.stripe_charge_id = payment_intent['charges']['data'][0]['id'] if payment_intent['charges']['data'] else None
        payment.save()

        # Update linked order and delivery
        if payment.order:
            payment.order.status = 'Cleared'
            payment.order.save()

        if payment.delivery:
            payment.delivery.payment_status = 'Completed'
            payment.delivery.save()

        logger.info(f"Payment {payment_intent_id} marked as succeeded")
    except Payment.DoesNotExist:
        logger.warning(f"Payment record not found for intent {payment_intent_id}")
    except Exception as e:
        logger.error(f"Error handling payment success: {str(e)}")


def _handle_payment_failed(payment_intent):
    """Handle failed payment"""
    payment_intent_id = payment_intent['id']
    
    try:
        payment = Payment.objects.get(stripe_payment_intent_id=payment_intent_id)
        payment.status = 'failed'
        payment.save()

        # Update linked order status
        if payment.order:
            payment.order.status = 'Cancelled'
            payment.order.save()

        logger.info(f"Payment {payment_intent_id} marked as failed")
    except Payment.DoesNotExist:
        logger.warning(f"Payment record not found for intent {payment_intent_id}")
    except Exception as e:
        logger.error(f"Error handling payment failure: {str(e)}")


def _handle_charge_dispute(charge):
    """Handle charge disputes/chargebacks"""
    charge_id = charge['id']
    
    try:
        payment = Payment.objects.get(stripe_charge_id=charge_id)
        # You can mark the payment/order as disputed
        logger.warning(f"Charge {charge_id} has a dispute/chargeback")
    except Payment.DoesNotExist:
        logger.warning(f"Payment record not found for charge {charge_id}")
    except Exception as e:
        logger.error(f"Error handling charge dispute: {str(e)}")
