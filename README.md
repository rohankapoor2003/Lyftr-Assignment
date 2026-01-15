# Webhook API - FastAPI Backend

A production-ready FastAPI backend for processing webhook messages with HMAC signature validation, SQLite storage, and comprehensive API endpoints.

## Setup Used

This project was developed using:
- **VS Code** - Primary code editor
- **Cursor AI** - AI-powered coding assistant for rapid development
- **ChatGPT** - Additional AI assistance for code review and optimization

## Features

- ✅ HMAC-SHA256 signature validation for webhook security
- ✅ Idempotent message storage with duplicate detection
- ✅ Comprehensive message querying with filtering and pagination
- ✅ Statistics endpoint with sender analytics
- ✅ Structured JSON logging
- ✅ Health check endpoints (liveness and readiness)
- ✅ Docker support with multi-stage builds
- ✅ Comprehensive test suite

## API Documentation

### POST /webhook

Process incoming webhook messages with signature validation.

**Headers:**
- `X-Signature`: HMAC-SHA256 signature of the request body

**Request Body:**
```json
{
  "message_id": "m1",
  "from": "+919876543210",
  "to": "+14155550100",
  "ts": "2025-01-15T10:00:00Z",
  "text": "Hello"
}
```

**Validations:**
- `message_id`: Non-empty string
- `from`/`to`: E.164 format (+digits)
- `ts`: ISO-8601 UTC timestamp ending with Z
- `text`: Optional, maximum 4096 characters

**Responses:**
- `200 OK`: Message processed successfully
  ```json
  {"status": "ok"}
  ```
- `401 Unauthorized`: Invalid or missing signature
- `422 Unprocessable Entity`: Invalid payload

**Example Webhook Call:**

```bash
# Calculate signature
SECRET="your-webhook-secret"
BODY='{"message_id":"m1","from":"+919876543210","to":"+14155550100","ts":"2025-01-15T10:00:00Z","text":"Hello"}'
SIGNATURE=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | cut -d' ' -f2)

# Send request
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIGNATURE" \
  -d "$BODY"
```

### GET /messages

Retrieve messages with filtering and pagination.

**Query Parameters:**
- `limit` (optional): Number of messages to return (1-100, default: 50)
- `offset` (optional): Number of messages to skip (default: 0)
- `from` (optional): Filter by sender phone number
- `since` (optional): Filter by timestamp (ISO-8601, inclusive)
- `q` (optional): Search in message text

**Response:**
```json
{
  "items": [
    {
      "message_id": "m1",
      "from": "+919876543210",
      "to": "+14155550100",
      "ts": "2025-01-15T10:00:00Z",
      "text": "Hello"
    }
  ],
  "total": 120,
  "limit": 50,
  "offset": 0
}
```

**Example:**
```bash
# Get all messages
curl http://localhost:8000/messages

# Get messages from specific sender
curl "http://localhost:8000/messages?from=%2B919876543210"

# Search messages
curl "http://localhost:8000/messages?q=hello"

# Pagination
curl "http://localhost:8000/messages?limit=10&offset=20"
```

### GET /stats

Get statistics about stored messages.

**Response:**
```json
{
  "total_messages": 150,
  "senders_count": 25,
  "messages_per_sender": [
    {
      "from": "+919876543210",
      "count": 45
    }
  ],
  "first_message_ts": "2025-01-15T10:00:00Z",
  "last_message_ts": "2025-01-15T15:30:00Z"
}
```

**Example:**
```bash
curl http://localhost:8000/stats
```

### GET /health/live

Liveness probe - always returns 200 OK.

**Response:**
```json
{"status": "ok"}
```

### GET /health/ready

Readiness probe - checks if the service is ready to accept traffic.

**Checks:**
- WEBHOOK_SECRET is configured
- Database is reachable

**Response:**
```json
{"status": "ok"}
```

**Status Codes:**
- `200 OK`: Service is ready
- `503 Service Unavailable`: Service is not ready

## Configuration

Environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WEBHOOK_SECRET` | Yes | - | Secret key for HMAC signature validation |
| `DATABASE_URL` | No | `sqlite:////data/app.db` | SQLite database path |
| `LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ENABLE_METRICS` | No | `false` | Enable metrics collection |

## Design Decisions

### Storage Layer

- **SQLite**: Chosen for simplicity and zero-configuration deployment
- **Direct SQL**: Using `sqlite3` directly instead of ORM to avoid complexity and ensure stability
- **Idempotency**: Messages are stored with `message_id` as PRIMARY KEY to prevent duplicates
- **Indexing**: Indexes on `from_number` and `ts` for efficient querying

### Security

- **HMAC-SHA256**: Industry-standard signature algorithm for webhook validation
- **Constant-time comparison**: Using `hmac.compare_digest()` to prevent timing attacks
- **Raw body verification**: Signature is verified against raw request body before JSON parsing

### Logging

- **Structured JSON logs**: Machine-readable format for easy parsing and analysis
- **Request correlation**: Each request gets a unique `request_id` for tracing
- **Webhook-specific fields**: Logs include `message_id`, `dup`, and `result` for webhook requests

### API Design

- **RESTful endpoints**: Standard HTTP methods and status codes
- **Pydantic models**: Type-safe request/response validation
- **Query parameters**: Flexible filtering and pagination
- **Error handling**: Consistent error responses with appropriate status codes

## How to Run

### Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set environment variables:**
   ```bash
   export WEBHOOK_SECRET="your-secret-key-here"
   export DATABASE_URL="sqlite:///./data/app.db"
   ```

3. **Create data directory:**
   ```bash
   mkdir -p data
   ```

4. **Run the application:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Or use Makefile:**
   ```bash
   make install
   make run
   ```

### Docker

1. **Build and run with docker-compose:**
   ```bash
   docker-compose up --build
   ```

2. **Or use Makefile:**
   ```bash
   make docker-build
   make docker-up
   ```

3. **Set WEBHOOK_SECRET in docker-compose.yml or as environment variable:**
   ```bash
   WEBHOOK_SECRET="your-secret-key" docker-compose up
   ```

The application will be available at `http://localhost:8000`

### API Documentation

FastAPI automatically generates interactive API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

Or using Makefile:

```bash
make test
```

**Test Coverage:**
- Webhook signature validation
- Duplicate message handling
- Message filtering and pagination
- Statistics endpoint
- Health check endpoints
- Input validation

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application and endpoints
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic models
│   ├── storage.py           # SQLite storage layer
│   ├── logging_utils.py     # Structured logging
│   └── metrics.py           # Metrics (placeholder)
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   ├── test_webhook.py      # Webhook endpoint tests
│   ├── test_messages.py     # Messages endpoint tests
│   ├── test_stats.py        # Stats endpoint tests
│   └── test_health.py        # Health check tests
├── Dockerfile               # Multi-stage Docker build
├── docker-compose.yml       # Docker Compose configuration
├── Makefile                 # Common commands
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Database Schema

```sql
CREATE TABLE messages (
    message_id TEXT PRIMARY KEY,
    from_number TEXT NOT NULL,
    to_number TEXT NOT NULL,
    ts TEXT NOT NULL,
    text TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_from ON messages(from_number);
CREATE INDEX idx_ts ON messages(ts);
```

## Logging Format

Structured JSON logs include:

```json
{
  "ts": "2025-01-15T10:00:00Z",
  "level": "INFO",
  "request_id": "uuid-here",
  "method": "POST",
  "path": "/webhook",
  "status": 200,
  "latency_ms": 15,
  "message_id": "m1",
  "dup": false,
  "result": "ok"
}
```

## License

This project is part of a coding assignment.
