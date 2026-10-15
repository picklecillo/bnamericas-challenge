.PHONY: up down build logs race

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

# Race detector against the running stack (see loadtest/locustfile.py). Exits 1 on lost saves.
# Locust flags pass through, e.g. `make race args="-u 50 -t 60s"`.
race:
	cd loadtest && uv run locust $(args)
