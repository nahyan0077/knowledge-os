FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy project configuration and lockfile
COPY pyproject.toml uv.lock ./

# Install dependencies first (uses Docker layer caching)
RUN uv sync --frozen --no-install-project --no-dev

# Copy the application source code and migrations
COPY src/ ./src
COPY alembic.ini ./
COPY migrations/ ./migrations

# Sync the project itself
RUN uv sync --frozen --no-dev

# Set the Python path to locate the package in src/
ENV PYTHONPATH=/app/src

# Default port
ENV PORT=8000

# Run migrations and start the FastAPI uvicorn server
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn knowledge_os.main:app --host 0.0.0.0 --port $PORT"]
