"""Stable version 1 HTTP API contract."""

from src.api.v1.router import API_PREFIX, API_VERSION, router

__all__ = ["API_PREFIX", "API_VERSION", "router"]
