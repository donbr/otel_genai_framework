# Improvement Plan for GenAI Validation Framework

This document addresses the key improvement opportunities identified in the code review of the OpenTelemetry GenAI Validation Framework.

## Recent Improvements and Next Steps

### ✅ Implemented: Scenario-Based Testing

We've added support for scenario-based testing with YAML files:

- Created a `scenarios/` directory with well-defined YAML scenarios
- Added structured validation against OpenTelemetry GenAI SIG schemas
- Implemented a `scenario_runner.py` that can execute these scenarios
- Aligned the scenarios with official OpenTelemetry GenAI semantic conventions

### ✅ Implemented: Enhanced Schema Integration

Enhanced schema integration to better work with OpenTelemetry GenAI SIG schemas:

- Improved `schema_integration.py` to load and validate against official schemas
- Added support for span, event, and metric schema validation
- Created a more comprehensive schema registry

### Next Steps in Progress

1. **Unified Validator Implementation**
   - Create a unified validator class that combines both approaches
   - Support both trace and metrics validation
   - Add consistent interface across all tools

2. **Test Scenario Consolidation**
   - Move all test scenario implementations to a common module
   - Make scenarios compatible with both validators
   - Remove duplicated code

## Original Improvement Plan (Still Valid)

### 1. Dependency Management

**Issue**: Duplicated dependency lists in `setup.py` and `check_dependencies()`.

**Implementation Plan**:
```python
# In validation_suite.py
def get_required_packages():
    """Get required packages from setup.py"""
    # Parse setup.py to extract install_requires
    import ast, re
    
    with open('setup.py', 'r') as f:
        setup_content = f.read()
    
    # Find the install_requires list
    match = re.search(r'install_requires=\[(.*?)\]', setup_content, re.DOTALL)
    if match:
        requires_content = match.group(1)
        # Parse the string list into actual list
        packages = []
        for line in requires_content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Extract package name without version
            package = re.match(r'"([^">=<]+)', line)
            if package:
                packages.append(package.group(1))
        return packages
    return []
```

### 2. Test Isolation

**Issue**: Shared `TracerProvider` across tests risks cross-test contamination.

**Implementation Plan**:
```python
# In otel_genai_validator.py
def setup_test(self, service_name):
    """Setup for a specific test with isolated providers"""
    # Create resource with service name
    resource = Resource(attributes={"service.name": service_name})
    
    # Create a new, isolated TracerProvider for this test
    test_provider = TracerProvider(resource=resource)
    
    # Use InMemorySpanExporter for validation
    memory_exporter = InMemorySpanExporter()
    memory_processor = SimpleSpanProcessor(memory_exporter)
    test_provider.add_span_processor(memory_processor)
    
    processors = [memory_processor]
    
    # Optionally send to OTLP for visualization
    if self.enable_otlp:
        otlp_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint, insecure=True)
        otlp_processor = BatchSpanProcessor(otlp_exporter)
        test_provider.add_span_processor(otlp_processor)
        processors.append(otlp_processor)
    
    # Return a test-specific tracer using the isolated provider
    return test_provider.get_tracer(f"{service_name}-tracer"), memory_exporter, processors
```

### 3. Dynamic Test Registration

**Issue**: Hardcoded `TEST_SCENARIOS` mapping in `validation_suite.py`.

**Implementation Plan**:
```python
# In genai_test_scenarios.py
TEST_REGISTRY = {}

def register_test(test_id, display_name):
    """Decorator to register a test scenario"""
    def decorator(func):
        TEST_REGISTRY[test_id] = (display_name, func.__name__)
        return func
    return decorator

@register_test("basic", "Basic Agent Tracing")
def run_basic_agent_test(validator):
    # Test implementation...

# In validation_suite.py
from genai_test_scenarios import TEST_REGISTRY as TEST_SCENARIOS
```

### 4. Tool Span Validation

**Issue**: `verify_tool_span()` may miss multi-tool scenarios.

**Implementation Plan**:
```python
# In otel_genai_validator.py, update verify_tool_span
@staticmethod
def verify_tool_span(spans, parent_span_id, tool_name=None, expected_count=1):
    """
    Verify tool execution spans exist and have correct attributes
    
    Args:
        spans: List of spans to search
        parent_span_id: Expected parent span ID
        tool_name: Optional tool name to match
        expected_count: Expected number of tool spans (default: 1)
        
    Returns:
        The tool span(s) if found, raises AssertionError otherwise
    """
    # Find tool spans that are children of the parent
    tool_spans = [s for s in spans 
                 if s.parent_span_id == parent_span_id 
                 and s.attributes.get("gen_ai.operation.name") == "execute_tool"]
    
    assert len(tool_spans) == expected_count, f"Expected {expected_count} tool spans, got {len(tool_spans)}"
    
    if tool_name:
        # Find specific tool(s) by name
        matching_spans = [s for s in tool_spans 
                         if s.attributes.get("gen_ai.tool.name") == tool_name]
        assert len(matching_spans) > 0, f"Tool span for {tool_name} not found"
        return matching_spans[0] if len(matching_spans) == 1 else matching_spans
    else:
        # Return single tool span or list depending on expected count
        return tool_spans[0] if expected_count == 1 else tool_spans
```

### 5. Error Handling Tests

**Issue**: Custom `retry.count` attribute lacks documentation.

**Implementation Plan**:
```python
# Add docstring to error_handling_test function
def run_error_handling_test(validator):
    """
    Test Scenario 5: Error Handling and Resilience Validation
    
    Validates an agent's ability to handle errors and implement retries.
    
    Custom Attributes:
        retry.count: Tracks retry attempt number (0 for initial, 1+ for retries)
        fallback.for: Identifies which tool this is a fallback for
    
    Args:
        validator: OTelGenAIValidator instance
        
    Returns:
        bool: True if the test passes
    """
```

### 6. Test Parameterization

**Issue**: Hardcoded model/tool names limit reusability.

**Implementation Plan**:
```python
# Create genai_test_config.py
"""
Configuration for GenAI test scenarios

This module contains configuration parameters that can be customized
for different testing environments.
"""

# Models to test against
MODELS = {
    "openai": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-opus", "claude-3-sonnet"],
    "mistral": ["mistral-large", "mistral-medium"]
}

# Default model to use for each provider
DEFAULT_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-3-opus",
    "mistral": "mistral-large"
}

# Modify test functions to use configuration
def run_basic_agent_test(validator, provider="anthropic", model=None):
    """Basic Agent Test with configurable model"""
    model = model or DEFAULT_MODELS.get(provider, "claude-3-opus")
    tracer, memory_exporter, processors = validator.setup_test(f"agent-{provider}")
    # Test using the configured model...
```

## Updated Implementation Timeline

1. **Immediate (1-2 days):**
   - Complete the Unified Validator implementation
   - Finish scenario runner integration with existing tests

2. **Short-term (1 week):**
   - Implement test isolation
   - Add support for loading scenarios directly from YAML files
   - Fix dependency management

3. **Medium-term (2-3 weeks):**
   - Dynamic test registration
   - Test parameterization
   - Create more comprehensive validation scenarios

## Additional Future Enhancements

1. **OpenInference Compatibility Layer**
   - Add optional support for reading OpenInference JSONL formats
   - Create converters between OpenTelemetry and OpenInference formats
   - Support hybrid testing approaches

2. **Continuous Integration Support**
   - Add GitHub Actions workflow for automated testing
   - Create Docker container for easy deployment
   - Publish to PyPI for easier installation

3. **Documentation Improvements**
   - Create comprehensive documentation site
   - Add detailed examples for common use cases
   - Create tutorials for different GenAI frameworks
