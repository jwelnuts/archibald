#!/bin/bash
# Script per creare e applicare le migrazioni mancanti sulla VPS

cd ~/archibald

echo "=== Creazione migrazioni mancanti ==="
docker compose exec web python manage.py makemigrations finance_hub link_storage memory_stock

echo ""
echo "=== Applicazione migrazioni ==="
docker compose exec web python manage.py migrate

echo ""
echo "=== Verifica ==="
docker compose exec web python manage.py showmigrations finance_hub link_storage memory_stock

echo ""
echo "=== Riavvio container (opzionale) ==="
docker compose restart web mail_worker

echo ""
echo "Fatto!"
