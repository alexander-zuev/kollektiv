# Use a base image
FROM python:3.12-slim


# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Set the working directory in Container
WORKDIR /app

# Copy only the necessary files for installing dependencies
COPY pyproject.toml poetry.lock ./

# Install Poetry and dependencies
RUN pip install poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-dev

# Copy the rest of your application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV REDIS_URL=redis://host.docker.internal:6379/0
ENV REDIS_QUEUE_NAME=processing

# Use exec form with shell to handle env vars and signals properly
# CMD ["/bin/sh", "-c", "exec poetry run rq worker --url ${REDIS_URL} ${REDIS_QUEUE_NAME}"]
CMD ["/bin/sh", "-c", "exec poetry run python -m src/infrastructure/rq/rq_worker.py"]