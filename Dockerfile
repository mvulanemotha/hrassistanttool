# Use official Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libpq-dev \
    git \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    pkg-config \
    poppler-utils \
    libmagic-dev \
    libreoffice \
    libcairo2 \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy dependency files
COPY pyproject.toml uv.lock* requirements.txt* ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install sqlalchemy-pgvector directly from GitHub
RUN pip install --no-cache-dir git+https://github.com/pgvector/sqlalchemy-pgvector.git

# Copy the source code
COPY . .

# Expose the port
EXPOSE 8000

# Run the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
