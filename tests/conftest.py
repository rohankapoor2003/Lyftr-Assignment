"""Pytest configuration and fixtures."""
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage import Storage


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    db_path = Path(db_file.name)
    db_file.close()
    
    storage = Storage(db_path)
    yield storage
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def client(temp_db, monkeypatch):
    """Create a test client with temporary database."""
    # Override database path and storage
    monkeypatch.setattr("app.main.db_path", temp_db.db_path)
    monkeypatch.setattr("app.main.storage", temp_db)
    
    # Override webhook secret in settings
    monkeypatch.setattr("app.config.settings.webhook_secret", "test-secret-key")
    monkeypatch.setattr("app.main.settings.webhook_secret", "test-secret-key")
    
    return TestClient(app)


@pytest.fixture
def webhook_secret():
    """Return test webhook secret."""
    return "test-secret-key"
