# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir poetry==1.7.1

COPY libs/ /app/libs/
COPY services/job-dispatcher/pyproject.toml services/job-dispatcher/poetry.lock* /app/services/job-dispatcher/

WORKDIR /app/services/job-dispatcher

RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi --no-root

COPY services/job-dispatcher/src/ /app/services/job-dispatcher/src/

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

RUN groupadd -r adaptivx && useradd -r -g adaptivx adaptivx

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app/services/job-dispatcher/src /app/services/job-dispatcher/src
COPY --from=builder /app/libs /app/libs

ENV PYTHONPATH=/app/services/job-dispatcher/src:/app/libs
ENV PYTHONUNBUFFERED=1

USER adaptivx

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "job_dispatcher.main:app", "--host", "0.0.0.0", "--port", "8000"]
