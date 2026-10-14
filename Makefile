.PHONY: build test up down native verify
build:
	python3 scripts/build.py
test: build
	python3 -m unittest discover -s tests -v
up:
	docker compose up --build -d
down:
	docker compose down
native:
	python3 scripts/native.py up --seed
verify:
	python3 scripts/verify.py --faults
