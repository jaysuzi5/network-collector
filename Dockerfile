FROM python:3.12.9-slim-bookworm
WORKDIR /app
# Install ping (from iputils-ping) and iperf3
RUN apt-get update && apt-get install -y --no-install-recommends \
    iputils-ping \
    iperf3 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ /app/src/
ENV LOCAL_API_BASE_URL='http://home.dev.com/api/v1/network'

CMD ["opentelemetry-instrument", "--logs_exporter", "otlp", "--traces_exporter", "otlp", "python", "/app/src/network-collector.py"]
