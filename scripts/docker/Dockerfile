# Use a base image
FROM python:3.12-slim

# Define build arguments
# ARG CHROMA_PRIVATE_URL 

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    CHROMA_PRIVATE_URL=${CHROMA_PRIVATE_URL}

# Set the working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install Poetry and dependencies
RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev

# Copy application code
COPY . .

# Start worker
CMD ["/bin/sh", "-c", "exec poetry run python -m src.infra.rq.rq_worker"]