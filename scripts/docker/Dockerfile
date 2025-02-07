# Use a base image
##############################
# Base stage
##############################
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

##############################
# Builder stage: install deps
##############################
FROM base AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy only dependency files first to leverage caching
COPY pyproject.toml poetry.lock ./

# Use a cache mount for Poetry’s cache
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

# ##############################
# # Final runtime stage
# ##############################
# FROM base AS runtime

# COPY --from=builder /usr/local/bin/poetry* /usr/local/bin/

# # Copy the installed dependencies and virtual environment from builder
# COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
