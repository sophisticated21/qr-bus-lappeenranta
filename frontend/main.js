/* -------------------------------------------------
   QRBus frontend – minute list + live map pin
   ------------------------------------------------- */

/* --------------- config ------------------------- */
const params  = new URLSearchParams(location.search);
const stopId  = params.get("id") || "Lappeenranta:205390";

/* if we run from file:// or :8000 dev server, talk to Flask on :5000 */
const localDev = location.hostname === "localhost" || location.hostname === "127.0.0.1";
const apiRoot  = localDev ? "http://127.0.0.1:5000" : location.origin;

/* quick map from shortName to full route gtfsId (city lines only) */
const routeMap = {
  "1": "Lappeenranta:1",
  "1X": "Lappeenranta:1X",
  "2": "Lappeenranta:2",
  "3": "Lappeenranta:3",
  "4": "Lappeenranta:4",
  "5": "Lappeenranta:5",
  "6": "Lappeenranta:6",
  "7": "Lappeenranta:7",
  "8": "Lappeenranta:8"
};

/* --------------- helpers ------------------------ */
const norm = txt =>
  (txt || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

const isCityLine = sn => /^[1-8][A-Za-z]?$/.test(sn || "");

function minsUntil(serviceDay, sec) {
  const diff = (serviceDay + sec) - Math.floor(Date.now() / 1000);
  return Math.floor(diff / 60);
}

/* --------------- DOM refs ---------------------- */
const stopNameEl = document.getElementById("stopName");
const listEl     = document.getElementById("times");

/* --------------- map setup --------------------- */
const map   = L.map("map").setView([61.0652, 28.095], 14);   // temp center
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);
let busPin = null;

/* --------------- main loop --------------------- */
async function loadStop() {
  try {
    const res = await fetch(`${apiRoot}/api/stop/${encodeURIComponent(stopId)}`);
    if (!res.ok) throw new Error(res.status);
    const data = await res.json();

    stopNameEl.textContent = data.name;
    if (data.lat && data.lon) map.setView([data.lat, data.lon], 14);

    const coreWord = norm(data.name).split(/[- ]/).pop();   // e.g. "yliopisto"

    const list = [];
    const liveLines = new Set();
    const now = Math.floor(Date.now() / 1000);

    data.stoptimesWithoutPatterns.forEach(st => {
      const sn   = st.trip.route.shortName;
      const head = st.trip.tripHeadsign || "";
      if (!isCityLine(sn)) return;                          // filter lines
      if (norm(head).includes(coreWord)) return;            // arrival row

      const arrSec = st.realtime ? st.realtimeArrival : st.scheduledArrival;
      const mins   = Math.floor((st.serviceDay + arrSec - now) / 60);
      if (mins < 0 || mins > 120) return;                   // keep 0-120 min

      list.push({ line: sn, head, mins, live: st.realtime });
      liveLines.add(sn);
    });

    list.sort((a, b) => a.mins - b.mins);
    renderList(list);

    /* update vehicle pin for first line (if mapping exists) */
    const firstLine = list[0]?.line;
    if (firstLine && routeMap[firstLine]) loadVehicles(routeMap[firstLine]);
  } catch (err) {
    stopNameEl.textContent = "Error loading stop";
    console.error(err);
  }
}

function renderList(arr) {
  listEl.innerHTML = "";
  arr.forEach(v => {
    const li = document.createElement("li");
    li.className = v.live ? "live" : "plan";
    li.textContent = `${v.line} → ${v.head} — ${v.mins} min ${v.live ? "⚡" : "⏰"}`;
    listEl.appendChild(li);
  });
}

async function loadVehicles(routeId) {
  try {
    const res = await fetch(`${apiRoot}/api/route/${routeId}/vehicles`);
    if (!res.ok) throw new Error(res.status);
    const list = await res.json();
    if (!list.length) return;

    const v = list[0];                       // first vehicle for now
    if (!busPin)
      busPin = L.marker([v.lat, v.lon]).addTo(map);
    else
      busPin.setLatLng([v.lat, v.lon]);
  } catch (err) {
    console.error("vehicle fetch", err);
  }
}

/* --------------- start ------------------------- */
loadStop();               // first run
setInterval(loadStop, 30000);   // refresh every 30 s