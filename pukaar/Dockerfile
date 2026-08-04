FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY pukaar ./pukaar
RUN pip install --no-cache-dir .
ENV PUKAAR_HOST=0.0.0.0 PUKAAR_PORT=8877
EXPOSE 8877
# A hosted deploy MUST set, at minimum:
#   PUKAAR_HMAC_KEY     — persistent provenance signing (boot refuses without it)
#   PUKAAR_ADMIN_TOKEN  — staff gate: without it every surface/API is public
#   PUKAAR_DB=/data/pukaar.db  — on a mounted volume, or all state dies with the container
# And serve behind HTTPS (a reverse proxy / platform TLS): the responder
# app's install + push notifications require a secure origin.
# Optional: PUKAAR_SEED_DEMO=1 (photogenic demo session), WA_* (real
# WhatsApp), PUKAAR_TELEGRAM_TOKEN (Telegram line), ANTHROPIC_API_KEY
# (live Claude backend — the deploying org's choice and key, never ours).
CMD ["python", "-m", "pukaar"]
