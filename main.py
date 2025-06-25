from flask import Flask, request, jsonify
from agent.langGraphRouter import build_graph
import logging
import traceback

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bitbud.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# CORS(app)

# Initialize graph
try:
    graph = build_graph()
    logger.info("BitBud graph initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize graph: {e}")
    graph = None

@app.route("/")
def home():
    return "BitBud backend is running!"

@app.route("/ask", methods=["POST"])
def ask():
    try:
        # Validate request
        if not request.is_json:
            logger.warning("Received non-JSON request")
            return jsonify({"error": "Request must be JSON"}), 400
        
        # Validate message exists
        user_input = request.json.get("message", "").strip()
        if not user_input:
            logger.warning("Received empty message")
            return jsonify({"error": "Message cannot be empty"}), 400
        
        # Check if graph is available
        if graph is None:
            logger.error("Graph not initialized, cannot process request")
            return jsonify({"error": "BitBud is not ready. Please restart the service. If the issue persists, check the logs or contact support."}), 503
        
        logger.info(f"Processing user input: {user_input}...")
        
        # Process with graph
        result = graph.invoke({"input": user_input})
        reply = result.get("output", "I'm having trouble processing that right now.")
        
        logger.info(f"Generated reply: {reply[:50]}...")
        return jsonify({"reply": reply})
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            "error": "Something went wrong processing your request.",
            "reply": "I'm experiencing technical difficulties. Please try again."
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    logger.info("Starting BitBud backend on port 5001")
    app.run(port=5001, debug=False)