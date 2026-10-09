FROM python:3.12.9-slim
WORKDIR /app
COPY requirements-lock.txt requirements-local.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt -r requirements-local.txt
COPY . .
RUN useradd -m -u 10001 closetwise && mkdir -p /app/data/images && chown -R closetwise:closetwise /app
USER closetwise
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
