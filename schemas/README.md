# OpenTelemetry GenAI Schema Directory

This directory contains the official OpenTelemetry Generative AI Special Interest Group (SIG) semantic convention schemas used for validation.

## Schema Files

The following schema files will be automatically downloaded when needed:

- **spans.yaml**: Definitions for GenAI spans (e.g., `span.gen_ai.client`, `span.gen_ai.execute_tool.internal`)
- **events.yaml**: Definitions for GenAI events (e.g., `event.gen_ai.user.message`, `event.gen_ai.assistant.message`)
- **metrics.yaml**: Definitions for GenAI metrics (e.g., `metric.gen_ai.client.token.usage`)
- **registry.yaml**: Registry of common attributes used across spans, events, and metrics

## Usage

These schema files are used by the validation framework to verify that generated telemetry conforms to the official semantic conventions. 

The schema files are automatically downloaded from the OpenTelemetry specification repository when the validator is run for the first time. You can also manually download them using:

```python
from schema_integration import SchemaRegistry

registry = SchemaRegistry()
registry.download_schemas()
```

## Schema Structure

The schemas follow the OpenTelemetry conventions format:

```yaml
groups:
  - id: span.gen_ai.client
    type: span
    brief: "Describes GenAI operation span"
    attributes:
      - ref: gen_ai.system
        requirement_level: required
      - ref: gen_ai.operation.name
        requirement_level: required
      # ... more attributes
```

Each schema defines the expected attributes, their requirement levels (required, recommended, opt-in), and additional validation rules.

## Source

These schemas are sourced from the official OpenTelemetry Specification repository:
https://github.com/open-telemetry/opentelemetry-specification/tree/main/semantic_conventions/genai
