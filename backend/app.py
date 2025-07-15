from flask import Flask, jsonify
from dotenv import load_dotenv
from flask_cors import CORS 
import os, time, json, requests

load_dotenv()                       # reads WALTTI_KEY from .env
API_KEY   = os.getenv("WALTTI_KEY")
API_URL   = "https://api.digitransit.fi/routing/v2/waltti/gtfs/v1"
HEADERS   = {"Content-Type": "application/json",
             "digitransit-subscription-key": API_KEY}

cache = {}          # key → (timestamp, data)
TTL   = 15          # seconds

def gql(query):
    r = requests.post(API_URL, headers=HEADERS,
                      data=json.dumps({"query": query}))
    r.raise_for_status()
    return r.json()["data"]

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})   # ← EKLE

@app.get("/api/stop/<gtfs_id>")
def stop(gtfs_id):
    now = time.time()
    if (gtfs_id in cache) and (now - cache[gtfs_id][0] < TTL):
        return jsonify(cache[gtfs_id][1])

    q = f'''{{ stop(id:"{gtfs_id}") {{
              name
              stoptimesWithoutPatterns(numberOfDepartures:8) {{
                realtime realtimeArrival scheduledArrival serviceDay
                trip {{ route {{ shortName }} tripHeadsign }}
              }}
    }} }}'''
    data = gql(q)["stop"]
    cache[gtfs_id] = (now, data)
    return jsonify(data)

@app.get("/api/route/<gtfs_id>/vehicles")
def vehicles(gtfs_id):
    now = time.time()
    key = f"veh:{gtfs_id}"
    if (key in cache) and (now - cache[key][0] < TTL):
        return jsonify(cache[key][1])

    q = f'''{{ route(id:"{gtfs_id}") {{
              patterns {{ vehiclePositions {{
                lat lon heading lastUpdated
                trip {{ route {{ shortName }} tripHeadsign }}
              }} }}
    }} }}'''
    # flatten to one list
    raw = gql(q)["route"]["patterns"]
    data = [v for p in raw for v in p["vehiclePositions"]]
    cache[key] = (now, data)
    return jsonify(data)

@app.get("/api/route/<gtfs_id>/stops")
def route_stops(gtfs_id):
    """
    Return unique stops (name, lat, lon) on the first pattern of the route.
    Good enough for a quick map.
    """
    q = f'''{{ route(id:"{gtfs_id}") {{
              patterns(first:1) {{ stops {{ name lat lon gtfsId }} }}
    }} }}'''
    stops = gql(q)["route"]["patterns"][0]["stops"]
    # remove dup names
    seen, uniq = set(), []
    for s in stops:
        if s["gtfsId"] in seen: continue
        seen.add(s["gtfsId"])
        uniq.append({"name": s["name"], "lat": s["lat"], "lon": s["lon"]})
    return jsonify(uniq)

if __name__ == "__main__":
    app.run(debug=True, port=5000)