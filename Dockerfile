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
EXPOSE 8080

# Use standard uvicorn runner, defaulting to 8080 if PORT isn't passed
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8080}
