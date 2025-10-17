# Use an official python base Image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install system dependencies, including LibreOffice and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
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

# Copy project dependency files
COPY pyproject.toml uv.lock* requirements.txt* ./

# Install dependencies using pip (not uv)
RUN pip install --no-cache-dir -r requirements.txt

# If sqlalchemy-pgvector fails from PyPI, install from GitHub
# RUN pip install --no-cache-dir git+https://github.com/pgvector/sqlalchemy-pgvector.git

# Copy your actual Python code
COPY . .

# Expose the port the app is running on
EXPOSE 8000

# Run the app with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
