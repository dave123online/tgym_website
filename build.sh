#!/usr/bin/env bash
# Quitter le script immédiatement si une commande échoue
set -o errexit

# 1. Installer les dépendances Python
pip install -r requirements.txt

# 2. Collecter les fichiers statiques (Tailwind, Admin, etc.)
python manage.py collectstatic --no-input --ignore=src

# 3. Appliquer les migrations sur la base de données de prod
python manage.py migrate --fake-initial

# Création automatique du superuser en prod
if [ "$DJANGO_SUPERUSER_USERNAME" ]; then
  python manage.py createsuperuser --noinput || true
fi
