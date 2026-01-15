"""Tests for GET /stats endpoint."""
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


def test_get_stats_empty(client: TestClient):
    """Test GET /stats with no messages."""
    response = client.get("/stats")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total_messages"] == 0
    assert data["senders_count"] == 0
    assert data["messages_per_sender"] == []
    assert data["first_message_ts"] is None
    assert data["last_message_ts"] is None


def test_get_stats_with_data(client: TestClient, webhook_secret: str):
    """Test GET /stats with messages."""
    # Insert messages from different senders
    messages = [
        {"message_id": "m1", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T10:00:00Z", "text": "Msg1"},
        {"message_id": "m2", "from": "+919876543211", "to": "+14155550100", "ts": "2025-01-15T11:00:00Z", "text": "Msg2"},
        {"message_id": "m3", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T12:00:00Z", "text": "Msg3"},
        {"message_id": "m4", "from": "+919876543210", "to": "+14155550100", "ts": "2025-01-15T13:00:00Z", "text": "Msg4"},
    ]
    
    for msg in messages:
        body = json.dumps(msg).encode()
        signature = calculate_signature(body, webhook_secret)
        client.post("/webhook", content=body, headers={"X-Signature": signature, "Content-Type": "application/json"})
    
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_messages"] == 4
    assert data["senders_count"] == 2
    assert len(data["messages_per_sender"]) == 2
    assert data["first_message_ts"] == "2025-01-15T10:00:00Z"
    assert data["last_message_ts"] == "2025-01-15T13:00:00Z"
    
    # Check top sender
    top_sender = data["messages_per_sender"][0]
    assert top_sender["from"] == "+919876543210"
    assert top_sender["count"] == 3


def test_get_stats_top_10_senders(client: TestClient, webhook_secret: str):
    """Test GET /stats returns top 10 senders only."""
    # Insert messages from 15 different senders
    for i in range(15):
        msg = {
            "message_id": f"m{i+1}",
            "from": f"+9198765432{i:02d}",
            "to": "+14155550100",
            "ts": f"2025-01-15T{10+i:02d}:00:00Z",
            "text": f"Msg{i+1}"
        }
        body = json.dumps(msg).encode()
        signature = calculate_signature(body, webhook_secret)
        client.post("/webhook", content=body, headers={"X-Signature": signature, "Content-Type": "application/json"})
    
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_messages"] == 15
    assert data["senders_count"] == 15
    assert len(data["messages_per_sender"]) == 10  # Top 10 only
