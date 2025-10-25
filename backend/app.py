from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os, time, json, requests, logging

# ------------------ ENV ------------------
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv("WALTTI_KEY")

if not API_KEY:
    raise RuntimeError("❌ IP Key issue!")

API_URL = "https://api.digitransit.fi/routing/v2/waltti/gtfs/v1"
HEADERS = {
    "Content-Type": "application/json",
    "digitransit-subscription-key": API_KEY
}

CACHE = {}
TTL = 15  # saniye

# ------------------ GraphQL Helper ------------------
def gql(query: str):
    try:
        r = requests.post(API_URL, headers=HEADERS, data=json.dumps({"query": query}))
        r.raise_for_status()
        out = r.json()
        if "errors" in out:
            raise RuntimeError(out["errors"])
        return out["data"]
    except Exception as e:
        logging.warning("GraphQL error: %s", e)
        raise

# ------------------ Flask App ------------------
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})  

# ------------------ 1. Stops Data ------------------
@app.get("/api/stop/<gtfs_id>")
def stop(gtfs_id):
    now = time.time()
    if gtfs_id in CACHE and now - CACHE[gtfs_id][0] < TTL:
        return jsonify(CACHE[gtfs_id][1])
    
    query = f'''{{ stop(id:"{gtfs_id}") {{
        name
        stoptimesWithoutPatterns(numberOfDepartures:20) {{
            realtime realtimeArrival scheduledArrival serviceDay
            stopPositionInPattern
            trip {{ route {{ shortName }} tripHeadsign }}
        }}
    }} }}'''
    try:
        data = gql(query)["stop"]
        CACHE[gtfs_id] = (now, data)
        return jsonify(data)
    except Exception as e:
        app.logger.warning("stop gql error: %s", e)
        return jsonify({"error": "backend"}), 502

# ------------------ 2. Live vehicles ------------------
@app.get("/api/route/<gtfs_id>/vehicles")
def route_vehicles(gtfs_id):
    now = time.time()
    key = f"veh:{gtfs_id}"
    if key in CACHE and now - CACHE[key][0] < TTL:
        return jsonify(CACHE[key][1])

    query = f'''{{ route(id:"{gtfs_id}") {{
        patterns {{
            vehiclePositions {{
                lat lon heading lastUpdated
                stopRelationship {{
                    status
                    stop {{ gtfsId name }}
                }}
            }}
        }}
    }} }}'''
    try:
        pats = gql(query)["route"]["patterns"]
        vehicles = [v for p in pats for v in p["vehiclePositions"]]
        CACHE[key] = (now, vehicles)
        return jsonify(vehicles)
    except Exception as e:
        app.logger.warning("vehicle gql error: %s", e)
        return jsonify([])

# ------------------ 3.Stops list ------------------
@app.get("/api/route/<gtfs_id>/stops")
def route_stops(gtfs_id):
    query = f'''{{ route(id:"{gtfs_id}") {{
        patterns {{ stops {{ gtfsId name lat lon }} }}
    }} }}'''
    try:
        pats = gql(query)["route"]["patterns"]
        if not pats:
            return jsonify([])
        raw = pats[0]["stops"]
        seen, out = set(), []
        for idx, s in enumerate(raw):
            if s["gtfsId"] in seen:
                continue
            seen.add(s["gtfsId"])
            out.append({**s, "index": idx})
        return jsonify(out)
    except Exception as e:
        app.logger.warning("route_stops error: %s", e)
        return jsonify([])

# ------------------ Run ------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)