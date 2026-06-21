#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# Compilar Tailwind CSS (requiere Node.js en el entorno de build)
if command -v npm &> /dev/null; then
  npm ci
  npm run build:css
fi

python manage.py collectstatic --no-input
python manage.py migrate --no-input
