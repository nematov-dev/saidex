#!/bin/bash
# Saidex AI Agent uchun Nginx reverse-proxy config generatsiya qiladi.
# Foydalanish: ./scripts/generate_nginx.sh <domen.uz> [PROJECT_ROOT]
# Masalan:     ./scripts/generate_nginx.sh saidex.uz /opt/saidex_ai_agent
set -e

DOMAIN=$1
PROJECT_ROOT=${2:-/opt/saidex_ai_agent}

if [ -z "$DOMAIN" ]; then
  echo "Foydalanish: ./scripts/generate_nginx.sh <domen.uz> [PROJECT_ROOT]"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT_DIR/deploy/nginx/saidex.conf"
mkdir -p "$ROOT_DIR/deploy/nginx"

cat > "$OUT" <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 20M;

    location /static/ {
        alias $PROJECT_ROOT/staticfiles/;
    }
    location /media/ {
        alias $PROJECT_ROOT/media/;
    }

    location / {
        # Docker (docker-compose.prod.yml) web konteyneri "127.0.0.1:8000"ga
        # bog'langan — shu yerga proxy qilinadi (unix socket emas, chunki
        # gunicorn konteyner ICHIDA ishlaydi, hostdagi socket fayliga
        # yozolmaydi).
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

echo "Tayyor: deploy/nginx/saidex.conf"
cat <<MSG

MUHIM: bu skript Docker orqali joylashtirishni ("docker compose -f
docker-compose.prod.yml up -d --build") nazarda tutadi — web konteyneri
127.0.0.1:8000ga bog'langan bo'lishi kerak (prod compose faylida shunday).

Serverga joylashtirish:
  sudo cp deploy/nginx/saidex.conf /etc/nginx/sites-available/saidex.conf
  sudo ln -s /etc/nginx/sites-available/saidex.conf /etc/nginx/sites-enabled/
  sudo nginx -t && sudo systemctl reload nginx

  # SSL (bepul, avtomatik yangilanadi):
  sudo certbot --nginx -d ${DOMAIN}
MSG
