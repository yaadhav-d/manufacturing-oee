import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import mysql.connector
import plotly.graph_objects as go

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Manufacturing Live Dashboard",
    layout="wide"
)

st.title("🏭 Manufacturing Live Monitoring Dashboard")

# --------------------------------------------------
# DATABASE CONFIG (Railway + Streamlit Cloud SAFE)
# --------------------------------------------------
DB_CONFIG = {
    "host": st.secrets["DB_HOST"],
    "user": st.secrets["DB_USER"],
    "password": st.secrets["DB_PASSWORD"],
    "database": st.secrets["DB_NAME"],
    "port": int(st.secrets["DB_PORT"]),
    "ssl_disabled": False,
    "connection_timeout": 10
}

def get_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error:
        st.error("❌ Database connection failed")
        st.stop()

conn = get_connection()

# --------------------------------------------------
# SIDEBAR CONTROLS
# --------------------------------------------------
st.sidebar.title("🔧 Controls")

MACHINES = ["M-1", "M-2", "M-3", "M-4", "M-5"]

selected_machine = st.sidebar.selectbox("Select Machine", MACHINES)

refresh_rate = st.sidebar.slider(
    "Refresh rate (seconds)",
    min_value=2,
    max_value=10,
    value=5
)

pause_generation = st.sidebar.checkbox("⏸ Pause data generation")

# --------------------------------------------------
# INITIALIZE MACHINE STATE (REALISTIC BEHAVIOR)
# --------------------------------------------------
if "machine_state" not in st.session_state:
    st.session_state.machine_state = {}
    for m in MACHINES:
        st.session_state.machine_state[m] = {
            "temperature": np.random.uniform(65, 72),
            "vibration": np.random.uniform(2.5, 3.5),
            "units": np.random.randint(12, 16)
        }

# --------------------------------------------------
# LIVE DATA GENERATION (RATIONAL)
# --------------------------------------------------
def insert_live_data():
    cursor = conn.cursor()
    now = datetime.now()

    for m in MACHINES:
        state = st.session_state.machine_state[m]

        # Temperature drift
        temp_change = np.random.uniform(-0.3, 0.6)
        temperature = max(60, min(state["temperature"] + temp_change, 92))

        # Vibration wear + heat stress
        vib_change = np.random.uniform(-0.05, 0.12)
        if temperature > 80:
            vib_change += np.random.uniform(0.1, 0.25)

        vibration = max(1.5, min(state["vibration"] + vib_change, 9))

        # Stable output
        units = max(8, min(state["units"] + np.random.randint(-1, 2), 20))

        st.session_state.machine_state[m] = {
            "temperature": temperature,
            "vibration": vibration,
            "units": units
        }

        cursor.execute(
            """
            INSERT INTO machine_telemetry
            (timestamp, machine_id, temperature, vibration, units)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (now, m, round(temperature, 2), round(vibration, 2), units)
        )

    conn.commit()
    cursor.close()

# --------------------------------------------------
# FETCH DATA
# --------------------------------------------------
def fetch_data(machine_id):
    query = """
        SELECT timestamp, machine_id, temperature, vibration, units
        FROM machine_telemetry
        WHERE machine_id = %s
        ORDER BY timestamp DESC
        LIMIT 500
    """
    return pd.read_sql(query, conn, params=(machine_id,))

# --------------------------------------------------
# MAIN EXECUTION
# --------------------------------------------------
if not pause_generation:
    insert_live_data()

df = fetch_data(selected_machine)

if df.empty:
    st.warning("Waiting for live data...")
    time.sleep(refresh_rate)
    st.rerun()

df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp")
latest = df.iloc[-1]

# --------------------------------------------------
# KPI DERIVED LOGIC (REQUIREMENT COMPLIANT)
# --------------------------------------------------
TEMP_WARNING = 80
TEMP_CRITICAL = 85
VIB_WARNING = 6.5
VIB_CRITICAL = 7.5

if latest["temperature"] >= TEMP_CRITICAL or latest["vibration"] >= VIB_CRITICAL:
    machine_status = "CRITICAL"
elif latest["temperature"] >= TEMP_WARNING or latest["vibration"] >= VIB_WARNING:
    machine_status = "WARNING"
else:
    machine_status = "NORMAL"

if "critical_cycles" not in st.session_state:
    st.session_state.critical_cycles = 0

if machine_status == "CRITICAL":
    st.session_state.critical_cycles += 1

estimated_downtime_minutes = round(
    (st.session_state.critical_cycles * refresh_rate) / 60, 2
)

estimated_units_per_hour = round(
    (latest["units"] / refresh_rate) * 3600, 2
)

# --------------------------------------------------
# PRIMARY LIVE KPIs (TOP SECTION)
# --------------------------------------------------
st.subheader("📌 Primary Live KPIs")

k1, k2, k3 = st.columns(3)

with k1:
    st.metric("Estimated Downtime (mins)", estimated_downtime_minutes)

with k2:
    st.metric(
        "LIVE Vibration / Temperature",
        f"{latest['vibration']:.2f} mm/s | {latest['temperature']:.1f} °C"
    )

with k3:
    st.metric("Estimated Units / Hour", estimated_units_per_hour)

st.divider()

# --------------------------------------------------
# TEMPERATURE GAUGE
# --------------------------------------------------
def temperature_gauge(temp):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=temp,
        title={"text": "Temperature (°C)"},
        gauge={
            "axis": {"range": [0, 100]},
            "steps": [
                {"range": [0, 70], "color": "#4CAF50"},
                {"range": [70, 85], "color": "#FFC107"},
                {"range": [85, 100], "color": "#F44336"}
            ],
            "threshold": {"line": {"color": "black", "width": 4}, "value": 85}
        }
    ))
    fig.update_layout(height=300)
    return fig

# --------------------------------------------------
# LIVE STATUS
# --------------------------------------------------
st.subheader("📊 Live Machine Status")

c1, c2, c3 = st.columns([2, 1, 1])

with c1:
    st.plotly_chart(temperature_gauge(latest["temperature"]), use_container_width=True)

with c2:
    st.metric("Machine", latest["machine_id"])
    st.metric("Status", machine_status)

with c3:
    st.metric("Vibration (mm/s)", f"{latest['vibration']:.2f}")

st.divider()

# --------------------------------------------------
# VIBRATION TREND
# --------------------------------------------------
st.subheader("📈 LIVE Vibration Trend")
st.line_chart(df.set_index("timestamp")[["vibration"]])

st.divider()

# --------------------------------------------------
# DAILY PEAK TEMPERATURE
# --------------------------------------------------
today = datetime.now().date()
today_df = df[df["timestamp"].dt.date == today]

if not today_df.empty:
    peak = today_df.loc[today_df["temperature"].idxmax()]
    st.subheader("🔥 Today’s Peak Temperature")

    a, b, c = st.columns(3)
    a.metric("Peak Temp (°C)", peak["temperature"])
    b.metric("Units at Peak", int(peak["units"]))
    c.metric("Vibration at Peak", peak["vibration"])

    peak_time = peak["timestamp"]
    window_df = today_df[
        (today_df["timestamp"] >= peak_time - timedelta(minutes=10)) &
        (today_df["timestamp"] <= peak_time + timedelta(minutes=10))
    ]

    st.subheader("🕒 10-Minute Window Around Peak")
    st.line_chart(window_df.set_index("timestamp")[["temperature", "vibration"]])

st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# --------------------------------------------------
# AUTO REFRESH
# --------------------------------------------------
time.sleep(refresh_rate)
st.rerun()
