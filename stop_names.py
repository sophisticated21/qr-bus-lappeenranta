import csv, json, requests, time

API = "http://localhost:5000/api/stop/"
input_file = "stops.txt"

stop_map = {}

with open(input_file, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        stop_code = row["stop_id"]
        gtfs_id = f"Lappeenranta:{stop_code}"
        try:
            r = requests.get(API + gtfs_id, timeout=5)
            r.raise_for_status()
            data = r.json()
            stop_map[gtfs_id] = data.get("name", "???")
        except Exception as e:
            print(f"{gtfs_id} -> Hata: {e}")
            stop_map[gtfs_id] = None
        time.sleep(0.1)  

with open("live_stop_names.json", "w", encoding="utf-8") as out:
    json.dump(stop_map, out, ensure_ascii=False, indent=2)
