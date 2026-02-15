FROM python:3.12.5-slim-bullseye AS builder

RUN apt-get update \
  && apt-get install -y --no-install-recommends --no-install-suggests \
  build-essential default-libmysqlclient-dev pkg-config \
  && pip install --no-cache-dir --upgrade pip

WORKDIR /app
COPY ./requirements.txt /app
RUN pip install --no-cache-dir --requirement /app/requirements.txt

# ─── Runtime Stage ──────────────────────────────────────────────
FROM python:3.12.5-slim-bullseye

RUN apt-get update \
  && apt-get install -y --no-install-recommends default-libmysqlclient-dev \
  && rm -rf /var/lib/apt/lists/* \
  && groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . /app

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

CMD ["python3", "server.py"]