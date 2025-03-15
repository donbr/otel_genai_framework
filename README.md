# README.md
# OpenTelemetry GenAI Validation Framework

A comprehensive validation framework for testing OpenTelemetry instrumentation of GenAI systems against official semantic conventions.

Version: 0.1.0

## Overview

This framework provides tools to validate that your OpenTelemetry instrumentation for GenAI systems correctly follows the semantic conventions defined by the OpenTelemetry community and GenAI SIG.

## Features

- Validates spans, events, and metrics against GenAI semantic conventions
- In-memory testing with optional visualization through OTLP exporters
- Comprehensive test scenarios covering basic agent interactions, tool usage, reasoning flows, and error handling
- Rich console output with detailed test results
- Modular design making it easy to add custom test scenarios

## Installation

1. Clone this repository
2. Install requirements:
   ```bash
   pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-grpc rich
   ```

## Usage

### Running the full test suite

```bash
python validation_suite.py
```

### Running specific tests

```bash
# Run only the tool usage test
python validation_suite.py --test tool

# Run only the error handling test
python validation_suite.py --test error
```

### Options

- `--skip-otlp`: Skip sending telemetry to OTLP endpoint (useful for isolated testing)
- `--debug`: Enable debug logging
- `--test TEST`: Run only the specified test (`basic`, `tool`, `reasoning`, `error`, or `all`)

## Test Scenarios

The framework includes the following test scenarios:

| ID | Name | Description |
|----|------|-------------|
| basic | Basic Agent Tracing | Simple agent interaction with user query and response |
| reasoning | Multi-step Reasoning Flow | Complex reasoning with chain-of-thought process |
| tool | Tool Usage | Agent using external tools with function calls |
| error | Error Handling | Error handling, retries, and fallback strategies |

## Semantic Convention Validation

The framework supports two levels of validation:

1. **Basic Attribute Validation**: Verifies span attributes match expected values (default).
2. **Schema-Based Validation**: Validates against official OpenTelemetry GenAI schemas (advanced).

For full schema validation:

1. Download schema files:
```bash
# Download schema files from GitHub
python -c "from schema_integration_example import download_otel_schema; download_otel_schema()"
```

2. Enable schema validation:
```python
# In your test script
from schema_integration_example import enhance_validator_with_schema
from otel_genai_validator import GenAISpanValidator

# Enhance the validator with schema capabilities
enhance_validator_with_schema(GenAISpanValidator)

# Now run tests with full schema validation
```

This validates against the official semantic conventions defined by the OpenTelemetry GenAI SIG.

## Architecture

The framework consists of three main components:

1. **OTelGenAIValidator**: Core validation framework that manages the OpenTelemetry setup
2. **GenAISpanValidator**: Utility class for validating spans against semantic conventions
3. **Test Scenarios**: Individual test cases that simulate GenAI operations

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
