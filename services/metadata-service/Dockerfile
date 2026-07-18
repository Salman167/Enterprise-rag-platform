FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
COPY shared/python /shared/python
RUN pip install --no-cache-dir /shared/python
COPY services/metadata-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/metadata-service/app ./app
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
