# Use a lightweight Python base
FROM python:3.14-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Poetry
ENV POETRY_VERSION=2.2.1
RUN pip install "poetry==$POETRY_VERSION"

# Copy only dependency files first (better caching)
COPY pyproject.toml poetry.lock* /app/

# Install dependencies (no dev, no virtualenv creation)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --only main

# Copy source code
COPY . /app

# Expose Uvicorn port
EXPOSE 8000

# Uvicorn startup command
CMD ["poetry", "run", "uvicorn", "src.ftc_queueing_api:app", "--host", "0.0.0.0", "--port", "8000"]
