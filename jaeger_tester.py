# jaeger_tester.py - Updated for March 2025
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
import time
import json
import logging
from opentelemetry.trace.status import Status, StatusCode

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jaeger-tester")

def setup_otlp_telemetry():
    """Set up telemetry with OTLP exporters for Jaeger"""
    # Create a resource with relevant service info
    resource = Resource(attributes={
        "service.name": "genai-validation-suite",
        "service.version": "0.1.0",
        "deployment.environment": "testing"
    })
    
    # Set up trace provider
    trace_provider = TracerProvider(resource=resource)
    
    # Set up OTLP trace exporter to Jaeger
    otlp_trace_exporter = OTLPSpanExporter(
        endpoint="localhost:4317",  # OTLP gRPC endpoint
        insecure=True  # No TLS for local testing
    )
    
    # Add in-memory exporter for testing
    memory_exporter = InMemorySpanExporter()
    
    # Add processors to trace provider
    otlp_trace_processor = BatchSpanProcessor(otlp_trace_exporter)
    trace_provider.add_span_processor(otlp_trace_processor)
    
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    memory_processor = SimpleSpanProcessor(memory_exporter)
    trace_provider.add_span_processor(memory_processor)
    
    # Set up metrics
    otlp_metric_exporter = OTLPMetricExporter(
        endpoint="localhost:4317",
        insecure=True
    )
    
    metric_reader = PeriodicExportingMetricReader(
        otlp_metric_exporter,
        export_interval_millis=1000
    )
    
    metrics_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader]
    )
    
    # Set as global providers
    trace.set_tracer_provider(trace_provider)
    metrics.set_meter_provider(metrics_provider)
    
    return {
        "trace_provider": trace_provider,
        "metrics_provider": metrics_provider,
        "processors": [otlp_trace_processor, memory_processor],
        "memory_exporter": memory_exporter,
        "meter": metrics.get_meter("genai-meter")
    }

class TelemetryValidator:
    """Validator for sending test telemetry to Jaeger"""
    
    def __init__(self):
        providers = setup_otlp_telemetry()
        self.trace_provider = providers["trace_provider"]
        self.metrics_provider = providers["metrics_provider"]
        self.processors = providers["processors"]
        self.memory_exporter = providers["memory_exporter"]
        self.meter = providers["meter"]
        
        # Create token counter
        self.token_counter = self.meter.create_counter(
            "gen_ai.token.usage",
            description="GenAI token usage counter",
            unit="{token}"
        )
        
        # Create latency histogram
        self.latency_histogram = self.meter.create_histogram(
            "gen_ai.request.duration",
            description="GenAI request duration",
            unit="s"
        )
    
    def setup_test(self, service_name):
        """Set up for a specific test"""
        # Create tracer for this test with service info
        tracer = trace.get_tracer(f"{service_name}-tracer")
        
        logger.info(f"Set up test for service: {service_name}")
        
        # Clear any previous spans
        self.memory_exporter.clear()
        
        return tracer, self.memory_exporter, self.processors
    
    def cleanup_test(self, processors):
        """Clean up after a test"""
        # Force flush to ensure data is sent
        self.trace_provider.force_flush()
        # Don't actually shutdown the processors since we're reusing them
        logger.info("Test data flushed to Jaeger")
        # Small delay to ensure complete transmission
        time.sleep(0.5)
    
    def record_token_usage(self, token_type, count, attributes):
        """Record token usage metrics"""
        all_attributes = attributes.copy()
        all_attributes["gen_ai.token.type"] = token_type
        self.token_counter.add(count, all_attributes)
    
    def record_latency(self, duration, attributes):
        """Record latency metrics"""
        self.latency_histogram.record(duration, attributes)

# Test functions for GenAI scenarios
def run_basic_agent_test(validator):
    """Basic Agent Test: simple query-response"""
    logger.info("Running Basic Agent Test")
    
    # Setup test
    tracer, memory_exporter, processors = validator.setup_test("agent-service")
    
    try:
        # Start timing
        start_time = time.time()
        
        # Create a span for the LLM call
        with tracer.start_as_current_span(
            "chat claude-3-opus",
            attributes={
                "gen_ai.system": "anthropic",
                "gen_ai.operation.name": "chat",
                "gen_ai.request.model": "claude-3-opus",
                "gen_ai.usage.input_tokens": 150,
                "gen_ai.usage.output_tokens": 75
            }
        ):
            # Add event for the user message
            current_span = trace.get_current_span()
            current_span.add_event(
                "gen_ai.user.message", 
                attributes={"content": "What is the capital of France?"}
            )
            
            # Simulate processing time
            time.sleep(0.2)
            
            # Add event for the assistant's response
            current_span.add_event(
                "gen_ai.assistant.message", 
                attributes={"content": "The capital of France is Paris."}
            )
            
            # Record token usage metrics
            validator.record_token_usage(
                "input", 150, 
                {
                    "gen_ai.system": "anthropic", 
                    "gen_ai.request.model": "claude-3-opus"
                }
            )
            validator.record_token_usage(
                "output", 75, 
                {
                    "gen_ai.system": "anthropic", 
                    "gen_ai.request.model": "claude-3-opus"
                }
            )
        
        # Record latency
        duration = time.time() - start_time
        validator.record_latency(
            duration, 
            {
                "gen_ai.system": "anthropic",
                "gen_ai.operation.name": "chat",
                "gen_ai.request.model": "claude-3-opus"
            }
        )
        
        logger.info("Basic Agent Test completed")
    finally:
        # Clean up
        validator.cleanup_test(processors)

