# Use an official python base Image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install system dependencies, including LibreOffice
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
    && rm -rf /var/lib/apt/lists/*

# Install uv (Astra's fast package manager)
RUN pip install uv

# Copy project files
COPY pyproject.toml uv.lock* requirements.txt* ./

# Install dependencies with uv
RUN uv pip install --system -r requirements.txt

# Now copy my actual python code
COPY . .

# Expose the port the app is running on
EXPOSE 8000

# Use uvicorn as your server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
