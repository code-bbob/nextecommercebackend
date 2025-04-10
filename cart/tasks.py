from celery import shared_task
from django.core.mail import EmailMultiAlternatives
@shared_task(bind=True, retry_backoff=True)  # Add retry
def send_order_email(self, subject, text_content, html_content, from_email, to_email_list):
    """
    Task for sending email notifications asynchronously using Celery.
    """
    try:
        msg = EmailMultiAlternatives(subject, text_content, from_email, to_email_list)
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        return f"Email sent to {', '.join(to_email_list)}"
    except Exception as e:
        # Retry the task (you might want to customize the retry behavior)
        raise self.retry(exc=e, countdown=5)  # Retry in 5 seconds
        
@shared_task
def test_task():
    print("HI")
    return 'Hello from Celery'