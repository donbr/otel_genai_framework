# schema_integration.py
"""
OpenTelemetry GenAI Schema Integration

This module provides integration with OpenTelemetry GenAI SIG semantic conventions
for schema-based validation of spans, events, and metrics.

Usage:
    from schema_integration import SchemaValidator
    validator = SchemaValidator()
    validator.validate_span(span, "span.gen_ai.client")
"""

import os
import yaml
import logging
from urllib.request import urlretrieve
import json
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

class SchemaRegistry:
    """
    Registry for OpenTelemetry GenAI SIG semantic convention schemas
    
    Loads and provides access to schema definitions for spans, events, and metrics.
    """
    
    def __init__(self, schema_dir="./schemas"):
        """
        Initialize the schema registry
        
        Args:
            schema_dir: Directory containing schema YAML files
        """
        self.schema_dir = schema_dir
        self.schemas = {
            "spans": {},
            "events": {},
            "metrics": {},
            "registry": {},
        }
        self.loaded = False
    
    def ensure_schemas(self):
        """Ensure schema files are present, downloading if necessary"""
        if not os.path.exists(self.schema_dir):
            os.makedirs(self.schema_dir)
        
        schema_files = ["spans.yaml", "events.yaml", "metrics.yaml", "registry.yaml"]
        missing_files = [f for f in schema_files if not os.path.exists(os.path.join(self.schema_dir, f))]
        
        if missing_files:
            logger.info(f"Missing schema files: {missing_files}, downloading...")
            self.download_schemas()
    
    def download_schemas(self):
        """Download the latest schema files from OpenTelemetry GitHub"""
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
            local_path = os.path.join(self.schema_dir, os.path.basename(schema_file))
            
            try:
                logger.info(f"Downloading schema: {url}")
                urlretrieve(url, local_path)
                logger.info(f"Downloaded to: {local_path}")
            except Exception as e:
                logger.error(f"Failed to download schema {schema_file}: {str(e)}")
    
    def load_schemas(self):
        """Load schema files into memory"""
        if self.loaded:
            return
        
        self.ensure_schemas()
        
        try:
            # Load spans schema
            with open(os.path.join(self.schema_dir, "spans.yaml"), 'r') as f:
                spans_data = yaml.safe_load(f)
                for group in spans_data.get('groups', []):
                    if group.get('type') == 'span':
                        self.schemas['spans'][group.get('id')] = group
            
            # Load events schema
            with open(os.path.join(self.schema_dir, "events.yaml"), 'r') as f:
                events_data = yaml.safe_load(f)
                for group in events_data.get('groups', []):
                    if group.get('type') == 'event':
                        self.schemas['events'][group.get('id')] = group
            
            # Load metrics schema
            with open(os.path.join(self.schema_dir, "metrics.yaml"), 'r') as f:
                metrics_data = yaml.safe_load(f)
                for group in metrics_data.get('groups', []):
                    if group.get('type') == 'metric':
                        self.schemas['metrics'][group.get('id')] = group
            
            # Load registry schema
            with open(os.path.join(self.schema_dir, "registry.yaml"), 'r') as f:
                registry_data = yaml.safe_load(f)
                for group in registry_data.get('groups', []):
                    self.schemas['registry'][group.get('id')] = group
            
            self.loaded = True
            logger.info(f"Loaded {len(self.schemas['spans'])} span schemas, "
                       f"{len(self.schemas['events'])} event schemas, and "
                       f"{len(self.schemas['metrics'])} metric schemas")
        
        except Exception as e:
            logger.error(f"Error loading schemas: {str(e)}")
    
    def get_span_schema(self, schema_id: str) -> Optional[Dict]:
        """
        Get span schema by ID
        
        Args:
            schema_id: ID of the schema (e.g., 'span.gen_ai.client')
            
        Returns:
            Dict containing the schema definition, or None if not found
        """
        if not self.loaded:
            self.load_schemas()
        
        return self.schemas['spans'].get(schema_id)
    
    def get_event_schema(self, schema_id: str) -> Optional[Dict]:
        """
        Get event schema by ID
        
        Args:
            schema_id: ID of the schema (e.g., 'event.gen_ai.user.message')
            
        Returns:
            Dict containing the schema definition, or None if not found
        """
        if not self.loaded:
            self.load_schemas()
        
        return self.schemas['events'].get(schema_id)
    
    def get_metric_schema(self, schema_id: str) -> Optional[Dict]:
        """
        Get metric schema by ID
        
        Args:
            schema_id: ID of the schema (e.g., 'metric.gen_ai.client.token.usage')
            
        Returns:
            Dict containing the schema definition, or None if not found
        """
        if not self.loaded:
            self.load_schemas()
        
        return self.schemas['metrics'].get(schema_id)
    
    def list_available_schemas(self) -> Dict[str, List[str]]:
        """
        List all available schemas
        
        Returns:
            Dict with schema types as keys and lists of schema IDs as values
        """
        if not self.loaded:
            self.load_schemas()
        
        return {
            'spans': list(self.schemas['spans'].keys()),
            'events': list(self.schemas['events'].keys()),
            'metrics': list(self.schemas['metrics'].keys())
        }


