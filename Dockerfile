# Base image
FROM python:3-slim-bookworm

# Set working directory
WORKDIR /app

# Copy the script into the container
COPY . .

# Create default file for TinyDB
RUN touch /app/video_history.json

# Install any necessary libraries
RUN pip install -r requirements.txt

# Run the script
CMD ["python", "main.py"]