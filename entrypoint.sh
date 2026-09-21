#!/bin/sh

echo "Esperando a la base de datos PostgreSQL (dev)..."
while ! nc -z $POSTGRES_HOST $POSTGRES_PORT; do
  sleep 0.1
done
echo "PostgreSQL listo."

python manage.py migrate --noinput
python manage.py runserver 0.0.0.0:8000