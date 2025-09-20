# network-collector:
This is a simple python application to get basic network information

## Project Structure

```bash
.
├── Dockerfile
├── requirements.txt
├── src/
│   └── network-collector.py
│   └──configuration/
│      └── configuration.yaml
└── .env
```

## .env
None at this time  

## Error Handling

There is no specific retry logic at this time. If there are errors with one session, this should be logged and it will
retry the same pull for a full 24 hours. 

## Traces, Logs, and Metrics

Logs are exposed as OpenTelemetry.  When running locally, the collector will capture Traces to Tempo, Logs to Splunk, 
and metrics to Prometheus. 

## Docker File

```bash
docker login
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t jaysuzi5/network-collector:latest \
  --push .
```
