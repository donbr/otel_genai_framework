# project_structure.md
# Project Structure

The OpenTelemetry GenAI Validation Framework has the following structure:

```
otel-genai-validator/
├── README.md                     # Project documentation
├── setup.py                      # Installation script
├── otel_genai_validator.py       # Core validation framework
├── genai_test_scenarios.py       # Test scenarios
└── validation_suite.py           # Main test runner
```

## File Descriptions

### otel_genai_validator.py

This is the core validation library that provides classes for setting up OpenTelemetry testing environments and validating trace data against semantic conventions.

Key components:
- `OTelGenAIValidator`: Main validator class that manages the OTel lifecycle
- `GenAISpanValidator`: Utility class with methods for validating spans

### genai_test_scenarios.py

Contains test scenarios that simulate different GenAI interactions. Each scenario:
1. Sets up a testing environment
2. Generates spans using OpenTelemetry
3. Validates that the spans conform to semantic conventions

Available scenarios:
- Basic Agent Tracing
- Multi-step Reasoning Flow
- Tool Usage and Function Calling
- Error Handling and Resilience

### validation_suite.py

The entry point for running tests. It provides a command-line interface for selecting and running tests, with options for controlling output verbosity and OTLP export.

## Python Module Organization

- Each file is a separate Python module
- The setup.py allows installation as a package
- Entry points are configured for CLI access

## Extending the Framework

To add new test scenarios:

1. Add your test function to `genai_test_scenarios.py`
2. Add your test to the `TEST_SCENARIOS` dictionary in `validation_suite.py`
3. Update documentation as needed
