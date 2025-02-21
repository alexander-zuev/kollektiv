# Use a base image
##############################
# Base stage
##############################
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    UV_VERSION=0.6.0

WORKDIR /app

##############################
# Builder stage: install deps
##############################
FROM base AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download the latest installer
ADD https://astral.sh/uv/${UV_VERSION}/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Copy the project into the image
ADD . /app

# Sync the project into a new environment
WORKDIR /app
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"

# Define the default command (runs at container start)
CMD kollektiv ${SERVICE}