class SchemaValidator:
    """
    Validator for OpenTelemetry telemetry against GenAI SIG schemas
    
    Validates spans, events, and metrics against their schema definitions.
    """
    
    def __init__(self, schema_dir="./schemas"):
        """
        Initialize the schema validator
        
        Args:
            schema_dir: Directory containing schema YAML files
        """
        self.registry = SchemaRegistry(schema_dir)
    
    def validate_span(self, span, schema_id: str) -> List[str]:
        """
        Validate a span against its schema
        
        Args:
            span: The span to validate
            schema_id: ID of the schema to validate against (e.g., 'span.gen_ai.client')
            
        Returns:
            List of validation error messages, empty if validation passed
        """
        schema = self.registry.get_span_schema(schema_id)
        if not schema:
            return [f"Schema not found: {schema_id}"]
        
        errors = []
        
        # Validate required attributes
        attributes_section = schema.get('attributes', [])
        for attr_entry in attributes_section:
            attr_ref = attr_entry.get('ref')
            if attr_ref:
                # This is a reference to a registry attribute
                # Check requirement level
                req_level = attr_entry.get('requirement_level', 'optional')
                if req_level == 'required' and attr_ref not in span.attributes:
                    errors.append(f"Missing required attribute: {attr_ref}")
                # Could add more complex validation for conditional requirements
        
        # Add more validation as needed for specific schema types
        
        return errors
    
    def validate_event(self, event, schema_id: str) -> List[str]:
        """
        Validate an event against its schema
        
        Args:
            event: The event to validate
            schema_id: ID of the schema to validate against (e.g., 'event.gen_ai.user.message')
            
        Returns:
            List of validation error messages, empty if validation passed
        """
        schema = self.registry.get_event_schema(schema_id)
        if not schema:
            return [f"Schema not found: {schema_id}"]
        
        errors = []
        
        # Validate event name
        expected_name = schema.get('name', '')
        if expected_name and event.name != expected_name:
            errors.append(f"Event name mismatch: expected '{expected_name}', got '{event.name}'")
        
        # Validate required attributes from body fields
        body = schema.get('body', {})
        fields = body.get('fields', [])
        
        for field in fields:
            field_id = field.get('id')
            req_level = field.get('requirement_level', 'optional')
            
            if req_level == 'required' and field_id not in event.attributes:
                errors.append(f"Missing required event attribute: {field_id}")
        
        return errors
    
    def validate_metric(self, metric_data, schema_id: str) -> List[str]:
        """
        Validate metric data against its schema
        
        Args:
            metric_data: Dict containing metric data
            schema_id: ID of the schema to validate against (e.g., 'metric.gen_ai.client.token.usage')
            
        Returns:
            List of validation error messages, empty if validation passed
        """
        schema = self.registry.get_metric_schema(schema_id)
        if not schema:
            return [f"Schema not found: {schema_id}"]
        
        errors = []
        
        # Validate metric name
        expected_name = schema.get('metric_name', '')
        if expected_name and metric_data.get('name') != expected_name:
            errors.append(f"Metric name mismatch: expected '{expected_name}', got '{metric_data.get('name')}'")
        
        # Validate attributes
        attributes_section = schema.get('attributes', [])
        for attr_entry in attributes_section:
            attr_ref = attr_entry.get('ref')
            if attr_ref:
                # This is a reference to a registry attribute
                # Check requirement level
                req_level = attr_entry.get('requirement_level', 'optional')
                if req_level == 'required' and attr_ref not in metric_data.get('attributes', {}):
                    errors.append(f"Missing required metric attribute: {attr_ref}")
        
        return errors
    
    def validate_scenario(self, scenario: Dict, generated_spans: List, generated_metrics: List) -> Dict:
        """
        Validate generated telemetry against a scenario definition
        
        Args:
            scenario: Scenario definition
            generated_spans: List of generated spans
            generated_metrics: List of generated metrics
            
        Returns:
            Dict containing validation results
        """
        results = {
            'span_validations': [],
            'metric_validations': [],
            'schema_validations': [],
            'all_passed': True
        }
        
        # Validate spans
        for span_def in scenario.get('spans', []):
            span_name = span_def.get('name', '')
            target_span = next((s for s in generated_spans if s.name == span_name), None)
            
            if not target_span:
                results['span_validations'].append({
                    'span': span_name,
                    'passed': False,
                    'errors': [f"Span not found: {span_name}"]
                })
                results['all_passed'] = False
                continue
            
            # Validate span attributes
            errors = []
            for attr_key, attr_value in span_def.get('expected_attributes', {}).items():
                if attr_key not in target_span.attributes:
                    errors.append(f"Missing attribute: {attr_key}")
                elif str(target_span.attributes[attr_key]) != str(attr_value):
                    errors.append(f"Attribute '{attr_key}' value mismatch: expected '{attr_value}', got '{target_span.attributes[attr_key]}'")
            
            # Add schema validation if specified
            schema_validation = scenario.get('schema_validation', {})
            for schema_id in schema_validation.get('span_schemas', []):
                if schema_id.startswith('span.'):
                    schema_errors = self.validate_span(target_span, schema_id)
                    errors.extend(schema_errors)
            
            results['span_validations'].append({
                'span': span_name,
                'passed': len(errors) == 0,
                'errors': errors
            })
            
            if len(errors) > 0:
                results['all_passed'] = False
        
        # Additional validations for metrics etc.
        
        return results


