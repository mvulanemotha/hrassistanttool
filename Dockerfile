# Use an official python base Image
FROM python:3.11-slim

#set the working directory
WORKDIR /app


# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*


# Install uv ( Astra's fast package manager )
RUN pip install uv

#Copy project files
COPY pyproject.toml uv.lock* requirements.txt* ./

#Install dependecies with uv
# uv will detect pyproject.toml or requirements and install into current environment
RUN uv pip install --system -r requirements.txt

# Now copy my actual python code
COPY . .

# Expose the port the app is running on
EXPOSE 8000

# Use uvicorn as your server
CMD ["uvicorn" , "main:app", "--host", "0.0.0.0" , "--port", "8000" ]
