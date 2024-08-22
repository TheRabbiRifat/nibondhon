# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables to prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that the Flask app runs on
EXPOSE 8080

# Run the application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "app:app"]

