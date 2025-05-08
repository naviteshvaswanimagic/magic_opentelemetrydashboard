# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and .env file
COPY loki_reader.py .
COPY .env .

# Create logs directory
RUN mkdir -p logs

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "loki_reader.py"] 