   # Use a base image
   FROM python:3.12-slim

   # Set the working directory
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

   # Command to run the worker
   CMD ["poetry", "run", "rq", "worker", "--url", "$REDIS_URL", "$REDIS_QUEUE_NAME"]