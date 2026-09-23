.PHONY: up down logs health seed test

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api-gateway query-service

health:
	curl -s http://localhost:8000/health | python -m json.tool
	curl -s http://localhost:8000/ready | python -m json.tool

seed:
	curl -s -X POST http://localhost:8000/api/v1/auth/login \
		-H "Content-Type: application/json" \
		-d '{"email":"admin@enterprise-rag.eu","password":"Admin@12345"}' | python -m json.tool

test:
	python -m compileall shared/python services -q
	@echo "Syntax check passed"
