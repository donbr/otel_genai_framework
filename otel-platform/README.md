# OpenTelemetry Platform

This directory contains the configuration files to run a complete OpenTelemetry observability platform using Docker Compose.

## Components

- **OpenTelemetry Collector**: Central component that receives, processes, and exports telemetry data
- **Jaeger**: Distributed tracing system for visualizing trace data
- **Prometheus**: Time series database for storing and querying metrics

## Prerequisites

- Docker and Docker Compose installed
- Git (to clone this repository)
- Port availability: 4317, 4318, 9090, 16686, 55679

## Getting Started

1. Clone this repository (if you haven't already)
2. Navigate to the `otel-platform` directory

```bash
cd otel_genai_framework/otel-platform
```

3. Start the OpenTelemetry platform:

```bash
docker-compose up -d
```

4. Verify all services are running:

```bash
docker-compose ps
```

## Accessing the Components

- **Jaeger UI**: http://localhost:16686
- **Prometheus UI**: http://localhost:9090
- **OpenTelemetry Collector zPages**: http://localhost:55679/debug/tracez

## Component Configuration

- OpenTelemetry Collector config: `./collector/otel-collector-config.yaml`
- Prometheus config: `./prometheus/prometheus-config.yaml`

## Sending Data to the Platform

Configure your applications to send telemetry data to:
- Traces (OTLP/gRPC): localhost:4317
- Traces (OTLP/HTTP): localhost:4318

Example environment variables for your applications:
```
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
```

## Stopping the Platform

To stop the platform:

```bash
docker-compose down
```

## Troubleshooting

- Check container logs: `docker-compose logs [service-name]`
- Ensure all required ports are available and not used by other applications
- Verify network connectivity between containers using `docker-compose exec [service-name] ping [other-service]`
