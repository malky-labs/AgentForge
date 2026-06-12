# Use standard Python 3.11 image
FROM python:3.11-slim

# Set workdir inside container
WORKDIR /app

# Install system dependencies (build-essential, git, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements first to cache docker layers
COPY backend/requirements.txt /app/

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY backend /app/backend

# Create directory for persistent local sqlite databases and assets
RUN mkdir -p /app/storage

# Set working directory to the backend directory
WORKDIR /app/backend

# Expose port
EXPOSE 8000

# Start command matching development entry point
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
