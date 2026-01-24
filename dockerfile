# ============================================================================
# Dockerfile para Docker Resource Monitor
# Imagen base: Python 3.11
# ============================================================================

FROM python:3.11-slim

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2 y otras librerías
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero (para aprovechar cache de Docker)
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copiar el proyecto completo
COPY . .

# Crear directorios necesarios
RUN mkdir -p logs staticfiles media

# Recolectar archivos estáticos
RUN python manage.py collectstatic --noinput || true

# Exponer puerto 8000
EXPOSE 8000

# Script de entrada por defecto
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]