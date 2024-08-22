# Stage 1: Build stage
FROM python:3.11-slim as build-stage

# Install system dependencies and CA certificates
RUN apt-get update && apt-get install -y \
    ca-certificates \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install required Python packages
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Stage 2: Production stage
FROM python:3.11-slim

# Install CA certificates
RUN apt-get update && apt-get install -y \
    ca-certificates \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from the build stage
COPY --from=build-stage /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Chrome and ChromeDriver
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb \
    && apt-get -f install -y \
    && rm google-chrome-stable_current_amd64.deb

RUN wget https://chromedriver.storage.googleapis.com/114.0.5735.90/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/ \
    && rm chromedriver_linux64.zip

# Copy the application code
COPY app.py /app/app.py
COPY requirements.txt /app/requirements.txt

# Set the working directory
WORKDIR /app

# Run the application
CMD ["python", "app.py"]
