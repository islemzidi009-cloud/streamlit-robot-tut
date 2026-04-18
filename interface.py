import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
import paho.mqtt.client as mqtt
import json

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="IoT Robot Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Rajdhani', sans-serif;
    background-color: #0a0e1a;
    color: #c9d1e0;
}
section[data-testid="stSidebar"] {
    background: #0d1220;
    border-right: 1px solid #1e2d4a;
}
div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #111827, #1a2340);
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 0 20px rgba(0,180,255,0.05);
}
div[data-testid="metric-container"] label {
    color: #5b8fb9 !important;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.75rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}
div[data-testid="metric-container"] [data-testid="metric-value"] {
    color: #00d4ff !important;
    font-family: 'Share Tech Mono', monospace;
    font-size: 2rem;
}
.stButton > button {
    background: linear-gradient(135deg, #0f2540, #1a3a5c);
    color: #00d4ff;
    border: 1px solid #00d4ff44;
    border-radius: 10px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 1.6rem;
    padding: 16px;
    width: 100%;
    transition: all 0.2s ease;
    box-shadow: 0 0 10px rgba(0,212,255,0.1);
}
.stButton > button:hover {
    background: linear-gradient(135deg, #1a3a5c, #0f4080);
    border-color: #00d4ff;
    box-shadow: 0 0 20px rgba(0,212,255,0.4);
    color: #ffffff;
    transform: translateY(-2px);
}
.stButton > button:active {
    transform: translateY(0px);
    box-shadow: 0 0 30px rgba(0,212,255,0.6);
}
.alert-danger {
    background: linear-gradient(135deg, #2d0a0a, #3d1010);
    border: 1px solid #ff4444;
    border-radius: 10px;
    padding: 12px 18px;
    color: #ff8888;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.85rem;
    margin: 6px 0;
    animation: pulse-red 2s infinite;
}
.alert-ok {
    background: linear-gradient(135deg, #0a2d0a, #103d10);
    border: 1px solid #44ff88;
    border-radius: 10px;
    padding: 12px 18px;
    color: #88ffaa;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.85rem;
    margin: 6px 0;
}
.badge {
    display: inline-block;
    border-radius: 8px;
    padding: 5px 16px;
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.95rem;
    font-weight: bold;
}
.badge-dark   { background:#1a1a2e; border:1px solid #4a4aff; color:#aaaaff; }
.badge-light  { background:#1a2a1a; border:1px solid #44ff88; color:#88ffaa; }
.badge-yes    { background:#2d0a0a; border:1px solid #ff4444; color:#ff8888;
                animation: pulse-red 1.5s infinite; }
.badge-no     { background:#0a1a2d; border:1px solid #224466; color:#4488aa; }
.badge-loud   { background:#2d1a0a; border:1px solid #ffaa44; color:#ffcc88;
                animation: pulse-orange 1.5s infinite; }
.badge-quiet  { background:#0a1a2d; border:1px solid #224466; color:#4488aa; }
@keyframes pulse-red    { 0%,100%{box-shadow:0 0 4px rgba(255,68,68,.3)} 50%{box-shadow:0 0 14px rgba(255,68,68,.8)} }
@keyframes pulse-orange { 0%,100%{box-shadow:0 0 4px rgba(255,170,68,.3)} 50%{box-shadow:0 0 14px rgba(255,170,68,.8)} }
.section-title {
    font-family: 'Share Tech Mono', monospace;
    color: #00d4ff;
    font-size: 0.8rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    border-bottom: 1px solid #1e3a5f;
    padding-bottom: 8px;
    margin-bottom: 16px;
    margin-top: 24px;
}
.status-online  { display:inline-block; background:#003a1a; border:1px solid #00ff88;
                  border-radius:20px; padding:3px 12px; color:#00ff88;
                  font-family:'Share Tech Mono',monospace; font-size:0.75rem; }
.status-offline { display:inline-block; background:#2d0a0a; border:1px solid #ff4444;
                  border-radius:20px; padding:3px 12px; color:#ff4444;
                  font-family:'Share Tech Mono',monospace; font-size:0.75rem; }
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  
# ─────────────────────────────────────────────
FIREBASE_DB_URL   = "https://robot-fcc6c-default-rtdb.firebaseio.com"
FIREBASE_KEY_FILE = "serviceAccountKey.json"  

MQTT_BROKER  = "10.99.219.54"   
MQTT_PORT    = 1883
TOPIC_ROBOT  = "esp/dht"


# ─────────────────────────────────────────────
#  FIREBASE
# ─────────────────────────────────────────────
@st.cache_resource
def init_firebase():
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(FIREBASE_KEY_FILE)
            firebase_admin.initialize_app(cred, {"databaseURL": FIREBASE_DB_URL})
        return True
    except Exception:
        return False


def get_sensor():
    try:
        return db.reference("sensor").get() or {}
    except Exception:
        return {}


# ─────────────────────────────────────────────
#  MQTT
# ─────────────────────────────────────────────
@st.cache_resource
def get_mqtt():
    client = mqtt.Client()
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        return client, True
    except Exception:
        return client, False


def send_cmd(cmd: str):
    client, ok = get_mqtt()
    if not ok:
        st.error("❌ MQTT غير متصل")
        return
    client.publish(TOPIC_ROBOT, json.dumps({"cmd": cmd, "ts": int(time.time()*1000)}))


# ─────────────────────────────────────────────
#  SESSION HISTORY
# ─────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []


def push_history(s):
    st.session_state.history.append({**s, "time": datetime.now()})
    if len(st.session_state.history) > 300:
        st.session_state.history = st.session_state.history[-300:]


# ─────────────────────────────────────────────
#  ALERTS
# ─────────────────────────────────────────────
def check_alerts(s):
    a = []
    if s.get("temp") is not None and float(s["temp"]) > 40:
        a.append(f"🌡️ Température élevée : {s['temp']} °C")
    if s.get("hum") is not None and float(s["hum"]) > 85:
        a.append(f"💧 Humidité élevée : {s['hum']} %")
    if str(s.get("motion","NO")).upper() == "YES":
        a.append("🚶 Mouvement détecté !")
    if str(s.get("sound","QUIET")).upper() == "LOUD":
        a.append("🔊 Son fort détecté !")
    if str(s.get("light","LIGHT")).upper() == "DARK":
        a.append("💡 Environnement sombre")
    return a


# ─────────────────────────────────────────────
#  CHART helper
# ─────────────────────────────────────────────
BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(13,18,32,0.8)",
    font=dict(color="#8899bb", family="Share Tech Mono"),
    margin=dict(l=44, r=10, t=36, b=40),
    xaxis=dict(gridcolor="#1e2d4a", linecolor="#1e2d4a"),
    yaxis=dict(gridcolor="#1e2d4a", linecolor="#1e2d4a"),
    height=210,
)


def num_chart(history, key, color, title, unit=""):
    rows  = [(h["time"], h[key]) for h in history if h.get(key) is not None]
    times = [r[0] for r in rows]
    vals  = [r[1] for r in rows]
    fig   = go.Figure()
    if vals:
        rgba = color.replace("rgb(","rgba(").replace(")",",0.09)")
        fig.add_trace(go.Scatter(
            x=times, y=vals, mode="lines",
            line=dict(color=color, width=2),
            fill="tozeroy", fillcolor=rgba,
            hovertemplate=f"%{{y:.1f}}{unit}<extra></extra>",
        ))
    fig.update_layout(title=dict(text=title, font=dict(color=color,size=13)), **BASE_LAYOUT)
    return fig


# ─────────────────────────────────────────────
#  RENDER
# ─────────────────────────────────────────────
firebase_ok = init_firebase()
_, mqtt_ok  = get_mqtt()

# Sidebar
with st.sidebar:
    st.markdown("## 🤖 IoT Robot")
    st.markdown("---")
    st.markdown(
        f'Firebase <span class="{"status-online" if firebase_ok else "status-offline"}">{"connecté" if firebase_ok else "erreur"}</span>',
        unsafe_allow_html=True)
    st.markdown(
        f'MQTT <span class="{"status-online" if mqtt_ok else "status-offline"}">{"connecté" if mqtt_ok else "hors ligne"}</span>',
        unsafe_allow_html=True)
    st.markdown("---")
    auto_refresh = st.checkbox("🔄 Auto-refresh (5s)", value=True)
    st.markdown("---")
    st.markdown("DB: robot-fcc6c")
    st.markdown("Node: /sensor")
    st.code(f"hum | light | motion\nsound | temp", language="text")

# Header
st.markdown("""
<div style="display:flex;align-items:baseline;gap:18px;margin-bottom:22px;">
  <span style="font-family:'Share Tech Mono',monospace;font-size:1.9rem;color:#00d4ff;letter-spacing:.08em;">
    ◈ IOT CONTROL CENTER
  </span>
  <span style="font-family:'Share Tech Mono',monospace;font-size:.75rem;color:#3a5a7a;">
    robot-fcc6c · /sensor
  </span>
</div>
""", unsafe_allow_html=True)

# Fetch
sensor = get_sensor() if firebase_ok else {}
if sensor:
    push_history(sensor)

temp   = sensor.get("temp",   "--")
hum    = sensor.get("hum",    "--")
light  = str(sensor.get("light",  "LIGHT")).upper()
motion = str(sensor.get("motion", "NO")).upper()
sound  = str(sensor.get("sound",  "QUIET")).upper()

# ── Sensor cards ──────────────────────────────
st.markdown('<div class="section-title">◆ Capteurs temps réel</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🌡️ Température", f"{temp} °C")
c2.metric("💧 Humidité",    f"{hum} %")

with c3:
    st.markdown("💡 Lumière")
    cls = "badge badge-dark" if light == "DARK" else "badge badge-light"
    st.markdown(f'<div class="{cls}">{"🌑 DARK" if light=="DARK" else "☀️ LIGHT"}</div>', unsafe_allow_html=True)

with c4:
    st.markdown("🚶 Mouvement")
    cls = "badge badge-yes" if motion == "YES" else "badge badge-no"
    st.markdown(f'<div class="{cls}">{"🚶 YES" if motion=="YES" else "🛑 NO"}</div>', unsafe_allow_html=True)

with c5:
    st.markdown("🔊 Son")
    cls = "badge badge-loud" if sound == "LOUD" else "badge badge-quiet"
    st.markdown(f'<div class="{cls}">{"🔊 LOUD" if sound=="LOUD" else "🔇 QUIET"}</div>', unsafe_allow_html=True)

# ── Alerts ────────────────────────────────────
st.markdown('<div class="section-title">◆ Alertes</div>', unsafe_allow_html=True)
alerts = check_alerts(sensor)
if alerts:
    for a in alerts:
        st.markdown(f'<div class="alert-danger">⚠️ {a}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="alert-ok">✅ Tous les capteurs sont normaux</div>', unsafe_allow_html=True)

# ── Charts ────────────────────────────────────
st.markdown('<div class="section-title">◆ Historique session</div>', unsafe_allow_html=True)
history = st.session_state.history

col1, col2 = st.columns(2)
col1.plotly_chart(num_chart(history, "temp", "rgb(255,100,80)", "Température (°C)", " °C"), use_container_width=True)
col2.plotly_chart(num_chart(history, "hum",  "rgb(0,180,255)",  "Humidité (%)",     " %"),  use_container_width=True)

# Boolean events timeline
if len(history) > 1:
    df = pd.DataFrame(history)
    df["motion_n"] = (df["motion"].str.upper() == "YES").astype(int)
    df["sound_n"]  = (df["sound"].str.upper()  == "LOUD").astype(int)
    df["light_n"]  = (df["light"].str.upper()  == "DARK").astype(int)
    fig = go.Figure()
    for col_name, color, label in [
        ("motion_n", "#ff4444", "🚶 Motion"),
        ("sound_n",  "#ffaa44", "🔊 Sound LOUD"),
        ("light_n",  "#4466ff", "🌑 Light DARK"),
    ]:
        fig.add_trace(go.Scatter(x=df["time"], y=df[col_name], mode="lines",
                                  name=label, line=dict(color=color, width=2)))
    fig.update_layout(
        title=dict(text="Événements — Motion / Son / Lumière", font=dict(color="#aabbdd",size=13)),
        yaxis=dict(tickvals=[0,1], ticktext=["OFF","ON"], gridcolor="#1e2d4a", linecolor="#1e2d4a"),
        xaxis=dict(gridcolor="#1e2d4a", linecolor="#1e2d4a"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,18,32,0.8)",
        font=dict(color="#8899bb", family="Share Tech Mono"),
        margin=dict(l=54,r=10,t=36,b=40), height=200,
        legend=dict(orientation="h", y=1.18),
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Robot Control ─────────────────────────────
st.markdown('<div class="section-title">◆ Contrôle Robot</div>', unsafe_allow_html=True)

_, mc, _ = st.columns([2, 1, 2])
with mc:
    if st.button("⬆️", key="fwd"):
        send_cmd("FORWARD"); st.toast("⬆️ AVANT", icon="✅")

lc, sc, rc = st.columns(3)
with lc:
    if st.button("⬅️", key="lft"):
        send_cmd("LEFT"); st.toast("⬅️ GAUCHE", icon="✅")
with sc:
    if st.button("⏹", key="stp"):
        send_cmd("STOP"); st.toast("⏹ STOP", icon="🛑")
with rc:
    if st.button("➡️", key="rgt"):
        send_cmd("RIGHT"); st.toast("➡️ DROITE", icon="✅")

_, mc2, _ = st.columns([2, 1, 2])
with mc2:
    if st.button("⬇️", key="bck"):
        send_cmd("BACKWARD"); st.toast("⬇️ ARRIÈRE", icon="✅")

# Timestamp
st.markdown(f"""
<div style="font-family:'Share Tech Mono',monospace;color:#2a4060;
            font-size:.72rem;text-align:right;margin-top:28px;">
  Mis à jour : {datetime.now().strftime("%Y-%m-%d  %H:%M:%S")}
</div>""", unsafe_allow_html=True)

# Auto-refresh
# ─────────────────────────────────────────────
#  LIVE UPDATE FIX (IMPORTANT)
# ─────────────────────────────────────────────
import time
time.sleep(3)
st.rerun()

sensor = get_sensor() if firebase_ok else {}

if sensor:
    push_history(sensor)