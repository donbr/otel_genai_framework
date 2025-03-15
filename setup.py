# setup.py
"""
Setup script for the OpenTelemetry GenAI Validation Framework

This script helps configure and install the validation framework and its dependencies.
"""

from setuptools import setup, find_packages

setup(
    name="otel-genai-validator",
    version="0.1.0",
    description="Validation framework for OpenTelemetry GenAI instrumentation",
    author="OpenTelemetry GenAI Validation Team",
    packages=find_packages(),
    py_modules=[
        "otel_genai_validator",
        "genai_test_scenarios",
        "validation_suite"
    ],
    python_requires=">=3.7",
    install_requires=[
        "opentelemetry-api>=1.18.0",
        "opentelemetry-sdk>=1.18.0",
        "opentelemetry-exporter-otlp-proto-grpc>=1.18.0",
        "rich>=13.0.0"
    ],
    entry_points={
        "console_scripts": [
            "otel-genai-validate=validation_suite:run_validation_suite",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
