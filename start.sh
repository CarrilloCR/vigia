#!/bin/bash
cd ~/vigia
source env/bin/activate.fish

echo "Iniciando Vigía..."

# Iniciar celery worker en background
celery -A vigia_backend worker --loglevel=warning --detach --logfile=/tmp/celery_worker.log --pidfile=/tmp/celery_worker.pid

# Iniciar celery beat en background  
celery -A vigia_backend beat --loglevel=warning --detach --logfile=/tmp/celery_beat.log --pidfile=/tmp/celery_beat.pid

echo "Celery Worker y Beat iniciados"

# Iniciar Django en foreground
python manage.py runserver