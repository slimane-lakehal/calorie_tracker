"""SQLAlchemy Base Configuration

This module provides the base configuration for SQLAlchemy ORM, including
the declarative base and database session management.
"""
from __future__ import annotations
from typing import Any, Optional

import os
from pathlib import Path
from contextlib import contextmanager

from sqlalchemy import create_engine, Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Create the declarative base for SQLAlchemy models
Base = declarative_base()

# Default database path in the user's home directory
DEFAULT_DB_PATH = os.path.join(
    os.path.expanduser("~"),
    ".calorie_tracker",
    "calorie_tracker.db"
)


def get_engine(db_url: Optional[str] = None) -> Engine:
    """Create and return a SQLAlchemy engine.
    
    Args:
        db_url: Optional database URL, if None uses SQLite with the default path
        
    Returns:
        SQLAlchemy Engine instance
    """
    if db_url is None:
        # Ensure directory exists
        db_dir = os.path.dirname(DEFAULT_DB_PATH)
        Path(db_dir).mkdir(parents=True, exist_ok=True)
        
        # Create SQLite URL
        db_url = f"sqlite:///{DEFAULT_DB_PATH}"
    
    # Create and return the engine
    return create_engine(db_url, echo=False)


def get_session_factory(engine: Optional[Engine] = None) -> sessionmaker:
    """Create a session factory for the given engine.
    
    Args:
        engine: SQLAlchemy Engine, created if not provided
        
    Returns:
        Session factory
    """
    if engine is None:
        engine = get_engine()
    
    return sessionmaker(bind=engine)


@contextmanager
def get_db_session(engine: Optional[Engine] = None) -> Session:
    """Context manager for database sessions.
    
    Args:
        engine: SQLAlchemy Engine, created if not provided
        
    Yields:
        Session: SQLAlchemy session
        
    Example:
        with get_db_session() as session:
            users = session.query(User).all()
    """
    if engine is None:
        engine = get_engine()
    
    SessionFactory = get_session_factory(engine)
    session = SessionFactory()
    
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Optional[Engine] = None) -> None:
    """Initialize the database schema.
    
    Args:
        engine: SQLAlchemy Engine, created if not provided
    """
    if engine is None:
        engine = get_engine()
    
    # Import models to ensure they're registered with Base
    from calorie_tracker.models import user, food
    
    # Create all tables
    Base.metadata.create_all(engine)