def run_reasoning_flow_test(validator):
    """Multi-step Reasoning Flow: complex reasoning with nested spans"""
    logger.info("Running Multi-step Reasoning Flow Test")
    
    # Setup test
    tracer, memory_exporter, processors = validator.setup_test("reasoning-agent")
    
    try:
        start_time = time.time()
        
        # Main agent span
        with tracer.start_as_current_span(
            "chain_of_thought",
            attributes={
                "gen_ai.operation.name": "agent",
                "gen_ai.system": "openai",
                "gen_ai.agent.name": "reasoning-agent",
                "gen_ai.request.model": "gpt-4o"
            }
        ):
            # Initial problem analysis
            with tracer.start_as_current_span(
                "step1_analyze",
                attributes={"gen_ai.operation.name": "thinking"}
            ):
                current_span = trace.get_current_span()
                current_span.add_event(
                    "reasoning_step", 
                    attributes={"thought": "Let me analyze this math problem step by step."}
                )
                time.sleep(0.1)  # Simulate processing time
            
            # Generate potential solutions
            with tracer.start_as_current_span(
                "step2_generate_options",
                attributes={"gen_ai.operation.name": "thinking"}
            ):
                current_span = trace.get_current_span()
                current_span.add_event(
                    "reasoning_step", 
                    attributes={"thought": "I need to find the derivative of x²sin(x)"}
                )
                time.sleep(0.1)  # Simulate processing time
            
            # Evaluate options
            with tracer.start_as_current_span(
                "step3_evaluate",
                attributes={"gen_ai.operation.name": "thinking"}
            ):
                current_span = trace.get_current_span()
                current_span.add_event(
                    "reasoning_step", 
                    attributes={"thought": "Using the product rule: d/dx[x²sin(x)] = 2xsin(x) + x²cos(x)"}
                )
                time.sleep(0.1)  # Simulate processing time
            
            # Final decision
            with tracer.start_as_current_span(
                "step4_decide",
                attributes={"gen_ai.operation.name": "thinking"}
            ):
                current_span = trace.get_current_span()
                current_span.add_event(
                    "reasoning_step", 
                    attributes={"thought": "The final answer is 2xsin(x) + x²cos(x)"}
                )
                time.sleep(0.1)  # Simulate processing time
                
            # Record token usage metrics
            validator.record_token_usage(
                "input", 200, 
                {
                    "gen_ai.system": "openai", 
                    "gen_ai.request.model": "gpt-4o"
                }
            )
            validator.record_token_usage(
                "output", 120, 
                {
                    "gen_ai.system": "openai", 
                    "gen_ai.request.model": "gpt-4o"
                }
            )
        
        # Record latency
        duration = time.time() - start_time
        validator.record_latency(
            duration, 
            {
                "gen_ai.system": "openai",
                "gen_ai.operation.name": "agent",
                "gen_ai.request.model": "gpt-4o"
            }
        )
        
        logger.info("Multi-step Reasoning Flow Test completed")
    finally:
        # Clean up
        validator.cleanup_test(processors)

def run_tool_usage_test(validator):
    """Tool Usage Test: agent using tools/function calling"""
    logger.info("Running Tool Usage Test")
    
    # Setup test
    tracer, memory_exporter, processors = validator.setup_test("agent-with-tools")
    
    try:
        start_time = time.time()
        
        # Main agent operation
        with tracer.start_as_current_span(
            "chat gpt-4o",
            attributes={
                "gen_ai.system": "openai",
                "gen_ai.operation.name": "chat",
                "gen_ai.request.model": "gpt-4o"
            }
        ):
            # Add event for the user message
            current_span = trace.get_current_span()
            current_span.add_event(
                "gen_ai.user.message", 
                attributes={"content": "What's the weather in Paris?"}
            )
            
            # Add event for the assistant deciding to use a tool
            current_span.add_event(
                "gen_ai.assistant.message", 
                attributes={
                    # Omit content field for tool calls
                    "tool_calls": json.dumps([{
                        "id": "call_abc123",
                        "type": "function",
                        "function": {
                            "name": "get_weather",
                            "arguments": '{"location":"Paris"}'
                        }
                    }])
                }
            )
            
            # Add a child span for the tool execution
            with tracer.start_as_current_span(
                "execute_tool get_weather",
                attributes={
                    "gen_ai.operation.name": "execute_tool",
                    "gen_ai.tool.name": "get_weather",
                    "gen_ai.tool.call.id": "call_abc123"
                }
            ):
                # Simulate tool execution
                time.sleep(0.2)
                
                # Add tool response event
                tool_span = trace.get_current_span()
                tool_span.add_event(
                    "gen_ai.tool.message", 
                    attributes={
                        "content": "rainy, 57°F",
                        "id": "call_abc123",
                        "role": "tool"
                    }
                )
            
            # Add event for the final assistant response
            current_span.add_event(
                "gen_ai.assistant.message", 
                attributes={
                    "content": "The weather in Paris is rainy with a temperature of 57°F."
                }
            )
            
            # Record token usage metrics
            validator.record_token_usage(
                "input", 25, 
                {
                    "gen_ai.system": "openai", 
                    "gen_ai.request.model": "gpt-4o"
                }
            )
            validator.record_token_usage(
                "output", 35, 
                {
                    "gen_ai.system": "openai", 
                    "gen_ai.request.model": "gpt-4o"
                }
            )
        
        # Record latency
        duration = time.time() - start_time
        validator.record_latency(
            duration, 
            {
                "gen_ai.system": "openai",
                "gen_ai.operation.name": "chat",
                "gen_ai.request.model": "gpt-4o"
            }
        )
        
        logger.info("Tool Usage Test completed")
    finally:
        # Clean up
        validator.cleanup_test(processors)

