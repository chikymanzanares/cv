.PHONY: up down logs build rebuild api front migrate \
        gen-build gen-data gen-data-1 gen-pdf gen-all gen-clean gen-shell

# -------------------------
# DEV / RUNTIME
# -------------------------

build:
	docker compose build

rebuild:
	docker compose build --no-cache

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

api:
	docker compose up -d api

front:
	docker compose up -d front

migrate:
	docker compose run --rm migrate


# -------------------------
# CV DATASET GENERATION
# -------------------------

gen-build:
	docker compose build generator

# Generate N CVs (default 30). Override: make gen-data N=10
gen-data:
	docker compose run --rm -e N_CVS=$(or $(N),30) generator sh -lc "python -m cv_generation.generate_data"

# Convenience: generate just 1
gen-data-1:
	docker compose run --rm -e N_CVS=1 generator sh -lc "python -m cv_generation.generate_data"

gen-pdf:
	docker compose run --rm generator sh -lc "python -m cv_generation.render_pdfs"

gen-all: gen-data gen-pdf

gen-clean:
	rm -rf cv_generation/data/cvs

# Optional: open a shell inside generator container for debugging
gen-shell:
	docker compose run --rm generator sh
