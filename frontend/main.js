/* -------------------------------------------------
   QRBus frontend – minute list + live map pin
   ------------------------------------------------- */

/* --------------- config ------------------------- */
const params  = new URLSearchParams(location.search);
const stopId  = params.get("id") || "Lappeenranta:205390";

/* if we run from file:// or :8000 dev server, talk to Flask on :5000 */
const localDev = location.hostname === "localhost" || location.hostname === "127.0.0.1";
const apiRoot  = localDev ? "http://127.0.0.1:5000" : location.origin;

/* quick map from shortName to full route gtfsId */
const routeMap = {
  "1": "Lappeenranta:1",
  "1X": "Lappeenranta:1X",
  "2": "Lappeenranta:2",
  "2H": "Lappeenranta:2H",
  "3": "Lappeenranta:3",
  "3K": "Lappeenranta:3K",
  "4": "Lappeenranta:4",
  "5": "Lappeenranta:5",
  "7": "Lappeenranta:7",
  "8": "Lappeenranta:8",
  "12": "Lappeenranta:12",
  "14": "Lappeenranta:14",
  "21": "Lappeenranta:21",
  "22": "Lappeenranta:22",
  "23": "Lappeenranta:23",
  "24": "Lappeenranta:24",
  "25": "Lappeenranta:25",
  "100": "Lappeenranta:100",
  "101": "Lappeenranta:101",
  "110": "Lappeenranta:110",
  "111": "Lappeenranta:111",
  "112": "Lappeenranta:112",
  "113": "Lappeenranta:113",
  "114": "Lappeenranta:114",
  "120": "Lappeenranta:120",
  "121": "Lappeenranta:121",
  "130": "Lappeenranta:130",
  "200": "Lappeenranta:200",
  "201": "Lappeenranta:201",
  "300": "Lappeenranta:300",
  "301": "Lappeenranta:301",
  "500": "Lappeenranta:500",
  "601": "Lappeenranta:601",
  "602": "Lappeenranta:602",
  "603": "Lappeenranta:603",
  "604": "Lappeenranta:604",
  "610": "Lappeenranta:610",
  "620": "Lappeenranta:620",
  "1001": "Lappeenranta:1001",
  "1003": "Lappeenranta:1003",
  "1011": "Lappeenranta:1011",
  "1012": "Lappeenranta:1012"
};

/* --------------- helpers ------------------------ */
const norm = txt =>
  (txt || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

const isCityLine = sn => /^[1-8][A-Za-z]?$/.test(sn || "");

/* --------------- time formatting---------------  */
function formatArrival(serviceDay, secondsFromMidnight) {
  const arrivalTimestamp = (serviceDay + secondsFromMidnight) * 1000;
  const now = Date.now();
  const diffMinutes = Math.round((arrivalTimestamp - now) / (1000 * 60));

  if (diffMinutes <= 0) return "⏳ now";
  else if (diffMinutes <= 20) return `⏱ ${diffMinutes} min`;
  else {
    const date = new Date(arrivalTimestamp);
    const hh = date.getHours().toString().padStart(2, "0");
    const mm = date.getMinutes().toString().padStart(2, "0");
    return `🕒 ${hh}:${mm}`;
  }
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

    const stopNorm = norm(data.name);
    const now = Math.floor(Date.now() / 1000);
    const list = [];
    const liveLines = new Set();

    data.stoptimesWithoutPatterns.forEach(st => {
      const sn   = st.trip.route.shortName;
      const head = st.trip.tripHeadsign || "";
      const headNorm = norm(head);

      if (!isCityLine(sn)) return;

      // direction filter
      if (
        (stopNorm.includes("yliopisto") && headNorm.includes("yliopisto")) ||
        (stopNorm.includes("matkakeskus") && headNorm.includes("matkakeskus"))
      ) return;

      const arrSec = st.realtime ? st.realtimeArrival : st.scheduledArrival;
      const mins   = Math.floor((st.serviceDay + arrSec - now) / 60);
      if (mins < 0 || mins > 120) return;

      list.push({
        line: sn,
        head,
        mins,
        seconds: arrSec,
        serviceDay: st.serviceDay,
        live: st.realtime
      });

      liveLines.add(sn);
    });

    list.sort((a, b) => a.mins - b.mins);
    renderList(list);

    // show first line
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
    const formattedTime = formatArrival(v.serviceDay, v.seconds);
    li.textContent = `${v.line} → ${v.head} — ${formattedTime}`;
    listEl.appendChild(li);
  });
}

async function loadVehicles(routeId) {
  try {
    const res = await fetch(`${apiRoot}/api/route/${routeId}/vehicles`);
    if (!res.ok) throw new Error(res.status);
    const list = await res.json();
    if (!list.length) return;

    const v = list[0];
    if (!busPin)
      busPin = L.marker([v.lat, v.lon]).addTo(map);
    else
      busPin.setLatLng([v.lat, v.lon]);
  } catch (err) {
    console.error("vehicle fetch", err);
  }
}

/* --------------- start ------------------------- */
loadStop();
setInterval(loadStop, 30000);  // update every 30 seconds