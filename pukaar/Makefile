PY = .venv/bin/python

install:
	uv venv .venv && uv pip install -p $(PY) -e ".[dev]"

test:
	$(PY) -m pytest -q

run:
	$(PY) -m pukaar

demo:
	PUKAAR_SEED_DEMO=1 $(PY) -m pukaar

.PHONY: install test run demo

docker:
	docker build -t pukaar .

docker-demo: docker
	docker run --rm -p 8877:8877 -e PUKAAR_SEED_DEMO=1 pukaar

.PHONY: docker docker-demo
