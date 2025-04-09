#!/bin/bash

# Apply database migrations
python manage.py makemigrations cart shop userauth blog
python manage.py migrate

# Check what service we're running
if [ "$1" = "celery" ]; then
    # Run Celery worker
    celery -A ecommerce worker -l info
elif [ "$1" = "celery-beat" ]; then
    # Run Celery beat
    celery -A ecommerce beat -l info
else
    # Start Gunicorn by default
    gunicorn ecommerce.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
fi