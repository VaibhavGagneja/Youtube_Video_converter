FROM python:3.12.5-slim-bullseye AS builder

RUN apt-get update \
  && apt-get install -y --no-install-recommends --no-install-suggests \
  build-essential \
  && pip install --no-cache-dir --upgrade pip

WORKDIR /app
COPY ./requirements.txt /app
RUN pip install --no-cache-dir --requirement /app/requirements.txt

# ─── Runtime Stage ──────────────────────────────────────────────
FROM python:3.12.5-slim-bullseye

RUN rm -rf /var/lib/apt/lists/* \
  && groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . /app

RUN chown -R appuser:appuser /app
USER appuser

CMD ["python3", "consumer.py"]
