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

# Local throwaway demo ONLY: the container binds 0.0.0.0, and the boot
# guard (correctly) refuses that without a provenance key. The demo opts
# out explicitly; a real deploy sets PUKAAR_HMAC_KEY + PUKAAR_ADMIN_TOKEN
# and never uses this target (see Dockerfile header).
docker-demo: docker
	docker run --rm -p 8877:8877 -e PUKAAR_SEED_DEMO=1 -e PUKAAR_ALLOW_INSECURE=1 pukaar

.PHONY: docker docker-demo
