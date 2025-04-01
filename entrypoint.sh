#!/bin/bash

# Collect static files
python manage.py collectstatic --noinput

# Apply database migrations
python manage.py makemigrations cart shop userauth blog
python manage.py migrate

# Start Gunicorn
gunicorn ecommerce.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
