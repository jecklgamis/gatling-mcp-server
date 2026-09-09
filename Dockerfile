FROM python:3.12.8-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY server/ server/

RUN useradd --system --no-create-home --uid 10001 gatling-mcp
USER gatling-mcp

EXPOSE 58090

CMD ["python", "server.py"]
