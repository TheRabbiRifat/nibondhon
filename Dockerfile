# Stage 1: Build stage
FROM python:3.11-slim as build-stage

# Install system dependencies and CA certificates
RUN apt-get update && apt-get install -y \
    ca-certificates \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements file and install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Stage 2: Production stage
FROM python:3.11-slim

# Install CA certificates
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the build stage
COPY --from=build-stage /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy the application code
COPY app.py /app/app.py

# Set the working directory
WORKDIR /app

# Expose port 8080
EXPOSE 8080

# Run the application
CMD ["python", "app.py"]
