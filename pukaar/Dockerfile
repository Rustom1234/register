FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY pukaar ./pukaar
RUN pip install --no-cache-dir .
ENV PUKAAR_HOST=0.0.0.0 PUKAAR_PORT=8877
EXPOSE 8877
# PUKAAR_SEED_DEMO=1 boots with a photogenic session; set WA_* env for the
# real WhatsApp transport, ANTHROPIC_API_KEY for the live Claude backend.
CMD ["python", "-m", "pukaar"]
