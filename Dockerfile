FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ app/
COPY docs/ docs/
COPY scripts/ scripts/
COPY README.md .

# Expose port
EXPOSE 8001

ENV PYTHONPATH=/app
ENV PORT=8001
ENV HOST=0.0.0.0

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
