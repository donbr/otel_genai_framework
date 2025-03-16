# genai_test_scenarios.py
"""
GenAI Test Scenarios

This module contains test scenarios for validating OpenTelemetry instrumentation
of GenAI systems against the semantic conventions.

Version: 0.1.0
"""

import time
import json
import logging
from opentelemetry import trace
from opentelemetry.trace.status import Status, StatusCode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("genai-test-scenarios")

def run_basic_agent_test(validator):
    """
    Test Scenario 1: Basic Agent Tracing Validation
    
    Validates a simple GenAI agent interaction with user query and response.
    
    Args:
        validator: OTelGenAIValidator instance
        
    Returns:
        bool: True if the test passes
    """
    logger.info("Running Basic Agent Test")
    
    # Setup test
    tracer, memory_exporter, processors = validator.setup_test("agent-service")
    
    try:
        # Run test
        with tracer.start_as_current_span(
            "chat claude-3-opus",  # Following the span naming convention
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
            
            # Add event for the model's response
            current_span.add_event(
                "gen_ai.assistant.message", 
                attributes={"content": "The capital of France is Paris."}
            )
        
        # Validation
        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 1, f"Expected 1 span, got {len(spans)}"
        
        from src.otel_genai_validator import GenAISpanValidator
        
        root_span = spans[0]
        GenAISpanValidator.verify_genai_span_attributes(root_span, {
            "gen_ai.system": "anthropic",
            "gen_ai.operation.name": "chat",
            "gen_ai.request.model": "claude-3-opus",
            "gen_ai.usage.input_tokens": 150,
            "gen_ai.usage.output_tokens": 75
        })
        
        GenAISpanValidator.verify_events_on_span(root_span, [
            {
                "name": "gen_ai.user.message",
                "attributes": {"content": "What is the capital of France?"}
            },
            {
                "name": "gen_ai.assistant.message",
                "attributes": {"content": "The capital of France is Paris."}
            }
        ])
        
        logger.info("Basic Agent Test successful")
        return True
        
    except AssertionError as e:
        logger.error(f"Validation failed: {str(e)}")
        raise
    finally:
        # Clean up
        validator.cleanup_test(processors)

def run_reasoning_flow_test(validator):
    """
    Test Scenario 2: Multi-step Reasoning Flow Validation
    
    Validates a complex reasoning flow with multiple nested thinking steps.
    
    Args:
        validator: OTelGenAIValidator instance
        
    Returns:
        bool: True if the test passes
    """
    logger.info("Running Multi-step Reasoning Flow Test")
    
    # Setup test
    tracer, memory_exporter, processors = validator.setup_test("reasoning-agent")
    
    try:
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
        
        # Validation
        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 5, f"Expected 5 spans (1 parent + 4 steps), got {len(spans)}"
        
        from src.otel_genai_validator import GenAISpanValidator
        
        # Find root span
        root_span = next((s for s in spans if s.name == "chain_of_thought"), None)
        assert root_span is not None, "Root span not found"
        
        # Verify root span attributes
        GenAISpanValidator.verify_genai_span_attributes(root_span, {
            "gen_ai.operation.name": "agent",
            "gen_ai.system": "openai",
            "gen_ai.agent.name": "reasoning-agent",
            "gen_ai.request.model": "gpt-4o"
        })
        
        # Verify child spans
        child_spans = [s for s in spans if hasattr(s.parent, "span_id") and s.parent.span_id == root_span.context.span_id]
        assert len(child_spans) == 4, f"Expected 4 child spans, got {len(child_spans)}"
        
        # Verify each step has a reasoning_step event
        for span in child_spans:
            assert len(span.events) > 0, f"Span {span.name} has no events"
            assert span.events[0].name == "reasoning_step", f"Expected reasoning_step event, got {span.events[0].name}"
            assert "thought" in span.events[0].attributes, "Missing thought attribute in reasoning_step event"
        
        logger.info("Multi-step Reasoning Flow Test successful")
        return True
        
    except AssertionError as e:
        logger.error(f"Validation failed: {str(e)}")
        raise
    finally:
        # Clean up
        validator.cleanup_test(processors)

def run_tool_usage_test(validator):
    """
    Test Scenario 3: Tool Usage and Function Calling Validation
    
    Validates an agent using tools, focusing on the tool calling pattern.
    
    Args:
        validator: OTelGenAIValidator instance
        
    Returns:
        bool: True if the test passes
    """
    logger.info("Running Tool Usage Test")
    
    # Setup test
    tracer, memory_exporter, processors = validator.setup_test("agent-with-tools")
    
    try:
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
                    "gen_ai.tool.call.id": "call_abc123",
                    "gen_ai.system": "openai"  # Add this line to fix the issue
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
        
        # Validation
        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 2, f"Expected 2 spans, got {len(spans)}"
        
        from src.otel_genai_validator import GenAISpanValidator
        
        # Find and validate parent span
        root_span = next((s for s in spans if s.name == "chat gpt-4o"), None)
        assert root_span is not None, "Root span not found"
        
        GenAISpanValidator.verify_genai_span_attributes(root_span, {
            "gen_ai.system": "openai",
            "gen_ai.operation.name": "chat",
            "gen_ai.request.model": "gpt-4o"
        })
        
        # Verify events on parent span
        GenAISpanValidator.verify_events_on_span(root_span, [
            {
                "name": "gen_ai.user.message",
                "attributes": {"content": "What's the weather in Paris?"}
            },
            {
                "name": "gen_ai.assistant.message"
                # We omit content field verification as it's not present
            }
        ])
        
        # Verify tool span
        tool_span = GenAISpanValidator.verify_tool_span(spans, root_span.context.span_id, "get_weather")
        
        GenAISpanValidator.verify_genai_span_attributes(tool_span, {
            "gen_ai.operation.name": "execute_tool",
            "gen_ai.tool.name": "get_weather",
            "gen_ai.tool.call.id": "call_abc123"
        })
        
        # Verify tool response event
        GenAISpanValidator.verify_events_on_span(tool_span, [
            {
                "name": "gen_ai.tool.message",
                "attributes": {
                    "content": "rainy, 57°F",
                    "id": "call_abc123",
                    "role": "tool"
                }
            }
        ])
        
        logger.info("Tool Usage Test successful")
        return True
        
    except AssertionError as e:
        logger.error(f"Validation failed: {str(e)}")
        raise
    finally:
        # Clean up
        validator.cleanup_test(processors)

def run_error_handling_test(validator):
    """
    Test Scenario 5: Error Handling and Resilience Validation
    
    Validates an agent's ability to handle errors and implement retries.
    
    Args:
        validator: OTelGenAIValidator instance
        
    Returns:
        bool: True if the test passes
    """
    logger.info("Running Error Handling Test")
    
    # Setup test
    tracer, memory_exporter, processors = validator.setup_test("resilient-agent")
    
    try:
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
        
        # Validation
        spans = memory_exporter.get_finished_spans()
        assert len(spans) == 3, f"Expected 3 spans, got {len(spans)}"
        
        from src.otel_genai_validator import GenAISpanValidator
        
        # Verify parent span
        root_span = next((s for s in spans if s.name == "chat gpt-4o"), None)
        assert root_span is not None, "Root span not found"
        
        # Find error span
        error_spans = [s for s in spans 
                    if hasattr(s.parent, "span_id") and s.parent.span_id == root_span.context.span_id 
                    and s.status.status_code == StatusCode.ERROR]
        assert len(error_spans) == 1, "Expected 1 error span"
        error_span = error_spans[0]
        
        # Verify error attributes
        assert error_span.attributes.get("retry.count") == 0, "Retry count should be 0"
        assert error_span.attributes.get("gen_ai.tool.name") == "news_api_lookup", "Tool name mismatch"
        
        # Find successful retry span
        retry_spans = [s for s in spans 
                    if hasattr(s.parent, "span_id") and s.parent.span_id == root_span.context.span_id 
                    and s.status.status_code != StatusCode.ERROR
                    and s.attributes.get("retry.count") == 1]
        assert len(retry_spans) == 1, "Expected 1 retry span"
        retry_span = retry_spans[0]
        
        # Verify retry succeeded
        GenAISpanValidator.verify_events_on_span(retry_span, [
            {
                "name": "gen_ai.tool.message",
                "attributes": {
                    "role": "tool",
                    "content": "Headline: 'Global AI Summit Addresses Ethical Concerns'"
                }
            }
        ])
        
        logger.info("Error Handling Test successful")
        return True
        
    except AssertionError as e:
        logger.error(f"Validation failed: {str(e)}")
        raise
    finally:
        # Clean up
        validator.cleanup_test(processors)
