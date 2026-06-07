import os
import uuid
import logging
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables from .env
load_dotenv()

# Import database and recommender functions
import database
from recommender import recommend_careers

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for development cross-origin requests

# Initialize SQLite database schema
database.init_db()

# Middleware: Authentication Decorator
def login_required(f):
    import functools
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Authentication token missing or invalid."}), 401
        
        token = auth_header.split(" ")[1]
        user = database.get_user_by_token(token)
        if not user:
            return jsonify({"error": "Session expired or invalid token."}), 401
        
        # Attach user and token to g for access in routes
        g.user = user
        g.token = token
        return f(*args, **kwargs)
    return decorated_function

# Endpoints
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    
    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required."}), 400
        
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
        
    # Check if user exists
    existing = database.get_user_by_email(email)
    if existing:
        return jsonify({"error": "An account with this email already exists."}), 400
        
    # Create user
    user_id = str(uuid.uuid4())
    password_hash = generate_password_hash(password)
    
    user = database.create_user(user_id, name, email, password_hash)
    token = database.create_session(user_id)
    
    database.log_activity(user_id, "Created account.")
    
    # Return user details + token
    return jsonify({
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "createdAt": user["createdAt"]
        },
        "token": token
    }), 201

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400
        
    user = database.get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401
        
    token = database.create_session(user["id"])
    database.log_activity(user["id"], "Logged in.")
    
    return jsonify({
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "createdAt": user["created_at"]
        },
        "token": token
    }), 200

@app.route("/api/logout", methods=["POST"])
@login_required
def logout():
    database.delete_session(g.token)
    return jsonify({"success": True, "message": "Successfully logged out."}), 200

@app.route("/api/session", methods=["GET"])
@login_required
def check_session():
    # Helper endpoint for frontend initialization check
    return jsonify({
        "user": {
            "id": g.user["id"],
            "name": g.user["name"],
            "email": g.user["email"],
            "createdAt": g.user["created_at"]
        },
        "token": g.token
    }), 200

@app.route("/api/profile", methods=["PUT"])
@login_required
def update_profile():
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    
    if not name:
        return jsonify({"error": "Name cannot be empty."}), 400
        
    updated = database.update_user_profile(g.user["id"], name)
    if not updated:
        return jsonify({"error": "User not found."}), 404
        
    database.log_activity(g.user["id"], "Updated profile name.")
    
    return jsonify({
        "id": updated["id"],
        "name": updated["name"],
        "email": updated["email"],
        "createdAt": updated["created_at"]
    }), 200

@app.route("/api/dashboard", methods=["GET"])
@login_required
def get_dashboard():
    user_id = g.user["id"]
    
    latest = database.get_latest_assessment(user_id)
    saved_ids = database.get_saved_careers(user_id)
    activity = database.get_activity_log(user_id, limit=6)
    
    # Pre-calculate top 3 recommendations if user has taken assessment
    recs = []
    if latest and latest.get("answers"):
        recs = recommend_careers(latest["answers"], limit=3)
        
    return jsonify({
        "latest": latest,
        "savedIds": saved_ids,
        "activity": activity,
        "recs": recs
    }), 200

@app.route("/api/assessment", methods=["GET"])
@login_required
def get_assessment_history_endpoint():
    history = database.get_assessment_history(g.user["id"])
    return jsonify(history), 200

@app.route("/api/assessment/latest", methods=["GET"])
@login_required
def get_latest_assessment_endpoint():
    latest = database.get_latest_assessment(g.user["id"])
    if not latest:
        return jsonify(None), 200
    
    # Run the recommendation engine
    recommendations = recommend_careers(latest["answers"], limit=10)
    return jsonify({
        "assessment": latest,
        "recommendations": recommendations
    }), 200

@app.route("/api/assessment", methods=["POST"])
@login_required
def process_assessment():
    data = request.get_json() or {}
    answers = data.get("answers")
    
    if not answers:
        return jsonify({"error": "Assessment answers are required."}), 400
        
    user_id = g.user["id"]
    assessment_id = str(uuid.uuid4())
    
    # Save user answers to database
    entry = database.save_assessment(assessment_id, user_id, answers)
    
    # Log the quiz completion
    database.log_activity(user_id, "Completed a career assessment.")
    
    # Run the recommendation engine
    recommendations = recommend_careers(answers, limit=10)
    
    return jsonify({
        "assessment": entry,
        "recommendations": recommendations
    }), 201

@app.route("/api/saved-careers", methods=["GET"])
@login_required
def get_saved_careers_endpoint():
    saved_ids = database.get_saved_careers(g.user["id"])
    return jsonify(saved_ids), 200

@app.route("/api/saved-careers/toggle", methods=["POST"])
@login_required
def toggle_saved_career_endpoint():
    data = request.get_json() or {}
    career_id = data.get("careerId")
    
    if not career_id:
        return jsonify({"error": "Career ID is required."}), 400
        
    user_id = g.user["id"]
    updated_saved_ids = database.toggle_saved_career(user_id, career_id)
    
    is_saved = career_id in updated_saved_ids
    action = "Saved" if is_saved else "Removed"
    
    # We need to retrieve career title, let's hardcode a default or fetch if needed
    # We can just say: Logged: Saved/Removed career
    database.log_activity(user_id, f"{action} career: {career_id.replace('-', ' ').title()}")
    
    return jsonify(updated_saved_ids), 200

@app.route("/api/activity", methods=["GET"])
@login_required
def get_activity_endpoint():
    activity = database.get_activity_log(g.user["id"])
    return jsonify(activity), 200

@app.route("/api/activity", methods=["POST"])
@login_required
def add_activity_endpoint():
    data = request.get_json() or {}
    message = data.get("message")
    
    if not message:
        return jsonify({"error": "Message is required."}), 400
        
    database.log_activity(g.user["id"], message)
    return jsonify({"success": True}), 201

if __name__ == "__main__":
    # In local development, port is 5000
    app.run(host="127.0.0.1", port=5000, debug=True)