def enhance_validator_with_schema(validator_class):
    """
    Enhance the GenAISpanValidator with schema-based validation
    
    Args:
        validator_class: The GenAISpanValidator class to enhance
        
    Returns:
        Enhanced validator class
    """
    # Create schema validator
    schema_validator = SchemaValidator()
    
    # Store original method
    original_verify = validator_class.verify_genai_span_attributes
    
    @staticmethod
    def enhanced_verify(span, expected_attributes, schema_id=None):
        """Enhanced verification with schema validation"""
        # First, perform original verification
        original_verify(span, expected_attributes)
        
        # If schema_id is provided, also validate against schema
        if schema_id:
            errors = schema_validator.validate_span(span, schema_id)
            if errors:
                error_msg = "Schema validation errors: " + ", ".join(errors)
                assert not errors, error_msg
                
        return True
    
    # Replace the method
    validator_class.verify_genai_span_attributes = enhanced_verify
    
    # Add a method for event schema validation
    @staticmethod
    def verify_event_schema(event, schema_id):
        """Verify an event against a schema"""
        errors = schema_validator.validate_event(event, schema_id)
        if errors:
            error_msg = "Event schema validation errors: " + ", ".join(errors)
            assert not errors, error_msg
        return True
    
    validator_class.verify_event_schema = verify_event_schema
    
    # Add a method for metric schema validation
    @staticmethod
    def verify_metric_schema(metric_data, schema_id):
        """Verify metric data against a schema"""
        errors = schema_validator.validate_metric(metric_data, schema_id)
        if errors:
            error_msg = "Metric schema validation errors: " + ", ".join(errors)
            assert not errors, error_msg
        return True
    
    validator_class.verify_metric_schema = verify_metric_schema
    
    return validator_class


if __name__ == "__main__":
    # Simple self-test
    logging.basicConfig(level=logging.INFO)
    registry = SchemaRegistry()
    registry.load_schemas()
    
    # List available schemas
    schemas = registry.list_available_schemas()
    print("Available schemas:")
    for type_name, schema_ids in schemas.items():
        print(f"{type_name}: {len(schema_ids)}")
        for schema_id in schema_ids:
            print(f"  - {schema_id}")
