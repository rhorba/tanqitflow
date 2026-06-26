FROM python:3.12-slim

WORKDIR /code

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev \
    fonts-noto-core fonts-noto-extra \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: API server (overridden per service in docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
