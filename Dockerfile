# Use the official Python image from the Docker Hub
FROM python:3.11

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create and set the working directory
WORKDIR /app

# Install system dependencies for Pyppeteer
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    libx11-dev \
    libxkbcommon-dev \
    libnss3 \
    libgdk-pixbuf2.0-0 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app/

# Expose port 8080
EXPOSE 8080

# Run the Flask application
CMD ["python", "app.py"]
