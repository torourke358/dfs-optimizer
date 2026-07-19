# Root Dockerfile for hosts that build from the repo root (e.g. Render).
# Builds the backend API; identical to backend/Dockerfile apart from paths.
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/sample_data ./sample_data

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
