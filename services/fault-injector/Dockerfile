# Build stage
FROM python:3.11-slim AS builder

WORKDIR /app

# Install poetry
RUN pip install --no-cache-dir poetry==1.7.1

# Copy dependency files
COPY libs/ /app/libs/
COPY services/fault-injector/pyproject.toml services/fault-injector/poetry.lock* /app/services/fault-injector/
WORKDIR /app/services/fault-injector

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi --no-root

# Copy source code
COPY services/fault-injector/src/ /app/services/fault-injector/src/

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r adaptivx && useradd -r -g adaptivx adaptivx

# Copy installed packages and source
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app/services/fault-injector/src /app/services/fault-injector/src
COPY --from=builder /app/libs /app/libs

# Set environment
ENV PYTHONPATH=/app/services/fault-injector/src:/app/libs
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER adaptivx

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

# Run the service
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "fault_injector.main:app", "--host", "0.0.0.0", "--port", "8000"]