def run_error_handling_test(validator):
    """Error Handling Test: agent dealing with errors and retries"""
    logger.info("Running Error Handling Test")
    
    # Setup test
    tracer, memory_exporter, processors = validator.setup_test("resilient-agent")
    
    try:
        start_time = time.time()
        
        # Main agent operation
        with tracer.start_as_current_span(
            "chat gpt-4o",
            attributes={
                "gen_ai.system": "openai",
                "gen_ai.operation.name": "chat",
                "gen_ai.request.model": "gpt-4o"
            }
        ):
            # Add event for the user message
            current_span = trace.get_current_span()
            current_span.add_event(
                "gen_ai.user.message", 
                attributes={"content": "Show me today's top headline from The New York Times"}
            )
            
            # First attempt - tool execution with error
            with tracer.start_as_current_span(
                "execute_tool news_api_lookup",
                attributes={
                    "gen_ai.operation.name": "execute_tool",
                    "gen_ai.tool.name": "news_api_lookup",
                    "retry.count": 0
                }
            ) as error_span:
                time.sleep(0.1)  # Simulate processing
                
                # Record error
                error_span.set_status(Status(StatusCode.ERROR, "API rate limit exceeded"))
                error_span.record_exception(
                    Exception("Rate limit exceeded: try again later"),
                    attributes={"error.type": "rate_limit_exceeded"}
                )
            
            # Add event for error handling decision
            current_span.add_event(
                "error_handling", 
                attributes={"decision": "Retry tool call with backoff"}
            )
            
            # Wait for backoff (simulated)
            time.sleep(0.2)
            
            # Second attempt - tool execution with success
            with tracer.start_as_current_span(
                "execute_tool news_api_lookup",
                attributes={
                    "gen_ai.operation.name": "execute_tool",
                    "gen_ai.tool.name": "news_api_lookup",
                    "retry.count": 1
                }
            ):
                time.sleep(0.1)  # Simulate processing
                
                # Add tool response event
                tool_span = trace.get_current_span()
                tool_span.add_event(
                    "gen_ai.tool.message", 
                    attributes={
                        "content": "Headline: 'Global AI Summit Addresses Ethical Concerns'",
                        "role": "tool"
                    }
                )
            
            # Add event for the final assistant response
            current_span.add_event(
                "gen_ai.assistant.message", 
                attributes={
                    "content": "Today's top headline from The New York Times is: 'Global AI Summit Addresses Ethical Concerns'"
                }
            )
            
            # Record token usage metrics
            validator.record_token_usage(
                "input", 40, 
                {
                    "gen_ai.system": "openai", 
                    "gen_ai.request.model": "gpt-4o"
                }
            )
            validator.record_token_usage(
                "output", 65, 
                {
                    "gen_ai.system": "openai", 
                    "gen_ai.request.model": "gpt-4o"
                }
            )
        
        # Record latency
        duration = time.time() - start_time
        validator.record_latency(
            duration, 
            {
                "gen_ai.system": "openai",
                "gen_ai.operation.name": "chat",
                "gen_ai.request.model": "gpt-4o"
            }
        )
        
        logger.info("Error Handling Test completed")
    finally:
        # Clean up
        validator.cleanup_test(processors)

def run_all_tests():
    """Run all test scenarios and send to Jaeger"""
    validator = TelemetryValidator()
    
    logger.info("Starting GenAI test scenarios")
    
    try:
        # Run our test functions
        run_basic_agent_test(validator)
        run_reasoning_flow_test(validator)
        run_tool_usage_test(validator)
        run_error_handling_test(validator)
        
        logger.info("All tests completed successfully!")
    except Exception as e:
        logger.error(f"Error running tests: {e}")
    finally:
        # Make sure we flush everything at the end
        validator.trace_provider.force_flush()
        logger.info("All data flushed to Jaeger")

if __name__ == "__main__":
    run_all_tests()