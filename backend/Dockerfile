FROM python:3.13-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip && /opt/venv/bin/pip install -r requirements.txt

FROM python:3.13-slim AS runtime
ENV PATH=/opt/venv/bin:$PATH PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    STOCKFISH_PATH=/usr/games/stockfish PORT=8080
RUN apt-get update && apt-get install -y --no-install-recommends stockfish ca-certificates \
    && test -x /usr/games/stockfish && /usr/games/stockfish --help </dev/null >/dev/null \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app && useradd --system --gid app --home /app app
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=app:app app ./app
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini ./alembic.ini
COPY --chown=app:app scripts/start_cloud_run.sh ./scripts/start_cloud_run.sh
RUN chmod +x ./scripts/start_cloud_run.sh
USER app
EXPOSE 8080
CMD ["./scripts/start_cloud_run.sh"]
