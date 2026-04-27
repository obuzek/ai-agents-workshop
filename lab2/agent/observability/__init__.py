"""
Observability utilities for Lab 2.

This module provides:
- PII masking for Langfuse traces (masking.py)
- A helper to create a pre-configured Langfuse callback handler
"""

from lab2.agent.observability.masking import mask_pii, create_langfuse_handler

__all__ = ["mask_pii", "create_langfuse_handler"]
