from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os, time, json, requests, logging

# ------------------------------------------------------------------
# temel ayarlar
# ------------------------------------------------------------------
load_dotenv()
API_KEY  = os.getenv("WALTTI_KEY")                 # .env dosyasından
API_URL  = "https://api.digitransit.fi/routing/v2/waltti/gtfs/v1"
HEADERS  = {"Content-Type": "application/json",
            "digitransit-subscription-key": API_KEY}

CACHE = {}               # {key: (timestamp, data)}
TTL   = 15               # sn – basit önbellek

def gql(query: str):
    """GraphQL yardımcı – hata durumunda RuntimeError fırlatır."""
    r = requests.post(API_URL, headers=HEADERS, data=json.dumps({"query": query}))
    r.raise_for_status()
    out = r.json()
    if "errors" in out:
        raise RuntimeError(out["errors"])
    return out["data"]

# ------------------------------------------------------------------
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
app.logger.setLevel(logging.INFO)

# ------------------------------------------------------------------
# 1) DURAK dakika listesi
# ------------------------------------------------------------------
@app.get("/api/stop/<gtfs_id>")
def stop(gtfs_id):
    now = time.time()
    if gtfs_id in CACHE and now - CACHE[gtfs_id][0] < TTL:
        return jsonify(CACHE[gtfs_id][1])

    query = f'''{{ stop(id:"{gtfs_id}") {{
                  name
                  stoptimesWithoutPatterns(numberOfDepartures:20) {{
                    realtime realtimeArrival scheduledArrival serviceDay
                    stopPositionInPattern                      # yön için
                    trip {{ route {{ shortName }} tripHeadsign }}
                  }}
    }} }}'''
    try:
        data = gql(query)["stop"]
    except Exception as e:
        app.logger.warning("stop gql error: %s", e)
        return jsonify({"error": "backend"}), 502

    CACHE[gtfs_id] = (now, data)
    return jsonify(data)

# ------------------------------------------------------------------
# 2) CANLI ARAÇ listesi
# ------------------------------------------------------------------
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
                        status                      # PASSED / STOPPED_AT ...
                        stop {{ gtfsId name }}
                      }}
                    }}
                  }}
    }} }}'''
    try:
        pats = gql(query)["route"]["patterns"]
        vehicles = [v for p in pats for v in p["vehiclePositions"]]
    except Exception as e:
        app.logger.warning("vehicle gql error: %s", e)
        vehicles = []

    CACHE[key] = (now, vehicles)
    return jsonify(vehicles)

# ------------------------------------------------------------------
# 3) ROTA durak listesi (ilk pattern)
# ------------------------------------------------------------------
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
    except Exception as e:
        app.logger.warning("route_stops error: %s", e)
        return jsonify([])

    seen, out = set(), []
    for idx, s in enumerate(raw):
        if s["gtfsId"] in seen:
            continue
        seen.add(s["gtfsId"])
        out.append({**s, "index": idx})    # index → sıradaki konum
    return jsonify(out)

# ------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)