#!/usr/bin/env bash
# Instalação em Ubuntu 22.04+ (VPS externo, até ~10 utilizadores)
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/sync2meet}"
DATA_DIR="${DATA_DIR:-/var/lib/sync2meet}"
DOMAIN="${DOMAIN:-sync2meet.local}"

echo "==> Sync2meet — instalação em ${APP_DIR}"

sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip ffmpeg nginx certbot python3-certbot-nginx git

sudo mkdir -p "${DATA_DIR}/storage"
sudo chown -R "$USER:$USER" "${DATA_DIR}"

if [ ! -d "${APP_DIR}" ]; then
  echo "Copia o projeto para ${APP_DIR} antes de correr este script."
  exit 1
fi

cd "${APP_DIR}/backend"
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

if [ ! -f "${APP_DIR}/backend/.env" ]; then
  cp "${APP_DIR}/deploy/env.production.example" "${APP_DIR}/backend/.env"
  echo "Edita ${APP_DIR}/backend/.env antes de continuar."
  exit 1
fi

cd "${APP_DIR}/frontend"
npm ci
npm run build

echo "==> A instalar serviços systemd..."
sudo cp "${APP_DIR}/deploy/sync2meet-api.service" /etc/systemd/system/
sudo cp "${APP_DIR}/deploy/sync2meet-web.service" /etc/systemd/system/
sudo sed -i "s|/opt/sync2meet|${APP_DIR}|g" /etc/systemd/system/sync2meet-*.service
sudo sed -i "s|/var/lib/sync2meet|${DATA_DIR}|g" /etc/systemd/system/sync2meet-*.service

sudo systemctl daemon-reload
sudo systemctl enable sync2meet-api sync2meet-web
sudo systemctl restart sync2meet-api sync2meet-web

echo "==> Nginx..."
sudo cp "${APP_DIR}/deploy/nginx-systemd.conf" /etc/nginx/sites-available/sync2meet
sudo sed -i "s|SERVER_NAME|${DOMAIN}|g" /etc/nginx/sites-available/sync2meet
sudo ln -sf /etc/nginx/sites-available/sync2meet /etc/nginx/sites-enabled/sync2meet
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "Pronto. Configura DNS para ${DOMAIN} e corre:"
echo "  sudo certbot --nginx -d ${DOMAIN}"
echo ""
echo "Estado: sudo systemctl status sync2meet-api sync2meet-web"
