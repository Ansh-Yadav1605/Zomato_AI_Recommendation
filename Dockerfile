FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and data
COPY . .

# Explicitly expose port 8080 as a hint for Railway's proxy
# Explicitly tell Railway to route traffic to 8080
EXPOSE 8080

# Hardcode Uvicorn to bind to 8080, intentionally ignoring Railway's $PORT env var
# This fixes the issue where the public domain is permanently glued to port 8080
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port 8080"]
