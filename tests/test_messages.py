"""Tests for GET /messages endpoint."""
import json
import hmac
import hashlib
from fastapi.testclient import TestClient


def calculate_signature(body: bytes, secret: str) -> str:
    """Calculate HMAC-SHA256 signature."""
    return hmac.new(
        secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()


def test_get_messages_empty(client: TestClient):
    """Test GET /messages with no messages."""
    response = client.get("/messages")
    
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["limit"] == 50
    assert data["offset"] == 0


def test_get_messages_with_data(client: TestClient, webhook_secret: str):
    """Test GET /messages with messages."""
    # Insert some messages
    messages = [
        {
            "message_id": "m1",
            "from": "+919876543210",
            "to": "+14155550100",
            "ts": "2025-01-15T10:00:00Z",
            "text": "First message"
        },
        {
            "message_id": "m2",
            "from": "+919876543211",
            "to": "+14155550100",
            "ts": "2025-01-15T11:00:00Z",
            "text": "Second message"
        },
        {
            "message_id": "m3",
            "from": "+919876543210",
            "to": "+14155550101",
            "ts": "2025-01-15T12:00:00Z",
            "text": "Third message"
        }
    ]
    
    for msg in messages:
        body = json.dumps(msg).encode()
        signature = calculate_signature(body, webhook_secret)
        client.post(
            "/webhook",
            content=body,
            headers={"X-Signature": signature, "Content-Type": "application/json"}
        )
    
    # Get all messages
    response = client.get("/messages")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    
    # Check ordering (ts ASC, message_id ASC)
    assert data["items"][0]["message_id"] == "m1"
    assert data["items"][1]["message_id"] == "m2"
    assert data["items"][2]["message_id"] == "m3"


def test_get_messages_limit(client: TestClient, webhook_secret: str):
    """Test GET /messages with limit parameter."""
    # Insert 5 messages
    for i in range(5):
        msg = {
            "message_id": f"m{i+1}",
            "from": "+919876543210",
            "to": "+14155550100",
            "ts": f"2025-01-15T{10+i:02d}:00:00Z",
            "text": f"Message {i+1}"
        }
        body = json.dumps(msg).encode()
        signature = calculate_signature(body, webhook_secret)
        client.post(
            "/webhook",
            content=body,
            headers={"X-Signature": signature, "Content-Type": "application/json"}
        )
    
    # Get with limit 2
    response = client.get("/messages?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["limit"] == 2
    assert data["total"] == 5


def test_get_messages_offset(client: TestClient, webhook_secret: str):
    """Test GET /messages with offset parameter."""
    # Insert 5 messages
    for i in range(5):
        msg = {
            "message_id": f"m{i+1}",
            "from": "+919876543210",
            "to": "+14155550100",
            "ts": f"2025-01-15T{10+i:02d}:00:00Z",
            "text": f"Message {i+1}"
        }
        body = json.dumps(msg).encode()
        signature = calculate_signature(body, webhook_secret)
        client.post(
            "/webhook",
            content=body,
            headers={"X-Signature": signature, "Content-Type": "application/json"}
        )
    
    # Get with offset 2
    response = client.get("/messages?offset=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 3  # 5 total - 2 offset
    assert data["offset"] == 2
    assert data["items"][0]["message_id"] == "m3"


def test_get_messages_filter_from(client: TestClient, webhook_secret: str):
    """Test GET /messages with from filter."""
    # Insert messages from different senders
    messages = [
        {"message_id": "m1", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T10:00:00Z", "text": "Msg1"},
        {"message_id": "m2", "from": "+919876543211", "to": "+14155550100", "ts": "2025-01-15T11:00:00Z", "text": "Msg2"},
        {"message_id": "m3", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T12:00:00Z", "text": "Msg3"},
    ]
    
    for msg in messages:
        body = json.dumps(msg).encode()
        signature = calculate_signature(body, webhook_secret)
        client.post("/webhook", content=body, headers={"X-Signature": signature, "Content-Type": "application/json"})
    
    # Filter by from
    response = client.get("/messages?from=%2B919876543210")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all(item["from"] == "+919876543210" for item in data["items"])


def test_get_messages_filter_since(client: TestClient, webhook_secret: str):
    """Test GET /messages with since filter."""
    messages = [
        {"message_id": "m1", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T10:00:00Z", "text": "Msg1"},
        {"message_id": "m2", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T11:00:00Z", "text": "Msg2"},
        {"message_id": "m3", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T12:00:00Z", "text": "Msg3"},
    ]
    
    for msg in messages:
        body = json.dumps(msg).encode()
        signature = calculate_signature(body, webhook_secret)
        client.post("/webhook", content=body, headers={"X-Signature": signature, "Content-Type": "application/json"})
    
    # Filter by since
    response = client.get("/messages?since=2025-01-15T11:00:00Z")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2  # m2 and m3
    assert data["items"][0]["message_id"] == "m2"


def test_get_messages_search_q(client: TestClient, webhook_secret: str):
    """Test GET /messages with text search."""
    messages = [
        {"message_id": "m1", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T10:00:00Z", "text": "Hello world"},
        {"message_id": "m2", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T11:00:00Z", "text": "Goodbye"},
        {"message_id": "m3", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T12:00:00Z", "text": "Hello again"},
    ]
    
    for msg in messages:
        body = json.dumps(msg).encode()
        signature = calculate_signature(body, webhook_secret)
        client.post("/webhook", content=body, headers={"X-Signature": signature, "Content-Type": "application/json"})
    
    # Search for "Hello"
    response = client.get("/messages?q=Hello")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert all("Hello" in item["text"] for item in data["items"])


def test_get_messages_invalid_limit(client: TestClient):
    """Test GET /messages with invalid limit."""
    response = client.get("/messages?limit=101")  # Exceeds max
    assert response.status_code == 422


def test_get_messages_invalid_offset(client: TestClient):
    """Test GET /messages with invalid offset."""
    response = client.get("/messages?offset=-1")  # Negative
    assert response.status_code == 422
