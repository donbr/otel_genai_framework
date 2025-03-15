# schema_integration_example.py
"""
Examples showing how to integrate the semantic validator with the testing framework

This demonstrates how to enhance the existing tests with schema-based validation.
"""

import os
import shutil
from urllib.request import urlretrieve
import logging
from otel_genai_validator import GenAISpanValidator
from semantic_validator import GenAISchema, SpanSchemaValidator

logger = logging.getLogger(__name__)

def download_otel_schema(target_dir="./schemas"):
    """
    Download the latest GenAI semantic convention schemas from OpenTelemetry GitHub
    
    Args:
        target_dir: Directory to save schema files to
    """
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    # Base URL for raw content from the OpenTelemetry specification repo
    base_url = "https://raw.githubusercontent.com/open-telemetry/opentelemetry-specification/main/semantic_conventions"
    
    # Schema files to download
    schema_files = [
        "genai/spans.yaml",
        "genai/events.yaml", 
        "genai/metrics.yaml",
        "genai/registry.yaml"
    ]
    
    for schema_file in schema_files:
        url = f"{base_url}/{schema_file}"
        local_path = os.path.join(target_dir, os.path.basename(schema_file))
        
        try:
            logger.info(f"Downloading schema: {url}")
            urlretrieve(url, local_path)
            logger.info(f"Downloaded to: {local_path}")
        except Exception as e:
            logger.error(f"Failed to download schema {schema_file}: {str(e)}")

def enhance_validator_with_schema(validator_class):
    """
    Enhance the GenAISpanValidator with schema-based validation
    
    Args:
        validator_class: The GenAISpanValidator class to enhance
        
    Returns:
        Enhanced validator class
    """
    # Load schema
    schema = GenAISchema("./schemas")
    schema_validator = SpanSchemaValidator(schema)
    
    # Store original method
    original_verify = validator_class.verify_genai_span_attributes
    
    @staticmethod
    def enhanced_verify(span, expected_attributes, span_type=None):
        """Enhanced verification with schema validation"""
        # First, perform original verification
        original_verify(span, expected_attributes)
        
        # If span type is provided, also validate against schema
        if span_type:
            errors = schema_validator.validate_span(span, span_type)
            if errors:
                error_msg = "Schema validation errors: " + ", ".join(errors)
                assert not errors, error_msg
                
        return True
    
    # Replace the method
    validator_class.verify_genai_span_attributes = enhanced_verify
    
    # Also add a new method for event validation
    @staticmethod
    def verify_event_schema(event, event_type):
        """Verify an event against its schema"""
        errors = schema_validator.validate_event(event, event_type)
        if errors:
            error_msg = "Event schema validation errors: " + ", ".join(errors)
            assert not errors, error_msg
        return True
    
    validator_class.verify_event_schema = verify_event_schema
    
    return validator_class

# Example usage in a test scenario
def run_enhanced_tool_usage_test(validator):
    """Example of how to enhance a test with schema validation"""
    # Setup test
    tracer, memory_exporter, processors = validator.setup_test("agent-with-tools")
    
    try:
        # Test code as before...
        
        # Validation
        spans = memory_exporter.get_finished_spans()
        
        # Find root span
        root_span = next((s for s in spans if s.name == "chat gpt-4o"), None)
        
        # Enhanced validation with schema type
        GenAISpanValidator.verify_genai_span_attributes(
            root_span, 
            {
                "gen_ai.system": "openai",
                "gen_ai.operation.name": "chat",
                "gen_ai.request.model": "gpt-4o"
            },
            span_type="span.gen_ai.client"  # Add schema type for validation
        )
        
        # Validate assistant message event
        assistant_event = root_span.events[1]  # Assuming second event is assistant message
        GenAISpanValidator.verify_event_schema(
            assistant_event,
            event_type="event.gen_ai.assistant.message"
        )
        
        # Rest of validation as before...
        
    finally:
        # Clean up
        validator.cleanup_test(processors)
