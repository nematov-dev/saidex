FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# psycopg2-binary o'rniga source build kerak bo'lib qolsa deb libpq-dev,
# ba'zi paketlar (lxml va h.k.) uchun esa build-essential qo'yiladi.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# MUHIM: bu standart CMD — docker-compose.yml (dev, runserver) va
# docker-compose.prod.yml (production, migrate+collectstatic+gunicorn
# zanjiri) o'zining "command:" bilan buni almashtiradi. Bu shunchaki
# konteyner compose'siz, to'g'ridan-to'g'ri ishga tushirilsa ham oqilona
# ishlashi uchun zaxira (production'ga mos, gunicorn bilan).
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
