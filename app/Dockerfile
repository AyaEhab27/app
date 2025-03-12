FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y espeak-ng mbrola-ar1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY models/ ./models/


EXPOSE 80

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
