FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY server/ server/

EXPOSE 58090

CMD ["python", "server.py"]
