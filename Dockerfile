# Root Dockerfile for Railway — build context is repo root
# App source lives in 06-lab-complete/

FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY 06-lab-complete/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim AS runtime

RUN groupadd -r agent && useradd -r -g agent -d /app agent

WORKDIR /app

COPY --from=builder /root/.local /app/.local
COPY 06-lab-complete/app/ ./app/
COPY 06-lab-complete/utils/ ./utils/
COPY 06-lab-complete/start.sh ./start.sh

RUN chmod +x /app/start.sh && chown -R agent:agent /app

USER agent

ENV PATH=/app/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

CMD ["/app/start.sh"]
