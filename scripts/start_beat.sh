#!/bin/bash
# Script para iniciar Celery Beat scheduler
# Este scheduler ejecuta tareas programadas automáticamente

set -e  # Exit on error

echo "🕐 Iniciando Celery Beat scheduler..."

# Verificar que Redis está disponible
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Error: Redis no está disponible"
    echo "   Inicia Redis con: docker-compose up -d redis"
    exit 1
fi

echo "✅ Redis disponible"

# Crear directorios si no existen
mkdir -p logs
mkdir -p tmp

# Limpiar PID file anterior si existe
if [ -f tmp/celerybeat.pid ]; then
    echo "🧹 Limpiando PID file anterior..."
    rm tmp/celerybeat.pid
fi

# Iniciar Celery Beat
echo "🚀 Iniciando scheduler..."
poetry run celery -A src.core.celery_app beat \
    --loglevel=info \
    --logfile=logs/celery_beat.log \
    --pidfile=tmp/celerybeat.pid

echo "✅ Celery Beat iniciado"
