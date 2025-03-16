# validation_suite.py
"""
OpenTelemetry GenAI Validation Suite

This script runs the validation test suite for OpenTelemetry instrumentation
of GenAI systems against the semantic conventions.

Usage:
    python validation_suite.py [--skip-otlp] [--debug] [--test TEST]

Options:
    --skip-otlp    Skip sending telemetry to OTLP endpoint
    --debug        Enable debug logging
    --test TEST    Run only the specified test (e.g., basic, tool, reasoning, error)

Version: 0.1.0
"""

import argparse
import sys
import time
import logging
import importlib
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.traceback import install as install_rich_traceback
from schema_integration import enhance_validator_with_schema
from otel_genai_validator import GenAISpanValidator

# Configure console
console = Console()
install_rich_traceback(console=console, show_locals=True)
enhance_validator_with_schema(GenAISpanValidator)

# Test mapping
TEST_SCENARIOS = {
    "basic": ("Basic Agent Tracing", "run_basic_agent_test"),
    "reasoning": ("Multi-step Reasoning Flow", "run_reasoning_flow_test"),
    "tool": ("Tool Usage", "run_tool_usage_test"),
    "error": ("Error Handling", "run_error_handling_test"),
}

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Validate OpenTelemetry instrumentation for GenAI systems"
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
        "--test",
        type=str,
        choices=["basic", "tool", "reasoning", "error", "all"],
        default="all",
        help="Run only the specified test"
    )
    return parser.parse_args()

def check_dependencies():
    """Check that all required dependencies are installed"""
    # Map package names to their actual import paths
    package_imports = {
        "opentelemetry-api": "opentelemetry",  # Just the base module is enough
        "opentelemetry-sdk": "opentelemetry.sdk",  
        "opentelemetry-exporter-otlp-proto-grpc": "opentelemetry.exporter.otlp.proto.grpc",
        "rich": "rich"
    }
    
    missing_packages = []
    for package, import_path in package_imports.items():
        try:
            importlib.import_module(import_path)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        console.print(Panel(
            f"[bold red]Missing required packages:[/bold red] {', '.join(missing_packages)}\n\n"
            f"Install with: [bold]pip install {' '.join(missing_packages)}[/bold]",
            title="Dependency Error"
        ))
        return False
    
    return True

def run_test(test_name, test_func_name, validator):
    """
    Run a single test scenario
    
    Args:
        test_name: Display name for the test
        test_func_name: Name of the function to call
        validator: OTelGenAIValidator instance
        
    Returns:
        tuple: (success, error_message)
    """
    from genai_test_scenarios import (
        run_basic_agent_test,
        run_reasoning_flow_test,
        run_tool_usage_test,
        run_error_handling_test,
    )
    
    # Map function names to actual functions
    test_funcs = {
        "run_basic_agent_test": run_basic_agent_test,
        "run_reasoning_flow_test": run_reasoning_flow_test,
        "run_tool_usage_test": run_tool_usage_test,
        "run_error_handling_test": run_error_handling_test,
    }
    
    test_func = test_funcs.get(test_func_name)
    if not test_func:
        return False, f"Unknown test function: {test_func_name}"
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"Running {test_name}...", total=None)
        
        try:
            test_func(validator)
            progress.update(task, completed=True)
            return True, None
        except AssertionError as e:
            progress.update(task, completed=True)
            return False, str(e)
        except Exception as e:
            progress.update(task, completed=True)
            return False, f"{type(e).__name__}: {str(e)}"

def run_validation_suite():
    """Run the full validation suite or specified test"""
    args = parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    logger = logging.getLogger("validation-suite")
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Import after dependency check
    from otel_genai_validator import OTelGenAIValidator
    
    # Print header
    console.print(Panel(
        "[bold green]OpenTelemetry GenAI Validation Suite[/bold green]\n\n"
        f"Testing semantic conventions compliance\n"
        f"Run date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        title="🔍 Validation Suite"
    ))
    
    # Initialize validator
    validator = OTelGenAIValidator(enable_otlp=not args.skip_otlp)
    
    # Determine which tests to run
    test_to_run = args.test
    tests = []
    if test_to_run == "all":
        tests = list(TEST_SCENARIOS.items())
    else:
        if test_to_run in TEST_SCENARIOS:
            tests = [(test_to_run, TEST_SCENARIOS[test_to_run])]
        else:
            console.print(f"[bold red]Unknown test: {test_to_run}[/bold red]")
            return 1
    
    # Run tests and collect results
    results = []
    for test_id, (test_name, test_func) in tests:
        console.rule(f"[bold]Test: {test_name}[/bold]")
        success, error = run_test(test_name, test_func, validator)
        status = "[bold green]PASS[/bold green]" if success else "[bold red]FAIL[/bold red]"
        results.append((test_id, test_name, status, error))
        
        # Print immediate results
        if success:
            console.print(f"[green]✓ {test_name} test passed[/green]")
        else:
            console.print(f"[red]✗ {test_name} test failed: {error}[/red]")
        
        # Small delay between tests
        time.sleep(0.5)
    
    # Print summary table
    console.rule("[bold]Test Results Summary[/bold]")
    
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim")
    table.add_column("Test")
    table.add_column("Result")
    table.add_column("Details")
    
    for test_id, test_name, status, error in results:
        details = f"[red]{error}[/red]" if error else ""
        table.add_row(test_id, test_name, status, details)
    
    console.print(table)
    
    # Final status
    all_passed = all(result[2] == "[bold green]PASS[/bold green]" for result in results)
    if all_passed:
        console.print("\n[bold green]✓ All validation tests passed![/bold green]")
        return 0
    else:
        console.print("\n[bold red]✗ Some validation tests failed. See details above.[/bold red]")
        return 1

if __name__ == "__main__":
    sys.exit(run_validation_suite())