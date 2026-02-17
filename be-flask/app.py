import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for your app

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.route('/')
def get_ip():
    try:
        # Get client IP address
        # Check for X-Forwarded-For header (when behind a proxy/load balancer)
        if request.headers.get('X-Forwarded-For'):
            client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        else:
            client_ip = request.remote_addr

        # Get user agent
        user_agent = request.headers.get('User-Agent', 'Unknown')

        ip_data = {
            "ip": client_ip,
            "user_agent": user_agent,
            "method": request.method
        }

        # Log success
        logger.info(f"Successfully retrieved IP information: {client_ip}")

        return jsonify({"message": "Success", "data": ip_data}), 200
    except Exception as e:
        # Log exception
        logger.exception(f"Exception while processing request: {str(e)}")

        return jsonify({"message": "Error", "error": str(e)}), 500

if __name__ == '__main__':
    app.run()
