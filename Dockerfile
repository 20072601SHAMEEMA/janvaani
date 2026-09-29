FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY static ./static
COPY data/districts.csv ./data/districts.csv
# The demo database is seeded on startup (see app/db.py)
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
