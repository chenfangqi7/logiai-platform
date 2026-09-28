FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/pip pip install .
COPY alembic.ini ./
COPY alembic ./alembic
EXPOSE 8000
