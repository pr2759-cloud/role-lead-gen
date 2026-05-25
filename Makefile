.PHONY: dev db-up db-down migrate test lint fmt run

dev: db-up
	uv sync

db-up:
	docker compose up -d postgres adminer

db-down:
	docker compose down

migrate:
	(cd apps/api && uv run alembic upgrade head)

migrate-new:
	(cd apps/api && uv run alembic revision --autogenerate -m "$(name)")

test:
	uv run pytest apps/api/tests -v

lint:
	uv run ruff check apps/api

fmt:
	uv run ruff format apps/api

run:
	uv run leadgen run --csv data/seeds/target_companies.csv --profile profiles/pranay_fde_gtm.yaml
