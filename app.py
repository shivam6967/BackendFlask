from flask import Flask, render_template, request, jsonify
import requests
import os
import json
from flask_cors import CORS
from astrapy import DataAPIClient
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
CORS(app)

# Fetch variables from .env
API_KEY = os.getenv("API_KEY")
LANGFLOW_BASE_API_URL = os.getenv("LANGFLOW_BASE_API_URL")
LANGFLOW_ID = os.getenv("LANGFLOW_ID")
FLOW_ID = os.getenv("FLOW_ID")
APPLICATION_TOKEN = os.getenv("APPLICATION_TOKEN")
ASTRA_DB_CLIENT_ID = os.getenv("ASTRA_DB_CLIENT_ID")
ASTRA_DB_SECRET = os.getenv("ASTRA_DB_SECRET")
ASTRA_DB_URL = os.getenv("ASTRA_DB_URL")
JSON_DIR = os.getcwd()
JSON_DIR = os.path.join(JSON_DIR, "AI")
os.makedirs(JSON_DIR, exist_ok=True)

# Astra DB Connection
client = DataAPIClient(f"AstraCS:{ASTRA_DB_CLIENT_ID}:{ASTRA_DB_SECRET}")
database = client.get_database(ASTRA_DB_URL)
collection = database.get_collection("data2")

@app.route("/name", methods=["GET"])
def get_user_name():
    user_file = os.path.join(JSON_DIR, "User.json")
    if os.path.exists(user_file):
        with open(user_file, "r") as file:
            user_data = json.load(file)
            return jsonify(user_data), 200
    else:
        return jsonify({"error": "User data not found"}), 404

@app.route("/planet/<planet_name>", methods=["GET"])
def get_planet_data(planet_name):
    planet_file = os.path.join(JSON_DIR, f"{planet_name}_report.json")
    if os.path.exists(planet_file):
        with open(planet_file, "r") as file:
            planet_data = json.load(file)
            return jsonify(planet_data), 200
    else:
        return jsonify({"error": f"Data for {planet_name} not found"}), 404

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        data = request.get_json()
        name = data.get("name")
        dob = data.get("dob")
        tob = data.get("timeOfBirth")
        gender = data.get("gender")
        city = data.get("city")
        state = data.get("state")
        lat, lon, tz = 19, 72, 5  # Hardcoded for now

        user_data = {"name": name, "tob": tob, "dob": dob, "gender": gender, "city": city, "state": state}
        file_path = os.path.join(JSON_DIR, "User.json")
        
        try:
            with open(file_path, "w") as file:
                json.dump(user_data, file)
        except Exception as e:
            return jsonify({"error": f"Failed to save user data: {str(e)}"}), 500

        planets = ["Sun", "Mars", "Jupiter", "Venus", "Saturn"]
        all_planet_data = {}

        for planet in planets:
            params = {"api_key": API_KEY, "dob": dob, "tob": tob, "lat": lat, "lon": lon, "tz": tz, "planet": planet, "lang": "en"}
            planet_response = requests.get("https://api.vedicastroapi.com/v3-json/horoscope/planet-report", params=params)
            planet_data = planet_response.json()

            if planet_response.status_code == 200 and planet_data.get('status') == 200:
                all_planet_data[planet] = planet_data['response'][0]
            else:
                all_planet_data[planet] = {"error": "Unable to fetch data"}

            planet_file_path = os.path.join(JSON_DIR, f"{planet}_report.json")
            with open(planet_file_path, "w") as planet_file:
                json.dump(all_planet_data[planet], planet_file, indent=4)

        return jsonify({"message": "Data processed successfully"}), 200

    return "Please make a POST request with the required data."

@app.route('/api/message', methods=['POST'])
def get_message():
    data = request.get_json()
    name = data.get('name')
    message = data.get('message')

    if not name or not message:
        return jsonify({"error": "Name and message are required"}), 400

    response = run_flow(name, message)
    return jsonify(response)

def run_flow(name, message):
    api_url = f"{LANGFLOW_BASE_API_URL}/lf/{LANGFLOW_ID}/api/v1/run/{FLOW_ID}"
    formatted_prompt = f"You are an Astrology expert for {name}. User's question: {message}"

    payload = {"input_value": formatted_prompt, "output_type": "chat", "input_type": "chat"}
    headers = {"Authorization": f"Bearer {APPLICATION_TOKEN}", "Content-Type": "application/json"}

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        return {"response": data.get("outputs", [{}])[0].get("outputs", [{}])[0].get("results", {}).get("message", {}).get("text", "No response found.")}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    app.run(debug=True)
