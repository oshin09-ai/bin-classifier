import os
from flask import Flask, render_template, request, jsonify, send_file, abort
import json
from werkzeug.utils import secure_filename
import base64
from models import RecyclingResult, es
from utils import classify_product, generate_csv
import ssl
from openai import OpenAI

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "recycling-secret-key")
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# Initialize OpenAI client
openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Initialize Elasticsearch index if connection is available
if es is not None:
    try:
        RecyclingResult.init_index()
    except Exception as e:
        print(f"Failed to initialize Elasticsearch index: {str(e)}")
else:
    print("Warning: Elasticsearch is not available. Some features may be limited.")

# Ensure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/classify", methods=["POST"])
def classify():
    try:
        description = request.form.get("description", "")
        image = request.files.get("image")
        
        image_data = None
        if image and image.filename:
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            try:
                image.save(image_path)
                with open(image_path, "rb") as img_file:
                    image_data = base64.b64encode(img_file.read()).decode()
            finally:
                if os.path.exists(image_path):
                    os.remove(image_path)  # Clean up
            
        result = classify_product(description, image_data, openai)
        
        # Only save to Elasticsearch if we have a valid result
        if result and isinstance(result, list) and len(result) > 0:
            try:
                RecyclingResult.save(description, result)
            except Exception as es_error:
                print(f"Warning: Failed to save to Elasticsearch: {str(es_error)}")
                # Continue without saving to Elasticsearch
        
        return jsonify({"success": True, "result": result})
        
    except Exception as e:
        error_message = str(e)
        print(f"Classification error: {error_message}")
        return jsonify({
            "success": False, 
            "error": "Failed to classify product. Please try again."
        }), 500

@app.route("/api/export-csv")
def export_csv():
    try:
        csv_path = generate_csv()
        return send_file(
            csv_path,
            mimetype="text/csv",
            as_attachment=True,
            download_name="recycling_results.csv"
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
