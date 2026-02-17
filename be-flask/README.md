# Flask IP Information API

A simple Flask backend application that returns the client's IP address information.

## Description

This Flask application provides a single endpoint at the root URL that returns information about the client making the request, including:
- Client IP address
- User agent
- HTTP request method

The application supports CORS to enable cross-origin requests.

## Features

- **IP Detection**: Automatically detects client IP, including support for proxied requests (X-Forwarded-For header)
- **CORS Enabled**: Allows requests from any origin
- **Logging**: Structured logging for monitoring and debugging
- **Error Handling**: Comprehensive error handling with appropriate HTTP status codes

## Endpoints

### GET /

Returns client IP information.

**Response Example:**
```json
{
  "message": "Success",
  "data": {
    "ip": "192.168.1.1",
    "user_agent": "Mozilla/5.0...",
    "method": "GET"
  }
}
```

**Status Codes:**
- `200 OK`: Successfully retrieved IP information
- `500 Internal Server Error`: Server error occurred

## Installation

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

### Development
```bash
python app.py
```

The application will start on `http://localhost:5000`

### Production
For production deployment, use a WSGI server like Gunicorn:
```bash
gunicorn app:app
```

### Docker
Build and run using Docker:
```bash
docker build -t flask-ip-api .
docker run -p 5000:5000 flask-ip-api
```

## Testing

### Unit Tests
Run unit tests:
```bash
python test_unit.py
```

### Integration Tests
First, start the Flask application:
```bash
python app.py
```

Then, in another terminal, run integration tests:
```bash
python test_integration.py
```

## Project Structure

```
be-flask/
├── app.py                 # Main Flask application
├── test_unit.py          # Unit tests
├── test_integration.py   # Integration tests
├── requirements.txt      # Python dependencies
├── Dockerfile           # Docker configuration
└── README.md            # This file
```

## Dependencies

- Flask: Web framework
- Flask-CORS: CORS support
- requests: HTTP library (used in integration tests)
- unittest2: Testing framework

## License

This project is part of the VIMEX deployment example.
