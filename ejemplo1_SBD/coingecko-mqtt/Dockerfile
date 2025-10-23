FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Instalar dependencias del sistema (red/SSL) y Python
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Salud básica: el contenedor corre indefinidamente publicando
HEALTHCHECK --interval=1m --timeout=5s --start-period=20s CMD python -c "import socket; import os; s=socket.socket(); s.settimeout(3); s.connect((os.environ.get('BROKER_HOST','mosquitto'), int(os.environ.get('BROKER_PORT','1883')))); print('ok')"

CMD ["python", "app.py"]