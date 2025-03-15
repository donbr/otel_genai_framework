# otel_genai_validator.py
"""
OpenTelemetry GenAI Validator Framework

This module provides a comprehensive validation framework for testing OpenTelemetry
instrumentation of GenAI systems against the official semantic conventions.

Version: 0.1.0
"""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, BatchSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
import time
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("otel-genai-validator")

class OTelGenAIValidator:
    """
    Validator framework for GenAI OpenTelemetry instrumentation
    
    This class provides utilities for setting up test environments, capturing
    spans, and validating them against GenAI semantic conventions.
    """
    
    def __init__(self, enable_otlp=True, otlp_endpoint="localhost:4317"):
        """
        Initialize the validator
        
        Args:
            enable_otlp: Whether to send spans to an OTLP endpoint (default: True)
            otlp_endpoint: Address of the OTLP endpoint (default: localhost:4317)
        """
        self.enable_otlp = enable_otlp
        self.otlp_endpoint = otlp_endpoint
        self._provider = None
        self._init_provider()
        logger.info(f"Initialized validator with OTLP {'enabled' if enable_otlp else 'disabled'}")
    
    def _init_provider(self):
        """Initialize a global tracer provider"""
        if self._provider is None:
            self._provider = TracerProvider()
            trace.set_tracer_provider(self._provider)
    
    def setup_test(self, service_name):
        """
        Setup for a specific test
        
        Args:
            service_name: Name of the service for this test
            
        Returns:
            tracer: Tracer for the test
            memory_exporter: In-memory exporter for validation
            processors: List of span processors that need cleanup
        """
        # Create resource with service name
        resource = Resource(attributes={"service.name": service_name})
        
        # Use InMemorySpanExporter for validation
        memory_exporter = InMemorySpanExporter()
        memory_processor = SimpleSpanProcessor(memory_exporter)
        
        processors = [memory_processor]
        provider = trace.get_tracer_provider()
        provider.add_span_processor(memory_processor)
        
        # Optionally send to OTLP for visualization
        if self.enable_otlp:
            otlp_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint, insecure=True)
            otlp_processor = BatchSpanProcessor(otlp_exporter)
            provider.add_span_processor(otlp_processor)
            processors.append(otlp_processor)
        
        logger.info(f"Set up test environment for service: {service_name}")
        # Return a test-specific tracer
        return trace.get_tracer(f"{service_name}-tracer"), memory_exporter, processors
    
    def cleanup_test(self, processors):
        """
        Clean up after a test
        
        Args:
            processors: List of processors to shutdown
        """
        # Force flush any pending spans
        provider = trace.get_tracer_provider()
        provider.force_flush()
        
        # Shutdown processors
        for processor in processors:
            processor.shutdown()
        
        # Small delay to ensure everything is processed
        time.sleep(0.5)
        logger.info("Test cleanup completed")


