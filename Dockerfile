FROM python:3.12-slim

WORKDIR /app

# Install uv via pip (no pre-downloaded binary required)
RUN pip install uv --quiet

COPY pyproject.toml uv.lock ./
# --no-dev: skip dev extras.  Drop --frozen so new deps are resolved when
# the lock file has not been regenerated yet after pyproject.toml changes.
RUN uv sync --no-dev

COPY src/ ./src/
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY llm/ ./llm/

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]