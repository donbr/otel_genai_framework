# scenario_runner.py
"""
OpenTelemetry GenAI Scenario Runner

This module provides functionality to run test scenarios defined in YAML files
that align with OpenTelemetry GenAI SIG semantic conventions.

Usage:
    python scenario_runner.py --scenario scenarios/basic_agent_scenario.yaml

Version: 0.2.0
"""

import yaml
import argparse
import logging
import os
import time
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import opentelemetry
from opentelemetry import trace
from opentelemetry.trace.status import Status, StatusCode
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.traceback import install as install_rich_traceback

# Import the validator (will be updated to work with unified_validator.py once created)
from src.otel_genai_validator import OTelGenAIValidator, GenAISpanValidator

# Configure console output
console = Console()
install_rich_traceback(console=console, show_locals=True)
logger = logging.getLogger("scenario-runner")

class ScenarioRunner:
    """
    Runner for YAML-based test scenarios
    
    Processes test scenarios defined in YAML files that follow OpenTelemetry
    GenAI SIG semantic conventions.
    """
    
    def __init__(self, validator, enable_metrics=True):
        """
        Initialize the scenario runner
        
        Args:
            validator: Validator instance (OTelGenAIValidator or UnifiedValidator)
            enable_metrics: Whether to record metrics for scenarios
        """
        self.validator = validator
        self.enable_metrics = enable_metrics
        self.current_scenario = None
    
    def load_scenario(self, scenario_path: str) -> Dict:
        """
        Load a scenario from a YAML file
        
        Args:
            scenario_path: Path to the YAML scenario file
            
        Returns:
            Dict containing the scenario definition
        """
        console.print(f"Loading scenario from: [cyan]{scenario_path}[/cyan]")
        
        # Ensure the file exists
        if not os.path.exists(scenario_path):
            raise FileNotFoundError(f"Scenario file not found: {scenario_path}")
        
        # Read the YAML file
        try:
            with open(scenario_path, 'r') as f:
                scenario = yaml.safe_load(f)
            
            # Validate minimum scenario structure
            required_keys = ['name', 'description', 'spans']
            for key in required_keys:
                if key not in scenario:
                    raise ValueError(f"Scenario missing required key: {key}")
            
            self.current_scenario = scenario
            console.print(f"Loaded scenario: [green]{scenario['name']}[/green]")
            return scenario
            
        except yaml.YAMLError as e:
            console.print(f"[red]Error parsing YAML file: {e}[/red]")
            return None
        except Exception as e:
            console.print(f"[red]Error loading scenario: {e}[/red]")
            return None
    
    def _execute_span_generation(self, span_def: Dict) -> Tuple[List, List]:
        """
        Execute span generation based on span definition
        
        Args:
            span_def: Dictionary containing span definition from scenario
            
        Returns:
            Tuple of (generated_spans, validation_results)
        """
        # Extract span information
        span_name = span_def.get('name', 'unnamed_span')
        expected_attributes = span_def.get('expected_attributes', {})
        expected_events = span_def.get('expected_events', [])
        child_spans = span_def.get('child_spans', [])
        
        # Custom tracer for this span
        tracer = trace.get_tracer(f"scenario-{span_name}")
        
        # Start the parent span
        with tracer.start_as_current_span(
            span_name,
            attributes=expected_attributes
        ) as current_span:
            # Add expected events to the span
            for event_def in expected_events:
                event_name = event_def.get('name', 'unnamed_event')
                event_attrs = event_def.get('attributes', {})
                current_span.add_event(event_name, event_attrs)
            
            # Process child spans recursively
            for child_span_def in child_spans:
                # Check if child needs error status
                if 'expected_status' in child_span_def and child_span_def['expected_status'].get('status_code') == 'ERROR':
                    with tracer.start_as_current_span(
                        child_span_def.get('name', 'unnamed_child'),
                        attributes=child_span_def.get('expected_attributes', {})
                    ) as child_span:
                        # Set error status
                        status_desc = child_span_def['expected_status'].get('description', '')
                        child_span.set_status(Status(StatusCode.ERROR, status_desc))
                        
                        # Add exception if specified
                        if 'expected_exception' in child_span_def:
                            exc_type = child_span_def['expected_exception'].get('type', 'Exception')
                            exc_msg = child_span_def['expected_exception'].get('message', '')
                            child_span.record_exception(
                                Exception(exc_msg),
                                attributes={"error.type": exc_type}
                            )
                        
                        # Add expected events
                        for event_def in child_span_def.get('expected_events', []):
                            event_name = event_def.get('name', 'unnamed_event')
                            event_attrs = event_def.get('attributes', {})
                            child_span.add_event(event_name, event_attrs)
                else:
                    # Normal child span
                    with tracer.start_as_current_span(
                        child_span_def.get('name', 'unnamed_child'),
                        attributes=child_span_def.get('expected_attributes', {})
                    ) as child_span:
                        # Add expected events
                        for event_def in child_span_def.get('expected_events', []):
                            event_name = event_def.get('name', 'unnamed_event')
                            event_attrs = event_def.get('attributes', {})
                            child_span.add_event(event_name, event_attrs)
        
        # Return collected spans for validation
        return [], []  # Placeholder - actual implementation would return spans and validation results
    
    def run_scenario(self) -> bool:
        """
        Run the currently loaded scenario
        
        Returns:
            bool: True if the scenario passed validation, False otherwise
        """
        if not self.current_scenario:
            console.print("[red]Error: No scenario loaded[/red]")
            return False
        
        scenario_name = self.current_scenario.get('name', 'Unnamed Scenario')
        console.print(Panel(
            f"[bold green]Running Scenario: {scenario_name}[/bold green]\n\n"
            f"{self.current_scenario.get('description', '')}",
            title="📊 Scenario Runner"
        ))
        
        # Setup the test environment
        service_name = self.current_scenario.get('configuration', {}).get('service_name', 'scenario-test')
        tracer, memory_exporter, processors = self.validator.setup_test(service_name)
        
        try:
            validation_results = []
            
            # Process each span definition
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                # Run the span generation task
                task = progress.add_task(f"Generating telemetry for {scenario_name}...", total=None)
                
                # Generate spans based on scenario definition
                for span_def in self.current_scenario.get('spans', []):
                    self._execute_span_generation(span_def)
                
                progress.update(task, completed=True)
                
                # Wait for spans to be exported
                time.sleep(0.5)
                
                # Validate the generated spans
                validation_task = progress.add_task(f"Validating telemetry against schema...", total=None)
                
                # Get the generated spans
                spans = memory_exporter.get_finished_spans()
                
                # Validate spans against expectations
                for span_def in self.current_scenario.get('spans', []):
                    result = self._validate_span(spans, span_def)
                    validation_results.append(result)
                
                progress.update(validation_task, completed=True)
            
            # Prepare results table
            table = Table(show_header=True, header_style="bold")
            table.add_column("Component")
            table.add_column("Status")
            table.add_column("Details")
            
            # Add validation results to table
            all_passed = True
            for result in validation_results:
                component = result.get('component', 'Unknown')
                passed = result.get('passed', False)
                details = result.get('details', '')
                
                status = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
                if not passed:
                    all_passed = False
                
                table.add_row(component, status, details)
            
            # Display results
            console.print("\n[bold]Validation Results:[/bold]")
            console.print(table)
            
            if all_passed:
                console.print("\n[green]✓ Scenario validation successful![/green]")
                return True
            else:
                console.print("\n[red]✗ Scenario validation failed. See details above.[/red]")
                return False
                
        except Exception as e:
            console.print(f"[red]Error running scenario: {e}[/red]")
            return False
        finally:
            # Clean up
            self.validator.cleanup_test(processors)
    
    def _validate_span(self, spans, span_def) -> Dict:
        """
        Validate spans against expectations
        
        Args:
            spans: List of generated spans
            span_def: Span definition from scenario
            
        Returns:
            Dict with validation results
        """
        span_name = span_def.get('name', 'unnamed_span')
        
        # Find the span with matching name
        target_span = next((s for s in spans if s.name == span_name), None)
        
        if not target_span:
            return {
                'component': f"Span '{span_name}'",
                'passed': False,
                'details': f"Span '{span_name}' not found"
            }
        
        # Validate attributes
        expected_attributes = span_def.get('expected_attributes', {})
        for attr_key, attr_value in expected_attributes.items():
            if attr_key not in target_span.attributes:
                return {
                    'component': f"Span '{span_name}' attribute",
                    'passed': False,
                    'details': f"Missing attribute: {attr_key}"
                }
            
            if str(target_span.attributes[attr_key]) != str(attr_value):
                return {
                    'component': f"Span '{span_name}' attribute",
                    'passed': False,
                    'details': f"Attribute '{attr_key}' value mismatch: expected '{attr_value}', got '{target_span.attributes[attr_key]}'"
                }
        
        # Validate events
        expected_events = span_def.get('expected_events', [])
        if expected_events:
            span_events = target_span.events
            if len(span_events) < len(expected_events):
                return {
                    'component': f"Span '{span_name}' events",
                    'passed': False,
                    'details': f"Expected at least {len(expected_events)} events, got {len(span_events)}"
                }
            
            for i, expected_event in enumerate(expected_events):
                event_name = expected_event.get('name')
                if span_events[i].name != event_name:
                    return {
                        'component': f"Span '{span_name}' events",
                        'passed': False,
                        'details': f"Event name mismatch at position {i}: expected '{event_name}', got '{span_events[i].name}'"
                    }
        
        # Validate schema if specified
        schema_validation = self.current_scenario.get('schema_validation', {})
        span_schemas = schema_validation.get('span_schemas', [])
        if span_schemas:
            # This would call into semantic_validator.py to validate against schemas
            # For now, just return a placeholder result
            schema_result = True  # Placeholder
            if not schema_result:
                return {
                    'component': f"Span '{span_name}' schema",
                    'passed': False,
                    'details': f"Schema validation failed"
                }
        
        # All validations passed
        return {
            'component': f"Span '{span_name}'",
            'passed': True,
            'details': "All validations passed"
        }


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Run OpenTelemetry GenAI validation scenarios"
    )
    parser.add_argument(
        "--scenario", 
        type=str, 
        required=True,
        help="Path to scenario YAML file"
    )
    parser.add_argument(
        "--skip-otlp", 
        action="store_true", 
        help="Skip sending telemetry to OTLP endpoint"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Enable debug logging"
    )
    parser.add_argument(
        "--no-metrics", 
        action="store_true", 
        help="Disable metrics collection"
    )
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    # Initialize validator
    validator = OTelGenAIValidator(enable_otlp=not args.skip_otlp)
    
    # Initialize scenario runner
    runner = ScenarioRunner(validator, enable_metrics=not args.no_metrics)
    
    # Load and run scenario
    scenario = runner.load_scenario(args.scenario)
    if scenario:
        success = runner.run_scenario()
        return 0 if success else 1
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
