# semantic_validator.py
"""
GenAI Semantic Convention Validator

This module provides utilities for validating spans, events, and metrics
against the official GenAI semantic conventions defined in YAML schema files.

Version: 0.1.0
"""

import os
import yaml
import logging
from typing import Dict, List, Any, Optional, Set, Union

logger = logging.getLogger(__name__)

class GenAISchema:
    """
    Represents the GenAI semantic convention schema loaded from YAML files
    """
    
    def __init__(self, schema_directory: Optional[str] = None):
        """
        Initialize the schema from YAML files
        
        Args:
            schema_directory: Directory containing schema YAML files (spans.yaml, events.yaml, etc.)
                              If None, attempts to use built-in schemas
        """
        self.spans_schema = {}
        self.events_schema = {}
        self.metrics_schema = {}
        self.attributes_registry = {}
        
        # Use built-in schema if no directory provided
        if schema_directory is None:
            # Try to load from package data
            schema_directory = os.path.join(os.path.dirname(__file__), "schemas")
        
        self._load_schemas(schema_directory)
    
    def _load_schemas(self, directory: str) -> None:
        """
        Load schema files from the specified directory
        
        Args:
            directory: Directory containing schema YAML files
        """
        schema_files = {
            "spans.yaml": self.spans_schema,
            "events.yaml": self.events_schema,
            "metrics.yaml": self.metrics_schema,
            "registry.yaml": self.attributes_registry
        }
        
        for filename, schema_dict in schema_files.items():
            try:
                filepath = os.path.join(directory, filename)
                if os.path.exists(filepath):
                    with open(filepath, 'r') as f:
                        loaded_schema = yaml.safe_load(f)
                        if loaded_schema:
                            # Extract groups from schema
                            if 'groups' in loaded_schema:
                                for group in loaded_schema['groups']:
                                    schema_dict[group.get('id')] = group
                            
                    logger.info(f"Loaded schema from {filepath}")
                else:
                    logger.warning(f"Schema file not found: {filepath}")
            except Exception as e:
                logger.error(f"Failed to load schema from {filename}: {str(e)}")
    
    def get_span_schema(self, span_type: str) -> Dict:
        """
        Get schema for a specific span type
        
        Args:
            span_type: Type of span (e.g., span.gen_ai.client)
            
        Returns:
            Dictionary containing the span schema or empty dict if not found
        """
        return self.spans_schema.get(span_type, {})
    
    def get_event_schema(self, event_type: str) -> Dict:
        """
        Get schema for a specific event type
        
        Args:
            event_type: Type of event (e.g., event.gen_ai.user.message)
            
        Returns:
            Dictionary containing the event schema or empty dict if not found
        """
        return self.events_schema.get(event_type, {})
    
    def get_required_attributes(self, schema_type: str, schema_id: str) -> Set[str]:
        """
        Get required attributes for a schema entity
        
        Args:
            schema_type: Type of schema ("span", "event", "metric")
            schema_id: ID of the schema entity
            
        Returns:
            Set of required attribute names
        """
        schema_dict = {
            "span": self.spans_schema,
            "event": self.events_schema,
            "metric": self.metrics_schema
        }.get(schema_type, {})
        
        schema = schema_dict.get(schema_id, {})
        required_attrs = set()
        
        # Extract required attributes from schema
        if 'attributes' in schema:
            for attr in schema['attributes']:
                if 'requirement_level' in attr and attr['requirement_level'] == 'required':
                    if 'ref' in attr:
                        required_attrs.add(attr['ref'])
                    elif 'id' in attr:
                        required_attrs.add(attr['id'])
        
        return required_attrs
    
    def get_conditionally_required_attributes(self, schema_type: str, schema_id: str) -> Dict[str, str]:
        """
        Get conditionally required attributes for a schema entity
        
        Args:
            schema_type: Type of schema ("span", "event", "metric")
            schema_id: ID of the schema entity
            
        Returns:
            Dictionary mapping attribute names to their conditions
        """
        schema_dict = {
            "span": self.spans_schema,
            "event": self.events_schema,
            "metric": self.metrics_schema
        }.get(schema_type, {})
        
        schema = schema_dict.get(schema_id, {})
        conditional_attrs = {}
        
        # Extract conditionally required attributes from schema
        if 'attributes' in schema:
            for attr in schema['attributes']:
                if 'requirement_level' in attr and isinstance(attr['requirement_level'], dict):
                    if 'conditionally_required' in attr['requirement_level']:
                        attr_name = attr.get('ref', attr.get('id', ''))
                        condition = attr['requirement_level']['conditionally_required']
                        conditional_attrs[attr_name] = condition
        
        return conditional_attrs


class SpanSchemaValidator:
    """
    Validator for checking spans against GenAI semantic conventions
    """
    
    def __init__(self, schema: GenAISchema):
        """
        Initialize the validator with a schema
        
        Args:
            schema: GenAISchema instance containing loaded conventions
        """
        self.schema = schema
    
    def validate_span(self, span: Any, expected_span_type: str) -> List[str]:
        """
        Validate a span against its expected schema
        
        Args:
            span: The span to validate
            expected_span_type: Expected span type (e.g., span.gen_ai.client)
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Get schema for this span type
        span_schema = self.schema.get_span_schema(expected_span_type)
        if not span_schema:
            errors.append(f"No schema found for span type {expected_span_type}")
            return errors
        
        # Check required attributes
        required_attrs = self.schema.get_required_attributes("span", expected_span_type)
        for attr in required_attrs:
            if attr not in span.attributes:
                errors.append(f"Missing required attribute: {attr}")
        
        # Check conditionally required attributes
        conditional_attrs = self.schema.get_conditionally_required_attributes("span", expected_span_type)
        for attr, condition in conditional_attrs.items():
            # Simple condition checking - this would need to be more sophisticated
            # for complex conditions in real implementation
            if "if available" in condition.lower():
                # Skip this check - we can't determine if available
                continue
            
            # Check for attribute presence
            if attr not in span.attributes:
                errors.append(f"Missing conditionally required attribute: {attr} ({condition})")
        
        # Additional validation could include:
        # - Type checking for attribute values
        # - Validating against expected enums
        # - Cross-attribute validation
        
        return errors
    
    def validate_event(self, event: Any, expected_event_type: str) -> List[str]:
        """
        Validate an event against its expected schema
        
        Args:
            event: The event to validate
            expected_event_type: Expected event type (e.g., event.gen_ai.user.message)
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Get schema for this event type
        event_schema = self.schema.get_event_schema(expected_event_type)
        if not event_schema:
            errors.append(f"No schema found for event type {expected_event_type}")
            return errors
        
        # Check required attributes
        required_attrs = self.schema.get_required_attributes("event", expected_event_type)
        for attr in required_attrs:
            if attr not in event.attributes:
                errors.append(f"Missing required attribute: {attr}")
        
        # Check conditionally required attributes (similar to spans)
        conditional_attrs = self.schema.get_conditionally_required_attributes("event", expected_event_type)
        for attr, condition in conditional_attrs.items():
            if "if available" in condition.lower():
                continue
            
            if attr not in event.attributes:
                errors.append(f"Missing conditionally required attribute: {attr} ({condition})")
        
        return errors
    
    def validate_attribute_values(self, attributes: Dict[str, Any]) -> List[str]:
        """
        Validate attribute values against their expected types and enums
        
        Args:
            attributes: Dictionary of attribute name-value pairs
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # For each attribute, check type and enum constraints
        for attr_name, attr_value in attributes.items():
            # This would need to reference the attribute registry to validate values
            # against their expected types and enum values
            pass
        
        return errors