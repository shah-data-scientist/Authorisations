.PHONY: install data train evaluate api dashboard test lint clean \
        docker-dev docker-prod docker-down docker-clean

install:
	pip install -e ".[dev]"

data:
	python -m src.role_recommender.data.download
	python -m src.role_recommender.data.preprocess

train:
	python -m src.role_recommender.mining.probabilistic

evaluate:
	python -m role_recommender.evaluation

api:
	uvicorn src.role_recommender.api.main:app --reload --port 8000

dashboard:
	streamlit run src/role_recommender/dashboard/app.py --server.port 8501

test:
	pytest tests/ -v

lint:
	black src/ tests/
	flake8 src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov/

# ── Docker ────────────────────────────────────────────────────────────────────

docker-dev:
	docker compose up --build

docker-restart:
	docker compose up --build -d

docker-down:
	docker compose down

docker-clean:
	docker compose down -v --rmi local
