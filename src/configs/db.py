# app/db.py
"""Backward-compatible database imports; new code uses :mod:`src.core.database`."""

from src.core.database import Base, SessionLocal, engine, get_db

__all__ = ["Base", "SessionLocal", "engine", "get_db"]
