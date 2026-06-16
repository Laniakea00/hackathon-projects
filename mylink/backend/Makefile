.PHONY: help install run docker-up docker-down migrate test clean

help:
	@echo "SmartBot Backend - Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make run          - Run development server"
	@echo "  make docker-up    - Start Docker containers"
	@echo "  make docker-down  - Stop Docker containers"
	@echo "  make migrate      - Run database migrations"
	@echo "  make migration    - Create new migration"
	@echo "  make test-data    - Create test data"
	@echo "  make clean        - Clean cache files"

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-up:
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 5
	docker-compose exec app alembic upgrade head
	@echo "✅ Services are running!"
	@echo "API: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f app

migrate:
	alembic upgrade head

migration:
	alembic revision --autogenerate -m "$(msg)"

test-data:
	python scripts/create_test_data.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete

format:
	black app/
	isort app/

lint:
	flake8 app/
	mypy app/

