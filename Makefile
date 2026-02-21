.PHONY: up down rebuild build logs restart ps clean fresh

# Levanta todo (API + Postgres) y reconstruye si hace falta
up:
	docker compose up --build

# Baja contenedores
down:
	docker compose down

# Rebuild sin cache (cuando cambies requirements/Dockerfile)
build:
	docker compose build --no-cache

# Baja, rebuild sin cache, y sube
rebuild:
	docker compose down
	docker compose build --no-cache
	docker compose up

# Fuerza recreación (útil si algo se queda pillado)
fresh:
	docker compose up --build --force-recreate

# Logs en vivo
logs:
	docker compose logs -f

# Reinicia servicios
restart:
	docker compose restart

# Estado de servicios
ps:
	docker compose ps

# Reset total (borra volumen de Postgres también)
clean:
	docker compose down -v --remove-orphans
	docker system prune -f



## allembic
upgrade:
	docker compose exec api alembic upgrade head


alembic-init:
	docker compose exec api alembic init alembic
