.PHONY: setup scan scan-images scan-deps up down logs test test-unit test-integration auth-strava auth-withings add-resting-hr

setup: ## Install pre-commit Trivy hook and copy .env.example
	@cp -n .env.example .env 2>/dev/null && echo "Created .env from .env.example" || echo ".env already exists"
	@cp scripts/trivy-scan.sh .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "Pre-commit hook installed."

scan: ## Scan repo filesystem for secrets and misconfigs + Python deps
	./scripts/trivy-scan.sh

scan-images: ## Scan built Docker images (run after docker compose build)
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		aquasec/trivy:latest image second-engine-worker --severity HIGH,CRITICAL
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		aquasec/trivy:latest image postgres:16 --severity HIGH,CRITICAL
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		aquasec/trivy:latest image grafana/grafana:10.4.2 --severity HIGH,CRITICAL

scan-deps: ## Scan Python requirements.txt for known vulnerabilities
	docker run --rm -v $(PWD)/worker:/scan \
		aquasec/trivy:latest fs /scan --severity HIGH,CRITICAL

up: ## Start default services (postgres + worker + grafana)
	docker compose up -d

down: ## Stop all services
	docker compose down

logs: ## Follow worker logs
	docker compose logs -f worker

test: ## Run full test suite
	docker compose run --rm worker pytest -v

test-unit: ## Run unit tests only (no DB needed)
	docker compose run --rm worker pytest tests/unit -v

test-integration: ## Run integration tests (requires postgres)
	docker compose run --rm worker pytest tests/integration -v

auth-strava: ## Run Strava OAuth setup
	python setup/auth.py strava

auth-withings: ## Run Withings OAuth setup
	python setup/auth.py withings

add-resting-hr: ## Record manual resting HR — usage: make add-resting-hr BPM=58
	docker compose run --rm worker python scripts/add_resting_hr.py --bpm $(BPM)

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
