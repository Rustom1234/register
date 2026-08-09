# Wayside — one container runs everything (control room, rider app,
# witness chat, webhook receiver, sim engine).
#
#   docker build -t wayside .
#   docker run -p 8877:8877 -e PUKAAR_ALLOW_INSECURE=1 wayside
#
# In production, set the env vars listed in DEPLOY.md instead of
# PUKAAR_ALLOW_INSECURE. Secrets (ANTHROPIC_API_KEY, WA_TOKEN, ...) are
# provided by the host's env settings — never baked into this image.

FROM python:3.11-slim

WORKDIR /app
COPY pukaar/ ./pukaar/
RUN pip install --no-cache-dir ./pukaar

ENV PUKAAR_HOST=0.0.0.0
EXPOSE 8877

# Render/Railway inject PORT; fall back to 8877 locally.
CMD ["sh", "-c", "PUKAAR_PORT=${PORT:-8877} python -m pukaar"]
