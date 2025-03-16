# Draft instructions for launching from commnad line

- to run collector base config from command line

```bash
docker run --rm \
  -p 4317:4317 \
  -p 4318:4318 \
  -p 55679:55679 \
  -v "$(pwd)/otel-collector-base-config.yaml:/etc/otel/otel-collector-config.yaml" \
  otel/opentelemetry-collector:latest \
  --config /etc/otel/otel-collector-config.yaml
  ```

  ```pwsh
    docker run --rm `
    -p 4317:4317 `
    -p 4318:4318 `
    -p 55679:55679 `
    -v "$(pwd)/otel-collector-base-config.yaml:/etc/otel/otel-collector-config.yaml" `
    otel/opentelemetry-collector:latest `
    --config /etc/otel/otel-collector-config.yaml
  ```
