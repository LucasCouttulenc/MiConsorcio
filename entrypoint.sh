#!/bin/sh

# Espera a que PostgreSQL esté listo antes de correr migraciones
echo "Esperando a la base de datos PostgreSQL..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 0.1
done
echo "PostgreSQL listo."

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2