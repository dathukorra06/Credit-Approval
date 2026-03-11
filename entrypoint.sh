#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 0.5
done
echo "PostgreSQL is ready."

echo "Running migrations..."
python manage.py migrate --noinput

echo "Triggering data ingestion via background tasks..."
python manage.py ingest_data

echo "Starting Django development server..."
exec python manage.py runserver 0.0.0.0:8000
