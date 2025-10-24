import csv
import requests

# Dosya yolu
file_path = "stops.txt"

# API rotası
api_base = "http://127.0.0.1:5000/api/stop/Lappeenranta:"

# Sonuçlar
working_stops = []
null_stops = []

# stops.txt'yi oku
with open(file_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        stop_id = row["stop_id"]
        stop_name = row["stop_name"]
        gtfs_id = f"Lappeenranta:{stop_id}"
        url = f"http://127.0.0.1:5000/api/stop/{gtfs_id}"
        
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200 and r.json():
                print(f"✅ {stop_name} ({stop_id}) → OK")
                working_stops.append((stop_id, stop_name))
            else:
                print(f"❌ {stop_name} ({stop_id}) → NULL")
                null_stops.append((stop_id, stop_name))
        except Exception as e:
            print(f"🔴 {stop_name} ({stop_id}) → ERROR: {e}")
            null_stops.append((stop_id, stop_name))

# Sonuçları kaydet
with open("working_stops.txt", "w", encoding="utf-8") as f:
    for sid, name in working_stops:
        f.write(f"{sid},{name}\n")

with open("null_stops.txt", "w", encoding="utf-8") as f:
    for sid, name in null_stops:
        f.write(f"{sid},{name}\n")

print(f"\nToplam {len(working_stops)} çalışıyor, {len(null_stops)} çalışmıyor.")