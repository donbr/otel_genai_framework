# OpenTelemetry GenAI Validation Framework - Project Structure

This document describes the structure and organization of the OpenTelemetry GenAI Validation Framework.

## Directory Structure

```
otel_genai_framework/
├── README.md                     # Project documentation and usage instructions
├── setup.py                      # Installation script and package metadata
├── project_structure.md          # This document
├── improvement-plan.md           # Plans for future improvements
├── otel_genai_validator.py       # Core validation framework
├── genai_test_scenarios.py       # Test scenarios with validation logic
├── validation_suite.py           # Main test runner with rich console output
├── jaeger_tester.py              # Alternative tester focusing on Jaeger integration
├── semantic_validator.py         # Base schema validation utilities
├── schema_integration.py         # Integration with OpenTelemetry schema definitions
├── scenario_runner.py            # Runner for YAML-based scenarios
├── scenarios/                    # Directory containing YAML test scenarios
│   ├── basic_agent_scenario.yaml      # Basic agent interaction scenario
│   ├── tool_usage_scenario.yaml       # Tool usage scenario
│   ├── reasoning_flow_scenario.yaml   # Multi-step reasoning scenario
│   └── error_handling_scenario.yaml   # Error handling scenario
└── garbage/                      # Deprecated or unused files
```

## Core Components

### Validation Framework

- **otel_genai_validator.py**: Core validation library that provides classes for setting up OpenTelemetry testing environments and validating trace data against semantic conventions.
  - `OTelGenAIValidator`: Main validator class that manages the OTel lifecycle and test environment setup
  - `GenAISpanValidator`: Utility class with methods for validating spans against expected attributes and events

- **semantic_validator.py**: Base classes for schema-based validation of spans, events, and metrics.
  - `GenAISchema`: Class to load and manage schema definitions from YAML files
  - `SpanSchemaValidator`: Core validator for checking spans against GenAI semantic conventions

- **schema_integration.py**: Enhanced schema validation that integrates with OpenTelemetry GenAI SIG schemas.
  - `SchemaRegistry`: Manages loading and accessing official schema definitions
  - `SchemaValidator`: Validates spans, events, and metrics against official schemas
  - `enhance_validator_with_schema()`: Function to add schema validation capabilities to the base validator

### Test Execution

- **validation_suite.py**: Primary entry point for running predefined tests with rich console output.
  - Well-structured approach with clear test result reporting
  - Command-line interface for selecting tests and controlling output
  - Comprehensive dependency checking

- **jaeger_tester.py**: Alternative test runner focused on sending telemetry to Jaeger.
  - Includes metrics recording capabilities
  - Emphasizes visualization in Jaeger UI
  - Currently contains duplicated test logic from genai_test_scenarios.py (will be addressed in future updates)

- **scenario_runner.py**: Runner for YAML-based test scenarios.
  - Loads and executes scenarios defined in YAML files
  - Validates generated telemetry against scenario expectations
  - Supports validation against OpenTelemetry GenAI SIG schemas

### Test Definitions

- **genai_test_scenarios.py**: Collection of test functions that simulate different GenAI interactions.
  - Each function sets up a test environment, generates spans, and validates them
  - Tests include basic agent interaction, multi-step reasoning, tool usage, and error handling

- **scenarios/**: Directory containing YAML-based test scenarios.
  - Each scenario defines expected spans, events, metrics, and validation rules
  - Structured format that aligns with OpenTelemetry GenAI SIG conventions
  - Separates test definitions from implementation code

## Framework Interfaces

The framework offers multiple ways to run validation:

1. **Command-line Interface (validation_suite.py)**:
   ```bash
   python validation_suite.py --test [basic|tool|reasoning|error|all]
   ```

2. **Scenario-based Testing (scenario_runner.py)**:
   ```bash
   python scenario_runner.py --scenario scenarios/basic_agent_scenario.yaml
   ```

3. **Programmatic API**:
   ```python
   from otel_genai_validator import OTelGenAIValidator
   from genai_test_scenarios import run_basic_agent_test

   validator = OTelGenAIValidator()
   run_basic_agent_test(validator)
   ```

## Schema Validation

The framework supports validation against official OpenTelemetry GenAI SIG schemas:

1. **Basic Validation**: Checks that spans, events, and metrics have the expected attributes with correct values.

2. **Schema-based Validation**: Validates telemetry against the official schemas, including:
   - Required attributes based on schema definitions
   - Conditionally required attributes with their conditions
   - Attribute value types and constraints (enum values, etc.)

The schema definition files are automatically downloaded from the OpenTelemetry specification repository when needed.

## Current Status and Future Direction

The framework currently has two parallel approaches (validation_suite.py and jaeger_tester.py) with some duplication. The ongoing improvement plan includes:

1. Creating a unified validator that combines features from both approaches
2. Consolidating test scenarios to eliminate duplication
3. Enhancing schema validation to fully align with the latest OpenTelemetry GenAI SIG standards

The introduction of YAML-based scenarios represents a significant step toward more data-driven testing that separates test definitions from implementation code.
