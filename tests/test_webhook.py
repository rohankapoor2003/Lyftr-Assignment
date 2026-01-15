"""Tests for webhook endpoint."""
import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient


def calculate_signature(body: bytes, secret: str) -> str:
    """Calculate HMAC-SHA256 signature."""
    return hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()


def test_webhook_valid_signature(client: TestClient, webhook_secret: str):
    """Test webhook with valid signature."""
    payload = {
        "message_id": "m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    }
    body = json.dumps(payload).encode()
    signature = calculate_signature(body, webhook_secret)
    
    response = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_invalid_signature(client: TestClient):
    """Test webhook with invalid signature."""
    payload = {
        "message_id": "m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    }
    body = json.dumps(payload).encode()
    
    response = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": "invalid-signature", "Content-Type": "application/json"}
    )
    
    assert response.status_code == 401
    assert "Invalid signature" in response.json()["detail"]


def test_webhook_missing_signature(client: TestClient):
    """Test webhook with missing signature header."""
    payload = {
        "message_id": "m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    }
    body = json.dumps(payload).encode()
    
    response = client.post(
        "/webhook",
        content=body,
        headers={"Content-Type": "application/json"}
    )
    
    assert response.status_code == 401
    assert "Missing signature" in response.json()["detail"]


def test_webhook_invalid_payload(client: TestClient, webhook_secret: str):
    """Test webhook with invalid payload."""
    payload = {
        "message_id": "",  # Invalid: empty
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    }
    body = json.dumps(payload).encode()
    signature = calculate_signature(body, webhook_secret)
    
    response = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 422


def test_webhook_invalid_e164(client: TestClient, webhook_secret: str):
    """Test webhook with invalid E.164 format."""
    payload = {
        "message_id": "m1",
        "from": "9876543210",  # Invalid: missing +
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    }
    body = json.dumps(payload).encode()
    signature = calculate_signature(body, webhook_secret)
    
    response = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 422


def test_webhook_invalid_timestamp(client: TestClient, webhook_secret: str):
    """Test webhook with invalid timestamp."""
    payload = {
        "message_id": "m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00",  # Invalid: missing Z
        "text": "Hello"
    }
    body = json.dumps(payload).encode()
    signature = calculate_signature(body, webhook_secret)
    
    response = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 422


def test_webhook_duplicate_message(client: TestClient, webhook_secret: str):
    """Test webhook with duplicate message_id."""
    payload = {
        "message_id": "m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "Hello"
    }
    body = json.dumps(payload).encode()
    signature = calculate_signature(body, webhook_secret)
    
    # First request
    response1 = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    assert response1.status_code == 200
    
    # Duplicate request
    response2 = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    assert response2.status_code == 200  # Still returns 200
    assert response2.json() == {"status": "ok"}


def test_webhook_text_too_long(client: TestClient, webhook_secret: str):
    """Test webhook with text exceeding max length."""
    payload = {
        "message_id": "m1",
        "from": "+919876543210",
        "to": "+14155550100",
        "ts": "2025-01-15T10:00:00Z",
        "text": "x" * 4097  # Exceeds 4096 limit
    }
    body = json.dumps(payload).encode()
    signature = calculate_signature(body, webhook_secret)
    
    response = client.post(
        "/webhook",
        content=body,
        headers={"X-Signature": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 422
