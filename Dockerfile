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
# Explicitly expose port 8000 to tell Railway proxy to route traffic here
EXPOSE 8000

# Force --loop asyncio --http h11 to prevent uvloop/httptools silent crashes on Railway Linux
# Hardcode port 8000 to perfectly match the EXPOSE directive above
CMD ["sh", "-c", "uvicorn src.main:app --host :: --port 8000 --loop asyncio --http h11"]
