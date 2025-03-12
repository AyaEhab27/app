# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# تثبيت الحزم الأساسية
RUN apt-get update && \
    apt-get install -y wget espeak-ng

# تنزيل وتثبيت mbrola
RUN wget https://github.com/numediart/MBROLA/raw/master/Binaries/mbrola-linux-i386.tar.gz -O mbrola.tar.gz && \
    tar -xzf mbrola.tar.gz && \
    mv mbrola-linux-i386 /usr/local/bin/mbrola && \
    chmod +x /usr/local/bin/mbrola && \
    rm mbrola.tar.gz

# تنزيل وتثبيت الأصوات العربية (mbrola-ar1)
RUN mkdir -p /usr/share/mbrola/ar1 && \
    wget https://github.com/numediart/MBROLA-voices/raw/master/data/ar1/ar1 -O /usr/share/mbrola/ar1/ar1 && \
    chmod 644 /usr/share/mbrola/ar1/ar1

# Copy the requirements file into the container
COPY app/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY app/ .

# Copy the models directory
COPY app/models/ ./models/

# Copy the Firebase service account key
COPY app/voice-ec9bd-firebase-adminsdk-fbsvc-0215fa1324.json ./voice-ec9bd-firebase-adminsdk-fbsvc-0215fa1324.json

# Make port 80 available to the world outside this container
EXPOSE 80

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
