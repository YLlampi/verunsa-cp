#!/bin/bash

echo "Bajando cambios de GitHub..."
git pull origin master

echo "Reconstruyendo contenedores..."
sudo docker compose -f docker-compose.prod.yml up -d --build

echo "Aplicando migraciones..."
sudo docker compose -f docker-compose.prod.yml exec web python manage.py migrate

echo "Subiendo estáticos a S3..."
sudo docker compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput

echo "*******************************"
echo "Despliegue completado con éxito"
echo "*******************************"
