.PHONY: up down build logs

# Tail one service with `make logs s=backend` (frontend, backend, upstream); all by default.
s ?=

up:
	docker compose up -d

down:
	docker compose down

# Rebuild images first, e.g. after changing dependencies.
build:
	docker compose up --build -d

logs:
	docker compose logs -f $(s)
