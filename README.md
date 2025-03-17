# OpenTelemetry GenAI Validation Framework

A comprehensive validation framework for testing OpenTelemetry instrumentation of GenAI systems against official semantic conventions.

Version: 0.2.0

## Overview

This framework provides tools to validate that your OpenTelemetry instrumentation for GenAI systems correctly follows the semantic conventions defined by the OpenTelemetry community and GenAI SIG.

## Features

- Validates spans, events, and metrics against GenAI semantic conventions
- Supports scenario-based testing with YAML definition files
- In-memory testing with optional visualization through OTLP exporters
- Comprehensive test scenarios covering basic agent interactions, tool usage, reasoning flows, and error handling
- Rich console output with detailed test results
- Modular design making it easy to add custom test scenarios

## Installation

1. Clone this repository
2. Install requirements:
   ```bash
   pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc rich pyyaml
   ```

## Prerequisites

For full functionality with telemetry visualization, you'll need Jaeger running:

```bash
# Start Jaeger with Docker
docker run --rm --name jaeger \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  -p 5778:5778 \
  -p 9411:9411 \
  jaegertracing/jaeger:latest
```

```pwsh
# PowerShell version
docker run --rm --name jaeger `
  -p 16686:16686 `
  -p 4317:4317 `
  -p 4318:4318 `
  -p 5778:5778 `
  -p 9411:9411 `
  jaegertracing/jaeger:latest
```

The Jaeger UI will be available at: http://localhost:16686

## Usage

### Running the Test Suite

```bash
# Run all tests
python validation_suite.py

# Skip sending telemetry to OTLP/Jaeger (for faster testing without visualization)
python validation_suite.py --skip-otlp
```

### Running Specific Tests

```bash
# Run only the tool usage test
python validation_suite.py --test tool

# Run only the error handling test
python validation_suite.py --test error

# Run with debug logging
python validation_suite.py --debug --test basic
```

## Test Scenarios

The framework includes the following test scenarios:

| ID | Name | Description |
|----|------|-------------|
| basic | Basic Agent Tracing | Simple agent interaction with user query and response |
| reasoning | Multi-step Reasoning Flow | Complex reasoning with chain-of-thought process |
| tool | Tool Usage | Agent using external tools with function calls |
| error | Error Handling | Error handling, retries, and fallback strategies |

All these scenarios are available both through `validation_suite.py` and as YAML definitions in the `scenarios/` directory.

## Scenario-Based Testing

The framework supports defining test scenarios in YAML files:

```yaml
# Example scenario definition
name: "Basic Agent Test"
description: "Tests a simple query-response pattern with a GenAI agent"

configuration:
  service_name: "agent-service"
  trace_validation: true
  metrics_validation: true

spans:
  - name: "chat claude-3-opus"
    expected_attributes:
      gen_ai.system: "anthropic"
      gen_ai.operation.name: "chat"
      gen_ai.request.model: "claude-3-opus"
    expected_events:
      - name: "gen_ai.user.message"
        attributes:
          content: "What is the capital of France?"
      - name: "gen_ai.assistant.message"
        attributes:
          content: "The capital of France is Paris."

schema_validation:
  span_schema: "span.gen_ai.client"
  event_schemas:
    - "event.gen_ai.user.message"
    - "event.gen_ai.assistant.message"
```

See the `scenarios/` directory for more comprehensive examples.

## Semantic Convention Validation

The framework supports two levels of validation:

1. **Basic Attribute Validation**: Verifies span attributes match expected values (default).
2. **Schema-Based Validation**: Validates against official OpenTelemetry GenAI schemas.

For full schema validation:

1. The framework will automatically download schema files to the `schemas/` directory if they don't exist:
```python
from schema_integration import SchemaValidator
validator = SchemaValidator()
```

2. Enhance the validator with schema capabilities:
```python
from schema_integration import enhance_validator_with_schema
from src.otel_genai_validator import GenAISpanValidator

# Enhance the validator with schema capabilities
enhance_validator_with_schema(GenAISpanValidator)

# Now run tests with full schema validation
```

This validates against the official semantic conventions defined by the OpenTelemetry GenAI SIG.

## Architecture

The framework consists of several key components:

1. **OTelGenAIValidator**: Core validation framework that manages the OpenTelemetry setup
2. **GenAISpanValidator**: Utility class for validating spans against semantic conventions
3. **SchemaValidator**: Validates telemetry against OpenTelemetry GenAI SIG schemas
4. **ScenarioRunner**: Runs scenario-based tests defined in YAML files
5. **Test Scenarios**: Individual test cases that simulate GenAI operations

## Directory Structure

```
otel_genai_framework/
├── README.md                     # Main project documentation and getting started guide
├── background.md                 # Overview of OpenTelemetry standards and their value for GenAI
├── validation_suite.py           # Main test runner for executing validation scenarios
├── scenario_runner.py            # Utility for running individual test scenarios from YAML files
├── otel-platform/                # Docker Compose setup for local OpenTelemetry observability stack
├── scenarios/                    # YAML definitions for test scenarios (basic, tool usage, reasoning, errors)
├── schemas/                      # Auto-downloaded OpenTelemetry GenAI schema files for validation
├── docs/                         # Additional documentation (quickstart guides, architecture diagrams)
├── notebooks/                    # Jupyter notebooks for interactive exploration and validation examples
└── src/                          # Core source code for the validation framework components
```

For more details, see [project_structure.md](project_structure.md).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

Licensing is determined by the [OpenTelemetry standard](https://github.com/open-telemetry/opentelemetry-collector/blob/main/LICENSE).
