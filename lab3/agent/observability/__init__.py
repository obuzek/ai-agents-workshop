"""
Observability utilities for Lab 3.

This module provides:
- PII masking for Langfuse traces (masking.py)
- A helper to create a pre-configured Langfuse callback handler
"""

from lab3.agent.observability.masking import mask_pii, create_langfuse_handler

__all__ = ["mask_pii", "create_langfuse_handler"]
