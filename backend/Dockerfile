FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv==0.8.4

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY alembic.ini ./
COPY alembic ./alembic

RUN uv pip install --system --no-cache .

EXPOSE 8000

CMD ["uvicorn", "agentrooms.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
