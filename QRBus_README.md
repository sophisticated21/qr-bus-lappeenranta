# QRBus – Lappeenranta Real-Time Stop Information

## Purpose
Scan a QR code at any bus stop in Lappeenranta and immediately see:
* **How many minutes** until the next city bus (lines 1 – 8)
* Whether the data is **live** (⚡) or scheduled (⏰)
* The **live position** of the approaching vehicle on a small map

## Key Features
| Feature | Details |
|---------|---------|
| Minute list | Live prediction (⚡) falls back to schedule (⏰) |
| Accessibility & bikes | Icons if the stop is wheelchair-accessible or bikes are allowed |
| Live vehicle pin | Updated every 15 s via Waltti real-time feed |
| Two languages | Turkish & English (?lang=tr\|en) |

## Technology Stack
| Layer      | Tooling | Notes |
|------------|---------|-------|
| **Backend**| Python 3.13 + Flask | /api endpoints, API key is hidden here |
| **Data**   | Waltti Routing v2 GTFS (GraphQL) | One subscription key covers all |
| **Frontend**| Static HTML + Vanilla JS + Leaflet | Lightweight, responsive |
| **QR Build**| `qrencode` CLI | Generates one PNG per stop from CSV |

## Repository Layout
```
qrbus/
├── backend/
│   ├── app.py            # Flask server
│   ├── cache.py          # Simple TTL cache helper
│   └── requirements.txt  # Flask, requests, python-dotenv
├── frontend/
│   ├── index.html        # Entry page (stop id comes via querystring)
│   ├── main.js           # API calls, countdown, map
│   └── style.css         # High-contrast UI
├── scripts/
│   └── gen_qr.py         # stops.csv → QR PNGs
├── stops.csv             # gtfsId,name,lat,lon (auto-generated)
└── README.md             # This file
```

## Developer Setup
```bash
# 1. clone
git clone https://github.com/<user>/qrbus.git
cd qrbus

# 2. optional venv
python3 -m venv env && source env/bin/activate

# 3. install deps
pip install -r backend/requirements.txt

# 4. set Waltti key
export WALTTI_KEY="<your_key>"

# 5. run server
python backend/app.py            # default http://127.0.0.1:5000
```

## REST-ish API
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/stop/<gtfsId> | Minute list JSON |
| GET | /api/route/<gtfsId>/vehicles | Live vehicle positions JSON |

### Sample Call
```bash
curl http://127.0.0.1:5000/api/stop/Lappeenranta:205390 | jq
```

## Deployment Plan
| Part      | Where                     | Cost |
|-----------|---------------------------|------|
| Frontend  | GitHub Pages / Netlify    | Free |
| Backend   | Fly.io / Render free tier | Free / €5 |
| Domain    | qrbus.fi                  | ~€10/yr |

## Roadmap / TODO
- [ ] Build backend/app.py with 15 s TTL cache
- [ ] Front-end countdown & auto-refresh (setInterval)
- [ ] QR generator script (scripts/gen_qr.py)
- [ ] i18n toggle (tr / en)
- [ ] Night-time empty-schedule message