class GenAISpanValidator:
    """
    Utility class for validating GenAI spans against semantic conventions
    
    This class provides static methods for validating spans, events, and
    hierarchical relationships according to GenAI semantic conventions.
    """
    
    REQUIRED_ATTRIBUTES = {
        "all": ["gen_ai.system"],
        "chat": ["gen_ai.request.model"],
        "text_completion": ["gen_ai.request.model"],
        "execute_tool": ["gen_ai.tool.name"],
        "agent": ["gen_ai.agent.name"],
    }
    
    @staticmethod
    def verify_genai_span_attributes(span, expected_attributes):
        """
        Verify GenAI span has required attributes according to semantic conventions
        
        Args:
            span: The span to validate
            expected_attributes: Dict of expected attribute key-values
            
        Returns:
            bool: True if validation passes, raises AssertionError otherwise
        """
        operation_name = span.attributes.get("gen_ai.operation.name")
        
        # Check global required attributes
        for attr in GenAISpanValidator.REQUIRED_ATTRIBUTES["all"]:
            assert attr in span.attributes, f"Missing required attribute: {attr}"
        
        # Check operation-specific required attributes
        if operation_name and operation_name in GenAISpanValidator.REQUIRED_ATTRIBUTES:
            for attr in GenAISpanValidator.REQUIRED_ATTRIBUTES[operation_name]:
                assert attr in span.attributes, f"Missing required attribute for {operation_name}: {attr}"
        
        # Check expected attributes are present with correct values
        for key, expected_value in expected_attributes.items():
            assert key in span.attributes, f"Missing expected attribute: {key}"
            assert span.attributes[key] == expected_value, \
                f"Attribute {key} value mismatch: expected {expected_value}, got {span.attributes[key]}"
        
        return True
    
    @staticmethod
    def verify_tool_span(spans, parent_span_id, tool_name=None):
        """
        Verify a tool execution span exists and has correct attributes
        
        Args:
            spans: List of spans to search
            parent_span_id: Expected parent span ID
            tool_name: Optional tool name to match
            
        Returns:
            The tool span if found, raises AssertionError otherwise
        """
        # Find tool spans that are children of the parent
        tool_spans = [s for s in spans 
                     if hasattr(s.parent, "span_id") and s.parent.span_id == parent_span_id 
                     and s.attributes.get("gen_ai.operation.name") == "execute_tool"]
        
        assert len(tool_spans) > 0, "No tool spans found"
        
        if tool_name:
            # Find the specific tool by name
            tool_span = next((s for s in tool_spans 
                             if s.attributes.get("gen_ai.tool.name") == tool_name), None)
            assert tool_span is not None, f"Tool span for {tool_name} not found"
            return tool_span
        else:
            # Return the first tool span
            return tool_spans[0]
    
    @staticmethod
    def verify_events_on_span(span, expected_events):
        """
        Verify span has the expected events in sequence
        
        Args:
            span: The span to check
            expected_events: List of expected event dicts with name and optional attributes
            
        Returns:
            bool: True if validation passes, raises AssertionError otherwise
        """
        span_events = span.events
        assert len(span_events) >= len(expected_events), \
            f"Expected at least {len(expected_events)} events, got {len(span_events)}"
        
        for i, expected_event in enumerate(expected_events):
            assert span_events[i].name == expected_event["name"], \
                f"Event name mismatch at position {i}"
            
            if "attributes" in expected_event:
                for attr_key, attr_value in expected_event["attributes"].items():
                    assert attr_key in span_events[i].attributes, \
                        f"Missing attribute {attr_key} in event {i}"
                    assert span_events[i].attributes[attr_key] == attr_value, \
                        f"Event attribute value mismatch for {attr_key}: expected {attr_value}, got {span_events[i].attributes[attr_key]}"
        
        return True
    
    @staticmethod
    def verify_span_hierarchy(spans, root_span_name, expected_children):
        """
        Verify spans form the expected hierarchy
        
        Args:
            spans: List of spans to check
            root_span_name: Name of the root span
            expected_children: List of expected child span names
            
        Returns:
            tuple: (root_span, child_spans) if validation passes, raises AssertionError otherwise
        """
        # Find root span
        root_span = next((s for s in spans if s.name == root_span_name), None)
        assert root_span is not None, f"Root span '{root_span_name}' not found"
        
        # Find child spans
        child_spans = [s for s in spans if hasattr(s.parent, "span_id") and s.parent.span_id == root_span.context.span_id]
        child_names = [s.name for s in child_spans]
        
        # Verify we have the expected children
        for expected_child in expected_children:
            assert any(expected_child in name for name in child_names), \
                f"Expected child span '{expected_child}' missing"
        
        return root_span, child_spans
    
    @staticmethod
    def validate_semantic_conventions(span, conventions_type, schema_id=None):
        """
        Validate against specific GenAI semantic conventions
        
        Args:
            span: The span to validate
            conventions_type: Type of conventions to validate against ('span', 'event', 'metric')
            schema_id: ID of the schema to validate against (e.g., 'span.gen_ai.client')
            
        Returns:
            bool: True if validation passes, raises AssertionError otherwise
            
        Note:
            This is a placeholder method. For actual schema validation, 
            implement using semantic_validator.py or enable schema integration.
        """
        # For full schema validation, either:
        # 1. Load YAML schemas from OpenTelemetry specification repo
        # 2. Use semantic_validator.py and schema_integration_example.py
        
        logger.warning("Using placeholder schema validation. For full validation, implement schema loading.")
        return True
